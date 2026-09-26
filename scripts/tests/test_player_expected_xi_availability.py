import unittest

from scripts.player_expected_xi_availability import resolve_player_availability


BASE = {
    "player_id": "10",
    "team_id": "100",
    "competition_scope": "SERIE A",
}


def ev(event_type, status, observed, **extra):
    row = {
        **BASE,
        "event_type": event_type,
        "status": status,
        "observed_at_utc": observed,
    }
    row.update(extra)
    return row


class Point14AvailabilityGateTests(unittest.TestCase):

    def resolve(self, events, competition="SERIE A"):
        return resolve_player_availability(
            events,
            player_id="10",
            team_id="100",
            target_competition=competition,
            before_utc="2026-10-10T18:00:00Z",
        )

    def test_red_card_alone_is_not_automatic_ban(self):
        result = self.resolve([
            ev("RED_CARD", "RED_CARD_EVENT", "2026-10-01T20:00:00Z")
        ])
        self.assertEqual(result["availability_status"], "UNCERTAIN")
        self.assertFalse(result["hard_excluded_from_expected_xi"])
        self.assertEqual(
            result["resolution_reason"],
            "RED_CARD_REQUIRES_SUSPENSION_VERIFICATION",
        )

    def test_confirmed_suspension_excludes_player(self):
        result = self.resolve([
            ev("RED_CARD", "RED_CARD_EVENT", "2026-10-01T20:00:00Z"),
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-03T10:00:00Z"),
        ])
        self.assertEqual(result["availability_status"], "UNAVAILABLE")
        self.assertTrue(result["hard_excluded_from_expected_xi"])
        self.assertEqual(result["start_probability_ceiling"], 0.0)

    def test_pending_appeal_reopens_uncertainty(self):
        result = self.resolve([
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-03T10:00:00Z"),
            ev("APPEAL", "APPEAL_PENDING", "2026-10-05T10:00:00Z"),
        ])
        self.assertEqual(result["availability_status"], "UNCERTAIN")
        self.assertFalse(result["hard_excluded_from_expected_xi"])

    def test_successful_appeal_restores_availability(self):
        result = self.resolve([
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-03T10:00:00Z"),
            ev("APPEAL", "SUSPENSION_OVERTURNED", "2026-10-06T10:00:00Z"),
        ])
        self.assertEqual(result["availability_status"], "AVAILABLE")
        self.assertFalse(result["hard_excluded_from_expected_xi"])

    def test_rejected_appeal_keeps_confirmed_ban(self):
        result = self.resolve([
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-03T10:00:00Z"),
            ev("APPEAL", "APPEAL_REJECTED", "2026-10-06T10:00:00Z"),
        ])
        self.assertEqual(result["availability_status"], "UNAVAILABLE")
        self.assertEqual(result["resolution_reason"], "SUSPENSION_UPHELD")

    def test_reduced_suspension_requires_fixture_recheck(self):
        result = self.resolve([
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-03T10:00:00Z"),
            ev("APPEAL", "SUSPENSION_REDUCED", "2026-10-06T10:00:00Z"),
        ])
        self.assertEqual(result["availability_status"], "UNCERTAIN")

    def test_wrong_competition_suspension_does_not_exclude(self):
        result = self.resolve([
            {
                **BASE,
                "competition_scope": "COPPA ITALIA",
                "event_type": "SUSPENSION",
                "status": "CONFIRMED_SUSPENSION",
                "observed_at_utc": "2026-10-03T10:00:00Z",
            }
        ])
        self.assertEqual(result["availability_status"], "AVAILABLE")

    def test_confirmed_injury_out_excludes(self):
        result = self.resolve([
            ev("INJURY", "CONFIRMED_INJURY_OUT", "2026-10-08T10:00:00Z")
        ])
        self.assertEqual(result["availability_status"], "UNAVAILABLE")

    def test_questionable_injury_is_uncertain_not_out(self):
        result = self.resolve([
            ev("INJURY", "QUESTIONABLE", "2026-10-08T10:00:00Z")
        ])
        self.assertEqual(result["availability_status"], "UNCERTAIN")
        self.assertFalse(result["hard_excluded_from_expected_xi"])

    def test_future_evidence_is_ignored(self):
        result = self.resolve([
            ev("SUSPENSION", "CONFIRMED_SUSPENSION", "2026-10-11T10:00:00Z")
        ])
        self.assertEqual(result["availability_status"], "AVAILABLE")


if __name__ == "__main__":
    unittest.main()
