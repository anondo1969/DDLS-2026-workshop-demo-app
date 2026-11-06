"""Data-to-Plotly chart tests that do not need a running browser."""

import unittest

from app.charts import build_comparison_chart, build_trend_chart
from app.data import DATA_PATH, comparison_for_year, filter_trends, load_data


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data(DATA_PATH)

    def test_trend_has_selected_areas_in_year_order(self):
        selected = filter_trends(self.data, ["Riket", "Stockholm"], (2021, 2023))
        chart = build_trend_chart(selected)
        self.assertEqual(len(chart.data), 2)
        self.assertEqual(set(trace.name for trace in chart.data), {"Riket", "Stockholm"})
        for trace in chart.data:
            self.assertEqual(list(trace.x), [2021, 2022, 2023])
            self.assertIn("per 1,000", trace.hovertemplate)
            self.assertIn("ADHD medication", trace.hovertemplate)
        self.assertEqual(chart.layout.xaxis.title.text, "Year")
        self.assertIn("ADHD medication", chart.layout.yaxis.title.text)
        self.assertEqual(chart.layout.legend.title.text, "Area")

    def test_legend_stays_readable_for_many_areas(self):
        areas = self.data["area"].unique().tolist()[:12]
        selected = filter_trends(self.data, areas, (2023, 2025))
        chart = build_trend_chart(selected)
        self.assertEqual(len(chart.data), 12)
        self.assertEqual(chart.layout.legend.orientation, "v")
        self.assertGreater(chart.layout.height, 500)

    def test_comparison_has_21_regions_and_actual_reference_line(self):
        regions, national = comparison_for_year(self.data, 2025)
        chart = build_comparison_chart(regions, national)
        self.assertEqual(len(chart.data), 1)
        bars = chart.data[0]
        self.assertEqual(len(bars.x), 21)
        self.assertEqual(list(bars.y), regions["area"].tolist())
        self.assertEqual(list(bars.x), sorted(bars.x))
        self.assertEqual(len(chart.layout.shapes), 1)
        self.assertAlmostEqual(float(chart.layout.shapes[0].x0), 48.80)
        self.assertIn("per 1,000", bars.hovertemplate)
        self.assertIn("ADHD medication", bars.hovertemplate)
        self.assertIn("per 1,000 inhabitants", chart.layout.xaxis.title.text)
        self.assertEqual(chart.layout.yaxis.title.text, "Region")

    def test_comparison_year_changes_reference(self):
        region_2012, national_2012 = comparison_for_year(self.data, 2012)
        chart = build_comparison_chart(region_2012, national_2012)
        self.assertEqual(national_2012, 16.32)
        self.assertAlmostEqual(float(chart.layout.shapes[0].x0), 16.32)


if __name__ == "__main__":
    unittest.main()
