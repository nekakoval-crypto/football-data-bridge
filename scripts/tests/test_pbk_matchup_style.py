import unittest

from scripts.pbk_matchup_style import (
    MATCHUP_COMPONENTS,
    STYLE_DIMENSIONS,
    directed_matchup,
    matchup_report,
    normalize_style_vector,
)


CUTOFF = "2026-09-16T18:00:00+00:00"


def evidence(value=6.0, observed="2026-09-16T17:00:00+00:00", source="fixture-events"):
    return {
        "value": value,
        "observed_at_utc": observed,
        "source": source,
        "sample_size": 8,
        "confidence": "MEDIUM",
    }


class MatchupStyleTests(unittest.TestCase):
    def test_requires_aware_cutoff(self):
        with self.assertRaises(ValueError):
            normalize_style_vector({}, "2026-09-16T18:00:00")

    def test_missing_evidence_remains_unknown_not_zero(self):
        payload = normalize_style_vector({}, CUTOFF)
        self.assertEqual(payload["known_dimensions"], 0)
        self.assertEqual(payload["coverage_pct"], 0.0)
        for row in payload["dimensions"].values():
            self.assertEqual(row["status"], "UNKNOWN")
            self.assertIsNone(row["value"])
        self.assertEqual(payload["missing_evidence_policy"], "UNKNOWN_NOT_ZERO")

    def test_post_cutoff_evidence_is_excluded(self):
        payload = normalize_style_vector(
            {"PRESS_INTENSITY": evidence(observed="2026-09-16T18:01:00+00:00")},
            CUTOFF,
        )
        row = payload["dimensions"]["PRESS_INTENSITY"]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertIn("EVIDENCE_AFTER_CUTOFF", row["limitations"])

    def test_source_and_timestamp_are_required(self):
        missing_source = normalize_style_vector(
            {"PRESS_INTENSITY": evidence(source="")}, CUTOFF
        )
        self.assertIn(
            "SOURCE_REQUIRED",
            missing_source["dimensions"]["PRESS_INTENSITY"]["limitations"],
        )
        missing_time = normalize_style_vector(
            {"PRESS_INTENSITY": {"value": 6.0, "source": "events"}}, CUTOFF
        )
        self.assertIn(
            "AWARE_OBSERVED_AT_REQUIRED",
            missing_time["dimensions"]["PRESS_INTENSITY"]["limitations"],
        )

    def test_unsupported_dimension_blocks_formation_as_style(self):
        with self.assertRaisesRegex(ValueError, "unsupported style dimensions"):
            normalize_style_vector({"FORMATION": evidence()}, CUTOFF)

    def test_values_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "value must be within 0..10"):
            normalize_style_vector({"PRESS_INTENSITY": evidence(11.0)}, CUTOFF)

    def test_directional_component_exposes_descriptive_delta_only(self):
        acting = {"PRESS_INTENSITY": evidence(8.0)}
        opponent = {"BUILDUP_RESISTANCE": evidence(5.5)}
        payload = directed_matchup(acting, opponent, CUTOFF)
        row = payload["components"]["PRESS_VS_BUILDUP"]
        self.assertEqual(row["status"], "KNOWN")
        self.assertEqual(row["delta"], 2.5)
        self.assertIn("DESCRIPTIVE_DELTA_ONLY", row["limitations"])
        self.assertIsNone(payload["matchup_grade"])
        self.assertIsNone(payload["overall_edge"])
        self.assertIsNone(payload["component_weights"])

    def test_component_with_one_missing_side_stays_unknown(self):
        payload = directed_matchup(
            {"TRANSITION_ATTACK": evidence(7.0)},
            {},
            CUTOFF,
        )
        row = payload["components"]["TRANSITION_VS_TRANSITION_DEFENCE"]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertIsNone(row["delta"])
        self.assertTrue(any("OPPONENT_TRANSITION_DEFENCE_UNKNOWN" == x for x in row["limitations"]))

    def test_formation_is_context_only(self):
        payload = matchup_report(
            {},
            {},
            CUTOFF,
            home_formation="4-3-3",
            away_formation="3-4-2-1",
        )
        self.assertEqual(payload["home_vs_away"]["known_components"], 0)
        self.assertEqual(
            payload["home_vs_away"]["formation_context"]["purpose"],
            "CONTEXT_ONLY",
        )
        self.assertFalse(payload["home_vs_away"]["formation_used_as_style_feature"])

    def test_both_directions_are_independent_and_no_winner_is_created(self):
        home = {
            "PRESS_INTENSITY": evidence(8.0),
            "TRANSITION_DEFENCE": evidence(4.0),
        }
        away = {
            "BUILDUP_RESISTANCE": evidence(5.0),
            "TRANSITION_ATTACK": evidence(7.0),
        }
        payload = matchup_report(home, away, CUTOFF)
        self.assertEqual(
            payload["home_vs_away"]["components"]["PRESS_VS_BUILDUP"]["delta"],
            3.0,
        )
        self.assertEqual(
            payload["away_vs_home"]["components"]["TRANSITION_VS_TRANSITION_DEFENCE"]["delta"],
            3.0,
        )
        self.assertIsNone(payload["winner"])
        self.assertIsNone(payload["matchup_grade"])
        self.assertFalse(payload["creates_signal"])
        self.assertFalse(payload["probability_mutation"])
        self.assertFalse(payload["eligibility_mutation"])
        self.assertFalse(payload["stake_changes"])
        self.assertFalse(payload["forward_journal_mutation"])
        self.assertFalse(payload["ui_changes"])

    def test_registry_shape_is_explicit(self):
        self.assertGreaterEqual(len(STYLE_DIMENSIONS), 10)
        self.assertIn("PRESS_VS_BUILDUP", MATCHUP_COMPONENTS)
        self.assertIn("LOW_BLOCK_BREAKING_VS_LOW_BLOCK_DEFENCE", MATCHUP_COMPONENTS)
        self.assertIn("SET_PIECE_VS_SET_PIECE_DEFENCE", MATCHUP_COMPONENTS)


if __name__ == "__main__":
    unittest.main()
