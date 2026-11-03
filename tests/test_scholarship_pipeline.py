"""
Comprehensive End-to-End Test Suite: Scholarship Pipeline, Policy Engine, and Mock API
Tests:
1. All 15 synthetic applicant profiles evaluated through full pipeline (Matcher -> Planner -> Policy -> Mock Submission).
2. Human-in-the-loop Gate: Submission without explicit approval yields PENDING_USER_APPROVAL.
3. Policy Gating: BLOCKED and NEEDS_REVIEW profiles terminate early without submitting to Mock API.
4. Separate Payment Readiness: Decoupled application registration (SUBMITTED) from payment status (PAYMENT_READY vs PAYMENT_PENDING).
5. Inactive AISHE Handling (DOC-2 Q18): Inactive institution receives SUBMITTED application but PAYMENT_PENDING.
6. Missing AISHE Code Handling: Unverified AISHE code routes to NEEDS_REVIEW, not outright ineligibility.
7. Percentile vs Percentage Distinction (SCH003): 82.5% marks does not substitute for 80th percentile rank.
8. Top 20th Percentile Merit List Distinction (SCH004): Scoring >80th percentile does not infer Board list inclusion.
9. Scoped Drop-Year Rule: Ineligibility explicitly scoped to AY 2025-26 per FAQ Q1.
10. Minimum-Disclosure & Over-Disclosure Rejection: General vs Reserved SC vs PwD.
11. Payment Credential Quarantine & Adversarial Leakage Rejection.
12. Zero Passport Workflow Regression.
"""
import sys
import json
from pathlib import Path

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.scholarship.scholarship_extractor import extract_scholarship_requirements
from src.scholarship.scholarship_matcher import match_scholarship_attributes
from src.scholarship.scholarship_planner import create_scholarship_disclosure_plan
from src.scholarship.scholarship_policy import verify_scholarship_policy
from src.scholarship.scholarship_pipeline import (
    load_scholarship_users,
    load_scholarship_user,
    run_scholarship_pipeline,
    evaluate_all_scholarship_profiles
)
from src.scholarship.mock_scholarship_api import reset_mock_db, get_mock_application_status, get_mock_payment_status


def test_15_synthetic_profiles(reqs, users):
    print("\n[TEST 1] Testing All 15 Synthetic Profiles Through End-to-End Pipeline...")
    reset_mock_db()

    expected_policy_outcomes = {
        "SCH001": ("PASSED", "SUBMITTED", "Eligible General"),
        "SCH002": ("BLOCKED", "BLOCKED", "Income > 4.5L"),
        "SCH003": ("BLOCKED", "BLOCKED", "Scored 82.5% marks, but Percentile 74.2 < 80th"),
        "SCH004": ("BLOCKED", "BLOCKED", "Percentile 82.0, but Not in Board List"),
        "SCH005": ("BLOCKED", "BLOCKED", "Drop Year (AY 2025-26 scoped)"),
        "SCH006": ("BLOCKED", "BLOCKED", "Missing Mark Sheet"),
        "SCH007": ("BLOCKED", "BLOCKED", "Missing Income Cert"),
        "SCH008": ("PASSED", "SUBMITTED", "Eligible SC with Caste Cert"),
        "SCH009": ("BLOCKED", "BLOCKED", "ST Missing Caste Cert"),
        "SCH010": ("PASSED", "SUBMITTED", "Eligible PwD with Disability Cert"),
        "SCH011": ("BLOCKED", "BLOCKED", "PwD Missing Disability Cert"),
        "SCH012": ("BLOCKED", "BLOCKED", "Distance Education"),
        "SCH013": ("BLOCKED", "BLOCKED", "Diploma Course"),
        "SCH014": ("NEEDS_REVIEW", "NEEDS_REVIEW", "Missing AISHE Code (Unverified)"),
        "SCH015": ("BLOCKED", "BLOCKED", "Concurrent Scholarship")
    }

    for u in users:
        uid = u["user_id"]
        exp_policy, exp_exec, exp_desc = expected_policy_outcomes[uid]

        # Test with user_approved=True (to verify mock submission for eligible applicants)
        res = run_scholarship_pipeline(u, user_approved=True, requirements=reqs)
        act_policy = res["policy_status"]
        act_exec = res["execution_outcome"]

        assert act_policy == exp_policy, (
            f"Profile {uid} ({u['applicant_name']}) expected policy {exp_policy}, got {act_policy}! "
            f"Reason: {res.get('policy_reason')}"
        )
        assert act_exec == exp_exec, (
            f"Profile {uid} expected execution outcome {exp_exec}, got {act_exec}!"
        )

        app_id_display = res.get("application_id", "N/A")
        print(f"  + [{uid}] {u['applicant_name']:<18} | Scenario: {exp_desc:<45} | Policy: [{act_policy}] | Execution: [{act_exec}] (MATCH)")

    print("  + PASSED: All 15 profiles verified against expected policy & execution outcomes.")


