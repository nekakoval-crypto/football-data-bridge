"""Content-addressed raw API-Football response archive for PBK Stage80.

The archive receives already-successful provider responses from the shared broker.
It never performs network I/O. Payload blobs are canonical JSON compressed with
GZip and addressed by SHA-256; an append-only JSONL manifest records observation
provenance without API keys or HTTP headers.

Persistence is intentionally storage-configurable. Set API_FOOTBALL_ARCHIVE_DIR
to a durable mounted/off-site-backed location. Without that variable the archive
is disabled rather than pretending a temporary CI filesystem is durable.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

ARCHIVE_VERSION = "PBK_STAGE80_RAW_API_ARCHIVE_V1"
_LOCK = Lock()


def archive_root_from_env():
    raw = os.getenv("API_FOOTBALL_ARCHIVE_DIR", "").strip()
    return Path(raw) if raw else None


def canonical_payload_bytes(payload):
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def payload_sha256(payload):
    return hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()


def utc_iso(timestamp):
    return datetime.fromtimestamp(float(timestamp), timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def observation_id(request_key, fetched_at_utc, payload_hash):
    raw = f"{request_key}|{fetched_at_utc}|{payload_hash}|{ARCHIVE_VERSION}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def archive_response(*, root, request_key, path, normalized_params, payload, fetched_at):
    """Persist one successful real-provider observation.

    The same payload may be observed repeatedly. Its blob is deduplicated by hash,
    while each provider observation receives its own manifest record because the
    fact that PBK observed the same data at a later time can itself be important.
    """
    root = Path(root)
    raw = canonical_payload_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    fetched_at_utc = utc_iso(fetched_at)
    obs_id = observation_id(request_key, fetched_at_utc, digest)
    relative_blob = Path("blobs") / digest[:2] / f"{digest}.json.gz"
    blob_path = root / relative_blob
    manifest_path = root / "manifest.jsonl"

    record = {
        "archive_version": ARCHIVE_VERSION,
        "observation_id": obs_id,
        "provider": "api-football",
        "method": "GET",
        "path": str(path),
        "normalized_params": list(normalized_params),
        "request_key_sha256": hashlib.sha256(str(request_key).encode("utf-8")).hexdigest(),
        "fetched_at_utc": fetched_at_utc,
        "payload_sha256": digest,
        "payload_bytes": len(raw),
        "blob_path": relative_blob.as_posix(),
    }

    with _LOCK:
        root.mkdir(parents=True, exist_ok=True)
        blob_created = False
        if not blob_path.exists():
            _atomic_write(blob_path, gzip.compress(raw, compresslevel=6, mtime=0))
            blob_created = True

        # Observation IDs are deterministic. Avoid a duplicate manifest row if a
        # caller retries archive persistence for the exact same successful fetch.
        duplicate_observation = False
        if manifest_path.exists():
            needle = f'"observation_id":"{obs_id}"'
            with manifest_path.open(encoding="utf-8") as stream:
                duplicate_observation = any(needle in line.replace(" ", "") for line in stream)
        if not duplicate_observation:
            with manifest_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

    return {
        "observation_id": obs_id,
        "payload_sha256": digest,
        "blob_path": relative_blob.as_posix(),
        "blob_created": blob_created,
        "manifest_appended": not duplicate_observation,
    }
