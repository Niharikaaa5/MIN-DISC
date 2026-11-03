"""
Module: Evaluation Engine
Evaluates Baseline (Full Disclosure) vs MIN-DISC across synthetic user profiles (U001 - U010)
using ground_truth.json and evaluation_cases.csv.
"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any

from src.config import USERS_FILE, GROUND_TRUTH_PATH, EVALUATION_CASES_PATH
from src.attribute_matcher import match_user_attributes
from src.disclosure_planner import create_disclosure_plan
from src.policy_checker import verify_privacy_policy
from src.mock_passport_api import execute_mock_api_call


def load_evaluation_cases() -> List[Dict]:
    """Loads evaluation test cases from CSV."""
    cases = []
    if not EVALUATION_CASES_PATH.exists():
        return cases

    with open(EVALUATION_CASES_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
    return cases


def load_ground_truth() -> Dict:
    """Loads ground truth requirements definition."""
    if not GROUND_TRUTH_PATH.exists():
        return {}
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_users() -> List[Dict]:
    """Loads synthetic user profiles from users.json."""
    if not USERS_FILE.exists():
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation_suite(extracted_requirements: Dict) -> List[Dict[str, Any]]:
    """
    Runs evaluation suite across all user test cases (U001 to U010).
    Compares Baseline (Full Disclosure) vs MIN-DISC.
    """
    users = load_users()
    eval_cases = load_evaluation_cases()
    ground_truth = load_ground_truth()

    results = []

    for user in users:
        user_id = user["user_id"]
        user_name = user["name"]

        # 1. BASELINE: Full Profile Disclosure
        # Non-null profile attributes available for the user (excluding user_id and name)
        available_profile_keys = [k for k, v in user.items() if v is not None and k not in ["user_id", "name"]]
        baseline_disclosed_count = len(available_profile_keys)
        
        # Base mandatory required attributes for standard adult fresh passport
        base_required_keys = ["address_proof", "date_of_birth_proof"]
        baseline_unnecessary_count = len([k for k in available_profile_keys if k not in base_required_keys])

        # Baseline execution simulation
        baseline_payload = {k: user[k] for k in available_profile_keys}
        try:
            baseline_api_res = execute_mock_api_call(baseline_payload)
            baseline_status = "SUCCESS" if baseline_api_res.get("status") == "success" else "FAILED"
        except Exception:
            baseline_status = "FAILED (PRIVACY VIOLATION)"

        # 2. MIN-DISC PIPELINE
        matched_data = match_user_attributes(extracted_requirements, user)
        
        # Enforce rule: Non-ECR eligibility is UNKNOWN by default unless explicitly established
        requires_non_ecr = False
        
        plan = create_disclosure_plan(
            task_name="fresh passport application",
            extracted_requirements=extracted_requirements,
            matched_data=matched_data,
            user_profile=user,
            requires_non_ecr=requires_non_ecr
        )
        policy_res = verify_privacy_policy(plan, matched_data, user, requires_non_ecr=requires_non_ecr)

        if policy_res["approved"]:
            min_disc_payload = plan["approved_payload"]
            api_res = execute_mock_api_call(min_disc_payload)
            min_disc_status = "SUCCESS" if api_res.get("status") == "success" else "FAILED"
            min_disc_disclosed_count = plan["disclosed_attributes_count"]
        else:
            min_disc_status = f"BLOCKED ({policy_res['reason']})"
            min_disc_disclosed_count = 0

        # Disclosed attributes prevented from leakage for this user
        attributes_prevented_count = baseline_disclosed_count - min_disc_disclosed_count

        # Calculate Reduction Percentage
        if baseline_disclosed_count > 0:
            reduction = round((1 - (min_disc_disclosed_count / baseline_disclosed_count)) * 100, 1)
        else:
            reduction = 0.0

        results.append({
            "user_id": user_id,
            "user_name": user_name,
            "baseline_disclosed": baseline_disclosed_count,
            "baseline_unnecessary": baseline_unnecessary_count,
            "baseline_status": baseline_status,
            "min_disc_disclosed": min_disc_disclosed_count,
            "attributes_prevented": attributes_prevented_count,
            "min_disc_status": min_disc_status,
            "policy_approved": policy_res["approved"],
            "disclosure_reduction_pct": reduction,
            "approved_attributes": plan.get("approved_attributes", []) if policy_res["approved"] else []
        })

    return results
