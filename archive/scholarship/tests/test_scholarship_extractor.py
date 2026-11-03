"""
Validation Test Suite: Phase 2 Scholarship Requirement Extraction & Schema
Verifies:
1. Structured Fresh Scholarship Requirement Extraction.
2. Source and page provenance grounded in Guidelines & FAQ.
3. Missing or unsupported evidence handling and UNKNOWN markers.
4. Architectural separation of eligibility attributes, supporting documents, application fields, and payment quarantine.
5. Zero contamination from Passport requirements.
"""
import sys
from pathlib import Path
import json

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.scholarship.scholarship_extractor import extract_scholarship_requirements, CANONICAL_FRESH_SCHOLARSHIP_TAXONOMY


def test_requirement_extraction():
    print("[TEST 1] Testing Fresh Scholarship Requirement Extraction...")
    res = extract_scholarship_requirements()
    
    assert isinstance(res, dict), "Result must be a dictionary!"
    assert res.get("workflow") == "fresh_scholarship_application", "Workflow must be fresh_scholarship_application!"
    assert "PM-USP" in res.get("scheme", ""), "Scheme must be PM-USP!"
    assert "canonical_requirements" in res, "canonical_requirements key missing!"
    assert len(res["canonical_requirements"]) >= 15, f"Expected >= 15 requirements, got {len(res['canonical_requirements'])}"
    print(f"  + PASSED: Extracted {len(res['canonical_requirements'])} canonical requirements (Mode: {res.get('extraction_mode')}).")
    return res


def test_source_and_page_provenance(res):
    print("\n[TEST 2] Testing Source and Page Provenance...")
    reqs = res["canonical_requirements"]
    
    valid_sources = {
        "CSSS_GUIDLINES_07022024_updated.pdf",
        "FAQ_DOHE_CSSS.pdf",
        "training_of_users_nsp.pdf"
    }
    
    for r in reqs:
        rid = r["requirement_id"]
        assert r.get("requirement_name"), f"Requirement {rid} missing requirement_name"
        assert r.get("description"), f"Requirement {rid} missing description"
        assert r.get("requirement_type"), f"Requirement {rid} missing requirement_type"
        assert r.get("mandatory_or_conditional") in ("mandatory", "conditional"), f"Invalid mandatory status in {rid}"
        assert r.get("applicable_to"), f"Requirement {rid} missing applicable_to"
        
        # Provenance checks
        src_file = r.get("source_file")
        assert src_file in valid_sources, f"Invalid source file '{src_file}' in {rid}"
        assert isinstance(r.get("source_page"), int) and r.get("source_page") >= 1, f"Invalid source page in {rid}"
        assert r.get("exact_evidence") and len(r.get("exact_evidence")) > 10, f"Evidence missing/empty in {rid}"
        assert r.get("confidence_status"), f"Confidence status missing in {rid}"
        
    print(f"  + PASSED: All {len(reqs)} requirements have complete source file, page, evidence, and confidence provenance.")


def test_missing_or_unsupported_evidence(res):
    print("\n[TEST 3] Testing Missing, Unsupported & Ambiguous Evidence Handling...")
    
    unsupported = res.get("unsupported_or_excluded_attributes", [])
    assert len(unsupported) >= 3, "unsupported_or_excluded_attributes must contain items!"
    
    unsupported_keys = {item["attribute"] for item in unsupported}
    assert "religion" in unsupported_keys, "Religion should be documented as unsupported/excluded"
    assert "medical_history" in unsupported_keys, "Medical history should be documented as unsupported/excluded"
    assert "land_records_assets" in unsupported_keys, "Land assets should be documented as unsupported/excluded"
    
    for item in unsupported:
        assert item.get("status") in ("UNSUPPORTED_EXCLUDED", "NOT_APPLICABLE_TO_FRESH")
        assert len(item.get("reason", "")) > 10, f"Missing rationale for unsupported attribute {item['attribute']}"
        print(f"  + Confirmed Unsupported Attribute: '{item['attribute']}' [{item['status']}]")

    ambiguities = res.get("unresolved_operational_ambiguities", [])
    assert len(ambiguities) >= 2, "unresolved_operational_ambiguities must contain items!"
    for amb in ambiguities:
        assert amb.get("status") == "UNKNOWN", f"Ambiguous parameter must be marked UNKNOWN: {amb}"
        assert len(amb.get("limitation", "")) > 10, f"Missing limitation for {amb['parameter']}"
        print(f"  + Confirmed Operational Ambiguity: '{amb['parameter']}' [{amb['status']}] -> {amb['limitation'][:70]}...")

    print("  + PASSED: Unsupported attributes and operational ambiguities properly classified.")


