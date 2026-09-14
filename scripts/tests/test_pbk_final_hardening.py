"""PBK v1 final arithmetic and immutable Forward journal acceptance tests."""
from __future__ import annotations

import csv
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pbk_calculation_contract as calc
import pbk_forward_journal as journal
import stage75_value_radar as radar

SCREENED = "2026-09-14T10:00:00Z"
OBSERVED = "2026-09-14T11:00:00Z"
KICKOFF = "2026-09-14T12:00:00Z"
SETTLED = "2026-09-14T13:30:00Z"


class CalculationContractTests(unittest.TestCase):
    def test_no_vig_requires_complete_valid_market(self):
        values = calc.no_vig_probabilities({"HOME": "2.00", "DRAW": "4.00", "AWAY": "4.00"})
        self.assertIsNotNone(values)
        self.assertEqual(sum(values.values()), calc.Decimal("1"))
        self.assertEqual(values["HOME"], calc.Decimal("0.5"))
        self.assertIsNone(calc.no_vig_probabilities({"HOME": "2", "DRAW": "", "AWAY": "4"}))
        self.assertIsNone(calc.no_vig_probabilities({"HOME": "1", "DRAW": "4", "AWAY": "4"}))

    def test_match_winner_aliases_and_ev(self):
        p = calc.match_winner_no_vig("2", "4", "4", "П2")
        self.assertEqual(p, calc.Decimal("0.25"))
        self.assertEqual(calc.expected_value("0.55", "2"), calc.Decimal("0.10"))
        self.assertIsNone(calc.expected_value("1", "2"))
        self.assertIsNone(calc.expected_value("0.5", "1"))

    def _canonical_kinds(self, pp, pm, odds=None, bookmaker=None):
        result = calc.evaluate_value(pp, pm, odds, executable=(bookmaker == "Marathonbet"))
        if result is None:
            return None
        kinds = [] if result["rating"] == "NO_VALUE" else [result["rating"]]
        kinds.extend(result["tags"])
        return kinds

    def test_legacy_radar_is_locked_to_canonical_boundaries(self):
        cases = [
            (".525", ".495", "2", "Marathonbet"),
            (".51", ".49", "2", "Marathonbet"),
            (".524995", ".494995", "2", "Marathonbet"),
            (".55", ".50", None, "Marathonbet"),
            (".65", ".64", "1.5", "Marathonbet"),
            (".68", ".67", "1.5", "Marathonbet"),
            (".60", ".50", "3", "Pinnacle"),
        ]
        for pp, pm, odds, bookmaker in cases:
            with self.subTest(pp=pp, pm=pm, odds=odds, bookmaker=bookmaker):
                legacy = radar.classify(pp, pm, odds, bookmaker)
                legacy_kinds = None if legacy is None else legacy["kinds"]
                self.assertEqual(legacy_kinds, self._canonical_kinds(pp, pm, odds, bookmaker))

    def test_contract_can_never_create_signal_or_change_stake(self):
        result = calc.evaluate_value(".60", ".50", "2", executable=True)
        self.assertEqual(result["rating"], "STRONG_VALUE")
        self.assertFalse(result["creates_signal"])
        self.assertFalse(result["stake_changes"])
        self.assertFalse(result["eligibility_mutation"])
        policy = calc.contract_policy()
        self.assertFalse(policy["creates_signal"])
        self.assertFalse(policy["stake_changes"])
        self.assertFalse(policy["eligibility_mutation"])


class ForwardJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ops = Path(self.tmp.name)
        self.forward_fields = [
            "forward_id", "rule", "screened_at_utc", "league", "div", "api_fixture_id",
            "match_date", "kickoff_time", "home_team", "away_team", "bet_market",
            "bet_selection", "stake_u", "trigger_source", "trigger_b365_home",
            "trigger_b365_draw", "trigger_b365_away", "execution_source",
            "execution_bookmaker", "execution_odds", "execution_last_update_utc",
            "execution_verified", "status", "result", "settled_at_utc", "profit_u",
        ]
        self.view_fields = [
            "forward_id", "rule", "api_fixture_id", "kickoff_utc", "selection", "status",
            "paper_user_execution_odds", "paper_user_execution_bookmaker",
            "paper_user_execution_at_utc", "user_execution_status", "user_profit_u",
        ]
        self.pred_fields = [
            "prediction_id", "model_version", "rule", "api_fixture_id", "kickoff_utc",
            "selection", "trigger_captured_at_utc", "p_market_no_vig", "p_pbk",
            "created_at_utc", "status",
        ]
        self.forward = [self._forward()]
        self.views = [self._view()]
        self.predictions = [self._prediction()]
        self._write_all()

    def _forward(self, **changes):
        row = {
            "forward_id": "R1|1001|Away", "rule": "R1", "screened_at_utc": SCREENED,
            "league": "Serie A", "div": "I1", "api_fixture_id": "1001",
            "match_date": "2026-09-14", "kickoff_time": "12:00", "home_team": "Home",
            "away_team": "Away", "bet_market": "Match Winner", "bet_selection": "Away",
            "stake_u": "1.0", "trigger_source": "Bet365", "trigger_b365_home": "3.2",
            "trigger_b365_draw": "3.3", "trigger_b365_away": "2.2",
            "execution_source": "best market", "execution_bookmaker": "Book",
            "execution_odds": "2.25", "execution_last_update_utc": SCREENED,
            "execution_verified": "YES", "status": "PAPER", "result": "",
            "settled_at_utc": "", "profit_u": "",
        }
        row.update(changes)
        return row

    def _view(self, **changes):
        row = {
            "forward_id": "R1|1001|Away", "rule": "R1", "api_fixture_id": "1001",
            "kickoff_utc": KICKOFF, "selection": "Away", "status": "PAPER",
            "paper_user_execution_odds": "2.30", "paper_user_execution_bookmaker": "Marathonbet",
            "paper_user_execution_at_utc": "2026-09-14T10:20:00Z",
            "user_execution_status": "FROZEN", "user_profit_u": "",
        }
        row.update(changes)
        return row

    def _prediction(self, **changes):
        row = {
            "prediction_id": "v1|R1|1001|Away", "model_version": "v1", "rule": "R1",
            "api_fixture_id": "1001", "kickoff_utc": KICKOFF, "selection": "Away",
            "trigger_captured_at_utc": "2026-09-14T10:00:00Z",
            "p_market_no_vig": ".45", "p_pbk": ".50",
            "created_at_utc": "2026-09-14T10:30:00Z", "status": "FROZEN_PREMATCH",
        }
        row.update(changes)
        return row

    def _write_csv(self, name, fields, rows):
        with (self.ops / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def _write_all(self):
        self._write_csv("forward_log.csv", self.forward_fields, self.forward)
        self._write_csv("user_forward_view.csv", self.view_fields, self.views)
        self._write_csv("stage75_probability_predictions.csv", self.pred_fields, self.predictions)

    def _run(self, when=OBSERVED):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            return journal.materialize(self.ops, when)

    def _events(self, name):
        path = self.ops / name
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_prematch_signal_and_calculation_are_append_only_and_rerun_stable(self):
        meta = self._run()
        self.assertEqual(meta["status"], "OK")
        self.assertEqual(meta["api_calls"], 0)
        self.assertEqual(meta["historical_backfill"], "FORBIDDEN")
        events = self._events("forward_prematch_journal.jsonl")
        self.assertEqual([e["event_type"] for e in events], ["SIGNAL_FROZEN", "CALCULATION_FROZEN"])
        calculation = events[1]["payload"]
        self.assertEqual(calculation["value_rating"], "STRONG_VALUE")
        self.assertFalse(calculation["creates_signal"])
        first = (self.ops / "forward_prematch_journal.jsonl").read_bytes()
        meta = self._run()
        self.assertEqual(meta["prematch_events_created"], 0)
        self.assertEqual((self.ops / "forward_prematch_journal.jsonl").read_bytes(), first)

    def test_immutable_source_drift_is_visible_and_never_overwrites_old_bytes(self):
        self._run()
        before = (self.ops / "forward_prematch_journal.jsonl").read_bytes()
        self.forward[0]["trigger_b365_away"] = "9.99"
        self._write_all()
        meta = self._run()
        self.assertEqual(meta["status"], "ATTENTION")
        self.assertGreaterEqual(meta["immutable_drift_detected"], 1)
        self.assertEqual((self.ops / "forward_prematch_journal.jsonl").read_bytes(), before)

    def test_first_seen_after_kickoff_is_not_backfilled(self):
        self.forward = [self._forward(forward_id="late", api_fixture_id="2002")]
        self.views = []
        self.predictions = []
        self._write_all()
        meta = self._run("2026-09-14T12:00:00Z")
        self.assertEqual(meta["prematch_events_total"], 0)
        self.assertEqual(meta["skipped_first_seen_at_or_after_kickoff"], 1)
        self.assertEqual(self._events("forward_prematch_journal.jsonl"), [])

    def test_postkickoff_prediction_is_rejected(self):
        self.predictions[0]["created_at_utc"] = KICKOFF
        self._write_all()
        meta = self._run()
        events = self._events("forward_prematch_journal.jsonl")
        self.assertEqual([e["event_type"] for e in events], ["SIGNAL_FROZEN"])
        self.assertGreaterEqual(meta["skipped_lookahead_or_invalid_time"], 1)

    def test_settlement_is_separate_and_never_mutates_prematch_bytes(self):
        self._run()
        prematch = (self.ops / "forward_prematch_journal.jsonl").read_bytes()
        self.forward[0].update(status="SETTLED", result="A", settled_at_utc=SETTLED, profit_u="1.250")
        self.views[0].update(status="SETTLED", user_profit_u="1.300")
        self._write_all()
        meta = self._run("2026-09-14T14:00:00Z")
        self.assertEqual(meta["settlement_events_created"], 1)
        self.assertEqual((self.ops / "forward_prematch_journal.jsonl").read_bytes(), prematch)
        settlements = self._events("forward_settlement_journal.jsonl")
        self.assertEqual(len(settlements), 1)
        self.assertEqual(settlements[0]["payload"]["result"], "A")
        rerun = (self.ops / "forward_settlement_journal.jsonl").read_bytes()
        self._run("2026-09-14T14:30:00Z")
        self.assertEqual((self.ops / "forward_settlement_journal.jsonl").read_bytes(), rerun)

    def test_duplicate_event_id_fails_closed_without_rewriting(self):
        self._run()
        path = self.ops / "forward_prematch_journal.jsonl"
        original = path.read_bytes()
        first_line = original.splitlines(keepends=True)[0]
        path.write_bytes(original + first_line)
        corrupt = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            self._run()
        self.assertEqual(path.read_bytes(), corrupt)


if __name__ == "__main__":
    unittest.main()
