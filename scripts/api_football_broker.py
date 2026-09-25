"""Shared, cache-aware access to the API-Football HTTP API."""
from __future__ import annotations

import json
import os
import random
import sqlite3
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from api_football_raw_archive import (
    archive_enabled_from_env,
    archive_response,
    archive_root_from_env,
    read_archived_response,
)

API_BASE = "https://v3.football.api-sports.io"


class ApiFootballBrokerError(RuntimeError):
    """Base class for broker failures."""


class ApiFootballBudgetExceeded(ApiFootballBrokerError):
    """Raised before a provider request when the configured hard cap is reached."""


class ApiFootballProviderError(ApiFootballBrokerError):
    """Raised for transport, HTTP, or API-Football JSON errors."""


def _utc_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def normalize_path(path: str) -> str:
    path = str(path or "")
    return path if path.startswith("/") else "/" + path


def normalize_params(params=None) -> tuple[tuple[str, str], ...]:
    """Return deterministic query pairs without dropping semantic parameters."""
    pairs = []
    for key, value in (params or {}).items():
        if isinstance(value, (list, tuple)):
            value = tuple(_jsonable(x) for x in value)
        else:
            value = _jsonable(value)
        pairs.append((str(key), json.dumps(value, sort_keys=True, separators=(",", ":"))
                      if isinstance(value, (dict, list, tuple)) else str(value)))
    return tuple(sorted(pairs))


def request_key(method: str, path: str, params=None) -> str:
    return json.dumps(
        [str(method or "GET").upper(), normalize_path(path), normalize_params(params)],
        sort_keys=True, separators=(",", ":"),
    )


def _default_cache_path() -> Path:
    return Path(os.getenv(
        "API_FOOTBALL_CACHE_PATH",
        str(Path(tempfile.gettempdir()) / "football-data-bridge" / "api_football_cache.sqlite3"),
    ))


