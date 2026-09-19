import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_international_duty_source_allowlist as s


def source_row(pid,name,season="2024",matchday="true",minutes="true"):
    return {
        "provider_league_id":str(pid),
        "competition_name":name,
        "competition_type":"Cup",
        "provider_country_name":"World",
        "provider_country_code":"",
        "candidate_family":"TEST",
        "season":str(season),
        "season_start":"",
        "season_end":"",
        "current_season":"false",
        "coverage_events":"true",
        "coverage_lineups":matchday,
        "coverage_fixture_statistics":"true",
        "coverage_player_statistics":minutes,
        "coverage_players":"true",
        "coverage_injuries":"false",
        "direct_matchday_squad_evidence_possible":matchday,
        "direct_minutes_evidence_possible":minutes,
        "historical_callup_evidence_possible":"false",
        "nationality_inference_allowed":"false",
        "future_fixture_backfill_required":"true",
        "research_only":"true",
        "operational_betting_authority":"false",
        "creates_signal":"false",
        "probability_mutation":"false",
        "eligibility_mutation":"false",
        "stake_changes":"false",
        "forward_journal_mutation":"false",
    }


class InternationalDutySourceAllowlistTests(unittest.TestCase):
    def test_exact_allow_and_reject_ids_are_disjoint(self):
        self.assertEqual(len(s.ALLOWED),25)
        self.assertEqual(len(s.REJECTED),5)
        self.assertFalse(set(s.ALLOWED)&set(s.REJECTED))

    def test_direct_minutes_has_highest_backfill_priority(self):
        self.assertEqual(s.evidence_tier(source_row(1,"World Cup")),"DIRECT_MINUTES")
        squad=source_row(4,"Euro Championship",minutes="false")
        self.assertEqual(s.evidence_tier(squad),"DIRECT_MATCHDAY_SQUAD")
        fixture=source_row(5,"UEFA Nations League",matchday="false",minutes="false")
        self.assertEqual(s.evidence_tier(fixture),"FIXTURE_ONLY")
        self.assertEqual(s.priority_for("DIRECT_MINUTES"),1)
        self.assertEqual(s.priority_for("DIRECT_MATCHDAY_SQUAD"),2)
        self.assertEqual(s.priority_for("FIXTURE_ONLY"),9)

    def test_selection_is_fail_closed_for_unknown_provider_id(self):
        rows=[source_row(9999,"Mystery National Cup")]
        allow,audit,diag=s.select(rows)
        self.assertEqual(allow,[])
        self.assertEqual(audit[0]["decision"],"UNREVIEWED")
        self.assertEqual(diag["unknown_provider_competition_ids"],["9999"])

    def test_name_drift_is_fail_closed(self):
        rows=[source_row(1,"World Cup Renamed")]
        allow,audit,diag=s.select(rows)
        self.assertEqual(allow,[])
        self.assertEqual(audit,[])
        self.assertEqual(diag["name_mismatch_provider_competition_ids"],["1"])

    def test_rejected_competitions_never_enter_allowlist(self):
        rows=[
            source_row(926,"Copa America Femenina"),
            source_row(1028,"CONCACAF Central American Cup"),
            source_row(1213,"Kings World Cup Nations"),
            source_row(19,"African Nations Championship"),
            source_row(1163,"African Nations Championship - Qualification"),
        ]
        allow,audit,diag=s.select(rows)
        self.assertEqual(allow,[])
        self.assertFalse(diag["unknown_provider_competition_ids"])
        self.assertFalse(diag["name_mismatch_provider_competition_ids"])
        self.assertEqual({r["decision"] for r in audit},{"REJECT"})

    def test_allowed_row_cannot_promote_callup_or_authority(self):
        rows=[source_row(1,"World Cup")]
        allow,audit,diag=s.select(rows)
        self.assertEqual(len(allow),1)
        row=allow[0]
        self.assertEqual(row["pbk_source_selection_status"],"EXPLICIT_ALLOWLIST")
        self.assertEqual(row["historical_callup_evidence_possible"],"false")
        self.assertEqual(row["nationality_inference_allowed"],"false")
        self.assertEqual(row["operational_betting_authority"],"false")
        self.assertEqual(row["creates_signal"],"false")


if __name__=="__main__":
    unittest.main()
