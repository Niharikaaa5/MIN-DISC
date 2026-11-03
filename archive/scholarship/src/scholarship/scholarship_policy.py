"""
Module: Deterministic Scholarship Policy Engine
Enforces independent deterministic privacy and policy checks for PM-USP CSSS applications.
Does not trust the planner blindly: performs defense-in-depth re-verification.

Possible Outcomes:
- PASSED: Eligible and required application information/documents are complete.
- BLOCKED: Applicant fails a supported eligibility condition or mandatory documents are missing.
- NEEDS_REVIEW: Critical eligibility information is unknown or cannot be verified.
"""
from typing import Dict, List, Any, Optional


# Strictly forbidden payment-layer attributes in application payload
FORBIDDEN_PAYMENT_ATTRIBUTES = {
    "aadhaar_number", "bank_account_number", "bank_ifsc", "aadhaar_seeding_status"
}

# Cross-domain passport attributes forbidden in scholarship payloads
FORBIDDEN_PASSPORT_ATTRIBUTES = {
    "address_proof", "date_of_birth_proof", "academic_record",
    "police_verification", "post_police_verification", "tatkaal", "non_ecr"
}

# Authorized supporting documents for Fresh CSSS application
AUTHORIZED_FRESH_DOCUMENTS = {
    "class_12_marksheet", "income_certificate", "caste_certificate", "disability_certificate"
}


