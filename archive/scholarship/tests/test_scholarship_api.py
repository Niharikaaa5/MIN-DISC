"""
Unit Tests for Mock Scholarship NSP / PFMS API
Verifies FastAPI endpoints, privacy enforcement, policy verification gating,
quarantine enforcement, application status retrieval, and decoupled payment readiness.
"""
import unittest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.scholarship.mock_scholarship_api import (
    app,
    reset_mock_db,
    submit_mock_scholarship_application,
    get_mock_application_status,
    get_mock_payment_status
)


class TestMockScholarshipApi(unittest.TestCase):

    def setUp(self):
        reset_mock_db()
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test GET /health returns service metadata and mock disclaimer."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("Mock NSP", data["service"])
        self.assertIn("SIMULATED", data["mock_disclaimer"])

    def test_successful_application_submission(self):
        """Test POST /scholarship/apply with policy-approved minimum-disclosure payload."""
        valid_payload = {
            "applicant_id": "SCH001",
            "applicant_name": "Aditya Sharma",
            "aishe_status": "ACTIVE",
            "portal_application_fields": {
                "applicant_name": "Aditya Sharma",
                "otr_number": "OTR_2025_0001",
                "domicile_state": "Karnataka",
                "class_12_roll_no": "KA-2025-1001",
                "passing_year": 2025,
                "stream": "Science",
                "course_name": "B.Tech Computer Science",
                "institution_name": "National College of Engineering",
                "aishe_code": "C-10001",
                "caste_category": "General"
            },
            "approved_supporting_documents": {
                "class_12_marksheet": "DOC_MARKS_001",
                "income_certificate": "DOC_INC_001"
            },
            "policy_verification": {
                "policy_status": "PASSED",
                "policy_approved": True
            }
        }
        res = submit_mock_scholarship_application(valid_payload)
        self.assertEqual(res["status"], "SUBMITTED")
        self.assertIn("application_id", res)
        self.assertTrue(res["application_id"].startswith("NSP-2025-CSSS-"))
        self.assertEqual(res["disclosed_fields_count"], 10)
        self.assertEqual(res["disclosed_documents_count"], 2)

        # Verify application status endpoint
        app_id = res["application_id"]
        status_res = get_mock_application_status(app_id)
        self.assertEqual(status_res["application_status"], "SUBMITTED")
        self.assertEqual(status_res["current_stage"], "UNDER_INSTITUTE_VERIFICATION")

        # Verify payment status endpoint (Active AISHE -> PAYMENT_READY)
        pay_res = get_mock_payment_status(app_id)
        self.assertEqual(pay_res["payment_status"], "PAYMENT_READY")
        self.assertTrue(pay_res["dbt_ready"])

    def test_inactive_aishe_payment_hold(self):
        """Test application submission with INACTIVE AISHE status: registers successfully, payment is on hold."""
        inactive_payload = {
            "applicant_id": "SCH001_INACTIVE",
            "applicant_name": "Aditya Sharma",
            "aishe_status": "INACTIVE",
            "portal_application_fields": {
                "applicant_name": "Aditya Sharma",
                "otr_number": "OTR_2025_0001",
                "aishe_code": "C-10001",
                "caste_category": "General"
            },
            "approved_supporting_documents": {
                "class_12_marksheet": "DOC_MARKS_001",
                "income_certificate": "DOC_INC_001"
            },
            "policy_verification": {
                "policy_status": "PASSED",
                "policy_approved": True
            }
        }
        res = submit_mock_scholarship_application(inactive_payload)
        self.assertEqual(res["status"], "SUBMITTED")
        app_id = res["application_id"]

        # Application is SUBMITTED
        status_res = get_mock_application_status(app_id)
        self.assertEqual(status_res["application_status"], "SUBMITTED")

        # Payment status is PAYMENT_PENDING with DOC-2 Q18 reason
        pay_res = get_mock_payment_status(app_id)
        self.assertEqual(pay_res["payment_status"], "PAYMENT_PENDING")
        self.assertFalse(pay_res["dbt_ready"])
        self.assertIn("INACTIVE", pay_res["hold_reason"])
        self.assertIn("DOC-2 Q18", pay_res["hold_reason"])

    def test_rejection_without_policy_approval(self):
        """Test POST /scholarship/apply rejects payload missing policy approval."""
        unapproved_payload = {
            "applicant_id": "SCH001",
            "portal_application_fields": {"applicant_name": "Aditya Sharma"},
            "policy_verification": {"policy_status": "BLOCKED", "policy_approved": False}
        }
        res = submit_mock_scholarship_application(unapproved_payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["status_code"], 400)
        self.assertIn("POLICY_ENFORCEMENT_ERROR", res["error"])

    def test_rejection_of_quarantined_payment_leakage(self):
        """Test POST /scholarship/apply strictly blocks raw Aadhaar or bank account leakage."""
        tampered_payload = {
            "applicant_id": "SCH001",
            "portal_application_fields": {
                "applicant_name": "Aditya Sharma",
                "bank_account_number": "ACCT_99880001"  # Leaked!
            },
            "policy_verification": {"policy_status": "PASSED", "policy_approved": True}
        }
        res = submit_mock_scholarship_application(tampered_payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["status_code"], 400)
        self.assertIn("PRIVACY_VIOLATION_PAYMENT_CREDENTIALS", res["error"])

    def test_rejection_of_cross_workflow_passport_attributes(self):
        """Test POST /scholarship/apply blocks passport attributes."""
        passport_polluted_payload = {
            "applicant_id": "SCH001",
            "portal_application_fields": {"applicant_name": "Aditya Sharma"},
            "approved_supporting_documents": {
                "class_12_marksheet": "DOC_MARKS_001",
                "address_proof": "PASSPORT_ADDRESS_PROOF"  # Leaked passport doc!
            },
            "policy_verification": {"policy_status": "PASSED", "policy_approved": True}
        }
        res = submit_mock_scholarship_application(passport_polluted_payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["status_code"], 400)
        self.assertIn("PRIVACY_VIOLATION_CROSS_WORKFLOW", res["error"])

    def test_rejection_of_internal_profile_evaluations(self):
        """Test POST /scholarship/apply blocks transmission of internal evaluation data like family_income."""
        internal_leak_payload = {
            "applicant_id": "SCH001",
            "portal_application_fields": {
                "applicant_name": "Aditya Sharma",
                "family_income": 320000  # Should remain internal evaluation!
            },
            "policy_verification": {"policy_status": "PASSED", "policy_approved": True}
        }
        res = submit_mock_scholarship_application(internal_leak_payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["status_code"], 400)
        self.assertIn("PRIVACY_VIOLATION_INTERNAL_DATA", res["error"])

    def test_rejection_of_unnecessary_caste_certificate(self):
        """Test POST /scholarship/apply rejects over-disclosure of caste certificate for General applicant."""
        overdisclosed_payload = {
            "applicant_id": "SCH001",
            "portal_application_fields": {
                "applicant_name": "Aditya Sharma",
                "caste_category": "General"
            },
            "approved_supporting_documents": {
                "class_12_marksheet": "DOC_MARKS_001",
                "income_certificate": "DOC_INC_001",
                "caste_certificate": "DOC_UNNECESSARY_CASTE"  # Over-disclosure!
            },
            "policy_verification": {"policy_status": "PASSED", "policy_approved": True}
        }
        res = submit_mock_scholarship_application(overdisclosed_payload)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["status_code"], 400)
        self.assertIn("OVER_DISCLOSURE_ERROR", res["error"])

    def test_unknown_application_id_404(self):
        """Test retrieving non-existent application returns 404."""
        status_res = get_mock_application_status("NON_EXISTENT_ID")
        self.assertEqual(status_res["status"], "ERROR")
        self.assertEqual(status_res["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