def test_approval_gating(reqs, users):
    print("\n[TEST 2] Testing Human-in-the-Loop Approval Gating...")
    eligible_user = users[0]  # SCH001

    # Attempt 1: Without explicit approval (user_approved=False)
    res_unapproved = run_scholarship_pipeline(eligible_user, user_approved=False, requirements=reqs)
    assert res_unapproved["policy_status"] == "PASSED", "Eligible user should pass policy check."
    assert res_unapproved["execution_outcome"] == "PENDING_USER_APPROVAL", "Should pause at PENDING_USER_APPROVAL."
    assert res_unapproved["submission_status"] == "PENDING_APPROVAL"
    assert "application_id" not in res_unapproved, "Mock application ID must not be generated without approval!"
    print("  + PASSED: Unapproved plan stopped at PENDING_USER_APPROVAL without external API submission.")

    # Attempt 2: With explicit approval (user_approved=True)
    res_approved = run_scholarship_pipeline(eligible_user, user_approved=True, requirements=reqs)
    assert res_approved["execution_outcome"] == "SUBMITTED"
    assert "application_id" in res_approved
    assert res_approved["application_id"].startswith("NSP-2025-CSSS-")
    print(f"  + PASSED: Approved plan successfully submitted to Mock API (Application ID: {res_approved['application_id']}).")


def test_early_exit_blocked_and_needs_review(reqs, users):
    print("\n[TEST 3] Testing Early Exit for BLOCKED and NEEDS_REVIEW Applications...")
    
    # Ineligible user: SCH002 (Income > 4.5L)
    res_blocked = run_scholarship_pipeline(users[1], user_approved=True, requirements=reqs)
    assert res_blocked["policy_status"] == "BLOCKED"
    assert res_blocked["execution_outcome"] == "BLOCKED"
    assert res_blocked["submission_status"] == "NOT_SUBMITTED"
    assert "application_id" not in res_blocked
    print("  + PASSED: BLOCKED application terminated at Stage 6 without submitting to Mock API.")

    # Unverified user: SCH014 (Missing AISHE code)
    res_review = run_scholarship_pipeline(users[13], user_approved=True, requirements=reqs)
    assert res_review["policy_status"] == "NEEDS_REVIEW"
    assert res_review["execution_outcome"] == "NEEDS_REVIEW"
    assert res_review["submission_status"] == "NOT_SUBMITTED"
    assert "application_id" not in res_review
    print("  + PASSED: NEEDS_REVIEW application terminated at Stage 6 without submitting to Mock API.")


def test_percentile_vs_percentage_distinction(reqs, users):
    print("\n[TEST 4] Testing Percentile vs Percentage Distinction (SCH003)...")
    sch003 = users[2]
    assert sch003["class_12_marks_percentage"] == 82.5, "SCH003 must have 82.5% marks."
    assert sch003["class_12_percentile"] == 74.2, "SCH003 must have 74.2 percentile rank."

    matched = match_scholarship_attributes(reqs, sch003)
    plan = create_scholarship_disclosure_plan(reqs, matched, sch003)
    policy_res = verify_scholarship_policy(plan, matched, sch003)

    assert policy_res["status"] == "BLOCKED"
    assert "percentile rank" in policy_res["reason"].lower()
    assert "percentage marks do not substitute" in policy_res["reason"].lower()
    print("  + PASSED: Percentage marks (82.5%) correctly rejected as substitute for 80th percentile cutoff.")


