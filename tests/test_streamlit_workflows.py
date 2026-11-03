"""
Automated Test Suite for Streamlit UI Views and Workflow State Transitions
Verifies:
1. UI style imports and CSS definitions.
2. View function imports (dashboard, passport, scholarship).
3. All 15 scholarship profiles selection and state logic.
4. Credential masking function (no raw Aadhaar/bank exposed in UI).
5. Inactive AISHE decoupled payment status.
6. Approval gating and early exit prevention in UI workflow.
7. Passport workflow integrity and zero regressions.
"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.ui.styles import SAAS_CSS, apply_saas_styles
from src.ui.dashboard_view import render_dashboard_view
from src.ui.passport_view import render_passport_view, init_passport_session_state
from src.ui.scholarship_view import (
    render_scholarship_view,
    init_scholarship_session_state,
    mask_sensitive_credential
)
from src.scholarship.scholarship_pipeline import (
    load_scholarship_users,
    run_scholarship_pipeline,
    evaluate_all_scholarship_profiles
)
from src.scholarship.mock_scholarship_api import (
    reset_mock_db,
    get_mock_application_status,
    get_mock_payment_status
)


class TestStreamlitWorkflows(unittest.TestCase):

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

    def test_credential_masking(self):
        """Verify raw Aadhaar and bank details are masked for UI display."""
        masked_aadhaar = mask_sensitive_credential("9999-0001-1111")
        self.assertEqual(masked_aadhaar, "XXXXXXXXXX1111")
        self.assertNotIn("9999-0001", masked_aadhaar)

        masked_acct = mask_sensitive_credential("50100234567890")
        self.assertEqual(masked_acct, "XXXXXXXXXX7890")
        self.assertNotIn("501002", masked_acct)

        self.assertEqual(mask_sensitive_credential(None), "None")

    def test_all_15_scholarship_profiles_in_ui_dataset(self):
        """Verify all 15 synthetic profiles load and evaluate correctly."""
        users = load_scholarship_users()
        self.assertEqual(len(users), 15, "Should load exactly 15 synthetic scholarship profiles.")

        expected = {
            "SCH001": ("PASSED", "SUBMITTED"),
            "SCH002": ("BLOCKED", "BLOCKED"),
            "SCH003": ("BLOCKED", "BLOCKED"),
            "SCH004": ("BLOCKED", "BLOCKED"),
            "SCH005": ("BLOCKED", "BLOCKED"),
            "SCH006": ("BLOCKED", "BLOCKED"),
            "SCH007": ("BLOCKED", "BLOCKED"),
            "SCH008": ("PASSED", "SUBMITTED"),
            "SCH009": ("BLOCKED", "BLOCKED"),
            "SCH010": ("PASSED", "SUBMITTED"),
            "SCH011": ("BLOCKED", "BLOCKED"),
            "SCH012": ("BLOCKED", "BLOCKED"),
            "SCH013": ("BLOCKED", "BLOCKED"),
            "SCH014": ("NEEDS_REVIEW", "NEEDS_REVIEW"),
            "SCH015": ("BLOCKED", "BLOCKED"),
        }

        results = evaluate_all_scholarship_profiles(auto_approve_passed=True)
        for r in results:
            uid = r["user_id"]
            exp_pol, exp_out = expected[uid]
            self.assertEqual(r["policy_status"], exp_pol, f"Profile {uid} policy mismatch!")
            self.assertEqual(r["execution_outcome"], exp_out, f"Profile {uid} outcome mismatch!")

    def test_ui_submission_gating(self):
        """Verify that without user_approved=True, execution outcome is PENDING_USER_APPROVAL."""
        users = load_scholarship_users()
        sch001 = users[0]

        # Without approval
        res_unapproved = run_scholarship_pipeline(sch001, user_approved=False)
        self.assertEqual(res_unapproved["policy_status"], "PASSED")
        self.assertEqual(res_unapproved["execution_outcome"], "PENDING_USER_APPROVAL")
        self.assertEqual(res_unapproved["submission_status"], "PENDING_APPROVAL")

        # With approval
        res_approved = run_scholarship_pipeline(sch001, user_approved=True)
        self.assertEqual(res_approved["policy_status"], "PASSED")
        self.assertEqual(res_approved["execution_outcome"], "SUBMITTED")
        self.assertTrue(res_approved["application_id"].startswith("NSP-2025-CSSS-"))

    def test_ui_inactive_aishe_payment_decoupling(self):
        """Verify that inactive AISHE applicant receives SUBMITTED application and PAYMENT_PENDING payment readiness."""
        users = load_scholarship_users()
        sch_inactive = dict(users[0])
        sch_inactive["aishe_status"] = "INACTIVE"

        res = run_scholarship_pipeline(sch_inactive, user_approved=True)
        self.assertEqual(res["policy_status"], "PASSED")
        self.assertEqual(res["execution_outcome"], "SUBMITTED")
        app_id = res["application_id"]

        # Check decoupled payment status
        pay_res = get_mock_payment_status(app_id)
        self.assertEqual(pay_res["payment_status"], "PAYMENT_PENDING")
        self.assertFalse(pay_res["dbt_ready"])
        self.assertIn("INACTIVE", pay_res["hold_reason"])

    def test_passport_benchmark_non_regression(self):
        """Verify Passport 10 profiles remain completely stable."""
        from src.evaluation import load_users as load_pass_users, run_evaluation_suite
        from src.requirement_extractor import extract_requirements
        from src.main import build_or_load_rag_pipeline

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


if __name__ == "__main__":
    unittest.main()