def verify_scholarship_policy(
    plan: Dict,
    matched_data: Dict,
    applicant_profile: Dict
) -> Dict:
    """
    Independently verifies minimum-disclosure plan against deterministic CSSS policy rules.
    """
    approved_docs = plan.get("approved_supporting_documents", {})
    portal_fields = plan.get("portal_application_fields", {})
    justifications = plan.get("justifications", {})
    
    all_approved_payload_keys = set(approved_docs.keys()) | set(portal_fields.keys())
    
    # -------------------------------------------------------------
    # RULE 1: SENSITIVE PAYMENT & RAW AADHAAR QUARANTINE CHECK
    # -------------------------------------------------------------
    leaked_payment = all_approved_payload_keys.intersection(FORBIDDEN_PAYMENT_ATTRIBUTES)
    if leaked_payment:
        return {
            "approved": False,
            "status": "BLOCKED",
            "reason": f"Execution BLOCKED: Quarantined payment/identity attribute(s) {sorted(leaked_payment)} detected in application disclosure payload.",
            "violations": [f"Payment attribute '{k}' must not enter Stage 1/2 application payload" for k in sorted(leaked_payment)],
            "approved_attributes": []
        }

    # -------------------------------------------------------------
    # RULE 2: CROSS-DOMAIN PASSPORT CONTAMINATION CHECK
    # -------------------------------------------------------------
    leaked_passport = all_approved_payload_keys.intersection(FORBIDDEN_PASSPORT_ATTRIBUTES)
    if leaked_passport:
        return {
            "approved": False,
            "status": "BLOCKED",
            "reason": f"Execution BLOCKED: Cross-domain passport attribute(s) {sorted(leaked_passport)} detected in scholarship disclosure payload.",
            "violations": [f"Passport attribute '{k}' is prohibited in scholarship workflow" for k in sorted(leaked_passport)],
            "approved_attributes": []
        }

    # -------------------------------------------------------------
    # RULE 3: INDEPENDENT SUBSTANTIVE ELIGIBILITY AUDIT
    # -------------------------------------------------------------
    failed_reasons = []
    
    # 3.1 Family Income Ceiling (<= 4.5 Lakh p.a.)
    family_income = applicant_profile.get("family_income")
    if family_income is not None:
        if int(family_income) > 450000:
            failed_reasons.append(f"Gross family income (Rs {int(family_income):,}) exceeds the maximum scheme limit of Rs 4,50,000 p.a. (DOC-1 Sec 4.v).")
            
    # 3.2 Class XII Merit Cutoff (>= 80th percentile rank)
    percentile = applicant_profile.get("class_12_percentile")
    if percentile is not None:
        if float(percentile) < 80.0:
            failed_reasons.append(f"Class XII percentile rank ({percentile}) is below the mandatory 80th percentile cutoff (DOC-1 Sec 4.i; percentage marks do not substitute for percentile rank).")
            
    # 3.3 State Board Top 20th Percentile List
    board_merit = applicant_profile.get("board_merit_list_status")
    if board_merit is False:
        failed_reasons.append("Applicant is excluded from the concerned Board Top 20th percentile list (DOC-2 Q10.a).")
        
    # 3.4 Preceding Year Passing (No Drop Year) - Scoped to AY 2025-26
    gap_year = applicant_profile.get("gap_year_flag")
    if gap_year is True:
        failed_reasons.append("Applicant took a drop year; ineligible under immediate preceding academic year rule explicitly scoped to AY 2025-26 (DOC-2 Q1).")
        
    # 3.5 Regular Full-Time Degree Mode
    course_mode = applicant_profile.get("course_mode")
    if course_mode and course_mode != "Regular":
        failed_reasons.append(f"Enrolled in '{course_mode}' mode; correspondence and distance education courses are strictly ineligible (DOC-1 Sec 4.ii).")
        
    # 3.6 Degree Level (No Diplomas)
    degree_level = applicant_profile.get("degree_level")
    if degree_level == "Diploma":
        failed_reasons.append("Diploma students are strictly ineligible for PM-USP CSSS (DOC-1 Sec 2, DOC-2 Q1).")
        
    # 3.7 Institutional Regulatory Recognition
    inst_recog = applicant_profile.get("institution_recognized")
    if inst_recog is False:
        failed_reasons.append("Institution lacks recognized affiliation from AICTE, UGC, or concerned regulatory body (DOC-1 Sec 4.iii).")
        
    # 3.8 Scholarship Exclusivity
    other_scholarships = applicant_profile.get("other_scholarships_flag")
    if other_scholarships is True:
        failed_reasons.append("Applicant is availing another scholarship/fee waiver scheme; violates scheme exclusivity rule (DOC-1 Sec 4.iv).")

    # Combine with matcher failures if any
    for failure in matched_data.get("failed_eligibility_requirements", []):
        r_msg = failure.get("reason")
        if r_msg and r_msg not in failed_reasons:
            failed_reasons.append(r_msg)

    if failed_reasons:
        return {
            "approved": False,
            "status": "BLOCKED",
            "reason": f"Execution BLOCKED: Applicant fails scheme substantive eligibility condition(s): {' | '.join(failed_reasons)}",
            "violations": failed_reasons,
            "approved_attributes": []
        }

    # -------------------------------------------------------------
    # RULE 4: UNKNOWN / UNVERIFIABLE INFORMATION CHECK
    # -------------------------------------------------------------
    missing_info = matched_data.get("missing_information", [])
    critical_fields = {"class_12_percentile", "board_merit_list_status", "family_income", "gap_year_flag", "aishe_code"}
    unknown_critical = [f for f in missing_info if f in critical_fields]
    
    aishe_val = applicant_profile.get("aishe_code")
    if (aishe_val is None or str(aishe_val).strip() == "") and "aishe_code" not in unknown_critical:
        unknown_critical.append("aishe_code")
    
    if unknown_critical:
        return {
            "approved": False,
            "status": "NEEDS_REVIEW",
            "reason": f"Execution PENDING: Critical eligibility attribute(s) {unknown_critical} are unknown or unverified in applicant record.",
            "violations": [f"Missing critical verification data for '{f}'" for f in unknown_critical],
            "approved_attributes": []
        }

    # -------------------------------------------------------------
    # RULE 5: MANDATORY SUPPORTING DOCUMENT COMPLETENESS
    # -------------------------------------------------------------
    missing_docs = []
    
    # 5.1 Class 12th Mark Sheet (SD-01)
    if "class_12_marksheet" not in approved_docs or not approved_docs["class_12_marksheet"]:
        missing_docs.append("Class 12th Mark Sheet (SD-01)")
        
    # 5.2 Family Income Certificate (SD-02)
    if "income_certificate" not in approved_docs or not approved_docs["income_certificate"]:
        missing_docs.append("Family Income Certificate (SD-02)")
        
    if missing_docs:
        return {
            "approved": False,
            "status": "BLOCKED",
            "reason": f"Execution BLOCKED: Missing mandatory supporting document upload(s): {', '.join(missing_docs)} (DOC-2 Q19.a).",
            "violations": [f"Mandatory document '{d}' is missing from profile" for d in missing_docs],
            "approved_attributes": []
        }

    # -------------------------------------------------------------
    # RULE 6: CONDITIONAL QUOTA SUPPORTING DOCUMENT COMPLETENESS
    # -------------------------------------------------------------
    caste_category = applicant_profile.get("caste_category", "General")
    disability_pct = float(applicant_profile.get("disability_percentage") or 0.0)
    
    # 6.1 Caste Certificate for Reserved Quota Claims
    if caste_category in ("SC", "ST", "OBC"):
        if "caste_certificate" not in approved_docs or not approved_docs["caste_certificate"]:
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": f"Execution BLOCKED: Applicant claimed Central {caste_category} reservation quota, but required Caste Certificate (SD-03) is missing (DOC-2 Q19.a).",
                "violations": [f"Caste Certificate mandatory when claiming {caste_category} quota"],
                "approved_attributes": []
            }
    else:
        # 6.2 Over-disclosure check: General category must not disclose caste certificate
        if "caste_certificate" in approved_docs:
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": "Execution BLOCKED: Unnecessary data disclosure detected: 'caste_certificate' included for General merit applicant.",
                "violations": ["Caste Certificate must not be disclosed for General category applicants"],
                "approved_attributes": []
            }

    # 6.3 Disability Certificate for PwD Horizontal Quota Claims
    if disability_pct >= 40.0:
        if "disability_certificate" not in approved_docs or not approved_docs["disability_certificate"]:
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": f"Execution BLOCKED: Applicant claimed 5% PwD horizontal reservation ({disability_pct}% disability), but required Disability Certificate (SD-04) is missing (DOC-2 Q19.a).",
                "violations": [f"Disability Certificate mandatory for benchmark disability >= 40%"],
                "approved_attributes": []
            }
    else:
        # Over-disclosure check: Non-PwD must not disclose disability certificate
        if "disability_certificate" in approved_docs:
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": "Execution BLOCKED: Unnecessary data disclosure detected: 'disability_certificate' included for non-PwD applicant.",
                "violations": ["Disability Certificate must not be disclosed when disability benchmark < 40%"],
                "approved_attributes": []
            }

    # -------------------------------------------------------------
    # RULE 7: DOCUMENT CLASSIFICATION & JUSTIFICATION CHECK
    # -------------------------------------------------------------
    for doc_key in approved_docs:
        if doc_key not in AUTHORIZED_FRESH_DOCUMENTS:
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": f"Execution BLOCKED: Unauthorized document '{doc_key}' detected in Fresh CSSS disclosure plan.",
                "violations": [f"Document '{doc_key}' is not an authorized Fresh CSSS supporting document"],
                "approved_attributes": []
            }
        if doc_key not in justifications or not str(justifications.get(doc_key, "")).strip():
            return {
                "approved": False,
                "status": "BLOCKED",
                "reason": f"Execution BLOCKED: Approved document '{doc_key}' lacks task necessity justification.",
                "violations": [f"Missing statutory justification for '{doc_key}'"],
                "approved_attributes": []
            }

    # -------------------------------------------------------------
    # RULE 8: PAYMENT READINESS ADVISORY (DOES NOT BLOCK INITIAL APP)
    # -------------------------------------------------------------
    payment_conds = matched_data.get("payment_conditions", {})
    payment_advisories = []
    
    if not payment_conds.get("aishe_active", True):
        payment_advisories.append("Advisory: Institution AISHE status is INACTIVE. Application registration is accepted, but payment release requires active status (DOC-2 Q18).")
    if not payment_conds.get("aadhaar_seeded", True):
        payment_advisories.append("Advisory: Bank account is not seeded with Aadhaar on NPCI mapper. Payment credit will fail until seeded.")

    # -------------------------------------------------------------
    # POLICY VERIFICATION PASSED
    # -------------------------------------------------------------
    approved_list = sorted(list(all_approved_payload_keys))
    
    return {
        "approved": True,
        "status": "PASSED",
        "reason": "Applicant satisfies all substantive CSSS eligibility criteria and disclosure plan strictly satisfies minimum-disclosure policy.",
        "approved_attributes": approved_list,
        "approved_documents": list(approved_docs.keys()),
        "approved_fields": list(portal_fields.keys()),
        "payment_advisories": payment_advisories,
        "payment_release_ready": payment_conds.get("payment_release_ready", True)
    }
