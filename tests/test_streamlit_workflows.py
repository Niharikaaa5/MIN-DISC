"""
Automated Test Suite for Streamlit UI Views and Passport Workflow State Transitions
Verifies:
1. UI style imports and SaaS CSS definitions.
2. View function imports (dashboard, passport).
3. Passport workflow session state initialization.
4. Verification that scholarship modules and assets are NOT imported or loaded in the active app.
5. Passport workflow integrity, non-regression, and deterministic policy benchmark.
"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.ui.styles import SAAS_CSS, apply_saas_styles
from src.ui.dashboard_view import render_dashboard_view
from src.ui.passport_view import render_passport_view, init_passport_session_state
from src.evaluation import load_users as load_pass_users, run_evaluation_suite
from src.requirement_extractor import extract_requirements
from src.main import build_or_load_rag_pipeline
from src.mock_passport_api import execute_mock_api_call


class TestPassportWorkflows(unittest.TestCase):

    def test_css_styles_defined(self):
        """Verify SaaS stylesheet contains required classes and design tokens."""
        self.assertIn("workflow-card", SAAS_CSS)
        self.assertIn("card-passed", SAAS_CSS)
        self.assertIn("card-blocked", SAAS_CSS)
        self.assertIn("card-review", SAAS_CSS)
        self.assertIn("stage-box", SAAS_CSS)
        self.assertIn("#15803D", SAAS_CSS)  # Dark green
        self.assertIn("#DC2626", SAAS_CSS)  # Red
        self.assertIn("#D97706", SAAS_CSS)  # Amber
        self.assertIn("#0F172A", SAAS_CSS)  # Navy / Slate

    def test_passport_session_state_init(self):
        """Verify Passport view initialization functions exist and are callable."""
        self.assertTrue(callable(init_passport_session_state))
        self.assertTrue(callable(render_passport_view))
        self.assertTrue(callable(render_dashboard_view))

    def test_scholarship_assets_not_in_active_path(self):
        """Verify scholarship package and view are not present in active src/."""
        active_scholarship_dir = ROOT_DIR / "src" / "scholarship"
        active_scholarship_view = ROOT_DIR / "src" / "ui" / "scholarship_view.py"
        active_scholarship_reqs = ROOT_DIR / "data" / "requirements" / "scholarship"
        active_scholarship_users = ROOT_DIR / "data" / "users" / "scholarship_users.json"

        self.assertFalse(active_scholarship_dir.exists(), "src/scholarship should be archived.")
        self.assertFalse(active_scholarship_view.exists(), "src/ui/scholarship_view.py should be archived.")
        self.assertFalse(active_scholarship_reqs.exists(), "data/requirements/scholarship should be archived.")
        self.assertFalse(active_scholarship_users.exists(), "data/users/scholarship_users.json should be archived.")

    def test_passport_dataset_and_users(self):
        """Verify 10 standardized synthetic Passport profiles load correctly."""
        p_users = load_pass_users()
        self.assertEqual(len(p_users), 10, "Should load exactly 10 synthetic Passport profiles (U001 - U010).")
        user_ids = [u["user_id"] for u in p_users]
        self.assertEqual(user_ids, [f"U{i:03d}" for i in range(1, 11)])

    def test_passport_mock_api(self):
        """Verify Passport mock API accepts approved payload and records correct attributes."""
        test_payload = {
            "address_proof": "PASSPORT_ADDRESS_PROOF_DOC",
            "date_of_birth_proof": "PASSPORT_DOB_PROOF_DOC"
        }
        res = execute_mock_api_call(test_payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["received_attributes_count"], 2)
        self.assertIn("address_proof", res["received_attributes"])
        self.assertIn("date_of_birth_proof", res["received_attributes"])

    def test_passport_benchmark_non_regression(self):
        """Verify Passport 10 profiles remain completely stable."""
        p_users = load_pass_users()
        self.assertEqual(len(p_users), 10)

        retriever = build_or_load_rag_pipeline()
        chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=3)
        reqs = extract_requirements(chunks, task_name="fresh passport application")
        eval_res = run_evaluation_suite(reqs)
        self.assertEqual(len(eval_res), 10)

        passed_cnt = sum(1 for r in eval_res if r["policy_approved"])
        blocked_cnt = sum(1 for r in eval_res if not r["policy_approved"])
        self.assertEqual(passed_cnt, 8)
        self.assertEqual(blocked_cnt, 2)

        # Average disclosure reduction verification
        red_sum = sum(r["disclosure_reduction_pct"] for r in eval_res)
        avg_red = red_sum / len(eval_res)
        self.assertAlmostEqual(avg_red, 86.3, delta=0.5)


if __name__ == "__main__":
    unittest.main()