class ApiFootballBroker:
    """Reusable API-Football GET broker.

    A custom transport receives ``(path, params, headers, timeout)`` and may
    return a JSON payload, ``(status, headers, payload)``, or
    ``(status, headers, raw_json_bytes)``.

    Successful *real* provider responses can additionally be copied into the
    Stage80 raw archive. The archive is disabled unless ``archive_dir`` is passed
    or ``API_FOOTBALL_ARCHIVE_DIR`` is configured. Cache hits never create fake
    provider observations and archive failures never block primary collection.
    """

    def __init__(self, *, transport=None, cache_path=None, archive_dir=None,
                 max_real_calls=None, default_ttl_seconds=300, attempts=3, sleep=None):
        self.transport = transport or self._transport
        self.cache_path = Path(cache_path) if cache_path else _default_cache_path()
        self.archive_dir = Path(archive_dir) if archive_dir is not None else archive_root_from_env()
        self.archive_enabled = self.archive_dir is not None or archive_enabled_from_env()
        self.max_real_calls = (
            int(max_real_calls) if max_real_calls is not None
            else self._env_limit()
        )
        self.default_ttl_seconds = float(default_ttl_seconds)
        self.attempts = max(1, int(attempts))
        self._sleep = sleep or time.sleep
        self._memory = {}
        self._lock = Lock()
        self._stats = {
            "logical_requests": 0, "real_api_calls": 0,
            "memory_cache_hits": 0, "disk_cache_hits": 0,
            "cache_misses": 0, "retries": 0, "errors": 0,
            "budget_rejections": 0, "real_calls_by_path": {},
            "archive_observations": 0, "archive_blob_dedup_hits": 0,
            "archive_manifest_dedup_hits": 0, "archive_errors": 0,
            "archive_read_hits": 0, "archive_read_misses": 0,
            "archive_read_errors": 0,
            "archive_backend": None,
            "archive_last_observation_path": None,
            "archive_last_blob_path": None,
            "archive_last_payload_sha256": None,
        }
        self._rate_limit = {}

    @staticmethod
    def _env_limit():
        raw = os.getenv("API_FOOTBALL_MAX_REAL_CALLS", "").strip()
        return int(raw) if raw else None

    def _connect(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.cache_path))
        conn.execute(
            """CREATE TABLE IF NOT EXISTS api_football_cache (
                request_key TEXT PRIMARY KEY, path TEXT NOT NULL,
                normalized_params TEXT NOT NULL, fetched_at_utc TEXT NOT NULL,
                expires_at_utc REAL NOT NULL, payload TEXT NOT NULL
            )"""
        )
        return conn

    def _disk_get(self, key, now):
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT fetched_at_utc, expires_at_utc, payload FROM api_football_cache WHERE request_key=?",
                (key,),
            ).fetchone()
            if not row:
                return None
            if float(row[1]) <= now:
                conn.execute("DELETE FROM api_football_cache WHERE request_key=?", (key,))
                conn.commit()
                return None
            return row
        finally:
            conn.close()

    def _disk_put(self, key, path, params, payload, fetched, expires):
        conn = self._connect()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO api_football_cache
                (request_key, path, normalized_params, fetched_at_utc, expires_at_utc, payload)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (key, path, json.dumps(normalize_params(params)),
                 datetime.fromtimestamp(fetched, timezone.utc).isoformat(),
                 expires, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            )
            conn.commit()
        finally:
            conn.close()

    def _archive_success(self, key, path, params, payload, fetched):
        if not self.archive_enabled:
            return
        try:
            result = archive_response(
                root=self.archive_dir,
                request_key=key,
                path=path,
                normalized_params=normalize_params(params),
                payload=payload,
                fetched_at=fetched,
            )
            self._stats["archive_backend"] = result.get("backend")
            self._stats["archive_last_observation_path"] = result.get("observation_path")
            self._stats["archive_last_blob_path"] = result.get("blob_path")
            self._stats["archive_last_payload_sha256"] = result.get("payload_sha256")
            if result.get("manifest_appended"):
                self._stats["archive_observations"] += 1
            else:
                self._stats["archive_manifest_dedup_hits"] += 1
            if not result.get("blob_created"):
                self._stats["archive_blob_dedup_hits"] += 1
        except Exception:
            # Archive storage is secondary evidence storage. A bad/missing mount
            # must be visible in telemetry but must not discard a valid football
            # provider response needed by operational stages.
            self._stats["archive_errors"] += 1

    @staticmethod
    def _transport(path, params, headers, timeout):
        query = urllib.parse.urlencode(params or {}, doseq=True)
        url = API_BASE + normalize_path(path) + (("?" + query) if query else "")
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, dict(response.headers), json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                body = body.decode("utf-8", errors="replace")
            return exc.code, dict(exc.headers or {}), body

    def _call_transport(self, path, params):
        result = self.transport(
            path, dict(params or {}),
            {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "").strip(),
             "User-Agent": "football-data-bridge/api-broker"},
            30,
        )
        if isinstance(result, tuple) and len(result) == 3:
            return result
        return 200, {}, result

    def get(self, path, params=None, *, ttl_seconds=None, force_refresh=False, archive_first=False):
        path = normalize_path(path)
        params = dict(params or {})
        key = request_key("GET", path, params)
        self._stats["logical_requests"] += 1
        now = _utc_timestamp()
        ttl = self.default_ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        if not force_refresh and ttl > 0:
            item = self._memory.get(key)
            if item and item[0] + ttl > now and item[1] > now:
                self._stats["memory_cache_hits"] += 1
                return item[2]
            item = self._disk_get(key, now)
            if item is not None:
                fetched, expires, payload = item
                fetched = datetime.fromisoformat(fetched).timestamp()
                if fetched + ttl > now and float(expires) > now:
                    self._memory[key] = (fetched, float(expires), json.loads(payload))
                    self._stats["disk_cache_hits"] += 1
                    return self._memory[key][2]
        self._stats["cache_misses"] += 1
        with self._lock:
            # Another thread may have populated either cache while this
            # request waited for the provider lock.
            if not force_refresh and ttl > 0:
                item = self._memory.get(key)
                if item and item[0] + ttl > _utc_timestamp() and item[1] > _utc_timestamp():
                    self._stats["memory_cache_hits"] += 1
                    return item[2]
                item = self._disk_get(key, _utc_timestamp())
                if item is not None:
                    fetched, expires, payload = item
                    fetched = datetime.fromisoformat(fetched).timestamp()
                    if fetched + ttl > _utc_timestamp() and float(expires) > _utc_timestamp():
                        self._memory[key] = (fetched, float(expires), json.loads(payload))
                        self._stats["disk_cache_hits"] += 1
                        return self._memory[key][2]
            if archive_first and not force_refresh:
                try:
                    payload = read_archived_response(key)
                except Exception:
                    self._stats["archive_read_errors"] += 1
                    payload = None
                if payload is not None:
                    fetched = _utc_timestamp()
                    expires = fetched + max(0.0, ttl)
                    if ttl > 0:
                        self._memory[key] = (fetched, expires, payload)
                        self._disk_put(key, path, params, payload, fetched, expires)
                    self._stats["archive_read_hits"] += 1
                    return payload
                self._stats["archive_read_misses"] += 1

            if not os.getenv("API_FOOTBALL_KEY", "").strip():
                raise ApiFootballBrokerError("API_FOOTBALL_KEY is missing")
            if self.max_real_calls is not None and self._stats["real_api_calls"] >= self.max_real_calls:
                self._stats["budget_rejections"] += 1
                raise ApiFootballBudgetExceeded(
                    f"API-Football hard cap reached: {self._stats['real_api_calls']}/{self.max_real_calls}"
                )
            last_error = None
            for attempt in range(1, self.attempts + 1):
                try:
                    if self.max_real_calls is not None and self._stats["real_api_calls"] >= self.max_real_calls:
                        self._stats["budget_rejections"] += 1
                        raise ApiFootballBudgetExceeded(
                            f"API-Football hard cap reached: {self._stats['real_api_calls']}/{self.max_real_calls}"
                        )
                    self._stats["real_api_calls"] += 1
                    by_path = self._stats["real_calls_by_path"]
                    by_path[path] = by_path.get(path, 0) + 1
                    status, headers, payload = self._call_transport(path, params)
                    self._rate_limit.update({
                        k.lower(): v for k, v in headers.items()
                        if k.lower() in {"x-ratelimit-remaining", "x-ratelimit-limit", "retry-after"}
                    })
                    transient = status == 429 or status >= 500
                    if status >= 400:
                        if transient and attempt < self.attempts:
                            self._retry_delay(attempt, headers)
                            continue
                        raise ApiFootballProviderError(f"API-Football HTTP {status} for {path}")
                    if not isinstance(payload, dict):
                        raise ApiFootballProviderError(f"API-Football returned non-JSON object for {path}")
                    if payload.get("errors"):
                        raise ApiFootballProviderError(f"API-Football {path}: {payload['errors']}")
                    fetched = _utc_timestamp()
                    expires = fetched + max(0.0, ttl)
                    self._memory[key] = (fetched, expires, payload)
                    self._disk_put(key, path, params, payload, fetched, expires)
                    self._archive_success(key, path, params, payload, fetched)
                    return payload
                except (ApiFootballProviderError, OSError, TimeoutError, urllib.error.URLError) as exc:
                    last_error = exc
                    self._stats["errors"] += 1
                    if attempt < self.attempts and not (
                        isinstance(exc, ApiFootballProviderError) and "HTTP 429" not in str(exc)
                    ):
                        self._retry_delay(attempt, {})
                        continue
                    raise
            raise last_error or ApiFootballProviderError(f"API-Football request failed: {path}")

    def _retry_delay(self, attempt, headers):
        self._stats["retries"] += 1
        raw = (headers or {}).get("Retry-After") or (headers or {}).get("retry-after")
        try:
            delay = min(30.0, max(0.0, float(raw)))
        except (TypeError, ValueError):
            delay = min(30.0, attempt * 0.5 + random.random() * 0.1)
        self._sleep(delay)

    def stats(self):
        out = json.loads(json.dumps(self._stats))
        out["rate_limit"] = dict(self._rate_limit)
        out["archive_enabled"] = self.archive_enabled
        return out


_DEFAULT_BROKER = None


def get_broker():
    global _DEFAULT_BROKER
    if _DEFAULT_BROKER is None:
        _DEFAULT_BROKER = ApiFootballBroker()
    return _DEFAULT_BROKER


def api_get(path, params=None, **kwargs):
    return get_broker().get(path, params, **kwargs)
