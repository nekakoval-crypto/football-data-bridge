#!/usr/bin/env python3
"""Stage 76 — PBK disaster-recovery pack, verification and safe restore.

The operational CSV/JSON/JSONL files remain PBK's audit/source-of-truth while
Stage72 SQLite is reproducible and intentionally excluded from the recovery
pack. Stage76 creates a content-addressed copy of allow-listed ``ops`` and
``config`` files, verifies every byte before restore, and defaults restore to a
dry-run. Existing destination files are never overwritten unless the operator
explicitly supplies ``--allow-overwrite``.

No provider calls, no secret discovery, no mutation of source ledgers during
pack creation/verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

PACK_VERSION = "PBK_STAGE76_V1"
DEFAULT_ROOTS = ("ops", "config")
ALLOWED_ROOTS = frozenset(DEFAULT_ROOTS)
ALLOWED_SUFFIXES = frozenset({".csv", ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml", ".toml"})
DENY_NAME_TOKENS = (
    ".env", "secret", "credential", "password", "private_key", "apikey", "api_key", "access_token"
)
REQUIRED_RECOVERY_FILES = (
    "ops/forward_log.csv",
    "ops/stage71_observation_state.json",
)
DERIVED_EXCLUSIONS = (
    "build/pbk_unified.sqlite",
    "build/",
)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_sha(explicit=None):
    if explicit:
        return str(explicit)
    env_sha = os.getenv("GITHUB_SHA")
    if env_sha:
        return env_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def _safe_relative(value: str) -> PurePosixPath:
    rel = PurePosixPath(str(value).replace("\\", "/"))
    if rel.is_absolute() or not rel.parts or ".." in rel.parts:
        raise ValueError(f"unsafe recovery path: {value!r}")
    if rel.parts[0] not in ALLOWED_ROOTS:
        raise ValueError(f"path outside recovery roots: {value!r}")
    return rel


def _sensitive_name(path: Path) -> bool:
    low = path.name.casefold()
    return any(token in low for token in DENY_NAME_TOKENS)


def discover_files(repo_root: Path, roots=DEFAULT_ROOTS):
    files = []
    excluded = []
    for root_name in roots:
        if root_name not in ALLOWED_ROOTS:
            raise ValueError(f"unsupported recovery root: {root_name}")
        root = repo_root / root_name
        if not root.exists():
            excluded.append({"path": root_name, "reason": "ROOT_MISSING"})
            continue
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(repo_root).as_posix()
            if path.is_symlink():
                excluded.append({"path": rel, "reason": "SYMLINK_EXCLUDED"})
                continue
            if not path.is_file():
                continue
            if _sensitive_name(path):
                excluded.append({"path": rel, "reason": "SENSITIVE_NAME_EXCLUDED"})
                continue
            if path.suffix.casefold() not in ALLOWED_SUFFIXES:
                excluded.append({"path": rel, "reason": "UNSUPPORTED_SUFFIX"})
                continue
            files.append(path)
    return files, excluded


def _critical_class(rel: str):
    name = PurePosixPath(rel).name.casefold()
    if rel.startswith("config/"):
        return "CONFIG"
    if "forward" in name or "ledger" in name or "settlement" in name:
        return "DURABLE_LEDGER"
    if "state" in name:
        return "DURABLE_STATE"
    if "snapshot" in name or "overlay" in name or "current_round" in name:
        return "OBSERVATION_SNAPSHOT"
    return "OPERATIONAL_AUDIT"


def create_pack(repo_root: Path, output: Path, roots=DEFAULT_ROOTS, replace=False, repository_sha=None):
    repo_root = repo_root.resolve()
    output = output.resolve()
    if output.exists():
        if not replace:
            raise FileExistsError(f"recovery output already exists: {output}")
        shutil.rmtree(output)
    payload_root = output / "payload"
    payload_root.mkdir(parents=True, exist_ok=False)

    source_files, excluded = discover_files(repo_root, roots)
    entries = []
    bytes_total = 0
    for source in source_files:
        rel = source.relative_to(repo_root).as_posix()
        _safe_relative(rel)
        destination = payload_root / Path(rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        size = destination.stat().st_size
        digest = sha256_file(destination)
        entries.append({
            "path": rel,
            "size": size,
            "sha256": digest,
            "critical_class": _critical_class(rel),
        })
        bytes_total += size

    included_paths = {entry["path"] for entry in entries}
    required = {
        path: ("PRESENT" if path in included_paths else "MISSING")
        for path in REQUIRED_RECOVERY_FILES
    }
    repo_sha = _repository_sha(repository_sha)
    created = now_iso()
    checkpoint_id = f"{created.replace(':', '').replace('-', '')}_{repo_sha[:12]}"
    manifest = {
        "pack_version": PACK_VERSION,
        "checkpoint_id": checkpoint_id,
        "created_at_utc": created,
        "repository_sha": repo_sha,
        "roots": list(roots),
        "source_policy": "allow-listed ops/config regular files only; secrets and symlinks excluded",
        "restore_policy": "verify first; dry-run by default; no deletion; overwrite requires explicit flag",
        "derived_data_policy": {
            "stage72_sqlite": "EXCLUDED_REBUILDABLE",
            "excluded_examples": list(DERIVED_EXCLUSIONS),
        },
        "required_recovery_files": required,
        "files": sorted(entries, key=lambda item: item["path"]),
        "excluded": sorted(excluded, key=lambda item: item["path"]),
        "summary": {
            "files": len(entries),
            "bytes": bytes_total,
            "required_missing": sum(1 for value in required.values() if value != "PRESENT"),
        },
    }
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(raw)
    (output / "manifest.sha256").write_text(hashlib.sha256(raw).hexdigest() + "  manifest.json\n", encoding="utf-8")
    return manifest


def load_manifest(pack: Path):
    pack = pack.resolve()
    manifest_path = pack / "manifest.json"
    checksum_path = pack / "manifest.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise ValueError("recovery pack missing manifest.json or manifest.sha256")
    raw = manifest_path.read_bytes()
    expected = checksum_path.read_text(encoding="utf-8").strip().split()[0]
    actual = hashlib.sha256(raw).hexdigest()
    if expected != actual:
        raise ValueError("manifest checksum mismatch")
    manifest = json.loads(raw.decode("utf-8"))
    if manifest.get("pack_version") != PACK_VERSION:
        raise ValueError(f"unsupported pack version: {manifest.get('pack_version')!r}")
    return manifest


def verify_pack(pack: Path):
    pack = pack.resolve()
    manifest = load_manifest(pack)
    payload_root = pack / "payload"
    if not payload_root.is_dir():
        raise ValueError("recovery pack missing payload directory")

    expected_paths = set()
    errors = []
    for entry in manifest.get("files") or []:
        try:
            rel = _safe_relative(entry.get("path"))
        except Exception as exc:
            errors.append(str(exc))
            continue
        key = rel.as_posix()
        if key in expected_paths:
            errors.append(f"duplicate manifest path: {key}")
            continue
        expected_paths.add(key)
        path = payload_root / Path(*rel.parts)
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing/non-regular payload file: {key}")
            continue
        size = path.stat().st_size
        if size != int(entry.get("size", -1)):
            errors.append(f"size mismatch: {key}")
            continue
        digest = sha256_file(path)
        if digest != entry.get("sha256"):
            errors.append(f"sha256 mismatch: {key}")

    actual_paths = {
        path.relative_to(payload_root).as_posix()
        for path in payload_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    for extra in sorted(actual_paths - expected_paths):
        errors.append(f"unmanifested payload file: {extra}")
    for missing in sorted(expected_paths - actual_paths):
        if f"missing/non-regular payload file: {missing}" not in errors:
            errors.append(f"missing payload file: {missing}")

    required = manifest.get("required_recovery_files") or {}
    required_missing = [path for path, state in required.items() if state != "PRESENT"]
    result = {
        "status": "OK" if not errors else "FAIL",
        "checkpoint_id": manifest.get("checkpoint_id"),
        "repository_sha": manifest.get("repository_sha"),
        "verified_files": len(expected_paths) - len([e for e in errors if e.startswith("missing")]),
        "manifest_files": len(expected_paths),
        "errors": errors,
        "required_missing_at_capture": required_missing,
    }
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def restore_plan(pack: Path, target_root: Path):
    manifest = load_manifest(pack)
    target_root = target_root.resolve()
    payload_root = pack.resolve() / "payload"
    plan = []
    for entry in manifest.get("files") or []:
        rel = _safe_relative(entry["path"])
        source = payload_root / Path(*rel.parts)
        destination = target_root / Path(*rel.parts)
        if not destination.exists():
            state = "MISSING"
        elif destination.is_symlink() or not destination.is_file():
            state = "CONFLICT_NON_FILE"
        elif destination.stat().st_size == entry["size"] and sha256_file(destination) == entry["sha256"]:
            state = "SAME"
        else:
            state = "DIFFERENT"
        plan.append({"path": rel.as_posix(), "state": state, "source": source, "destination": destination})
    return manifest, plan


def restore_pack(pack: Path, target_root: Path, apply=False, allow_overwrite=False):
    verification = verify_pack(pack)
    manifest, plan = restore_plan(pack, target_root)
    conflicts = [row for row in plan if row["state"] in {"DIFFERENT", "CONFLICT_NON_FILE"}]
    if apply and conflicts and not allow_overwrite:
        names = ", ".join(row["path"] for row in conflicts[:10])
        raise FileExistsError(f"restore would overwrite/conflict with existing files: {names}")
    restored = 0
    overwritten = 0
    if apply:
        target_root = target_root.resolve()
        for row in plan:
            if row["state"] == "SAME":
                continue
            destination = row["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.is_dir():
                if not allow_overwrite:
                    raise FileExistsError(f"restore destination is directory: {row['path']}")
                shutil.rmtree(destination)
            temp = destination.with_name(destination.name + ".stage76.tmp")
            if temp.exists():
                temp.unlink()
            shutil.copy2(row["source"], temp)
            expected = next(item for item in manifest["files"] if item["path"] == row["path"])
            if temp.stat().st_size != expected["size"] or sha256_file(temp) != expected["sha256"]:
                temp.unlink(missing_ok=True)
                raise IOError(f"restored temp verification failed: {row['path']}")
            existed = destination.exists()
            os.replace(temp, destination)
            restored += 1
            overwritten += int(existed)
    return {
        "status": "APPLIED" if apply else "DRY_RUN",
        "checkpoint_id": verification["checkpoint_id"],
        "target_root": str(target_root.resolve()),
        "files_total": len(plan),
        "same": sum(1 for row in plan if row["state"] == "SAME"),
        "missing": sum(1 for row in plan if row["state"] == "MISSING"),
        "different": sum(1 for row in plan if row["state"] == "DIFFERENT"),
        "conflict_non_file": sum(1 for row in plan if row["state"] == "CONFLICT_NON_FILE"),
        "restored": restored,
        "overwritten": overwritten,
        "allow_overwrite": bool(allow_overwrite),
        "deletes_files": False,
    }


def _print(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def main(argv=None):
    parser = argparse.ArgumentParser(description="PBK Stage76 disaster recovery")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create a recovery pack")
    create.add_argument("--repo-root", default=".")
    create.add_argument("--output", default="build/stage76-recovery")
    create.add_argument("--root", action="append", dest="roots", choices=sorted(ALLOWED_ROOTS))
    create.add_argument("--replace", action="store_true")
    create.add_argument("--repository-sha")

    verify = sub.add_parser("verify", help="verify an existing recovery pack")
    verify.add_argument("--pack", required=True)

    restore = sub.add_parser("restore", help="plan or apply a recovery pack")
    restore.add_argument("--pack", required=True)
    restore.add_argument("--target-root", required=True)
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--allow-overwrite", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            roots = tuple(args.roots or DEFAULT_ROOTS)
            payload = create_pack(
                Path(args.repo_root), Path(args.output), roots=roots,
                replace=args.replace, repository_sha=args.repository_sha,
            )
            _print({
                "status": "OK",
                "checkpoint_id": payload["checkpoint_id"],
                "repository_sha": payload["repository_sha"],
                "summary": payload["summary"],
                "required_recovery_files": payload["required_recovery_files"],
                "output": str(Path(args.output)),
            })
            return 0
        if args.command == "verify":
            _print(verify_pack(Path(args.pack)))
            return 0
        if args.command == "restore":
            if args.allow_overwrite and not args.apply:
                raise ValueError("--allow-overwrite is valid only together with --apply")
            _print(restore_pack(
                Path(args.pack), Path(args.target_root),
                apply=args.apply, allow_overwrite=args.allow_overwrite,
            ))
            return 0
    except Exception as exc:
        _print({"status": "FAIL", "error": str(exc), "command": args.command})
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
