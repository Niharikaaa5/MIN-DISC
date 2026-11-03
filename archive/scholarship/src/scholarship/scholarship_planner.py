"""
Module: Scholarship Minimum-Disclosure Planner
Formulates an explainable minimum-disclosure plan for PM-USP CSSS Fresh Scholarship Applications.
Enforces core MIN-DISC axiom: "Data availability must never be treated as data necessity."

Separates disclosure components into:
1. portal_application_fields: core form fields required by portal.
2. approved_supporting_documents: strictly necessary document uploads (SD-01 to SD-04).
3. internal_eligibility_evaluation: internally evaluated criteria (not transmitted as external docs).
4. quarantined_payment_attributes: sensitive banking/Aadhaar details isolated from Stages 1-2.
5. excluded_attributes: profile attributes withheld to prevent unnecessary data exposure.
"""
from typing import Dict, List, Any


def create_scholarship_disclosure_plan(
    extracted_requirements: Dict,
    matched_data: Dict,
    applicant_profile: Dict
) -> Dict:
    """
    Constructs a verifiable Minimum-Disclosure Plan for Fresh Scholarship Application.
    """
    applicant_id = applicant_profile.get("user_id")
    applicant_name = applicant_profile.get("applicant_name")
    
    # Core demographic filters
    caste_category = applicant_profile.get("caste_category", "General")
    disability_pct = float(applicant_profile.get("disability_percentage") or 0.0)
    is_reserved_caste = caste_category in ("SC", "ST", "OBC")
    is_pwd = disability_pct >= 40.0
    
    portal_fields = {}
    approved_documents = {}
    justifications = {}
    
    # -------------------------------------------------------------
    # 1. Portal Application Form Fields
    # -------------------------------------------------------------
    standard_field_keys = [
        ("otr_number", "FAQ_DOHE_CSSS.pdf p. 4 Q14: One-Time Registration login reference"),
        ("applicant_name", "FAQ_DOHE_CSSS.pdf p. 4 Q15.a: Applicant legal name matching Marksheet/Aadhaar"),
        ("father_name", "FAQ_DOHE_CSSS.pdf p. 4 Q15.a: Father name matching Marksheet/Aadhaar"),
        ("date_of_birth", "FAQ_DOHE_CSSS.pdf p. 4 Q15.f: Demographic date of birth entry"),
        ("mobile_number", "FAQ_DOHE_CSSS.pdf p. 4 Q15.b: Active personal mobile number for OTP alerts"),
        ("email", "FAQ_DOHE_CSSS.pdf p. 4 Q15.b: Active personal email id for notifications"),
        ("domicile_state", "FAQ_DOHE_CSSS.pdf p. 4 Q14: Domicile state for Board quota assignment"),
        ("class_12_roll_no", "FAQ_DOHE_CSSS.pdf p. 4 Q15.a: Class XII Examination Roll Number"),
        ("passing_year", "FAQ_DOHE_CSSS.pdf p. 8: Class XII passing year"),
        ("stream", "CSSS_GUIDLINES p. 1 Sec 3: Class XII stream (Humanities/Science/Commerce 3:3:1 quota)"),
        ("course_name", "FAQ_DOHE_CSSS.pdf p. 5 Q17: Enrolled regular graduation degree course"),
        ("institution_name", "FAQ_DOHE_CSSS.pdf p. 5 Q18: Higher education institution name"),
        ("aishe_code", "CSSS_GUIDLINES p. 2 Sec 4.vi: Valid institutional AISHE code"),
    ]
    
    for fkey, just in standard_field_keys:
        fval = applicant_profile.get(fkey)
        if fval is not None and str(fval).strip() != "":
            portal_fields[fkey] = fval
            justifications[fkey] = just

    # Conditional portal fields
    if is_reserved_caste:
        portal_fields["caste_category"] = caste_category
        justifications["caste_category"] = f"CSSS_GUIDLINES p. 2 Sec 5: Claim for Central {caste_category} reservation quota"
    else:
        # General merit - caste is not disclosed as a quota claim
        portal_fields["caste_category"] = "General"
        justifications["caste_category"] = "CSSS_GUIDLINES p. 2 Sec 5: General merit allocation"
        
    if is_pwd:
        portal_fields["disability_percentage"] = disability_pct
        justifications["disability_percentage"] = f"CSSS_GUIDLINES p. 2 Sec 5: Claim for 5% horizontal PwD reservation ({disability_pct}% >= 40% benchmark)"

    # -------------------------------------------------------------
    # 2. Approved Supporting Document Uploads
    # -------------------------------------------------------------
    # A. Mandatory Fresh Documents
    marks_doc = applicant_profile.get("class_12_marksheet")
    if marks_doc:
        approved_documents["class_12_marksheet"] = marks_doc
        justifications["class_12_marksheet"] = "FAQ_DOHE_CSSS.pdf p. 6 Q19.a: Mandatory Fresh supporting document to verify Class XII marks, roll number, and stream."

    income_doc = applicant_profile.get("income_certificate")
    if income_doc:
        approved_documents["income_certificate"] = income_doc
        justifications["income_certificate"] = "CSSS_GUIDLINES p. 2 Sec 4.v & FAQ p. 6 Q19.a: Mandatory Fresh supporting document to verify parental income <= Rs 4.5 Lakh p.a."

    # B. Conditional Supporting Documents
    if is_reserved_caste:
        caste_doc = applicant_profile.get("caste_certificate")
        if caste_doc:
            approved_documents["caste_certificate"] = caste_doc
            justifications["caste_certificate"] = f"FAQ_DOHE_CSSS.pdf p. 6 Q19.a: Conditional supporting document required to substantiate {caste_category} reservation quota."

    if is_pwd:
        pwd_doc = applicant_profile.get("disability_certificate")
        if pwd_doc:
            approved_documents["disability_certificate"] = pwd_doc
            justifications["disability_certificate"] = f"FAQ_DOHE_CSSS.pdf p. 6 Q19.a: Conditional supporting document required to substantiate 5% PwD horizontal reservation ({disability_pct}% disability)."

    # -------------------------------------------------------------
    # 3. Internally Evaluated Eligibility Attributes
    # (Maintained for explainability and deterministic audit, not transmitted as docs)
    # -------------------------------------------------------------
    internal_eligibility = {
        "class_12_percentile": applicant_profile.get("class_12_percentile"),
        "board_merit_list_status": applicant_profile.get("board_merit_list_status"),
        "gap_year_flag": applicant_profile.get("gap_year_flag"),
        "family_income": applicant_profile.get("family_income"),
        "course_mode": applicant_profile.get("course_mode"),
        "degree_level": applicant_profile.get("degree_level"),
        "institution_recognized": applicant_profile.get("institution_recognized"),
        "other_scholarships_flag": applicant_profile.get("other_scholarships_flag"),
        "aishe_code": applicant_profile.get("aishe_code")
    }

    # -------------------------------------------------------------
    # 4. Quarantined Payment and Identity Attributes
    # (Strictly isolated from application payload; handled exclusively by Stage-4 payment module)
    # -------------------------------------------------------------
    quarantined_payment = {
        "aadhaar_number": applicant_profile.get("aadhaar_number"),
        "aadhaar_seeding_status": applicant_profile.get("aadhaar_seeding_status"),
        "bank_account_number": applicant_profile.get("bank_account_number"),
        "bank_ifsc": applicant_profile.get("bank_ifsc"),
        "aishe_status": applicant_profile.get("aishe_status")
    }

    # -------------------------------------------------------------
    # 5. Excluded / Withheld Profile Attributes
    # -------------------------------------------------------------
    disclosed_keys = set(portal_fields.keys()) | set(approved_documents.keys())
    # Profile keys that exist in applicant profile but are not approved in application payload
    all_profile_keys = {k for k, v in applicant_profile.items() if v is not None}
    
    # Quarantined keys are explicitly withheld from application transmission
    quarantined_keys = set(quarantined_payment.keys())
    
    excluded_attributes = [
        k for k in sorted(all_profile_keys)
        if k not in disclosed_keys and k not in ("user_id", "applicant_name", "scenario_note")
    ]

    return {
        "task": "PM-USP CSSS Fresh Scholarship Application",
        "applicant_id": applicant_id,
        "applicant_name": applicant_name,
        "portal_application_fields": portal_fields,
        "approved_supporting_documents": approved_documents,
        "internal_eligibility_evaluation": internal_eligibility,
        "quarantined_payment_attributes": quarantined_payment,
        "excluded_attributes": excluded_attributes,
        "justifications": justifications,
        "missing_mandatory_documents": matched_data.get("missing_mandatory_documents", []),
        "missing_conditional_documents": matched_data.get("missing_conditional_documents", []),
        "failed_eligibility_requirements": matched_data.get("failed_eligibility_requirements", []),
        "payment_conditions": matched_data.get("payment_conditions", {}),
        "total_available_attributes": len(all_profile_keys),
        "disclosed_fields_count": len(portal_fields),
        "disclosed_documents_count": len(approved_documents),
        "total_disclosed_count": len(portal_fields) + len(approved_documents),
        "quarantined_attributes_count": len(quarantined_payment),
        "excluded_attributes_count": len(excluded_attributes)
    }
