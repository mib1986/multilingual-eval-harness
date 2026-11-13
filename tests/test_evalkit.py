"""Tests for evalkit. Run with: python -m unittest discover -s tests -v"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from evalkit import agreement, analyze, report, rubric  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestAgreement(unittest.TestCase):
    def test_median_odd_and_even(self):
        self.assertEqual(agreement.median([3, 1, 2]), 2.0)
        self.assertEqual(agreement.median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(agreement.median([]))

    def test_all_equal(self):
        self.assertTrue(agreement.all_equal([4, 4, 4]))
        self.assertFalse(agreement.all_equal([4, 4, 5]))
        self.assertFalse(agreement.all_equal([]))

    def test_within_tolerance(self):
        self.assertTrue(agreement.within_tolerance([4, 5, 4], 1))
        self.assertFalse(agreement.within_tolerance([3, 5], 1))

    def test_mean_abs_deviation(self):
        self.assertAlmostEqual(agreement.mean_abs_deviation([5, 5, 5]), 0.0)
        # median is 4, distances are 2, 0, 0 -> 2/3
        self.assertAlmostEqual(agreement.mean_abs_deviation([2, 4, 4]), 2 / 3, places=6)

    def test_fleiss_kappa_perfect_agreement(self):
        self.assertEqual(agreement.fleiss_kappa([[5, 5], [3, 3], [1, 1]]), 1.0)

    def test_fleiss_kappa_known_value(self):
        # 3 items, 2 raters, 2 categories: two items agree, one splits.
        # P_bar = 2/3, p_1 = 5/6, p_0 = 1/6 -> kappa = -0.2
        self.assertAlmostEqual(agreement.fleiss_kappa([[1, 1], [1, 1], [1, 0]]), -0.2, places=6)

    def test_fleiss_kappa_single_category_constant(self):
        self.assertEqual(agreement.fleiss_kappa([[5, 5, 5], [5, 5, 5]]), 1.0)

    def test_fleiss_kappa_requires_two_ratings(self):
        self.assertIsNone(agreement.fleiss_kappa([[5], [4]]))

    def test_fleiss_kappa_varying_rater_counts(self):
        kappa = agreement.fleiss_kappa([[4, 4, 4], [4, 4], [3, 4]])
        self.assertIsNotNone(kappa)
        self.assertGreaterEqual(kappa, -1.0)
        self.assertLessEqual(kappa, 1.0)


class TestRubric(unittest.TestCase):
    def test_sample_rubric_is_valid(self):
        data = rubric.load_rubric(str(ROOT / "rubric.json"))
        self.assertEqual(len(data["dimensions"]), 4)
        self.assertAlmostEqual(sum(d["weight"] for d in data["dimensions"]), 1.0)

    def test_weights_must_sum_to_one(self):
        bad = {
            "scale": {"min": 1, "max": 5},
            "dimensions": [
                {"id": "a", "weight": 0.6},
                {"id": "b", "weight": 0.6},
            ],
        }
        with self.assertRaises(rubric.RubricError):
            rubric.validate(bad, source="test")

    def test_duplicate_dimension_ids_rejected(self):
        bad = {
            "scale": {"min": 1, "max": 5},
            "dimensions": [{"id": "a", "weight": 0.5}, {"id": "a", "weight": 0.5}],
        }
        with self.assertRaises(rubric.RubricError):
            rubric.validate(bad, source="test")


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.spec = rubric.load_rubric(str(ROOT / "rubric.json"))
        self.records = analyze.load_annotations(str(ROOT / "data" / "sample_annotations.jsonl"))
        self.result = analyze.compute(self.records, self.spec)

    def test_shape(self):
        self.assertEqual(self.result["n_items"], 10)
        self.assertEqual(self.result["n_raters"], 3)
        self.assertEqual(self.result["n_annotations"], 30)
        self.assertEqual(len(self.result["by_dimension"]), 4)

    def test_rates_are_probabilities(self):
        overall = self.result["overall"]
        for key in ("exact_rate", "adjacent_rate"):
            self.assertGreaterEqual(overall[key], 0.0)
            self.assertLessEqual(overall[key], 1.0)
        self.assertGreaterEqual(overall["exact_rate"], 0.0)

    def test_adjacent_at_least_exact(self):
        self.assertGreaterEqual(self.result["overall"]["adjacent_rate"], self.result["overall"]["exact_rate"])

    def test_queue_is_sorted_by_spread(self):
        spreads = [row["spread"] for row in self.result["disagreements"]]
        self.assertEqual(spreads, sorted(spreads, reverse=True))

    def test_queue_respects_threshold(self):
        for row in self.result["disagreements"]:
            self.assertTrue(row["spread"] >= 2 or row["mad"] >= 0.75)

    def test_no_out_of_scale_scores(self):
        self.assertEqual(self.result["out_of_scale"], [])

    def test_weighted_score_ignores_missing_dimensions(self):
        dims = self.spec["dimensions"]
        full = analyze.weighted_score({d["id"]: 5 for d in dims}, dims)
        partial = analyze.weighted_score({"factuality": 5}, dims)
        self.assertAlmostEqual(full, 5.0)
        self.assertAlmostEqual(partial, 5.0)

    def test_markdown_renders(self):
        text = report.to_markdown(self.result, source="data/sample_annotations.jsonl")
        self.assertIn("# 评测一致性报告", text)
        self.assertIn("## 四、待仲裁清单", text)
        self.assertGreater(len(text), 800)


if __name__ == "__main__":
    unittest.main()
