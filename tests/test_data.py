"""Checks of the original dataset and intentionally corrupted temporary copies."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.data import (
    CSV_NAME,
    DATA_PATH,
    DataValidationError,
    comparison_for_year,
    filter_trends,
    load_data,
    summarize_area,
)


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(DATA_PATH)

    def assert_invalid(self, altered: pd.DataFrame, expected_part: str):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / CSV_NAME
            altered.to_csv(csv_path, index=False)
            with self.assertRaises(DataValidationError) as caught:
                load_data(csv_path)
        self.assertIn(expected_part, str(caught.exception))

    def test_uploaded_csv_structure(self):
        self.assertEqual(len(self.data), 308)
        self.assertEqual(self.data["area"].nunique(), 22)
        self.assertEqual(self.data["year"].nunique(), 14)
        self.assertEqual(self.data.loc[self.data.area_type == "Region", "area"].nunique(), 21)
        self.assertEqual(sorted(self.data.year.unique().tolist()), list(range(2012, 2026)))
        self.assertTrue(self.data["year"].is_monotonic_increasing)
        self.assertEqual(self.data.isna().sum().sum(), 0)
        self.assertEqual(self.data.duplicated(["area", "year"]).sum(), 0)

    def test_national_endpoints_are_source_values(self):
        self.assertEqual(float(self.data.query("area == 'Riket' and year == 2012").iloc[0].treated_per_1000), 16.32)
        self.assertEqual(float(self.data.query("area == 'Riket' and year == 2025").iloc[0].treated_per_1000), 48.80)

    def test_trend_filters_and_absolute_rate_change(self):
        filtered = filter_trends(self.data, ["Riket", "Stockholm"], (2022, 2025))
        self.assertEqual(len(filtered), 8)
        self.assertEqual(set(filtered["area"]), {"Riket", "Stockholm"})
        self.assertEqual(set(filtered["year"]), {2022, 2023, 2024, 2025})
        national = summarize_area(filtered, "Riket")
        self.assertEqual((national.first_year, national.latest_year), (2022, 2025))
        self.assertAlmostEqual(national.absolute_change, 48.80 - 34.86)
        initial = summarize_area(filter_trends(self.data, ["Riket"], (2012, 2025)), "Riket")
        self.assertAlmostEqual(initial.absolute_change, 32.48)
        self.assertEqual(len(filter_trends(self.data, ["Riket"], (2025, 2025))), 1)

    def test_region_comparison_uses_original_national_rate(self):
        regions, national = comparison_for_year(self.data, 2025)
        self.assertEqual(len(regions), 21)
        self.assertNotIn("Riket", regions["area"].tolist())
        self.assertEqual(national, 48.80)
        self.assertTrue(regions["treated_per_1000"].is_monotonic_increasing)
        self.assertNotAlmostEqual(national, regions["treated_per_1000"].mean(), places=3)

    def test_missing_csv_has_actionable_error(self):
        with self.assertRaises(DataValidationError) as caught:
            load_data(Path(tempfile.gettempdir()) / "nonexistent_workshop_adhd.csv")
        self.assertIn("data/" + CSV_NAME, str(caught.exception))

    def test_extra_column_is_rejected(self):
        altered = pd.read_csv(DATA_PATH)
        altered["unused"] = 0
        self.assert_invalid(altered, "Unexpected columns: unused")

    def test_missing_column_is_rejected(self):
        altered = pd.read_csv(DATA_PATH).drop(columns="area_type")
        self.assert_invalid(altered, "Missing required columns: area_type")

    def test_duplicate_pair_is_rejected(self):
        altered = pd.concat([pd.read_csv(DATA_PATH), pd.read_csv(DATA_PATH).iloc[[0]]], ignore_index=True)
        self.assert_invalid(altered, "Repeated area-year pair")

    def test_missing_numeric_value_is_rejected(self):
        altered = pd.read_csv(DATA_PATH)
        altered.loc[0, "treated_per_1000"] = None
        self.assert_invalid(altered, "Missing, nonnumeric, or nonfinite treated_per_1000")

    def test_non_numeric_and_fractional_year_are_rejected(self):
        altered = pd.read_csv(DATA_PATH, dtype=str)
        altered.loc[0, "year"] = "2012.5"
        self.assert_invalid(altered, "noninteger year")
        altered.loc[0, "year"] = "not-a-year"
        self.assert_invalid(altered, "nonnumeric")

    def test_year_rounded_by_float_would_be_invalid(self):
        original = pd.read_csv(DATA_PATH, dtype=str)
        for invalid_year in ("2012.0000000000000001", "2012.0", "1e100", "2011", "2026"):
            with self.subTest(invalid_year=invalid_year):
                altered = original.copy()
                altered.loc[0, "year"] = invalid_year
                self.assert_invalid(altered, "noninteger year")

    def test_missing_and_nonfinite_rates_are_rejected(self):
        original = pd.read_csv(DATA_PATH, dtype=str)
        for invalid_rate in ("", "Infinity", "-1", "1e309"):
            with self.subTest(invalid_rate=invalid_rate):
                altered = original.copy()
                altered.loc[0, "treated_per_1000"] = invalid_rate
                self.assert_invalid(altered, "treated_per_1000")

    def test_mismatched_area_type_is_rejected(self):
        altered = pd.read_csv(DATA_PATH)
        altered.loc[(altered.area == "Riket") & (altered.year == 2012), "area_type"] = "Region"
        self.assert_invalid(altered, "area_type mismatch")

    def test_invalid_national_reference_is_rejected(self):
        altered = pd.read_csv(DATA_PATH)
        altered.loc[(altered.area == "Riket") & (altered.year == 2025), "treated_per_1000"] = 48.81
        self.assert_invalid(altered, "Riket 2025 must be 48.80")

    def test_missing_observation_is_rejected(self):
        altered = pd.read_csv(DATA_PATH).iloc[1:].copy()
        self.assert_invalid(altered, "Missing area-year observations")


if __name__ == "__main__":
    unittest.main()
