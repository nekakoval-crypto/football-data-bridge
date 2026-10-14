from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "pbk_data_registry_v1.json"


class PBKRegistryError(RuntimeError):
    pass


class UnknownDatasetError(PBKRegistryError):
    pass


class DatasetMissingError(PBKRegistryError):
    pass


class DatasetClassError(PBKRegistryError):
    pass


class TimeScopeViolation(PBKRegistryError):
    pass


class PrematchAuthorizationError(PBKRegistryError):
    pass


class UnregisteredPathError(PBKRegistryError):
    pass


def _load():
    return json.loads(
        REGISTRY_PATH.read_text(
            encoding="utf-8"
        )
    )


def get_dataset(dataset_id: str) -> dict:

    registry = _load()

    for dataset in registry["datasets"]:
        if dataset["dataset_id"] == dataset_id:
            return dataset

    raise UnknownDatasetError(
        f"UNKNOWN_DATASET: {dataset_id}"
    )


def resolve(
    dataset_id: str,
    *,
    require_class: str | None = None,
    require_scope: str | None = None,
    require_prematch: bool = False,
    require_postmatch_target: bool = False,
) -> list[Path]:

    dataset = get_dataset(dataset_id)

    if require_class is not None:
        if dataset["data_class"] != require_class:
            raise DatasetClassError(
                f"WRONG_SOURCE_CLASS: {dataset_id} "
                f"is {dataset['data_class']} not {require_class}"
            )

    if require_scope is not None:
        if dataset["scope"] != require_scope:
            raise TimeScopeViolation(
                f"TIME_SCOPE_VIOLATION: {dataset_id} "
                f"is {dataset['scope']} not {require_scope}"
            )

    if require_prematch:
        if not dataset["prematch_authorized"]:
            raise PrematchAuthorizationError(
                f"LOOKAHEAD_VIOLATION: {dataset_id} "
                f"time_semantics={dataset['time_semantics']}"
            )

    if require_postmatch_target:
        if not dataset["postmatch_target_authorized"]:
            raise PBKRegistryError(
                f"POSTMATCH_TARGET_NOT_AUTHORIZED: {dataset_id}"
            )

    resolved = dataset.get(
        "resolved_paths",
        []
    )

    if not resolved:
        raise DatasetMissingError(
            f"DATASET_MISSING: {dataset_id}"
        )

    return [
        ROOT / path
        for path in resolved
    ]


def assert_registered_path(
    path: str | Path
) -> str:

    target = Path(path)

    if not target.is_absolute():
        target = ROOT / target

    target = target.resolve()

    registry = _load()

    for dataset in registry["datasets"]:

        for raw in dataset.get(
            "resolved_paths",
            []
        ):

            candidate = (
                ROOT / raw
            ).resolve()

            if candidate == target:
                return dataset["dataset_id"]

    raise UnregisteredPathError(
        f"UNREGISTERED_PATH: {target}"
    )
