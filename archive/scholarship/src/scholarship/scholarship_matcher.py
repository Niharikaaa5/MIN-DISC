"""
Module: Scholarship Attribute Matcher
Evaluates applicant profile against canonical Fresh CSSS requirements.
Identifies:
- Satisfied requirements.
- Failed eligibility requirements.
- Missing information / portal fields.
- Missing mandatory supporting documents (SD-01, SD-02).
- Missing conditional supporting documents (SD-03 for SC/ST/OBC, SD-04 for PwD).
- Payment conditions (quarantined and evaluated separately).
"""
from typing import Dict, List, Any, Optional


def match_scholarship_attributes(extracted_requirements: Dict, applicant_profile: Dict) -> Dict:
    """
    Evaluates applicant profile attributes against extracted CSSS requirements.
    Preserves strict architectural boundaries:
    - Internal eligibility criteria vs Uploaded supporting documents vs Portal form fields vs Payment layer.
    """
    canonical_reqs = extracted_requirements.get("canonical_requirements", [])
    
    satisfied_requirements = []
    failed_eligibility = []
    missing_mandatory_docs = []
    missing_conditional_docs = []
    missing_fields = []
    portal_fields_matched = {}
    quarantined_payment_matched = {}
    
    mapping = {}
    
    # Applicant core demographic attributes
    caste_category = applicant_profile.get("caste_category", "General")
    disability_pct = float(applicant_profile.get("disability_percentage") or 0.0)
    
    for req in canonical_reqs:
        rid = req.get("requirement_id")
        rname = req.get("requirement_name")
        rtype = req.get("requirement_type")
        mand = req.get("mandatory_or_conditional", "mandatory")
        target_key = req.get("target_profile_key")
        
        prof_val = applicant_profile.get(target_key) if target_key else None
        has_val = prof_val is not None and prof_val != ""
        
        req_status = "UNKNOWN"
        failure_reason = None
        
        # 1. ACADEMIC ELIGIBILITY CHECKS (Internal Evaluation)
        if rtype == "academic_eligibility":
            if rid == "REQ-SCH-ACAD-01":
                # Class XII 80th percentile cutoff (strictly percentile rank, NOT percentage marks)
                pct = float(prof_val or 0.0) if has_val else None
                if pct is None:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)
                elif pct >= 80.0:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "FAILED"
                    failure_reason = f"Class XII percentile rank ({pct}) is below the required 80th percentile threshold (percentage marks do not substitute for percentile rank)."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                    
            elif rid == "REQ-SCH-ACAD-02":
                # Board top 20th percentile merit list inclusion
                if prof_val is True:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                elif prof_val is False:
                    req_status = "FAILED"
                    failure_reason = "Applicant is not included in the State Board Top 20th percentile merit list."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                else:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)
                    
            elif rid == "REQ-SCH-ACAD-03":
                # Immediate preceding year passing (No drop year) - Scoped to AY 2025-26
                if prof_val is False:  # gap_year_flag == False -> No gap year
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                elif prof_val is True:
                    req_status = "FAILED"
                    failure_reason = "Applicant took a drop year; ineligible under immediate preceding academic year rule (scoped to AY 2025-26 per FAQ Q1)."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                else:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)

        # 2. FAMILY INCOME ELIGIBILITY (Internal Evaluation)
        elif rtype == "income_eligibility":
            if rid == "REQ-SCH-INC-01":
                income = int(prof_val or 0) if has_val else None
                if income is None:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)
                elif income <= 450000:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "FAILED"
                    failure_reason = f"Family gross annual income (Rs {income:,}) exceeds the maximum scheme ceiling of Rs 4,50,000 p.a."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})

        # 3. COURSE & INSTITUTIONAL ELIGIBILITY (Internal Evaluation)
        elif rtype == "institutional_eligibility":
            if rid == "REQ-SCH-INST-01":
                # Regular degree course
                degree_level = applicant_profile.get("degree_level", "Degree")
                if prof_val == "Regular" and degree_level != "Diploma":
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "FAILED"
                    if degree_level == "Diploma":
                        failure_reason = "Pursuing Diploma course; diploma students are strictly ineligible for CSSS."
                    else:
                        failure_reason = f"Course mode '{prof_val}' is ineligible; scheme strictly mandates regular, full-time study mode."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                    
            elif rid == "REQ-SCH-INST-02":
                # Regulatory recognition
                if prof_val is True:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "FAILED"
                    failure_reason = "Institution lacks recognized affiliation from AICTE, UGC, or concerned regulatory body."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                    
            elif rid == "REQ-SCH-INST-03":
                # Valid AISHE code - missing code is unknown/unverified (NEEDS_REVIEW), not outright ineligibility
                if has_val and str(prof_val).strip() != "":
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)
                    
            elif rid == "REQ-SCH-INST-04":
                # Handled under payment conditions
                pass

            elif rid == "REQ-SCH-INST-05":
                # Exclusivity: other_scholarships_flag must be False
                if prof_val is False:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                elif prof_val is True:
                    req_status = "FAILED"
                    failure_reason = "Applicant is already availing benefits of another scholarship, fee waiver, or reimbursement scheme."
                    failed_eligibility.append({"requirement_id": rid, "reason": failure_reason})
                else:
                    req_status = "UNKNOWN"
                    missing_fields.append(target_key)

        # 4. CONDITIONAL RESERVATION ELIGIBILITY
        elif rtype == "conditional_reservation":
            if rid == "REQ-SCH-RES-01":
                if caste_category in ("SC", "ST", "OBC"):
                    req_status = "APPLICABLE_CLAIMED"
                else:
                    req_status = "NOT_APPLICABLE_GENERAL"
            elif rid == "REQ-SCH-RES-02":
                if disability_pct >= 40.0:
                    req_status = "APPLICABLE_CLAIMED"
                else:
                    req_status = "NOT_APPLICABLE"

        # 5. REQUIRED SUPPORTING DOCUMENTS (Upload Proofs)
        elif rtype == "supporting_document":
            if mand == "mandatory":
                if has_val:
                    req_status = "SATISFIED"
                    satisfied_requirements.append(rid)
                else:
                    req_status = "MISSING_MANDATORY_DOC"
                    failure_reason = f"Missing mandatory supporting document upload: '{rname}' ({target_key})."
                    missing_mandatory_docs.append({"requirement_id": rid, "document_key": target_key, "name": rname})
            elif mand == "conditional":
                if rid == "REQ-SCH-DOC-03":
                    # Caste certificate
                    if caste_category in ("SC", "ST", "OBC"):
                        if has_val:
                            req_status = "SATISFIED"
                            satisfied_requirements.append(rid)
                        else:
                            req_status = "MISSING_CONDITIONAL_DOC"
                            failure_reason = f"Applicant claimed {caste_category} quota but failed to provide Caste Certificate."
                            missing_conditional_docs.append({"requirement_id": rid, "document_key": target_key, "name": rname, "condition": f"Claimed {caste_category} quota"})
                    else:
                        req_status = "NOT_REQUIRED"
                elif rid == "REQ-SCH-DOC-04":
                    # Disability certificate
                    if disability_pct >= 40.0:
                        if has_val:
                            req_status = "SATISFIED"
                            satisfied_requirements.append(rid)
                        else:
                            req_status = "MISSING_CONDITIONAL_DOC"
                            failure_reason = f"Applicant claimed PwD quota ({disability_pct}% disability) but failed to provide Disability Certificate."
                            missing_conditional_docs.append({"requirement_id": rid, "document_key": target_key, "name": rname, "condition": f"Claimed PwD quota ({disability_pct}%)"})
                    else:
                        req_status = "NOT_REQUIRED"

        # 6. PORTAL APPLICATION FIELDS (Form Entries)
        elif rtype == "application_field":
            if has_val:
                req_status = "SATISFIED"
                satisfied_requirements.append(rid)
                portal_fields_matched[target_key] = prof_val
            else:
                req_status = "MISSING_FIELD"
                missing_fields.append(target_key)

        # 7. PAYMENT & IDENTITY ATTRIBUTES (Quarantined)
        elif rtype == "payment_and_identity_quarantine":
            if has_val:
                req_status = "QUARANTINED_AVAILABLE"
                quarantined_payment_matched[target_key] = prof_val
            else:
                req_status = "QUARANTINED_MISSING"

        mapping[rid] = {
            "requirement_name": rname,
            "requirement_type": rtype,
            "mandatory_or_conditional": mand,
            "target_profile_key": target_key,
            "profile_value": prof_val,
            "evaluation_status": req_status,
            "failure_reason": failure_reason
        }

    # -------------------------------------------------------------
    # Evaluate Payment Conditions Separately (Disbursement Readiness)
    # -------------------------------------------------------------
    aishe_status = applicant_profile.get("aishe_status", "ACTIVE")
    aadhaar_seeded = bool(applicant_profile.get("aadhaar_seeding_status", False))
    aadhaar_present = bool(applicant_profile.get("aadhaar_number"))
    bank_present = bool(applicant_profile.get("bank_account_number"))
    
    hold_reasons = []
    if aishe_status == "INACTIVE":
        hold_reasons.append("Payment release hold: Institution status is INACTIVE on AISHE portal (DOC-2 Q18). Application registration can proceed, but disbursal requires active status.")
    if not aadhaar_seeded:
        hold_reasons.append("Payment release hold: Bank account is not seeded with Aadhaar on NPCI mapper (DOC-2 Q6-Q8).")
    if not aadhaar_present:
        hold_reasons.append("Payment release hold: Aadhaar number missing for DBT APBS routing.")
    if not bank_present:
        hold_reasons.append("Payment release hold: Student savings bank account missing.")
        
    payment_conditions = {
        "aadhaar_available": aadhaar_present,
        "aadhaar_seeded": aadhaar_seeded,
        "bank_account_available": bank_present,
        "aishe_active": (aishe_status == "ACTIVE"),
        "payment_release_ready": (len(hold_reasons) == 0),
        "payment_release_hold_reasons": hold_reasons
    }

    return {
        "applicant_id": applicant_profile.get("user_id"),
        "applicant_name": applicant_profile.get("applicant_name"),
        "workflow": "fresh_scholarship_application",
        "satisfied_requirements": satisfied_requirements,
        "failed_eligibility_requirements": failed_eligibility,
        "missing_mandatory_documents": missing_mandatory_docs,
        "missing_conditional_documents": missing_conditional_docs,
        "missing_information": missing_fields,
        "portal_fields_matched": portal_fields_matched,
        "quarantined_payment_matched": quarantined_payment_matched,
        "payment_conditions": payment_conditions,
        "mapping": mapping
    }
