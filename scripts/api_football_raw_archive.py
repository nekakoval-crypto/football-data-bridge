"""Content-addressed raw API-Football response archive for PBK Stage80.

Successful real provider responses are copied into durable evidence storage.
Two backends are supported:

1. Local/mounted storage via API_FOOTBALL_ARCHIVE_DIR.
2. S3-compatible object storage (Cloudflare R2 in production) via:
   PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID
   PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY
   PBK_RAW_ARCHIVE_S3_ENDPOINT
   PBK_RAW_ARCHIVE_S3_BUCKET

The archive never performs API-Football network I/O itself. It receives an
already-successful provider payload from the shared broker. Provider API keys and
HTTP headers are never persisted.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

ARCHIVE_VERSION = "PBK_STAGE80_RAW_API_ARCHIVE_V2_S3"
_LOCK = Lock()

S3_ENV = {
    "access_key_id": "PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID",
    "secret_access_key": "PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY",
    "endpoint": "PBK_RAW_ARCHIVE_S3_ENDPOINT",
    "bucket": "PBK_RAW_ARCHIVE_S3_BUCKET",
}


def archive_root_from_env():
    raw = os.getenv("API_FOOTBALL_ARCHIVE_DIR", "").strip()
    return Path(raw) if raw else None


def s3_config_from_env():
    values = {key: os.getenv(env, "").strip() for key, env in S3_ENV.items()}
    if not any(values.values()):
        return None
    missing = [S3_ENV[key] for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("Incomplete raw archive S3 configuration: " + ", ".join(missing))
    return {
        **values,
        "prefix": os.getenv("PBK_RAW_ARCHIVE_S3_PREFIX", "api-football-raw").strip().strip("/") or "api-football-raw",
        "region": os.getenv("PBK_RAW_ARCHIVE_S3_REGION", "auto").strip() or "auto",
    }


def archive_enabled_from_env():
    if archive_root_from_env() is not None:
        return True
    try:
        return s3_config_from_env() is not None
    except RuntimeError:
        # Partial configuration is considered enabled so the broker exposes
        # archive_errors instead of silently pretending archival is disabled.
        return True


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


def _record(*, request_key, path, normalized_params, payload, fetched_at):
    raw = canonical_payload_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    fetched_at_utc = utc_iso(fetched_at)
    obs_id = observation_id(request_key, fetched_at_utc, digest)
    return raw, {
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
    }


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def _archive_local(*, root, raw, record):
    root = Path(root)
    digest = record["payload_sha256"]
    relative_blob = Path("blobs") / digest[:2] / f"{digest}.json.gz"
    blob_path = root / relative_blob
    manifest_path = root / "manifest.jsonl"
    record = {**record, "blob_path": relative_blob.as_posix(), "storage_backend": "LOCAL"}

    with _LOCK:
        root.mkdir(parents=True, exist_ok=True)
        blob_created = False
        if not blob_path.exists():
            _atomic_write(blob_path, gzip.compress(raw, compresslevel=6, mtime=0))
            blob_created = True

        duplicate_observation = False
        if manifest_path.exists():
            needle = f'"observation_id":"{record["observation_id"]}"'
            with manifest_path.open(encoding="utf-8") as stream:
                duplicate_observation = any(needle in line.replace(" ", "") for line in stream)
        if not duplicate_observation:
            with manifest_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

    return {
        "backend": "LOCAL",
        "observation_id": record["observation_id"],
        "payload_sha256": digest,
        "blob_path": relative_blob.as_posix(),
        "blob_created": blob_created,
        "manifest_appended": not duplicate_observation,
    }


def _s3_client(config):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for S3/R2 raw archive storage") from exc
    return boto3.client(
        "s3",
        endpoint_url=config["endpoint"],
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        region_name=config["region"],
    )


def _not_found(exc):
    response = getattr(exc, "response", {}) or {}
    code = str((response.get("Error") or {}).get("Code") or "")
    status = int((response.get("ResponseMetadata") or {}).get("HTTPStatusCode") or 0)
    return code in {"404", "NoSuchKey", "NotFound"} or status == 404


def _exists(client, bucket, key):
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as exc:
        if _not_found(exc):
            return False
        raise


def _request_index_key(config, request_key_sha256):
    return f"{config['prefix']}/request-index/{request_key_sha256[:2]}/{request_key_sha256}.json"


def _archive_s3(*, config, raw, record, client=None):
    client = client or _s3_client(config)
    prefix = config["prefix"]
    digest = record["payload_sha256"]
    date = record["fetched_at_utc"][:10].replace("-", "/")
    blob_key = f"{prefix}/blobs/sha256/{digest[:2]}/{digest}.json.gz"
    observation_key = f"{prefix}/observations/{date}/{record['observation_id']}.json"
    record = {
        **record,
        "storage_backend": "S3",
        "bucket": config["bucket"],
        "blob_key": blob_key,
        "observation_key": observation_key,
    }

    blob_created = False
    if not _exists(client, config["bucket"], blob_key):
        client.put_object(
            Bucket=config["bucket"],
            Key=blob_key,
            Body=gzip.compress(raw, compresslevel=6, mtime=0),
            ContentType="application/gzip",
            Metadata={"payload-sha256": digest, "archive-version": ARCHIVE_VERSION},
        )
        blob_created = True

    observation_created = False
    if not _exists(client, config["bucket"], observation_key):
        body = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        client.put_object(
            Bucket=config["bucket"],
            Key=observation_key,
            Body=body,
            ContentType="application/json",
            Metadata={"observation-id": record["observation_id"], "payload-sha256": digest},
        )
        observation_created = True

    # Mutable request pointer for archive-first reads. Immutable observation/blob
    # objects remain the source of truth; this pointer only avoids scanning R2.
    index_key = _request_index_key(config, record["request_key_sha256"])
    index_body = json.dumps(
        {
            "archive_version": ARCHIVE_VERSION,
            "request_key_sha256": record["request_key_sha256"],
            "path": record["path"],
            "normalized_params": record["normalized_params"],
            "fetched_at_utc": record["fetched_at_utc"],
            "payload_sha256": digest,
            "blob_key": blob_key,
            "observation_key": observation_key,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    client.put_object(
        Bucket=config["bucket"],
        Key=index_key,
        Body=index_body,
        ContentType="application/json",
        Metadata={
            "request-key-sha256": record["request_key_sha256"],
            "payload-sha256": digest,
            "archive-version": ARCHIVE_VERSION,
        },
    )

    return {
        "backend": "S3",
        "bucket": config["bucket"],
        "observation_id": record["observation_id"],
        "payload_sha256": digest,
        "blob_path": blob_key,
        "observation_path": observation_key,
        "request_index_path": index_key,
        "blob_created": blob_created,
        "manifest_appended": observation_created,
    }


def archive_response(*, root=None, request_key, path, normalized_params, payload, fetched_at, s3_client=None):
    """Persist one successful real-provider observation.

    Local storage keeps one append-only JSONL manifest. S3/R2 stores one immutable
    observation JSON object per observation, which avoids unsafe append semantics
    on object storage while preserving an append-only evidence model.
    """
    raw, record = _record(
        request_key=request_key,
        path=path,
        normalized_params=normalized_params,
        payload=payload,
        fetched_at=fetched_at,
    )
    if root is not None:
        return _archive_local(root=root, raw=raw, record=record)
    config = s3_config_from_env()
    if config is None:
        raise RuntimeError("Raw archive storage is not configured")
    return _archive_s3(config=config, raw=raw, record=record, client=s3_client)



def read_archived_response(request_key, *, client=None):
    """Return a verified payload from the R2 request index, or None on miss.

    This function never calls API-Football. The request index is a mutable
    pointer to immutable observation/blob evidence.
    """
    config = s3_config_from_env()
    if config is None:
        return None
    client = client or _s3_client(config)
    request_hash = hashlib.sha256(str(request_key).encode("utf-8")).hexdigest()
    index_key = _request_index_key(config, request_hash)
    try:
        body = client.get_object(Bucket=config["bucket"], Key=index_key)["Body"].read()
    except Exception as exc:
        if _not_found(exc):
            return None
        raise
    record = json.loads(body.decode("utf-8"))
    if str(record.get("request_key_sha256") or "") != request_hash:
        raise RuntimeError("Raw archive request-index hash mismatch")
    blob_key = str(record.get("blob_key") or "")
    expected_digest = str(record.get("payload_sha256") or "")
    if not blob_key or not expected_digest:
        raise RuntimeError("Raw archive request-index is incomplete")
    compressed = client.get_object(Bucket=config["bucket"], Key=blob_key)["Body"].read()
    raw_payload = gzip.decompress(compressed)
    digest = hashlib.sha256(raw_payload).hexdigest()
    if digest != expected_digest:
        raise RuntimeError("Raw archive payload SHA-256 mismatch")
    payload = json.loads(raw_payload.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Raw archive payload is not a JSON object")
    return payload

def verify_s3_storage(*, client=None, keep_object=True):
    """Write/read/hash-verify one tiny object against the configured S3 backend."""
    config = s3_config_from_env()
    if config is None:
        raise RuntimeError("S3/R2 raw archive storage is not configured")
    client = client or _s3_client(config)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "archive_version": ARCHIVE_VERSION,
        "check": "PBK_RAW_ARCHIVE_STORAGE_READBACK",
        "created_at_utc": now.isoformat().replace("+00:00", "Z"),
        "nonce": uuid.uuid4().hex,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    key = f"{config['prefix']}/healthchecks/{now:%Y/%m/%d}/{digest}.json"
    client.put_object(
        Bucket=config["bucket"],
        Key=key,
        Body=body,
        ContentType="application/json",
        Metadata={"sha256": digest, "archive-version": ARCHIVE_VERSION},
    )
    fetched = client.get_object(Bucket=config["bucket"], Key=key)["Body"].read()
    readback_digest = hashlib.sha256(fetched).hexdigest()
    ok = fetched == body and readback_digest == digest
    if not keep_object:
        client.delete_object(Bucket=config["bucket"], Key=key)
    return {
        "status": "READY" if ok else "HASH_MISMATCH",
        "backend": "S3",
        "bucket": config["bucket"],
        "prefix": config["prefix"],
        "object_key": key,
        "written_bytes": len(body),
        "sha256": digest,
        "readback_sha256": readback_digest,
        "readback_match": ok,
        "durable": bool(ok),
    }