def test_separation_of_eligibility_and_documents(res):
    print("\n[TEST 4] Testing Separation of Eligibility Criteria vs Supporting Documents vs Payment...")
    
    acad = res.get("academic_eligibility", [])
    inc = res.get("income_eligibility", [])
    inst = res.get("institutional_eligibility", [])
    docs = res.get("supporting_documents", [])
    flds = res.get("application_fields", [])
    pay = res.get("payment_and_identity_attributes", [])
    
    assert len(acad) >= 2, "Academic eligibility criteria missing!"
    assert len(inc) >= 1, "Income eligibility criteria missing!"
    assert len(inst) >= 3, "Institutional criteria missing!"
    assert len(docs) >= 3, "Supporting document requirements missing!"
    assert len(pay) >= 2, "Payment/identity requirements missing!"
    
    # 1. Eligibility criteria must NOT be classified as document uploads
    for item in acad + inc + inst:
        assert item["requirement_type"] != "supporting_document", f"Eligibility criterion {item['requirement_id']} misclassified as supporting document!"
        assert item["transmission_mode"] == "internal_evaluation_only", f"Eligibility {item['requirement_id']} must have transmission_mode='internal_evaluation_only'"
        
    # 2. Supporting documents must have transmission_mode = portal_document_upload
    for doc in docs:
        assert doc["requirement_type"] == "supporting_document", f"Document {doc['requirement_id']} misclassified!"
        assert doc["transmission_mode"] == "portal_document_upload"
        
    # Check SD-01 and SD-02 are mandatory for fresh
    doc_keys = {d["target_profile_key"]: d for d in docs}
    assert "class_12_marksheet" in doc_keys, "class_12_marksheet missing from supporting documents!"
    assert doc_keys["class_12_marksheet"]["mandatory_or_conditional"] == "mandatory"
    assert "income_certificate" in doc_keys, "income_certificate missing from supporting documents!"
    assert doc_keys["income_certificate"]["mandatory_or_conditional"] == "mandatory"
    
    # Check caste and disability certs are conditional
    assert doc_keys["caste_certificate"]["mandatory_or_conditional"] == "conditional"
    assert doc_keys["disability_certificate"]["mandatory_or_conditional"] == "conditional"
    
    # 3. Payment attributes must be strictly quarantined
    for p in pay:
        assert p["requirement_type"] == "payment_and_identity_quarantine"
        assert p["transmission_mode"] == "quarantined_payment_layer", f"Payment attribute {p['requirement_id']} must be quarantined!"
        
    pay_keys = {p["target_profile_key"] for p in pay}
    assert "aadhaar_number" in pay_keys, "aadhaar_number must be in quarantined payment layer"
    assert "bank_account_number" in pay_keys, "bank_account_number must be in quarantined payment layer"
    assert "aadhaar_seeding_status" in pay_keys, "aadhaar_seeding_status must be in quarantined payment layer"
    
    print(f"  + Verified Category Counts: Academic={len(acad)}, Income={len(inc)}, Inst={len(inst)}, Docs={len(docs)}, Fields={len(flds)}, Payment(Quarantined)={len(pay)}")
    print("  + PASSED: Complete architectural separation of internal eligibility, uploaded documents, form fields, and quarantined payment attributes.")


def test_no_passport_contamination(res):
    print("\n[TEST 5] Testing Zero Contamination from Passport Requirements...")
    
    passport_forbidden_terms = [
        "address_proof", "date_of_birth_proof", "police_verification",
        "post_police_verification", "tatkaal", "non_ecr", "non-ecr", "document_no_41", "doc_41"
    ]
    
    serialized_reqs = json.dumps(res["canonical_requirements"]).lower()
    
    for term in passport_forbidden_terms:
        assert term not in serialized_reqs, f"CONTAMINATION DETECTED: Passport term '{term}' found in scholarship requirements!"
        
    print("  + PASSED: Zero passport terms, attributes, or rules found in scholarship requirement schema.")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  PHASE 2 VALIDATION: FRESH SCHOLARSHIP REQUIREMENT EXTRACTION")
    print("=" * 70)
    
    res = test_requirement_extraction()
    test_source_and_page_provenance(res)
    test_missing_or_unsupported_evidence(res)
    test_separation_of_eligibility_and_documents(res)
    test_no_passport_contamination(res)
    
    print("\n" + "=" * 70)
    print("  ALL PHASE 2 VALIDATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")
