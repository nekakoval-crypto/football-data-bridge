import unittest

from scripts.player_expected_xi import (
    positional_fit,
    ranked_candidates_for_slot,
    resolve_expected_xi,
)


def candidate(
    player_id,
    name,
    primary,
    *,
    documented=None,
    events=None,
    starts5=0,
    starts10=0,
    minutes5=0,
    form5=None,
):
    return {
        "player_id": str(player_id),
        "player_name": name,
        "primary_position": primary,
        "documented_positions": documented or [primary],
        "availability_events": events or [],
        "starts_last_5": starts5,
        "starts_last_10": starts10,
        "minutes_last_5": minutes5,
        "form_5": form5,
    }


def suspension(player_id, status="CONFIRMED_SUSPENSION"):
    return {
        "player_id": str(player_id),
        "team_id": "100",
        "event_type": "SUSPENSION",
        "status": status,
        "competition_scope": "SERIE A",
        "observed_at_utc": "2026-10-08T10:00:00Z",
    }


def injury(player_id, status="CONFIRMED_INJURY_OUT"):
    return {
        "player_id": str(player_id),
        "team_id": "100",
        "event_type": "INJURY",
        "status": status,
        "observed_at_utc": "2026-10-08T11:00:00Z",
    }


class Point14ExpectedXITests(unittest.TestCase):

    def test_primary_exact_position_beats_group_only(self):
        cb = candidate("1", "Natural CB", "CB", starts10=7)
        rb = candidate("2", "Natural RB", "RB", starts10=10)

        rows = ranked_candidates_for_slot(
            [rb, cb],
            slot="CB",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual(rows[0]["player_id"], "1")

    def test_documented_cb_replacement_is_allowed(self):
        dm = candidate(
            "5",
            "DM who played CB",
            "DM",
            documented=["DM", "CB"],
            starts10=8,
        )

        fit = positional_fit(dm, "CB")

        self.assertEqual(fit["fit_level"], "DOCUMENTED_EXACT")

    def test_confirmed_suspension_removes_candidate(self):
        banned = candidate(
            "1",
            "Banned CB",
            "CB",
            events=[suspension("1")],
            starts10=10,
        )

        healthy = candidate(
            "2",
            "Healthy CB",
            "CB",
            starts10=2,
        )

        rows = ranked_candidates_for_slot(
            [banned, healthy],
            slot="CB",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual([r["player_id"] for r in rows], ["2"])

    def test_four_cb_crisis(self):
        cb1 = candidate("1", "CB 1", "CB", events=[suspension("1")])
        cb2 = candidate("2", "CB 2", "CB", events=[suspension("2")])
        cb3 = candidate("3", "CB 3", "CB", events=[injury("3")])
        cb4 = candidate("4", "CB 4", "CB")

        emergency = candidate(
            "5",
            "DM emergency CB",
            "DM",
            documented=["DM", "CB"],
            starts10=8,
        )

        pool = [
            candidate("10", "GK", "GK"),
            candidate("11", "RB", "RB"),
            candidate("12", "LB", "LB"),
            candidate("13", "CM1", "CM"),
            candidate("14", "CM2", "CM"),
            candidate("15", "CM3", "CM"),
            candidate("16", "RW", "RW"),
            candidate("17", "ST", "ST"),
            candidate("18", "LW", "LW"),
            cb1, cb2, cb3, cb4, emergency,
        ]

        result = resolve_expected_xi(
            pool,
            formation="4-3-3",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        cb_ids = {
            row["player_id"]
            for row in result["expected_xi"]
            if row["slot"] == "CB"
        }

        self.assertEqual(cb_ids, {"4", "5"})

    def test_no_replacement_means_uncertain(self):
        pool = [
            candidate("10", "GK", "GK"),
            candidate("11", "RB", "RB"),
            candidate("12", "LB", "LB"),
            candidate("13", "CM1", "CM"),
            candidate("14", "CM2", "CM"),
            candidate("15", "CM3", "CM"),
            candidate("16", "RW", "RW"),
            candidate("17", "ST", "ST"),
            candidate("18", "LW", "LW"),
            candidate("1", "Only healthy CB", "CB"),
        ]

        result = resolve_expected_xi(
            pool,
            formation="4-3-3",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual(result["status"], "EXPECTED_XI_UNCERTAIN")
        self.assertEqual(result["expected_xi_count"], 10)

    def test_pending_appeal_keeps_uncertainty(self):
        events = [
            suspension("1"),
            {
                "player_id": "1",
                "team_id": "100",
                "event_type": "APPEAL",
                "status": "APPEAL_PENDING",
                "competition_scope": "SERIE A",
                "observed_at_utc": "2026-10-09T10:00:00Z",
            },
        ]

        player = candidate(
            "1",
            "Appeal CB",
            "CB",
            events=events,
        )

        rows = ranked_candidates_for_slot(
            [player],
            slot="CB",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual(
            rows[0]["availability"]["availability_status"],
            "UNCERTAIN",
        )

    def test_overturned_ban_restores_available(self):
        events = [
            suspension("1"),
            {
                "player_id": "1",
                "team_id": "100",
                "event_type": "APPEAL",
                "status": "SUSPENSION_OVERTURNED",
                "competition_scope": "SERIE A",
                "observed_at_utc": "2026-10-09T10:00:00Z",
            },
        ]

        player = candidate(
            "1",
            "Cleared CB",
            "CB",
            events=events,
        )

        rows = ranked_candidates_for_slot(
            [player],
            slot="CB",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual(
            rows[0]["availability"]["availability_status"],
            "AVAILABLE",
        )

    def test_probability_not_fabricated(self):
        pool = [
            candidate("10", "GK", "GK"),
            candidate("11", "RB", "RB"),
            candidate("12", "CB1", "CB"),
            candidate("13", "CB2", "CB"),
            candidate("14", "LB", "LB"),
            candidate("15", "CM1", "CM"),
            candidate("16", "CM2", "CM"),
            candidate("17", "CM3", "CM"),
            candidate("18", "RW", "RW"),
            candidate("19", "ST", "ST"),
            candidate("20", "LW", "LW"),
        ]

        result = resolve_expected_xi(
            pool,
            formation="4-3-3",
            team_id="100",
            target_competition="SERIE A",
            before_utc="2026-10-10T18:00:00Z",
        )

        self.assertEqual(result["status"], "EXPECTED_XI_COMPLETE")
        self.assertEqual(result["expected_xi_count"], 11)
        self.assertEqual(
            result["start_probability_authority"],
            "UNCALIBRATED",
        )
        self.assertTrue(
            all(
                row["start_probability"] is None
                for row in result["expected_xi"]
            )
        )


if __name__ == "__main__":
    unittest.main()
