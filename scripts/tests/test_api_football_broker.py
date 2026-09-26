import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api_football_broker import (
    ApiFootballBroker,
    ApiFootballBudgetExceeded,
    ApiFootballProviderError,
    request_key,
    make_archive_before_budget_get,
)


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []
        self.payload = {"response": [{"id": 1}]}
        self.env = patch.dict(os.environ, {"API_FOOTBALL_KEY": "not-for-logs"}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def broker(self, transport=None, **kwargs):
        return ApiFootballBroker(
            transport=transport or self.transport,
            cache_path=Path(self.temp.name) / "cache.sqlite3",
            sleep=lambda _: None,
            **kwargs,
        )

    def transport(self, path, params, headers, timeout):
        self.calls.append((path, params, headers, timeout))
        return 200, {"X-RateLimit-Remaining": "9"}, self.payload

    def test_key_is_order_independent_but_semantic_params_are_distinct(self):
        self.assertEqual(
            request_key("GET", "/odds", {"fixture": 123, "bet": 12}),
            request_key("get", "odds", {"bet": 12, "fixture": 123}),
        )
        keys = {
            request_key("GET", "/odds", params)
            for params in (
                {"fixture": 123},
                {"fixture": 123, "bet": 12},
                {"fixture": 123, "bookmaker": 8},
                {"fixture": 123, "bet": 12, "bookmaker": 8},
            )
        }
        self.assertEqual(len(keys), 4)

    def test_memory_and_disk_cache_hits(self):
        first = self.broker()
        self.assertEqual(first.get("/fixtures", {"id": 1}), self.payload)
        self.assertEqual(first.get("/fixtures", {"id": 1}), self.payload)
        self.assertEqual(len(self.calls), 1)
        second = self.broker()
        self.assertEqual(second.get("/fixtures", {"id": 1}), self.payload)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(first.stats()["memory_cache_hits"], 1)
        self.assertEqual(second.stats()["disk_cache_hits"], 1)

    def test_expiry_and_force_refresh_call_provider(self):
        broker = self.broker(default_ttl_seconds=0)
        broker.get("/fixtures", {"id": 1})
        broker.get("/fixtures", {"id": 1})
        broker.get("/fixtures", {"id": 1}, force_refresh=True)
        self.assertEqual(len(self.calls), 3)

    def test_caller_ttl_controls_disk_and_memory_freshness(self):
        first = self.broker()
        with patch("api_football_broker._utc_timestamp", return_value=1000.0):
            first.get("/fixtures", {"id": 1}, ttl_seconds=3600)
        second = self.broker()
        with patch("api_football_broker._utc_timestamp", return_value=1003.0):
            second.get("/fixtures", {"id": 1}, ttl_seconds=1)
        self.assertEqual(len(self.calls), 2)

    def test_stale_disk_refresh_counts_one_logical_request(self):
        first = self.broker()
        with patch("api_football_broker._utc_timestamp", return_value=1000.0):
            first.get("/fixtures", {"id": 1}, ttl_seconds=3600)
        second = self.broker()
        with patch("api_football_broker._utc_timestamp", return_value=1003.0):
            second.get("/fixtures", {"id": 1}, ttl_seconds=1)
        stats = second.stats()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(stats["logical_requests"], 1)
        self.assertEqual(stats["real_api_calls"], 1)
        self.assertEqual(stats["disk_cache_hits"], 0)

        third = self.broker()
        with patch("api_football_broker._utc_timestamp", return_value=1003.5):
            third.get("/fixtures", {"id": 1}, ttl_seconds=3600)
        self.assertEqual(len(self.calls), 2)

    def test_zero_ttl_never_reuses_memory_or_disk(self):
        broker = self.broker()
        broker.get("/fixtures", {"id": 1}, ttl_seconds=3600)
        broker.get("/fixtures", {"id": 1}, ttl_seconds=0)
        second = self.broker()
        second.get("/fixtures", {"id": 1}, ttl_seconds=0)
        self.assertEqual(len(self.calls), 3)

    def test_cache_hits_do_not_consume_budget(self):
        broker = self.broker(max_real_calls=1)
        broker.get("/fixtures", {"id": 1})
        broker.get("/fixtures", {"id": 1})
        self.assertEqual(broker.stats()["real_api_calls"], 1)
        with self.assertRaises(ApiFootballBudgetExceeded):
            broker.get("/fixtures", {"id": 2})
        self.assertEqual(broker.stats()["budget_rejections"], 1)


    def test_archive_before_budget_hit_does_not_call_fallback(self):
        calls = []
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}
        archived = {"response": [{"id": 99}], "errors": []}

        def fallback(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            raise AssertionError("fallback budget must not be called on archive hit")

        get = make_archive_before_budget_get(
            fallback, stats, archive_reader=lambda key: archived
        )
        result = get("/fixtures/events", {"fixture": 123}, force_refresh=False)
        self.assertEqual(result, archived)
        self.assertEqual(calls, [])
        self.assertEqual(stats["archive_read_hits"], 1)
        self.assertEqual(stats["archive_read_misses"], 0)

    def test_strict_archive_after_fallback_requires_durable_replay_source(self):
        calls = []
        reads = [None, None]
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}

        def archive_reader(key):
            return reads.pop(0)

        def fallback(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": [{"id": 1}]}

        get = make_archive_before_budget_get(
            fallback,
            stats,
            archive_reader=archive_reader,
            require_archive_after_fallback=True,
        )

        with self.assertRaisesRegex(
            Exception,
            "raw archive missing after provider/cache fallback",
        ):
            get("/fixtures/players", {"fixture": 123})

        self.assertEqual(len(calls), 1)
        self.assertEqual(stats["archive_read_misses"], 1)

    def test_strict_archive_after_fallback_accepts_exact_replay_source(self):
        calls = []
        archived = {"response": [{"id": 1}], "errors": []}
        reads = [None, archived]
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}

        def archive_reader(key):
            return reads.pop(0)

        def fallback(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            return archived

        get = make_archive_before_budget_get(
            fallback,
            stats,
            archive_reader=archive_reader,
            require_archive_after_fallback=True,
        )
        result = get("/fixtures/players", {"fixture": 123})

        self.assertEqual(result, archived)
        self.assertEqual(len(calls), 1)
        self.assertEqual(stats["archive_read_misses"], 1)

    def test_archive_before_budget_miss_calls_fallback_once(self):
        calls = []
        stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}

        def fallback(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            return {"response": []}

        get = make_archive_before_budget_get(
            fallback, stats, archive_reader=lambda key: None
        )
        result = get("/fixtures/players", {"fixture": 123}, archive_first=True)
        self.assertEqual(result, {"response": []})
        self.assertEqual(len(calls), 1)
        self.assertNotIn("archive_first", calls[0][2])
        self.assertEqual(stats["archive_read_hits"], 0)
        self.assertEqual(stats["archive_read_misses"], 1)

    def test_archive_first_hit_avoids_provider_and_api_key(self):
        broker = self.broker()
        archived = {"response": [{"id": 99}], "errors": []}
        with patch.dict(os.environ, {"API_FOOTBALL_KEY": ""}, clear=False):
            with patch("api_football_broker.read_archived_response", return_value=archived):
                result = broker.get(
                    "/fixtures/players",
                    {"fixture": 123},
                    ttl_seconds=0,
                    archive_first=True,
                )
        self.assertEqual(result, archived)
        self.assertEqual(self.calls, [])
        self.assertEqual(broker.stats()["archive_read_hits"], 1)
        self.assertEqual(broker.stats()["real_api_calls"], 0)

    def test_archive_first_miss_falls_back_to_provider(self):
        broker = self.broker()
        with patch("api_football_broker.read_archived_response", return_value=None):
            result = broker.get(
                "/fixtures/players",
                {"fixture": 123},
                archive_first=True,
            )
        self.assertEqual(result, self.payload)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(broker.stats()["archive_read_misses"], 1)
        self.assertEqual(broker.stats()["real_api_calls"], 1)

    def test_force_refresh_bypasses_archive_first(self):
        broker = self.broker()
        archived = {"response": [{"id": 99}]}
        with patch("api_football_broker.read_archived_response", return_value=archived) as read:
            result = broker.get(
                "/fixtures/players",
                {"fixture": 123},
                archive_first=True,
                force_refresh=True,
            )
        self.assertEqual(result, self.payload)
        self.assertFalse(read.called)
        self.assertEqual(len(self.calls), 1)

    def test_missing_key_does_not_call_transport(self):
        with patch.dict(os.environ, {"API_FOOTBALL_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "API_FOOTBALL_KEY"):
                self.broker().get("/fixtures")
        self.assertEqual(self.calls, [])

    def test_key_is_not_in_cache_key_or_telemetry(self):
        broker = self.broker()
        key = request_key("GET", "/fixtures", {"id": 1})
        broker.get("/fixtures", {"id": 1})
        self.assertNotIn("not-for-logs", key)
        self.assertNotIn("not-for-logs", json.dumps(broker.stats()))

    def test_provider_errors_and_bounded_retry(self):
        def errors(path, params, headers, timeout):
            return 200, {}, {"errors": {"rateLimit": "hit"}}
        with self.assertRaises(ApiFootballProviderError):
            self.broker(transport=errors).get("/fixtures")

        attempts = {"count": 0}
        def flaky(path, params, headers, timeout):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise OSError("temporary transport failure")
            return 200, {}, self.payload
        broker = self.broker(transport=flaky, attempts=2)
        self.assertEqual(broker.get("/fixtures"), self.payload)
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(broker.stats()["retries"], 1)

    def test_trigger_critical_refresh_cannot_use_stale_disk_odds(self):
        first = self.broker()
        first.get("/odds", {"fixture": 123, "bookmaker": 8, "bet": 1})
        self.calls.clear()
        second = self.broker()
        second.get("/odds", {"fixture": 123, "bookmaker": 8, "bet": 1}, force_refresh=True)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(second.stats()["disk_cache_hits"], 0)

    def test_stage71j_explicit_unfiltered_reuse(self):
        import stage71j_shared_core_market_capture as stage71j
        stage71j._cache.clear()
        stage71j._fixture_odds_cache.clear()
        stage71j.real_calls = stage71j.cache_hits = 0
        stage71j.by_path.clear()
        calls = []
        def provider(path, params):
            calls.append((path, dict(params or {})))
            return {"response": [{"fixture": params.get("fixture"), "bookmakers": []}]}
        with patch.object(stage71j, "_real", side_effect=provider):
            stage71j.cached_api_get("/odds", {"fixture": 123})
            result = stage71j.cached_api_get("/odds", {"fixture": 123, "bet": 12})
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["response"][0]["fixture"], 123)
        self.assertEqual(stage71j.real_calls, 1)
        self.assertEqual(stage71j.cache_hits, 1)
        self.assertNotEqual(
            stage71j._key("/odds", {"fixture": 123}),
            stage71j._key("/odds", {"fixture": 123, "bet": 12}),
        )

    def test_stage71j_disk_hit_does_not_increment_real_calls(self):
        import api_football_broker
        import stage53_daily_screener as stage53
        import stage71j_shared_core_market_capture as stage71j
        broker = self.broker()
        with patch.object(api_football_broker, "_DEFAULT_BROKER", broker):
            with patch.object(stage71j, "_real", stage53._stage53_api_get):
                stage71j._cache.clear()
                stage71j._fixture_odds_cache.clear()
                stage71j.real_calls = stage71j.cache_hits = 0
                stage71j.by_path.clear()
                stage71j.cached_api_get("/odds/bets")
                stage71j._cache.clear()
                broker._memory.clear()
                stage71j.cached_api_get("/odds/bets")
        self.assertEqual(stage71j.real_calls, 1)
        self.assertEqual(stage71j.cache_hits, 1)
        self.assertEqual(broker.stats()["disk_cache_hits"], 1)

    def test_stage71j_cap_counts_retry_transport_attempts(self):
        import api_football_broker
        import stage53_daily_screener as stage53
        import stage71j_shared_core_market_capture as stage71j
        attempts = []

        def failing(path, params, headers, timeout):
            attempts.append(path)
            raise OSError("temporary")

        broker = self.broker(transport=failing, attempts=3)
        old_cap = stage71j.MAX_REAL_CALLS
        stage71j.MAX_REAL_CALLS = 2
        try:
            with patch.object(api_football_broker, "_DEFAULT_BROKER", broker):
                with patch.object(stage71j, "_real", stage53._stage53_api_get):
                    with self.assertRaises(RuntimeError):
                        stage71j.cached_api_get("/fixtures", {"id": 1})
                    with self.assertRaises(RuntimeError):
                        stage71j.cached_api_get("/fixtures", {"id": 2})
            self.assertEqual(len(attempts), 2)
            self.assertEqual(broker.stats()["real_api_calls"], 2)
            self.assertEqual(stage71j.real_calls, 2)
        finally:
            stage71j.MAX_REAL_CALLS = old_cap

    def test_migrated_clients_delegate_api_football_to_broker(self):
        import stage53_daily_screener as stage53
        import stage54_forward_ops as stage54
        import stage55_context_enrichment as stage55
        import stage56_weather_rotation as stage56
        self.assertIsNotNone(stage53.broker_api_get)
        self.assertIsNotNone(stage55.broker_api_get)
        self.assertIsNotNone(stage56.broker_api_get)
        self.assertIsNotNone(stage54.broker_api_get)
        self.assertNotIn("API_BASE", stage55.__dict__)
        self.assertNotIn("API_BASE", stage54.__dict__)
        self.assertNotIn("API_FOOTBALL", stage56.__dict__)

    def test_stage55_and_stage56_wrappers_forward_force_refresh(self):
        import stage54_forward_ops
        import stage55_context_enrichment as stage55
        import stage56_weather_rotation as stage56
        fixture = {"response": [{"fixture": {"id": 1}}]}
        lineups = {"response": []}
        calls = []

        def mocked(path, params=None, **kwargs):
            calls.append((path, kwargs))
            return lineups if "lineups" in path else fixture

        with patch.object(stage55, "broker_api_get", side_effect=mocked):
            stage55.get_fixture(1)
            stage55.get_injuries(1)
            stage55.get_lineups(1)
        with patch.object(stage56, "broker_api_get", side_effect=mocked):
            stage56.get_lineups(1)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(call[1].get("force_refresh") is True for call in calls))


if __name__ == "__main__":
    unittest.main()