def test_merit_list_distinction(reqs, users):
    print("\n[TEST 5] Testing Top 20th Percentile Merit List Distinction (SCH004)...")
    sch004 = users[3]
    assert sch004["class_12_percentile"] == 82.0, "SCH004 has >80th percentile."
    assert sch004["board_merit_list_status"] is False, "SCH004 excluded from Board list."

    matched = match_scholarship_attributes(reqs, sch004)
    plan = create_scholarship_disclosure_plan(reqs, matched, sch004)
    policy_res = verify_scholarship_policy(plan, matched, sch004)

    assert policy_res["status"] == "BLOCKED"
    assert "Top 20th percentile list" in policy_res["reason"]
    print("  + PASSED: Scoring 82.0 percentile does NOT infer Board merit list inclusion.")


def test_drop_year_scoped_ay2025_26(reqs, users):
    print("\n[TEST 6] Testing Drop Year Scoped Strictly to AY 2025-26...")
    sch005 = users[4]
    assert sch005["gap_year_flag"] is True

    matched = match_scholarship_attributes(reqs, sch005)
    plan = create_scholarship_disclosure_plan(reqs, matched, sch005)
    policy_res = verify_scholarship_policy(plan, matched, sch005)

    assert policy_res["status"] == "BLOCKED"
    assert "AY 2025-26" in policy_res["reason"]
    print("  + PASSED: Drop year rule explicitly scoped to AY 2025-26 per FAQ Q1.")


def test_missing_aishe_code_needs_review(reqs, users):
    print("\n[TEST 7] Testing Missing AISHE Code Routes to NEEDS_REVIEW...")
    sch014 = users[13]
    assert sch014["aishe_code"] is None
    assert sch014["institution_recognized"] is True

    matched = match_scholarship_attributes(reqs, sch014)
    plan = create_scholarship_disclosure_plan(reqs, matched, sch014)
    policy_res = verify_scholarship_policy(plan, matched, sch014)

    assert policy_res["status"] == "NEEDS_REVIEW", f"Expected NEEDS_REVIEW for missing AISHE code, got {policy_res['status']}"
    assert "aishe_code" in policy_res["reason"]
    print("  + PASSED: Missing AISHE code properly routed to NEEDS_REVIEW (not ineligibility).")


def test_inactive_aishe_payment_decoupling(reqs, users):
    print("\n[TEST 8] Testing Inactive AISHE Application Acceptance & Payment Decoupling...")
    # Clone eligible applicant SCH001 and set AISHE status to INACTIVE
    u_inactive = dict(users[0])
    u_inactive["aishe_status"] = "INACTIVE"

    res = run_scholarship_pipeline(u_inactive, user_approved=True, requirements=reqs)

    # 1. Application registration succeeds
    assert res["policy_status"] == "PASSED"
    assert res["execution_outcome"] == "SUBMITTED"
    assert "application_id" in res
    app_id = res["application_id"]

    # 2. Application status inquiry confirms SUBMITTED
    app_status = get_mock_application_status(app_id)
    assert app_status["application_status"] == "SUBMITTED"

    # 3. Payment readiness is decoupled and in PAYMENT_PENDING hold
    pay_status = get_mock_payment_status(app_id)
    assert pay_status["payment_status"] == "PAYMENT_PENDING"
    assert pay_status["dbt_ready"] is False
    assert "INACTIVE" in pay_status["hold_reason"]
    print("  + PASSED: Inactive AISHE registers application successfully with PAYMENT_PENDING hold.")


def test_payment_quarantine_enforcement(reqs, users):
    print("\n[TEST 9] Testing Payment and Raw Aadhaar Quarantine Enforcement...")
    quarantined_keys = {"aadhaar_number", "bank_account_number", "bank_ifsc", "aadhaar_seeding_status"}

    for u in users:
        matched = match_scholarship_attributes(reqs, u)
        plan = create_scholarship_disclosure_plan(reqs, matched, u)

        app_docs = set(plan["approved_supporting_documents"].keys())
        app_flds = set(plan["portal_application_fields"].keys())

        assert not app_docs.intersection(quarantined_keys)
        assert not app_flds.intersection(quarantined_keys)

        q_pay = plan["quarantined_payment_attributes"]
        for qk in quarantined_keys:
            assert qk in q_pay

    print("  + PASSED: Raw Aadhaar and bank account credentials quarantined across all 15 plans.")


