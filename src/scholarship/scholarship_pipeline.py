"""
Module: PM-USP CSSS End-to-End Backend Orchestration Pipeline
Coordinates RAG retrieval, structured requirement extraction, attribute matching,
minimum-disclosure planning, deterministic policy enforcement, human-in-the-loop approval gating,
and simulated NSP/PFMS mock API submission.

Strict Guarantees:
1. Deterministic policy rules cannot be overridden by LLMs or heuristics.
2. Unapproved applications (BLOCKED or NEEDS_REVIEW) stop early and never reach the external API.
3. Submissions require explicit human/application-level confirmation (user_approved=True).
4. Raw payment credentials and identity numbers remain quarantined and never transmit.
5. Application submission status (SUBMITTED) is decoupled from payment disbursement readiness (PAYMENT_PENDING/PAYMENT_READY).
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.scholarship.scholarship_extractor import extract_scholarship_requirements
from src.scholarship.scholarship_matcher import match_scholarship_attributes
from src.scholarship.scholarship_planner import create_scholarship_disclosure_plan
from src.scholarship.scholarship_policy import verify_scholarship_policy
from src.scholarship.mock_scholarship_api import (
    submit_mock_scholarship_application,
    get_mock_application_status,
    get_mock_payment_status,
    MOCK_DISCLAIMER
)


def load_scholarship_users(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads all synthetic PM-USP CSSS applicant profiles."""
    path = Path(filepath) if filepath else ROOT_DIR / "data" / "users" / "scholarship_users.json"
    if not path.exists():
        raise FileNotFoundError(f"Scholarship synthetic users file not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scholarship_user(user_id: str, filepath: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves a single synthetic applicant profile by user_id."""
    users = load_scholarship_users(filepath)
    for u in users:
        if u.get("user_id") == user_id:
            return u
    raise ValueError(f"Scholarship user profile with id '{user_id}' not found.")


def run_scholarship_pipeline(
    user_profile_or_id: Any,
    user_approved: bool = False,
    requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes the 10-stage end-to-end backend scholarship pipeline.

    Stages:
    1. Ingestion: Load user profile.
    2. RAG Retrieval & Requirement Extraction: Isolated scholarship knowledge base.
    3. Attribute Matching: Match profile against canonical scheme requirements.
    4. Minimum-Disclosure Planning: Synthesize task-justified payload.
    5. Deterministic Policy Verification: Rigorous defense-in-depth policy check.
    6. Policy Gating: Terminate immediately if BLOCKED or NEEDS_REVIEW.
    7. User Approval Gate: Require explicit user confirmation before external transmission.
    8. Mock API Submission: Submit policy-approved payload to simulated NSP.
    9. Status Retrieval: Query simulated application status.
    10. Payment Readiness: Independently evaluate PFMS disbursement readiness.
    """
    # Stage 1: Ingestion
    if isinstance(user_profile_or_id, str):
        profile = load_scholarship_user(user_profile_or_id)
    else:
        profile = dict(user_profile_or_id)

    uid = profile.get("user_id", "UNKNOWN")
    uname = profile.get("applicant_name", "UNKNOWN")

    # Stage 2: RAG Retrieval & Requirements
    if requirements is None:
        requirements = extract_scholarship_requirements()

    # Stage 3: Attribute Matching
    matched_data = match_scholarship_attributes(requirements, profile)

    # Stage 4: Minimum-Disclosure Planning
    disclosure_plan = create_scholarship_disclosure_plan(requirements, matched_data, profile)

    # Stage 5: Deterministic Policy Verification
    policy_result = verify_scholarship_policy(disclosure_plan, matched_data, profile)
    policy_status = policy_result["status"]  # PASSED, BLOCKED, NEEDS_REVIEW

    base_response = {
        "user_id": uid,
        "applicant_name": uname,
        "policy_status": policy_status,
        "policy_approved": policy_result["approved"],
        "policy_reason": policy_result["reason"],
        "violations": policy_result.get("violations", []),
        "payment_advisories": policy_result.get("payment_advisories", []),
        "disclosed_fields_count": disclosure_plan["disclosed_fields_count"],
        "disclosed_documents_count": disclosure_plan["disclosed_documents_count"],
        "quarantined_attributes_count": disclosure_plan["quarantined_attributes_count"],
        "disclosure_plan": disclosure_plan,
        "mock_disclaimer": MOCK_DISCLAIMER
    }

    # Stage 6: Early exit if not PASSED
    if policy_status in ("BLOCKED", "NEEDS_REVIEW"):
        base_response.update({
            "execution_outcome": policy_status,
            "submission_status": "NOT_SUBMITTED",
            "payment_status": "NOT_EVALUATED",
            "message": f"Pipeline stopped at Stage 6: Policy engine evaluated status as {policy_status}."
        })
        return base_response

    # Stage 7: User Approval Gate
    if not user_approved:
        base_response.update({
            "execution_outcome": "PENDING_USER_APPROVAL",
            "submission_status": "PENDING_APPROVAL",
            "payment_status": "PENDING_APPROVAL",
            "message": "Policy verification PASSED. Submission to Mock NSP paused awaiting explicit user approval."
        })
        return base_response

    # Stage 8: Mock API Submission
    submission_payload = {
        "applicant_id": uid,
        "applicant_name": uname,
        "aishe_status": profile.get("aishe_status", "ACTIVE"),
        "portal_application_fields": disclosure_plan["portal_application_fields"],
        "approved_supporting_documents": disclosure_plan["approved_supporting_documents"],
        "policy_verification": {
            "policy_status": policy_result["status"],
            "policy_approved": policy_result["approved"]
        }
    }

    mock_sub_res = submit_mock_scholarship_application(submission_payload)

    if mock_sub_res.get("status") != "SUBMITTED":
        base_response.update({
            "execution_outcome": "SUBMISSION_FAILED",
            "submission_status": "REJECTED",
            "submission_error": mock_sub_res.get("error"),
            "payment_status": "NOT_EVALUATED"
        })
        return base_response

    application_id = mock_sub_res["application_id"]

    # Stage 9: Query Application Status
    app_status_res = get_mock_application_status(application_id)

    # Stage 10: Query Payment Readiness Separately
    payment_status_res = get_mock_payment_status(application_id)

    base_response.update({
        "execution_outcome": "SUBMITTED",
        "submission_status": "SUBMITTED",
        "application_id": application_id,
        "mock_registration": mock_sub_res,
        "mock_application_status": app_status_res,
        "mock_payment_status": payment_status_res,
        "payment_readiness": payment_status_res.get("payment_status"),
        "message": "Application successfully registered on Mock NSP. Payment readiness evaluated separately."
    })
    return base_response


def evaluate_all_scholarship_profiles(
    requirements: Optional[Dict[str, Any]] = None,
    auto_approve_passed: bool = True
) -> List[Dict[str, Any]]:
    """Evaluates all 15 synthetic applicant profiles through the end-to-end pipeline."""
    if requirements is None:
        requirements = extract_scholarship_requirements()

    users = load_scholarship_users()
    eval_results = []

    for u in users:
        # Run with user_approved = auto_approve_passed (to test mock submission on passing profiles)
        res = run_scholarship_pipeline(u, user_approved=auto_approve_passed, requirements=requirements)
        eval_results.append({
            "user_id": u["user_id"],
            "applicant_name": u["applicant_name"],
            "policy_status": res["policy_status"],
            "execution_outcome": res["execution_outcome"],
            "approved": res["policy_approved"],
            "application_id": res.get("application_id"),
            "payment_readiness": res.get("payment_readiness"),
            "disclosed_docs": list(res["disclosure_plan"]["approved_supporting_documents"].keys()),
            "reason": res["policy_reason"]
        })

    return eval_results


if __name__ == "__main__":
    args = sys.argv[1:]
    reqs = extract_scholarship_requirements()

    if "--eval" in args or not args:
        print("\n" + "=" * 80)
        print("  PM-USP CSSS END-TO-END BACKEND PIPELINE BENCHMARK (15 PROFILES)")
        print("=" * 80)
        results = evaluate_all_scholarship_profiles(reqs, auto_approve_passed=True)
        for r in results:
            app_id_str = r['application_id'] if r['application_id'] else "N/A"
            pay_str = r['payment_readiness'] if r['payment_readiness'] else "N/A"
            print(f"[{r['user_id']}] {r['applicant_name']:<18} | Policy: {r['policy_status']:<12} | Outcome: {r['execution_outcome']:<14} | AppID: {app_id_str:<22} | Payment: {pay_str}")
        print("=" * 80 + "\n")
    else:
        target_uid = args[0]
        approve_flag = "--approve" in args
        user = load_scholarship_user(target_uid)
        result = run_scholarship_pipeline(user, user_approved=approve_flag, requirements=reqs)
        print(json.dumps(result, indent=2))
