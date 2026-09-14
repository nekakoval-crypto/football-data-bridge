# Stage76 Disaster Recovery

Stage76 protects PBK's operational audit/source-of-truth files without adding provider calls or changing any betting/model state.

## What is backed up

A recovery checkpoint copies allow-listed regular files from `ops/` and `config/` into a content-addressed payload and writes `manifest.json` plus `manifest.sha256`. Each payload entry has its relative path, byte size, SHA-256 and recovery class.

The Stage72 SQLite database under `build/` is deliberately **not** part of the checkpoint because it is a reproducible projection. Rebuild it after restoring the operational files.

Files whose names look like secrets/credentials and symbolic links are excluded. Stage76 never searches outside `ops/` and `config/`.

Two operational files are explicitly reported in every manifest as recovery prerequisites when present:

- `ops/forward_log.csv`
- `ops/stage71_observation_state.json`

Their absence is recorded in the manifest rather than silently invented.

## Automatic checkpoints

`.github/workflows/stage76-disaster-recovery.yml` runs daily at 02:17 UTC and can also be started manually. It runs unit tests, creates a checkpoint, verifies it byte-for-byte, proves that restore is dry-run by default, and then uploads the verified checkpoint as a GitHub Actions artifact with 30-day retention.

Pull requests run the same validation but do not upload a recovery artifact.

Stage76 has read-only repository permissions and performs no API-Football/provider calls.

## Create and verify manually

```bash
python scripts/stage76_disaster_recovery.py create \
  --output build/stage76-recovery

python scripts/stage76_disaster_recovery.py verify \
  --pack build/stage76-recovery
```

Creation refuses to replace an existing checkpoint unless `--replace` is supplied.

## Recovery drill — dry run first

```bash
python scripts/stage76_disaster_recovery.py restore \
  --pack build/stage76-recovery \
  --target-root /path/to/recovery-target
```

Without `--apply`, Stage76 only reports what is `SAME`, `MISSING`, `DIFFERENT`, or a non-file conflict. It writes nothing and deletes nothing.

## Apply a restore

To restore missing files after the checkpoint verifies successfully:

```bash
python scripts/stage76_disaster_recovery.py restore \
  --pack build/stage76-recovery \
  --target-root /path/to/recovery-target \
  --apply
```

If a destination already exists with different contents, restore stops **before writing any recovery files**. To intentionally replace differing files, the operator must explicitly add:

```bash
--allow-overwrite
```

Stage76 never deletes extra files from the target. Every restored file is copied to a temporary sibling, hash/size verified, then atomically replaced into its destination.

## Recommended production recovery sequence

1. Stop or pause operational writers so the target does not change during recovery.
2. Obtain a Stage76 artifact from a known-good checkpoint and inspect its `repository_sha` and `created_at_utc`.
3. Run `verify` and require `status=OK`.
4. Run restore **without** `--apply` and review the plan.
5. Restore into a separate recovery directory first when possible.
6. Apply to the intended target only after reviewing conflicts. Use `--allow-overwrite` only for files you deliberately intend to replace.
7. Rebuild Stage72 from the restored `ops/`/`config/` files.
8. Run Stage72 integrity/no-lookahead gates, Stage73 self-test, Today/LIVE tests, Match Card tests and operational publish safety checks before resuming writers.
9. Confirm `forward_log.csv`, shared Stage71 observation/budget state, standings snapshots and current-round/lineup snapshots have the expected checkpoint timestamps/content.

## Safety invariants

- Recovery packs are provider-free.
- Pack creation and verification never mutate `ops/` or `config/`.
- Restore is dry-run unless `--apply` is explicit.
- Existing differing files are protected unless `--allow-overwrite` is explicit.
- No file deletion is performed by restore.
- Paths outside `ops/` and `config/`, absolute paths and `..` traversal are rejected.
- Manifest and every payload file are SHA-256 verified before restore.
- Secrets are not intentionally captured; filenames matching secret/credential patterns are excluded.
