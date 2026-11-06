"""Optional end-to-end app-script test; runs when Streamlit is installed."""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Streamlit not installed in test environment")
class StreamlitAppTests(unittest.TestCase):
    def test_app_renders_and_filters_update_metrics_table(self):
        from streamlit.testing.v1 import AppTest

        # Streamlit normally adds the main script's directory to sys.path.
        sys.path.insert(0, str(ROOT / "app"))
        app = AppTest.from_file(str(ROOT / "app" / "app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 3)
        self.assertIn("48.80", app.metric[0].value)
        self.assertEqual(len(app.dataframe[0].value), 14)

        app.sidebar.multiselect[0].set_value(["Riket", "Stockholm"]).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe[0].value), 28)
        app.sidebar.slider[0].set_value((2023, 2025)).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe[0].value), 6)
        self.assertIn("48.80", app.metric[0].value)
        self.assertIn("39.30", app.metric[1].value)
        app.sidebar.select_slider[0].set_value(2012).run()
        self.assertEqual(len(app.exception), 0)
        # The comparison year is independent of the trend/table range.
        self.assertEqual(len(app.dataframe[0].value), 6)


if __name__ == "__main__":
    unittest.main()
