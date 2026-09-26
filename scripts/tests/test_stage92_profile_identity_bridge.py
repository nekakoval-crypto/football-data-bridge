import unittest

from scripts import stage92_profile_identity_bridge as b


class Stage92ProfileIdentityBridgeTests(unittest.TestCase):
    def profile(self, **overrides):
        row = {
            "player_id": "278",
            "player_name": "Kylian Mbappé",
            "firstname": "Kylian",
            "lastname": "Mbappé Lottin",
        }
        row.update(overrides)
        return row

    def test_exact_firstname_lastname_is_high_authority(self):
        result = b.classify_exact_profile(
            "Kylian Mbappé Lottin",
            [self.profile()],
        )
        self.assertEqual(result["status"], "AUTO_MATCH")
        self.assertEqual(result["confidence"], "HIGH")
        self.assertTrue(result["authoritative"])
        self.assertEqual(result["pbk_player_id"], "278")
        self.assertEqual(result["method"], b.STRONG_PROFILE_METHOD)

    def test_observed_multitoken_name_is_review_only(self):
        result = b.classify_exact_profile(
            "Kylian Mbappé",
            [self.profile()],
        )
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["confidence"], "MEDIUM")
        self.assertFalse(result["authoritative"])
        self.assertEqual(result["method"], b.SECONDARY_PROFILE_METHOD)

    def test_ambiguous_exact_full_name_is_not_authoritative(self):
        rows = [
            self.profile(player_id="278"),
            self.profile(player_id="999", player_name="Other Player"),
        ]
        result = b.classify_exact_profile("Kylian Mbappé Lottin", rows)
        self.assertIsNone(result)

    def test_unicode_normalization_is_exact_not_fuzzy(self):
        self.assertEqual(
            b.normalized_name("  İlkay  GÜNDOĞAN "),
            b.normalized_name("İlkay Gündoğan"),
        )
        self.assertNotEqual(
            b.normalized_name("Ilkay Gundogan"),
            b.normalized_name("İlkay Gündoğan"),
        )


if __name__ == "__main__":
    unittest.main()
