"""
Unit tests for SEMS AI Energy Copilot Service.
Validates TNEB slab calculations, bilingual (English/Tamil) query parsing,
battery reasoning, and quick insights generation.
"""

import unittest
from services.copilot_service import (
    calculate_tneb_bill,
    copilot_service,
    EnergyCopilotService
)


class TestCopilotService(unittest.TestCase):

    def setUp(self):
        self.copilot = EnergyCopilotService()
        self.mock_telemetry = {
            "solar_power_kw": 3.8,
            "load_power_kw": 1.2,
            "battery_soc": 82.0,
            "grid_power_kw": 0.0,
            "units_used_today": 14.5,
            "recommended_action": "SOLAR + BATTERY"
        }

    def test_tneb_bill_slabs(self):
        """Validates TNEB LT-IA tiered domestic calculation."""
        # 0 units -> 0
        b0 = calculate_tneb_bill(0)
        self.assertEqual(b0["total_bill_inr"], 0.0)

        # 80 units (under 100 free subsidy)
        b80 = calculate_tneb_bill(80)
        self.assertEqual(b80["total_bill_inr"], 0.0)
        self.assertIn("Free", b80["slab_name"])

        # 200 units (100 free, 100 @ 4.70 = 470)
        b200 = calculate_tneb_bill(200)
        self.assertEqual(b200["total_bill_inr"], 470.0)

        # 450 units (100 free, 300 @ 4.70 = 1410 + 50 @ 6.30 = 315 -> 1725)
        b450 = calculate_tneb_bill(450)
        self.assertEqual(b450["total_bill_inr"], 1725.0)

    def test_quick_insights_english(self):
        insights = self.copilot.generate_quick_insights(self.mock_telemetry, lang="en")
        self.assertEqual(len(insights), 3)
        self.assertTrue(any("Solar generation" in i for i in insights))
        self.assertTrue(any("Battery reserve" in i for i in insights))

    def test_quick_insights_tamil(self):
        insights = self.copilot.generate_quick_insights(self.mock_telemetry, lang="ta")
        self.assertEqual(len(insights), 3)
        self.assertTrue(any("சூரிய" in i for i in insights))
        self.assertTrue(any("பேட்டரி" in i for i in insights))

    def test_billing_query_english(self):
        res = self.copilot.answer_query("How much is my electricity bill and savings today?", self.mock_telemetry, lang="en")
        self.assertEqual(res["category"], "billing_and_tariffs")
        self.assertEqual(res["language"], "en")
        self.assertIn("Estimated daily TNEB bill", res["answer"])
        self.assertIn("bill_today_inr", res["metrics"])

    def test_billing_query_tamil(self):
        res = self.copilot.answer_query("இன்றைய மின்சார பில் எவ்வளவு?", self.mock_telemetry, lang="ta")
        self.assertEqual(res["category"], "billing_and_tariffs")
        self.assertEqual(res["language"], "ta")
        self.assertIn("இன்றைய மின்சார கட்டண விவரம்", res["answer"])

    def test_battery_query(self):
        res = self.copilot.answer_query("How long will the battery backup last if power goes out?", self.mock_telemetry, lang="en")
        self.assertEqual(res["category"], "battery_and_resilience")
        self.assertIn("hours", res["answer"])
        self.assertGreater(res["metrics"]["backup_hours"], 0.0)

    def test_appliance_query(self):
        res = self.copilot.answer_query("Can I turn on the washing machine now?", self.mock_telemetry, lang="en")
        self.assertEqual(res["category"], "appliance_scheduling")
        self.assertTrue(res["metrics"]["can_run_heavy"])
        self.assertIn("Yes", res["answer"])


if __name__ == "__main__":
    unittest.main()
