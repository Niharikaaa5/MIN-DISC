"""
Module: Deterministic Privacy/Policy Checker
Enforces strict policy rules to validate disclosure plans before execution.
Does not duplicate requirement extraction or planning logic.
"""
from typing import Dict, List, Optional


def verify_privacy_policy(
    plan: Dict,
    matched_data: Dict,
    user_profile: Dict,
    requires_non_ecr: Optional[bool] = None,
    task_context: Optional[Dict] = None,
    repository_access_log: Optional[List[Dict]] = None
) -> Dict:
    """
    Deterministically evaluates the minimum-disclosure plan against privacy policy rules.

    Policy Rules Enforced:
    0. Repository Access Compliance: Asserts zero unauthorized access attempts and verifies
       that forbidden sensitive file categories (health, banking, tax) were never accessed.
    1. Mandatory requirement completeness: missing_mandatory_attributes must be empty.
    1B. Independent Conditional Requirement Validation (Non-ECR):
        - When requires_non_ecr=True: academic_record must be present in approved_payload, non-null, and non-empty.
        - When requires_non_ecr=False: academic_record must not be required and must not be disclosed solely because it exists.
    2. Justification check: every approved attribute must have a non-empty justification.
    3. Authorized disclosure check: only allowed supporting documents (address_proof,
       date_of_birth_proof, academic_record) are permitted. Application fields (name, DOB, address)
       are not permitted in the supporting-document disclosure payload.
    4. Sensitive / unrelated data protection: family_income, bank_account, medical_information,
       phone, email, employment, identity_proof are strictly forbidden.
    5. Value validity: approved attributes must not be null or empty.
    6. Document 41 safety: unmapped conditional documents do not cause fabricated disclosures.

    Returns:
        Dict: Policy check result with keys:
            - approved: bool
            - status: str ("PASSED" or "BLOCKED")
            - approved_attributes: List[str]
            - rejected_attributes: List[str]
            - reason: str
    """
    # 0. Resolve task context (defense-in-depth)
    if requires_non_ecr is None:
        if task_context and "requires_non_ecr" in task_context:
            requires_non_ecr = bool(task_context["requires_non_ecr"])
        elif isinstance(plan, dict) and "requires_non_ecr" in plan:
            requires_non_ecr = bool(plan["requires_non_ecr"])
        else:
            requires_non_ecr = False

    if repository_access_log is None:
        if task_context and "repository_access_log" in task_context:
            repository_access_log = task_context["repository_access_log"]
        elif isinstance(plan, dict) and "repository_access_log" in plan:
            repository_access_log = plan["repository_access_log"]

    missing_mandatory = plan.get("missing_mandatory_attributes")
    if missing_mandatory is None:
        missing_mandatory = matched_data.get("missing_mandatory_attributes", [])

    approved_payload = plan.get("approved_payload", {})
    approved_attributes = plan.get("approved_attributes", list(approved_payload.keys()))
    excluded_attributes = plan.get("excluded_attributes", [])

    all_profile_keys = list(user_profile.keys()) if user_profile else excluded_attributes

    # RULE 0 — Repository Access Policy Verification (if repository access log is provided)
    if repository_access_log:
        for entry in repository_access_log:
            if entry.get("action") == "BLOCKED_ACCESS_ATTEMPT" or entry.get("status") == "BLOCKED":
                return {
                    "approved": False,
                    "status": "BLOCKED",
                    "approved_attributes": [],
                    "rejected_attributes": all_profile_keys,
                    "reason": f"Execution BLOCKED: Repository access violation detected ({entry.get('reason', 'Unauthorized access attempt')})."
                }
            is_opened = entry.get("opened", False) or entry.get("action") == "AUTHORIZED_FETCH" or entry.get("decision") == "ACCESSED"
            cat = entry.get("category", "")
            if is_opened and cat in {"health_medical", "financial_banking", "financial_tax"}:
                return {
                    "approved": False,
                    "status": "BLOCKED",
                    "approved_attributes": [],
                    "rejected_attributes": all_profile_keys,
                    "reason": f"Execution BLOCKED: Access violation detected - sensitive file category '{cat}' was opened."
                }

    # RULE 1 — Mandatory requirement completeness check
    if missing_mandatory:
        missing_str = ", ".join(missing_mandatory)
        return {
            "approved": False,
            "status": "BLOCKED",
            "approved_attributes": [],
            "rejected_attributes": all_profile_keys,
            "reason": f"Execution BLOCKED: Applicant profile is missing mandatory requirement(s): {missing_str}."
        }

    # RULE 1B — Independent Conditional Requirement Integrity Check (Non-ECR)
    if requires_non_ecr:
        acad_val = approved_payload.get("academic_record")
        if "academic_record" not in approved_payload or acad_val is None or str(acad_val).strip() == "":
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": (
                    "Execution BLOCKED: Task explicitly requires Non-ECR documentary proof, "
                    "but 'academic_record' is missing or empty in approved payload."
                )
            }
    else:
        # When requires_non_ecr is False, academic_record must not be disclosed solely because it exists
        if "academic_record" in approved_payload or "academic_record" in approved_attributes:
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": (
                    "Execution BLOCKED: 'academic_record' was included in disclosure plan "
                    "but Non-ECR proof was not explicitly required for this task."
                )
            }

    # Allowed supporting document disclosure keys
    ALLOWED_SUPPORTING_DOCS = {"address_proof", "date_of_birth_proof", "academic_record"}

    # Strictly forbidden sensitive / unclassified profile attributes
    FORBIDDEN_ATTRIBUTES = {
        "family_income", "bank_account", "medical_information",
        "phone", "email", "employment", "identity_proof"
    }

    # Application fields not permitted as supporting document disclosures
    APPLICATION_FIELDS = {"name", "date_of_birth", "address"}

    justifications = plan.get("justifications", {})

    for attr in approved_attributes:
        val = approved_payload.get(attr)
        if val is None and user_profile:
            val = user_profile.get(attr)

        # RULE 5 — Empty or malformed disclosure check
        if val is None or str(val).strip() == "":
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": f"Execution BLOCKED: Approved attribute '{attr}' has empty or null value."
            }

        # RULE 2 — Approved disclosure justification check
        if attr not in justifications or not str(justifications.get(attr, "")).strip():
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": f"Execution BLOCKED: Attribute '{attr}' lacks task necessity justification."
            }

        # RULE 4 — Sensitive / unrelated data protection check
        if attr in FORBIDDEN_ATTRIBUTES:
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": f"Execution BLOCKED: Unauthorized sensitive/unclassified attribute '{attr}' detected in disclosure plan."
            }

        # RULE 3 — Application fields check
        if attr in APPLICATION_FIELDS:
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": f"Execution BLOCKED: Application field '{attr}' cannot be disclosed in supporting-document payload."
            }

        # RULE 3 — Authorized disclosure check
        if attr not in ALLOWED_SUPPORTING_DOCS:
            return {
                "approved": False,
                "status": "BLOCKED",
                "approved_attributes": [],
                "rejected_attributes": all_profile_keys,
                "reason": f"Execution BLOCKED: Attribute '{attr}' is not an authorized supporting document for this task."
            }

    # RULE 6 & Summary: Privacy check PASSED
    return {
        "approved": True,
        "status": "PASSED",
        "approved_attributes": approved_attributes,
        "rejected_attributes": excluded_attributes,
        "reason": "Only attributes strictly required for the identified passport task were approved for disclosure."
    }
