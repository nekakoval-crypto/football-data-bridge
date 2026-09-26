#!/usr/bin/env python3
"""Durable R2 storage for the large derived Stage91 StatsBomb research CSV.

The raw StatsBomb event JSON stays outside PBK. This module stores only PBK's
derived Stage91 CSV in the user's private S3-compatible bucket, together with a
small mutable pointer to an immutable content-addressed object.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "PBK_STAGE91_DERIVED_ARTIFACT_R2_V1"
DEFAULT_PREFIX = "pbk-derived-research"


def config_from_env() -> dict[str, str]:
    names = {
        "access_key_id": "PBK_RAW_ARCHIVE_S3_ACCESS_KEY_ID",
        "secret_access_key": "PBK_RAW_ARCHIVE_S3_SECRET_ACCESS_KEY",
        "endpoint": "PBK_RAW_ARCHIVE_S3_ENDPOINT",
        "bucket": "PBK_RAW_ARCHIVE_S3_BUCKET",
    }
    values = {key: os.getenv(env, "").strip() for key, env in names.items()}
    missing = [names[key] for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("Incomplete Stage91 R2 configuration: " + ", ".join(missing))
    values["prefix"] = (
        os.getenv("PBK_DERIVED_RESEARCH_S3_PREFIX", DEFAULT_PREFIX)
        .strip()
        .strip("/")
        or DEFAULT_PREFIX
    )
    values["region"] = os.getenv("PBK_RAW_ARCHIVE_S3_REGION", "auto").strip() or "auto"
    return values


def s3_client(config: dict[str, str]):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for Stage91 R2 artifact storage") from exc
    return boto3.client(
        "s3",
        endpoint_url=config["endpoint"],
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        region_name=config["region"],
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_key(config: dict[str, str], digest: str) -> str:
    return f"{config['prefix']}/stage91/statsbomb-player-xg-xa/blobs/{digest[:2]}/{digest}.csv.gz"


def pointer_key(config: dict[str, str]) -> str:
    return f"{config['prefix']}/stage91/statsbomb-player-xg-xa/latest.json"


def row_count(csv_bytes: bytes) -> int:
    if not csv_bytes:
        return 0
    return max(0, len(csv_bytes.splitlines()) - 1)


def upload(
    source: Path,
    *,
    source_revision: str,
    config: dict[str, str] | None = None,
    client=None,
) -> dict[str, Any]:
    config = config or config_from_env()
    client = client or s3_client(config)
    raw = source.read_bytes()
    digest = sha256_bytes(raw)
    key = object_key(config, digest)
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = {
        "version": VERSION,
        "artifact": "ops/statsbomb_player_xg_xa.csv",
        "sha256": digest,
        "bytes": len(raw),
        "rows": row_count(raw),
        "source_revision": str(source_revision or ""),
        "object_key": key,
        "created_at_utc": created_at,
        "raw_statsbomb_events_stored": False,
        "research_only": True,
        "operational_betting_authority": False,
    }
    client.put_object(
        Bucket=config["bucket"],
        Key=key,
        Body=compressed,
        ContentType="application/gzip",
        Metadata={"sha256": digest, "artifact-version": VERSION},
    )
    pointer = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    client.put_object(
        Bucket=config["bucket"],
        Key=pointer_key(config),
        Body=pointer,
        ContentType="application/json",
        Metadata={"sha256": digest, "artifact-version": VERSION},
    )
    return {**manifest, "status": "UPLOADED", "bucket": config["bucket"]}


def _not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", {}) or {}
    code = str((response.get("Error") or {}).get("Code") or "")
    status = int((response.get("ResponseMetadata") or {}).get("HTTPStatusCode") or 0)
    return code in {"404", "NoSuchKey", "NotFound"} or status == 404


def fetch(
    destination: Path,
    *,
    config: dict[str, str] | None = None,
    client=None,
    allow_missing: bool = False,
) -> dict[str, Any]:
    config = config or config_from_env()
    client = client or s3_client(config)
    try:
        pointer_body = client.get_object(
            Bucket=config["bucket"], Key=pointer_key(config)
        )["Body"].read()
    except Exception as exc:
        if allow_missing and (_not_found(exc) or isinstance(exc, KeyError)):
            return {
                "version": VERSION,
                "status": "MISSING",
                "bucket": config["bucket"],
                "destination": str(destination),
                "verified": False,
            }
        raise
    manifest = json.loads(pointer_body.decode("utf-8"))
    if manifest.get("version") != VERSION:
        raise RuntimeError("Stage91 artifact pointer version mismatch")
    key = str(manifest.get("object_key") or "")
    expected = str(manifest.get("sha256") or "")
    expected_bytes = int(manifest.get("bytes") or 0)
    if not key or not expected:
        raise RuntimeError("Stage91 artifact pointer is incomplete")
    compressed = client.get_object(Bucket=config["bucket"], Key=key)["Body"].read()
    raw = gzip.decompress(compressed)
    digest = sha256_bytes(raw)
    if digest != expected:
        raise RuntimeError("Stage91 artifact SHA-256 mismatch")
    if expected_bytes and len(raw) != expected_bytes:
        raise RuntimeError("Stage91 artifact byte-size mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(destination)
    return {
        **manifest,
        "status": "FETCHED",
        "bucket": config["bucket"],
        "destination": str(destination),
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    up = sub.add_parser("upload")
    up.add_argument("--source", required=True)
    up.add_argument("--source-revision", default="")

    down = sub.add_parser("fetch")
    down.add_argument("--destination", required=True)
    down.add_argument("--allow-missing", action="store_true")

    args = parser.parse_args()
    if args.command == "upload":
        result = upload(Path(args.source), source_revision=args.source_revision)
    else:
        result = fetch(
            Path(args.destination),
            allow_missing=bool(args.allow_missing),
        )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
