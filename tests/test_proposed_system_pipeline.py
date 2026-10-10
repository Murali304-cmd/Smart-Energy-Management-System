#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Automated unit test suite verifying the 13 stages of the proposed SEMS architecture.
"""

import sys
import unittest
import urllib.request
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_URL = "http://127.0.0.1:8080"


class TestProposedSystemPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            url = f"{SERVER_URL}/api/system/pipeline-verification"
            req = urllib.request.Request(url, headers={"User-Agent": "SEMS-TestSuite/1.0"})
            with urllib.request.urlopen(req, timeout=2) as response:
                cls.report = json.loads(response.read().decode('utf-8'))

            acc_url = f"{SERVER_URL}/api/models/accuracy"
            req_acc = urllib.request.Request(acc_url, headers={"User-Agent": "SEMS-TestSuite/1.0"})
            with urllib.request.urlopen(req_acc, timeout=2) as response:
                cls.accuracy = json.loads(response.read().decode('utf-8'))
        except Exception:
            # Fall back to FastAPI in-process TestClient for offline execution
            from fastapi.testclient import TestClient
            from server import app
            client = TestClient(app)
            r1 = client.get("/api/system/pipeline-verification")
            cls.report = r1.json()
            r2 = client.get("/api/models/accuracy")
            cls.accuracy = r2.json()

    def test_overall_pipeline_status(self):
        """Asserts that all 13 stages pass and report status 'ALL_13_STAGES_PASS'."""
        self.assertEqual(self.report.get("status"), "success")
        self.assertEqual(self.report.get("overall_status"), "ALL_13_STAGES_PASS")
        self.assertEqual(len(self.report.get("stages", [])), 13)

    def test_stage_01_live_data_sources(self):
        stage = self.report["stages"][0]
        self.assertEqual(stage["stage"], 1)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_02_data_preprocessing(self):
        stage = self.report["stages"][1]
        self.assertEqual(stage["stage"], 2)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_03_prediction_layer_and_accuracy(self):
        stage = self.report["stages"][2]
        self.assertEqual(stage["stage"], 3)
        self.assertEqual(stage["status"], "PASS")

        # Verify accuracy figures are > 90%
        models = self.accuracy.get("models", {})
        solar_acc = float(models["solar_mlp"]["metrics"]["Accuracy"].replace("%", ""))
        load_acc = float(models["load_lstm"]["metrics"]["Accuracy"].replace("%", ""))
        price_acc = float(models["price_xgboost"]["metrics"]["Accuracy"].replace("%", ""))

        self.assertGreater(solar_acc, 90.0, "Solar MLP accuracy should exceed 90%")
        self.assertGreater(load_acc, 88.0, "Load LSTM accuracy should exceed 88%")
        self.assertGreater(price_acc, 90.0, "Price XGBoost accuracy should exceed 90%")

    def test_stage_04_battery_soc(self):
        stage = self.report["stages"][3]
        self.assertEqual(stage["stage"], 4)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_05_user_budget_and_constraints(self):
        stage = self.report["stages"][4]
        self.assertEqual(stage["stage"], 5)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_06_state_representation(self):
        stage = self.report["stages"][5]
        self.assertEqual(stage["stage"], 6)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_07_dqn_agent_decision(self):
        stage = self.report["stages"][6]
        self.assertEqual(stage["stage"], 7)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_08_intelligent_action_power_dispatch(self):
        stage = self.report["stages"][7]
        self.assertEqual(stage["stage"], 8)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_09_energy_optimization(self):
        stage = self.report["stages"][8]
        self.assertEqual(stage["stage"], 9)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_10_explainable_ai(self):
        stage = self.report["stages"][9]
        self.assertEqual(stage["stage"], 10)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_11_monitoring_analytics(self):
        stage = self.report["stages"][10]
        self.assertEqual(stage["stage"], 11)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_12_dashboard(self):
        stage = self.report["stages"][11]
        self.assertEqual(stage["stage"], 12)
        self.assertEqual(stage["status"], "PASS")

    def test_stage_13_user_notifications(self):
        stage = self.report["stages"][12]
        self.assertEqual(stage["stage"], 13)
        self.assertEqual(stage["status"], "PASS")


if __name__ == '__main__':
    unittest.main()
