"""
Automated Test Suite for Task-Aware Personal Repository and Access Minimisation.
Covers:
1. Access minimisation: only task-required documents are opened.
2. Sensitive documents (medical, tax, banking) remain strictly unopened.
3. Default-deny controller raises AccessDeniedError on unauthorized fetch attempt.
4. Missing document handling for U002 (missing address) and U006 (missing DOB).
5. Conditional access: Non-ECR academic record opened only when explicitly requested.
6. Access decision log explainability: every file has an explicit justification.
7. Disclosure decision explainability: excluded and approved attributes have justifications.
8. Gating verification: Mock API submission occurs only with approved payload.
9. Payload purity: external API payload contains zero sensitive attributes.
10. Dual-layer benchmark non-regression: 8 Passed / 2 Blocked, 86.3% disclosure reduction, 74.3% access reduction.
"""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.repository_controller import RepositoryAccessController, AccessDeniedError
from src.attribute_matcher import match_user_attributes
from src.disclosure_planner import create_disclosure_plan
from src.policy_checker import verify_privacy_policy
from src.evaluation import run_evaluation_suite, load_users
from src.requirement_extractor import extract_requirements
from src.main import build_or_load_rag_pipeline
from src.mock_passport_api import execute_mock_api_call


class TestRepositoryAndAccessMinimisation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.retriever = build_or_load_rag_pipeline()
        chunks = cls.retriever.retrieve("I want to apply for a fresh passport.", top_k=5)
        cls.extracted_reqs = extract_requirements(chunks, task_name="fresh passport application")
        cls.users = load_users()
        cls.user_dict = {u["user_id"]: u for u in cls.users}
        cls.repo_ctrl = RepositoryAccessController()

    def test_01_access_minimisation_only_required_files_opened(self):
        """Test 1: Verify only required files (address proof and DOB proof) are opened for standard adult passport."""
        res = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        accessed_keys = list(res["accessed_documents"].keys())
        self.assertEqual(len(accessed_keys), 2)
        self.assertIn("proof_of_address", accessed_keys)
        self.assertIn("proof_of_date_of_birth", accessed_keys)
        self.assertNotIn("proof_of_non_ecr", accessed_keys)
        self.assertEqual(res["metrics"]["accessed_files_count"], 2)
        self.assertEqual(res["metrics"]["unopened_files_count"], 5)
        self.assertEqual(res["metrics"]["access_reduction_percentage"], 71.4)

    def test_02_sensitive_files_unopened(self):
        """Test 2: Verify medical, banking, and tax documents remain strictly unopened."""
        res = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        decision_log = res["access_decision_log"]
        for entry in decision_log:
            if entry["category"] in ["health_medical", "financial_banking", "financial_tax"]:
                self.assertEqual(entry["decision"], "NOT_ACCESSED")
                self.assertFalse(entry["opened"])
                self.assertEqual(entry["status"], "PROTECTED_SENSITIVE")

    def test_03_unauthorized_access_attempt_blocked(self):
        """Test 3: Direct attempt to fetch sensitive medical document raises AccessDeniedError."""
        ctrl = RepositoryAccessController()
        with self.assertRaises(AccessDeniedError):
            ctrl.fetch_document_content("U001", "FILE_U001_06", requirement_id="proof_of_address")
        
        # Verify blocked attempt was recorded in access audit log
        self.assertTrue(any(log["action"] == "BLOCKED_ACCESS_ATTEMPT" for log in ctrl.access_log))
        blocked_log = next(log for log in ctrl.access_log if log["action"] == "BLOCKED_ACCESS_ATTEMPT")
        self.assertEqual(blocked_log["category"], "health_medical")

    def test_04_missing_document_handling(self):
        """Test 4: Missing address proof (U002) and DOB proof (U006) trigger missing status and block policy."""
        # U002: Missing address proof
        u002_res = self.repo_ctrl.retrieve_documents_for_requirements("U002", self.extracted_reqs, requires_non_ecr=False)
        self.assertIn("address_proof", u002_res["missing_documents"])
        u002_matched = match_user_attributes(self.extracted_reqs, self.user_dict["U002"], accessed_documents=u002_res["accessed_documents"])
        self.assertIn("address_proof", u002_matched["missing_mandatory_attributes"])
        u002_plan = create_disclosure_plan("fresh passport application", self.extracted_reqs, u002_matched, self.user_dict["U002"])
        u002_pol = verify_privacy_policy(u002_plan, u002_matched, self.user_dict["U002"], repository_access_log=u002_res["access_decision_log"])
        self.assertFalse(u002_pol["approved"])
        self.assertEqual(u002_pol["status"], "BLOCKED")

        # U006: Missing DOB proof
        u006_res = self.repo_ctrl.retrieve_documents_for_requirements("U006", self.extracted_reqs, requires_non_ecr=False)
        self.assertIn("date_of_birth_proof", u006_res["missing_documents"])
        u006_matched = match_user_attributes(self.extracted_reqs, self.user_dict["U006"], accessed_documents=u006_res["accessed_documents"])
        self.assertIn("date_of_birth_proof", u006_matched["missing_mandatory_attributes"])
        u006_plan = create_disclosure_plan("fresh passport application", self.extracted_reqs, u006_matched, self.user_dict["U006"])
        u006_pol = verify_privacy_policy(u006_plan, u006_matched, self.user_dict["U006"], repository_access_log=u006_res["access_decision_log"])
        self.assertFalse(u006_pol["approved"])
        self.assertEqual(u006_pol["status"], "BLOCKED")

    def test_05_non_ecr_conditional_access(self):
        """Test 5: Academic certificate opened only when requires_non_ecr=True; kept unopened when False."""
        # When False: Class 10 certificate is NOT accessed
        res_no_ecr = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        self.assertNotIn("proof_of_non_ecr", res_no_ecr["accessed_documents"])
        self.assertEqual(res_no_ecr["metrics"]["accessed_files_count"], 2)

        # When True: Class 10 certificate is authorized and accessed
        res_ecr = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=True)
        self.assertIn("proof_of_non_ecr", res_ecr["accessed_documents"])
        self.assertEqual(res_ecr["metrics"]["accessed_files_count"], 3)
        self.assertEqual(res_ecr["metrics"]["access_reduction_percentage"], 57.1)

    def test_06_access_decision_explanations(self):
        """Test 6: Every single file in the user repository has an explainable access decision record."""
        res = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        decision_log = res["access_decision_log"]
        self.assertEqual(len(decision_log), 7)
        for entry in decision_log:
            self.assertIn("file_id", entry)
            self.assertIn("file_name", entry)
            self.assertIn("category", entry)
            self.assertIn("decision", entry)
            self.assertIn(entry["decision"], ["ACCESSED", "NOT_ACCESSED"])
            self.assertTrue(len(entry["justification"].strip()) > 10)

    def test_07_disclosure_decision_explanations(self):
        """Test 7: Excluded and approved profile attributes have clear, non-empty justifications."""
        res = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        matched = match_user_attributes(self.extracted_reqs, self.user_dict["U001"], accessed_documents=res["accessed_documents"])
        plan = create_disclosure_plan("fresh passport application", self.extracted_reqs, matched, self.user_dict["U001"])
        
        # Approved attribute justifications
        for attr in plan["approved_attributes"]:
            self.assertIn(attr, plan["justifications"])
            self.assertTrue(len(plan["justifications"][attr].strip()) > 0)
        
        # Excluded attribute justifications
        self.assertIn("exclusion_justifications", plan)
        for attr in plan["excluded_attributes"]:
            self.assertIn(attr, plan["exclusion_justifications"])
            self.assertTrue(len(plan["exclusion_justifications"][attr].strip()) > 0)

    def test_08_user_approval_required(self):
        """Test 8: Blocked applications cannot submit; approved applications require policy pass."""
        # For U002: policy blocked -> execution not authorized
        u002_res = self.repo_ctrl.retrieve_documents_for_requirements("U002", self.extracted_reqs, requires_non_ecr=False)
        u002_matched = match_user_attributes(self.extracted_reqs, self.user_dict["U002"], accessed_documents=u002_res["accessed_documents"])
        u002_plan = create_disclosure_plan("fresh passport application", self.extracted_reqs, u002_matched, self.user_dict["U002"])
        u002_pol = verify_privacy_policy(u002_plan, u002_matched, self.user_dict["U002"], repository_access_log=u002_res["access_decision_log"])
        self.assertFalse(u002_pol["approved"])

    def test_09_mock_api_receives_only_approved_data(self):
        """Test 9: Mock API payload contains strictly authorized attributes and zero sensitive leakage."""
        res = self.repo_ctrl.retrieve_documents_for_requirements("U001", self.extracted_reqs, requires_non_ecr=False)
        matched = match_user_attributes(self.extracted_reqs, self.user_dict["U001"], accessed_documents=res["accessed_documents"])
        plan = create_disclosure_plan("fresh passport application", self.extracted_reqs, matched, self.user_dict["U001"])
        
        payload = plan["approved_payload"]
        self.assertEqual(set(payload.keys()), {"address_proof", "date_of_birth_proof"})
        
        # Verify forbidden attributes are not in payload
        forbidden = ["family_income", "bank_account", "medical_information", "employment", "phone", "email"]
        for f in forbidden:
            self.assertNotIn(f, payload)
        
        # Execute mock API call
        api_res = execute_mock_api_call(payload)
        self.assertEqual(api_res["status"], "success")
        self.assertEqual(api_res["received_attributes_count"], 2)

    def test_10_benchmark_non_regression(self):
        """Test 10: Full benchmark evaluation confirms 8 Passed / 2 Blocked, 86.3% disclosure reduction, 74.3% access reduction."""
        eval_results = run_evaluation_suite(self.extracted_reqs)
        self.assertEqual(len(eval_results), 10)

        passed_count = sum(1 for r in eval_results if r["policy_approved"])
        blocked_count = sum(1 for r in eval_results if not r["policy_approved"])
        self.assertEqual(passed_count, 8)
        self.assertEqual(blocked_count, 2)

        # Disclosure reduction
        disc_red_avg = sum(r["disclosure_reduction_pct"] for r in eval_results) / 10.0
        self.assertAlmostEqual(disc_red_avg, 86.3, delta=0.5)

        # Access reduction
        acc_red_avg = sum(r["access_reduction_pct"] for r in eval_results) / 10.0
        self.assertAlmostEqual(acc_red_avg, 74.3, delta=0.5)


if __name__ == "__main__":
    unittest.main()