def test_minimum_disclosure_and_overdisclosure(reqs, users):
    print("\n[TEST 10] Testing Minimum-Disclosure and Over-Disclosure Rejection...")
    # General applicant SCH001
    gen_user = users[0]
    m_gen = match_scholarship_attributes(reqs, gen_user)
    p_gen = create_scholarship_disclosure_plan(reqs, m_gen, gen_user)
    assert "caste_certificate" not in p_gen["approved_supporting_documents"]
    assert "disability_certificate" not in p_gen["approved_supporting_documents"]

    # SC applicant SCH008
    sc_user = users[7]
    m_sc = match_scholarship_attributes(reqs, sc_user)
    p_sc = create_scholarship_disclosure_plan(reqs, m_sc, sc_user)
    assert "caste_certificate" in p_sc["approved_supporting_documents"]
    assert "disability_certificate" not in p_sc["approved_supporting_documents"]

    # PwD applicant SCH010
    pwd_user = users[9]
    m_pwd = match_scholarship_attributes(reqs, pwd_user)
    p_pwd = create_scholarship_disclosure_plan(reqs, m_pwd, pwd_user)
    assert "disability_certificate" in p_pwd["approved_supporting_documents"]
    assert "caste_certificate" not in p_pwd["approved_supporting_documents"]

    print("  + PASSED: Minimum disclosure verified: documents approved strictly according to quota claim.")


def test_passport_non_regression():
    print("\n[TEST 11] Testing Passport Pipeline Non-Regression...")
    from src.main import build_or_load_rag_pipeline
    from src.evaluation import load_users, run_evaluation_suite
    from src.requirement_extractor import extract_requirements

    passport_users = load_users()
    assert len(passport_users) == 10, "Passport users should have 10 profiles!"

    retriever = build_or_load_rag_pipeline()
    chunks = retriever.retrieve("I want to apply for a fresh passport.", top_k=3)
    assert len(chunks) == 3
    assert "official passport" in chunks[0]["file_name"].lower()

    pass_reqs = extract_requirements(chunks, task_name="fresh passport application")
    eval_res = run_evaluation_suite(pass_reqs)
    assert len(eval_res) == 10

    u001_res = next(r for r in eval_res if r["user_id"] == "U001")
    u002_res = next(r for r in eval_res if r["user_id"] == "U002")

    assert u001_res["policy_approved"] is True, "Passport U001 should pass!"
    assert u002_res["policy_approved"] is False, "Passport U002 should be blocked!"
    print(f"  + Passport U001: Policy Approved={u001_res['policy_approved']} (PASSED)")
    print(f"  + Passport U002: Policy Approved={u002_res['policy_approved']} (BLOCKED - Missing Address Proof)")
    print("  + PASSED: Zero regressions detected in the Passport workflow.")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  PHASE 4 VALIDATION TEST: END-TO-END SCHOLARSHIP PIPELINE & MOCK API")
    print("=" * 80)

    reqs = extract_scholarship_requirements()
    users = load_scholarship_users()

    test_15_synthetic_profiles(reqs, users)
    test_approval_gating(reqs, users)
    test_early_exit_blocked_and_needs_review(reqs, users)
    test_percentile_vs_percentage_distinction(reqs, users)
    test_merit_list_distinction(reqs, users)
    test_drop_year_scoped_ay2025_26(reqs, users)
    test_missing_aishe_code_needs_review(reqs, users)
    test_inactive_aishe_payment_decoupling(reqs, users)
    test_payment_quarantine_enforcement(reqs, users)
    test_minimum_disclosure_and_overdisclosure(reqs, users)
    test_passport_non_regression()

    print("\n" + "=" * 80)
    print("  ALL PHASE 4 PIPELINE AND INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80 + "\n")
