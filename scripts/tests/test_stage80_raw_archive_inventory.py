#!/usr/bin/env python3
import json
import unittest
from unittest.mock import patch

from scripts.stage80_raw_archive_inventory import inventory, params_dict


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FakePaginator:
    def __init__(self, keys):
        self.keys = keys

    def paginate(self, **kwargs):
        return [{"Contents": [{"Key": key} for key in self.keys]}]


class FakeClient:
    def __init__(self, records):
        self.records = records

    def get_paginator(self, name):
        return FakePaginator(list(self.records))

    def get_object(self, Bucket, Key):
        data = json.dumps(self.records[Key]).encode("utf-8")
        return {"Body": FakeBody(data)}


class InventoryTests(unittest.TestCase):
    def test_params_dict(self):
        self.assertEqual(params_dict([["fixture", "123"], ["season", '"2025"']]), {"fixture": "123", "season": "2025"})

    @patch("scripts.stage80_raw_archive_inventory.s3_config_from_env")
    def test_inventory_counts_targets(self, cfg):
        cfg.return_value = {"bucket": "b", "prefix": "api-football-raw"}
        records = {
            "api-football-raw/observations/2026/01/a.json": {
                "path": "/fixtures/lineups",
                "normalized_params": [["fixture", "101"]],
                "fetched_at_utc": "2026-01-01T00:00:00Z",
            },
            "api-football-raw/observations/2026/01/b.json": {
                "path": "/fixtures/lineups",
                "normalized_params": [["fixture", "101"]],
                "fetched_at_utc": "2026-01-02T00:00:00Z",
            },
            "api-football-raw/observations/2026/01/c.json": {
                "path": "/injuries",
                "normalized_params": [["fixture", "202"]],
                "fetched_at_utc": "2026-01-03T00:00:00Z",
            },
            "api-football-raw/observations/2026/01/d.json": {
                "path": "/status",
                "normalized_params": [],
                "fetched_at_utc": "2026-01-04T00:00:00Z",
            },
        }
        report = inventory(client=FakeClient(records))
        self.assertEqual(report["observation_records"], 4)
        self.assertEqual(report["targets"]["/fixtures/lineups"]["observations"], 2)
        self.assertEqual(report["targets"]["/fixtures/lineups"]["unique_fixture_ids"], 1)
        self.assertEqual(report["targets"]["/injuries"]["observations"], 1)
        self.assertEqual(report["targets"]["/injuries"]["unique_fixture_ids"], 1)
        self.assertEqual(report["provider_calls"], 0)
        self.assertFalse(report["reads_payload_blobs"])


if __name__ == "__main__":
    unittest.main()
