import json
import unittest
from pathlib import Path

from scripts import stage281_environmental_mechanism_comparisons as m


class EnvironmentalMechanismComparisonTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(
            Path("config/pbk_environmental_mechanism_comparisons_v1.json")
            .read_text(encoding="utf-8")
        )
        m.validate_contract(cls.cfg)

    def base_row(self, **extra):
        row={
            "over25_residual":"0.2",
            "total_expectation_deviation_class":"EXPECTED_OVER_ACTUAL_OVER",
            "temperature_mean_c":"18",
            "relative_humidity_mean_pct":"55",
            "precipitation_sum_mm":"0",
            "snowfall_sum_cm":"0",
            "wind_gust_max_kmh":"10",
            "visibility_min_m":"15000",
            "weather_code_mode":"0",
            "goals_total":"3",
            "shots_total":"24",
            "shots_on_goal_total":"9",
            "shots_outsidebox_total":"8",
            "goalkeeper_saves_total":"5",
            "corners_total":"9",
            "passes_accuracy_mean":"82",
            "expected_goals_total":"2.8",
        }
        row.update(extra)
        return row

    def test_cold_and_neutral_are_mutually_classified_by_frozen_bins(self):
        cold=m.exposure_flags(self.base_row(temperature_mean_c="2"))
        neutral=m.exposure_flags(self.base_row(temperature_mean_c="18"))
        self.assertIn("THERMAL_COLD",cold)
        self.assertNotIn("THERMAL_NEUTRAL",cold)
        self.assertIn("THERMAL_NEUTRAL",neutral)

    def test_hot_humid_joint_exposure(self):
        flags=m.exposure_flags(self.base_row(
            temperature_mean_c="31",
            relative_humidity_mean_pct="78",
        ))
        self.assertIn("THERMAL_HOT",flags)
        self.assertIn("HEAT_HUMIDITY",flags)

    def test_heavy_precip_and_strong_gust(self):
        flags=m.exposure_flags(self.base_row(
            precipitation_sum_mm="12",
            wind_gust_max_kmh="48",
        ))
        self.assertIn("HEAVY_PRECIPITATION",flags)
        self.assertIn("STRONG_GUST",flags)
        self.assertNotIn("DRY",flags)
        self.assertNotIn("LOW_GUST",flags)

    def test_thunderstorm_codes_are_frozen(self):
        for code in ("95","96","99"):
            self.assertIn(
                "THUNDERSTORM",
                m.exposure_flags(self.base_row(weather_code_mode=code)),
            )
        self.assertIn(
            "NO_THUNDERSTORM",
            m.exposure_flags(self.base_row(weather_code_mode="61")),
        )

    def test_bidirectional_expectation_breaks_are_counted(self):
        exposed=[
            self.base_row(
                temperature_mean_c="31",
                total_expectation_deviation_class="EXPECTED_OVER_ACTUAL_UNDER",
                over25_residual="-0.7",
            ),
            self.base_row(
                temperature_mean_c="32",
                total_expectation_deviation_class="EXPECTED_UNDER_ACTUAL_OVER",
                over25_residual="0.6",
            ),
        ]
        control=[
            self.base_row(temperature_mean_c="18"),
            self.base_row(
                temperature_mean_c="19",
                total_expectation_deviation_class="EXPECTED_UNDER_ACTUAL_UNDER",
                over25_residual="-0.3",
            ),
        ]
        rows=m.build_results(self.cfg,exposed+control)
        hot=next(r for r in rows if r["comparison_id"]=="THERMAL_HOT_vs_NEUTRAL")
        self.assertEqual(hot["expected_over_actual_under_exposed"],1)
        self.assertEqual(hot["expected_under_actual_over_exposed"],1)
        self.assertEqual(hot["sample_status"],"INSUFFICIENT_SAMPLE")

    def test_sample_gates_are_fixed(self):
        self.assertEqual(m.sample_status(self.cfg,29,1000),"INSUFFICIENT_SAMPLE")
        self.assertEqual(m.sample_status(self.cfg,30,30),"DESCRIPTIVE_READY")
        self.assertEqual(m.sample_status(self.cfg,100,100),"FORMAL_REVIEW_READY")

    def test_null_or_aligned_results_are_not_dropped(self):
        rows=[
            self.base_row(
                precipitation_sum_mm="10",
                total_expectation_deviation_class="EXPECTED_OVER_ACTUAL_OVER",
            ),
            self.base_row(
                precipitation_sum_mm="10",
                total_expectation_deviation_class="EXPECTED_UNDER_ACTUAL_UNDER",
            ),
            self.base_row(precipitation_sum_mm="0"),
        ]
        result=m.build_results(self.cfg,rows)
        precip=next(r for r in result if r["comparison_id"]=="HEAVY_PRECIPITATION_vs_DRY")
        self.assertEqual(precip["exposed_n"],2)
        self.assertEqual(precip["control_n"],1)

    def test_research_authority_never_opens(self):
        rows=m.build_results(self.cfg,[self.base_row()])
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["causal_claim_authorized"],"false")
            self.assertEqual(row["predictive_authority"],"NOT_AUTHORIZED")
            self.assertEqual(row["betting_authority"],"NOT_AUTHORIZED")
            self.assertEqual(row["automatic_model_promotion"],"false")

    def test_meta_keeps_preregistration_guards(self):
        meta=m.build_meta(self.cfg,[],[])
        self.assertTrue(meta["threshold_retargeting_after_results_forbidden"])
        self.assertTrue(meta["report_both_direction_and_null_results"])
        self.assertTrue(meta["multiple_testing_correction_required_before_formal_claim"])
        self.assertFalse(meta["automatic_model_promotion"])


if __name__=="__main__":
    unittest.main()
