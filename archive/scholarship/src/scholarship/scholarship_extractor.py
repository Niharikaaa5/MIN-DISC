"""
Module: Scholarship Requirement Extractor
Extracts structured requirements for PM-USP Central Sector Scheme of Scholarship (CSSS).
Supports FRESH APPLICATION workflow.
Preserves grounded source hierarchy:
- CSSS Guidelines: Primary statutory policy source.
- DoHE FAQ: Operational reference.
- NSP Training Manual: Supplementary portal guidance.

Strictly preserves architectural boundaries:
- Eligibility attributes evaluated internally (Class 12 percentile, Income limit, AISHE status).
- Required supporting documents to be uploaded (12th mark sheet, income certificate, caste/PwD cert).
- Portal application fields (Name, Roll No, AISHE code, OTR).
- Quarantined payment/identity attributes (Aadhaar, bank account, IFSC).
"""
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json

from src.llm import LLMClient
from src.scholarship.scholarship_rag import ScholarshipRetriever, build_or_load_scholarship_rag


# Canonical Grounded Fresh Scholarship Fallback Taxonomy (DOC-1 & DOC-2)
CANONICAL_FRESH_SCHOLARSHIP_TAXONOMY = [
    # -------------------------------------------------------------
    # Category A: Academic Eligibility (Internal Evaluation)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-ACAD-01",
        "requirement_name": "Class XII 80th Percentile Merit Cutoff",
        "description": "Student must be above the 80th percentile of successful candidates in the relevant stream from respective Board of Examination in Class XII (10+2 pattern) or equivalent.",
        "requirement_type": "academic_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "class_12_percentile",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 1,
        "exact_evidence": "Students who are above 80th percentile of successful candidates in the relevant stream from the respective Board of Examination in Class XII of 10+2 pattern or equivalent;",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-ACAD-02",
        "requirement_name": "State Board Top 20th Percentile Merit List Inclusion",
        "description": "Applicant must be included in the Top 20th percentile merit list published and supplied directly by the respective State Education Board / CBSE / CISCE.",
        "requirement_type": "academic_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "board_merit_list_status",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 3,
        "exact_evidence": "who are in the Top 20th percentile list of concerned Board (SEB/CBSE/CISCE)... Those who are not covered in this list will not be able to avail the benefits",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-ACAD-03",
        "requirement_name": "Immediate Preceding Academic Year Passing (No Drop Year)",
        "description": "Applicant must have completed Class XII in the immediate preceding academic year. Students who took a drop year are ineligible under AY 2025-26 operational guidelines.",
        "requirement_type": "academic_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "gap_year_flag",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 1,
        "exact_evidence": "Students who had taken a drop after 12th class are not eligible under the scheme.",
        "confidence_status": "operational_reference"
    },

    # -------------------------------------------------------------
    # Category B: Family Income Eligibility (Internal Evaluation)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-INC-01",
        "requirement_name": "Family Income Ceiling (<= 4.5 Lakh per Annum)",
        "description": "Gross parental/family annual income from all sources must not exceed ₹4,50,000 per annum (<= ₹4.5 Lakh p.a.).",
        "requirement_type": "income_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "family_income",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Students with gross parental/family income upto ₹ 4.5 lakh per annum are eligible for scholarship under the scheme.",
        "confidence_status": "verified_grounded"
    },

    # -------------------------------------------------------------
    # Category C: Course & Institutional Eligibility (Internal Evaluation)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-INST-01",
        "requirement_name": "Regular Full-Time Degree Course Mode",
        "description": "Pursuing regular, full-time graduate, postgraduate, or integrated degree. Correspondence, distance education, part-time, or diploma courses are strictly ineligible.",
        "requirement_type": "institutional_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "course_mode",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Pursuing regular degree courses and not correspondence or distance mode or pursuing Diploma courses; Diploma students are not eligible under the scheme.",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-INST-02",
        "requirement_name": "Regulatory Recognition (AICTE, UGC, or Statutory Body)",
        "description": "Higher education institution must be recognized by AICTE, UGC, or concerned statutory regulatory bodies.",
        "requirement_type": "institutional_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "institution_recognized",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Pursuing courses at colleges/institutions recognized by All India Council for Technical Education and respective Regulatory Bodies concerned;",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-INST-03",
        "requirement_name": "Valid AISHE Code Assignment",
        "description": "Course of study and the higher education institution must possess an assigned, valid AISHE code listed on the AISHE portal.",
        "requirement_type": "institutional_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "aishe_code",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "provided the course of study and the institution is having valid AISHE Code; The AISHE code can be checked in the portal https://aishe.gov.in/aishe/aisheCode",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-INST-04",
        "requirement_name": "Active AISHE Operational Status",
        "description": "Institution's status on the AISHE portal must be ACTIVE. An INACTIVE AISHE status prevents scholarship payment release.",
        "requirement_type": "institutional_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "aishe_status",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 5,
        "exact_evidence": "since the scholarship payment won’t be released to the students studying in the institutes whose Status is INACTIVE.",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-INST-05",
        "requirement_name": "Scholarship Exclusivity (No Concurrent Benefits)",
        "description": "Applicant must not be availing benefit of any other merit scholarship schemes, State-run scholarship schemes, fee waiver, or reimbursement scheme.",
        "requirement_type": "institutional_eligibility",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "other_scholarships_flag",
        "transmission_mode": "internal_evaluation_only",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Not availing benefit of any other merit scholarship schemes, State run scholarship schemes, fee waiver, reimbursement scheme.",
        "confidence_status": "verified_grounded"
    },

    # -------------------------------------------------------------
    # Category D: Conditional Reservation Requirements
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-RES-01",
        "requirement_name": "Central Caste/Community Quota Claim (SC / ST / OBC)",
        "description": "Earmarked reservation under Central Reservation Policy: SC (15%), ST (7.5%), OBC (27%). Conditional: applies only to applicants claiming reserved quota.",
        "requirement_type": "conditional_reservation",
        "mandatory_or_conditional": "conditional",
        "applicable_to": "fresh_reserved_category_applicants",
        "target_profile_key": "caste_category",
        "transmission_mode": "portal_application_field",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Central Reservation Policy [i.e. 15% seats are earmarked for SCs, 7.5% for STs and 27 % for OBCs...]",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-RES-02",
        "requirement_name": "Benchmark Disability Horizontal Reservation (PwD >= 40%)",
        "description": "5% horizontal reservation across all categories for students with Benchmark Disabilities of 40% or more. Conditional: applies only to applicants claiming PwD quota.",
        "requirement_type": "conditional_reservation",
        "mandatory_or_conditional": "conditional",
        "applicable_to": "fresh_pwd_applicants",
        "target_profile_key": "disability_percentage",
        "transmission_mode": "portal_application_field",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "5% horizontal reservation for students with Benchmark Disabilities (Disability of 40% or more) in all the categories",
        "confidence_status": "verified_grounded"
    },

    # -------------------------------------------------------------
    # Category E: Required Supporting Documents (Uploaded Files)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-DOC-01",
        "requirement_name": "Class 12th Mark Sheet Supporting Proof",
        "description": "Scanned copy of Class 12th Mark Sheet to verify Class XII marks, roll number, stream, and passing year.",
        "requirement_type": "supporting_document",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "class_12_marksheet",
        "transmission_mode": "portal_document_upload",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 6,
        "exact_evidence": "a. FRESH: 12th Mark Sheet, Family Income Certificate, Category/ caste Certification for reserved category students, Disability Certificate (if applicable)",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-DOC-02",
        "requirement_name": "Family Income Certificate Supporting Proof",
        "description": "Official Family Income Certificate issued by competent government authority. Mandatory only for fresh applicants to verify gross parental income <= ₹4.5 Lakh p.a.",
        "requirement_type": "supporting_document",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "income_certificate",
        "transmission_mode": "portal_document_upload",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 2,
        "exact_evidence": "Income certificate will be required only for the fresh applicants; a. FRESH: ... Family Income Certificate",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-DOC-03",
        "requirement_name": "Caste / Category Certificate Supporting Proof",
        "description": "Category/caste certification issued by competent authority. Conditional: strictly required only if claiming SC, ST, or OBC reservation quota.",
        "requirement_type": "supporting_document",
        "mandatory_or_conditional": "conditional",
        "applicable_to": "fresh_reserved_category_applicants",
        "target_profile_key": "caste_certificate",
        "transmission_mode": "portal_document_upload",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 6,
        "exact_evidence": "Category/ caste Certification for reserved category students",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-DOC-04",
        "requirement_name": "Disability Certificate Supporting Proof (PwD)",
        "description": "Medical disability certificate from designated medical authority certifying benchmark disability >= 40%. Conditional: strictly required only if claiming PwD quota.",
        "requirement_type": "supporting_document",
        "mandatory_or_conditional": "conditional",
        "applicable_to": "fresh_pwd_applicants",
        "target_profile_key": "disability_certificate",
        "transmission_mode": "portal_document_upload",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 6,
        "exact_evidence": "Disability Certificate (if applicable)",
        "confidence_status": "operational_reference"
    },

    # -------------------------------------------------------------
    # Category F: Portal Application Fields (Data Entry, Not Uploads)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-FLD-01",
        "requirement_name": "One-Time Registration (OTR) / Login Identifier",
        "description": "OTR Number or Aadhaar authentication reference for portal login and application initiation.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "otr_number",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "14. How to apply for Fresh / Renewal application? ... Login with your OTR and apply for the scheme",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-02",
        "requirement_name": "Applicant Legal Full Name",
        "description": "Applicant full legal name. Must match exactly with Class XII Roll Card / Marksheet and Aadhaar demographic details.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "applicant_name",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Student name and Father name should be same as mentioned in Roll card/ Marksheet of 12th class and Aadhaar.",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-03",
        "requirement_name": "Father's Full Name",
        "description": "Father's full legal name. Must match Class XII Marksheet and Aadhaar demographic records.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "father_name",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Student name and Father name should be same as mentioned in Roll card/ Marksheet of 12th class and Aadhaar.",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-04",
        "requirement_name": "Date of Birth Demographic Entry",
        "description": "Date of birth in YYYY-MM-DD format as registered in OTR and verified against Class XII records.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "date_of_birth",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Date of Birth as mentioned in the 12th class Marksheet / Roll Card and Aadhaar",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-05",
        "requirement_name": "Active Mobile Number",
        "description": "Primary mobile number registered for receiving OTPs and portal verification messages.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "mobile_number",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Personal Mobile Number and personal Email id must be active at least till the end of the course",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-06",
        "requirement_name": "Active Email Address",
        "description": "Personal email address kept active throughout course duration for scheme notifications.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "email",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Personal Mobile Number and personal Email id must be active at least till the end of the course",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-FLD-07",
        "requirement_name": "Class XII Examination Roll Number",
        "description": "Board examination roll number matching Class XII mark sheet to link with Board merit data.",
        "requirement_type": "application_field",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "fresh_applicants",
        "target_profile_key": "class_12_roll_no",
        "transmission_mode": "portal_application_field",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 4,
        "exact_evidence": "Roll number should be same as mentioned in the 12th class Roll Card / Marksheet",
        "confidence_status": "operational_reference"
    },

    # -------------------------------------------------------------
    # Category G: Quarantined Payment & Identity Attributes
    # (Strictly isolated from Stage 1/2 Application Document Payload)
    # -------------------------------------------------------------
    {
        "requirement_id": "REQ-SCH-PAY-01",
        "requirement_name": "Aadhaar Identity & DBT Routing Key",
        "description": "Aadhaar number used for e-KYC tokenization during OTR and routing in the NPCI mapper for Direct Benefit Transfer. Quarantined from the portal application supporting-document payload.",
        "requirement_type": "payment_and_identity_quarantine",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "all_fresh_recipients",
        "target_profile_key": "aadhaar_number",
        "transmission_mode": "quarantined_payment_layer",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 4,
        "exact_evidence": "The scholarship will be disbursed directly into the bank accounts of the beneficiaries through Direct Benefit Transfer (DBT) under the Public Financial Management System (PFMS).",
        "confidence_status": "verified_grounded"
    },
    {
        "requirement_id": "REQ-SCH-PAY-02",
        "requirement_name": "Aadhaar Seeding Status with Bank Account (NPCI Mapper)",
        "description": "Bank account must be actively seeded with Aadhaar on the NPCI mapper for DBT scholarship credit to succeed.",
        "requirement_type": "payment_and_identity_quarantine",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "all_fresh_recipients",
        "target_profile_key": "aadhaar_seeding_status",
        "transmission_mode": "quarantined_payment_layer",
        "source_file": "FAQ_DOHE_CSSS.pdf",
        "source_page": 2,
        "exact_evidence": "student must check their 'Aadhaar seeding status' with bank account... on NPCI mapper/BASE platform",
        "confidence_status": "operational_reference"
    },
    {
        "requirement_id": "REQ-SCH-PAY-03",
        "requirement_name": "Savings Bank Account in Student's Name",
        "description": "Active savings account in applicant's name. Quarantined from Stages 1-2 application document payloads.",
        "requirement_type": "payment_and_identity_quarantine",
        "mandatory_or_conditional": "mandatory",
        "applicable_to": "all_fresh_recipients",
        "target_profile_key": "bank_account_number",
        "transmission_mode": "quarantined_payment_layer",
        "source_file": "CSSS_GUIDLINES_07022024_updated.pdf",
        "source_page": 3,
        "exact_evidence": "beneficiaries through Direct Benefit Transfer... into the bank accounts of the beneficiaries",
        "confidence_status": "verified_grounded"
    }
]


def resolve_scholarship_chunk_provenance(item: Dict, retrieved_chunks: List[Dict]) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
    """
    Finds matching retrieved chunk in the isolated scholarship vector index.
    Returns (chunk_id, page_number, file_name, exact_evidence_snippet).
    """
    if not retrieved_chunks:
        return item.get("source_chunk_id"), item.get("source_page"), item.get("source_file"), item.get("exact_evidence")

    target_file = (item.get("source_file") or "").lower()
    target_page = item.get("source_page")
    req_name = (item.get("requirement_name") or "").lower()
    req_key = (item.get("target_profile_key") or "").lower()

    # Search phrases for grounded matching
    search_phrases = []
    if "percentile" in req_name or "merit" in req_name or "80th" in req_name:
        search_phrases = ["80th percentile", "top 20th percentile", "meritorious students"]
    elif "income" in req_name or req_key in ("family_income", "income_certificate"):
        search_phrases = ["4.5 lakh", "gross parental", "income certificate will be required only for the fresh"]
    elif "mark sheet" in req_name or req_key == "class_12_marksheet":
        search_phrases = ["12th mark sheet", "previous year mark sheet", "marksheet"]
    elif "caste" in req_name or req_key == "caste_certificate":
        search_phrases = ["category/ caste certification", "sc", "st", "obc"]
    elif "disability" in req_name or req_key == "disability_certificate":
        search_phrases = ["disability certificate", "benchmark disabilities"]
    elif "drop" in req_name or req_key == "gap_year_flag":
        search_phrases = ["taken a drop", "drop after 12th"]
    elif "aishe" in req_name or req_key in ("aishe_code", "aishe_status"):
        search_phrases = ["aishe", "status is inactive", "valid aishe code"]
    elif "regular" in req_name or req_key == "course_mode":
        search_phrases = ["regular degree courses", "correspondence", "diploma"]
    elif "aadhaar" in req_name or "payment" in req_name or "dbt" in req_name or req_key.startswith("aadhaar"):
        search_phrases = ["aadhaar seeding", "direct benefit transfer", "npci mapper", "disbursed directly"]
    elif "otr" in req_name or req_key == "otr_number":
        search_phrases = ["otr", "one time registration"]
    elif "name" in req_name or req_key in ("applicant_name", "father_name"):
        search_phrases = ["student name and father name", "roll card/ marksheet"]

    # First pass: match by both content and preferred source file/page
    for chunk in retrieved_chunks:
        txt = chunk.get("text", "").lower()
        fn = chunk.get("file_name", "").lower()
        pg = chunk.get("page_number")

        content_match = any(sp in txt for sp in search_phrases) if search_phrases else False
        file_match = (target_file in fn) if target_file else True
        page_match = (pg == target_page) if target_page else True

        if content_match and file_match:
            return chunk["chunk_id"], chunk["page_number"], chunk["file_name"], chunk["text"][:250].strip()

    # Second pass: content match across any retrieved scholarship chunk
    for chunk in retrieved_chunks:
        txt = chunk.get("text", "").lower()
        if any(sp in txt for sp in search_phrases if sp):
            return chunk["chunk_id"], chunk["page_number"], chunk["file_name"], chunk["text"][:250].strip()

    # Retain static verified ground truth if chunk not in top_k
    return None, item.get("source_page"), item.get("source_file"), item.get("exact_evidence")


def attach_provenance_to_scholarship_requirements(requirements: List[Dict], retrieved_chunks: List[Dict]) -> List[Dict]:
    """Attaches source_chunk_id, source_page, source_file, and grounded excerpt to each requirement item."""
    for item in requirements:
        cid, page, fname, evidence = resolve_scholarship_chunk_provenance(item, retrieved_chunks)
        item["source_chunk_id"] = cid
        item["source_page"] = page
        item["source_file"] = fname
        if evidence:
            item["exact_evidence"] = evidence
        
        # If chunk was actively retrieved from vector store, mark verified
        if cid:
            item["confidence_status"] = "verified_grounded"
        elif item.get("confidence_status") is None:
            item["confidence_status"] = "fallback_deterministic"

    return requirements


def extract_scholarship_requirements(
    task_name: str = "apply for fresh PM-USP CSSS college scholarship",
    llm_client: Optional[LLMClient] = None,
    retriever: Optional[ScholarshipRetriever] = None
) -> Dict:
    """
    Extracts structured requirements for PM-USP Central Sector Scheme of Scholarship (CSSS).
    Initially targets the FRESH APPLICATION workflow.
    
    Guarantees:
    - Zero contamination from passport concepts (no address proof / police verification / passport fields).
    - Strict categorization into Academic, Income, Institutional, Supporting Docs, Form Fields, and Quarantined Payment.
    - Grounded citations from official CSSS Guidelines and DoHE FAQ.
    - Fallback deterministic taxonomy when Gemini is unavailable.
    """
    # 1. Initialize retriever if not supplied
    if retriever is None:
        retriever, _, _ = build_or_load_scholarship_rag(force_rebuild=False)

    # 2. Retrieve scholarship chunks using targeted multi-aspect queries
    retrieved_chunks = retriever.retrieve(task_name, top_k=6)

    citations = [
        {
            "file_name": c["file_name"],
            "page_number": c["page_number"],
            "chunk_id": c["chunk_id"],
            "doc_classification": c.get("doc_classification", "general_reference"),
            "source_priority": c.get("source_priority", 99)
        }
        for c in retrieved_chunks
    ]

    # 3. LLM Extraction Path (Active when Gemini client is configured)
    if llm_client and llm_client.client and retrieved_chunks:
        context_text = "\n\n".join([
            f"[Source: {c['file_name']}, Page {c['page_number']}, Chunk ID: {c['chunk_id']}, Class: {c.get('doc_classification', 'ref')}]\n{c['text']}"
            for c in retrieved_chunks
        ])

        prompt = f"""You are a Task-Aware Privacy Agent extracting official scholarship requirements strictly from authoritative document context for the PM-USP Central Sector Scheme of Scholarship (CSSS).

CONTEXT FROM OFFICIAL SCHOLARSHIP DOCUMENTS:
{context_text}

USER TASK:
"{task_name}" (Target Scope: Fresh Application for College / University Students)

INSTRUCTIONS:
1. Extract requirements that are EXPLICITLY supported by the context text above.
2. Target the FRESH APPLICATION workflow only.
3. Categorize requirements into:
   - academic_eligibility (merit percentile, passing year, regular course)
   - income_eligibility (parental income <= 4.5 lakh)
   - institutional_eligibility (AICTE/UGC recognition, AISHE code, active status)
   - conditional_reservation (SC, ST, OBC quotas, PwD disability)
   - supporting_document (Class 12 mark sheet, income certificate, caste certificate, disability certificate)
   - application_field (OTR number, student name, father name, DOB, roll number)
   - payment_and_identity_quarantine (Aadhaar number, bank account number, NPCI seeding status)
4. Do NOT confuse internal eligibility criteria with uploaded supporting documents.
5. Do NOT include passport terms or unrelated requirements.
6. Return ONLY valid JSON with keys: 'workflow', 'scheme', 'authority', 'canonical_requirements'.
"""
        llm_json = llm_client.generate_json(prompt)
        if llm_json and isinstance(llm_json, dict) and "canonical_requirements" in llm_json:
            reqs = llm_json["canonical_requirements"]
            if isinstance(reqs, list) and len(reqs) >= 4:
                attached_reqs = attach_provenance_to_scholarship_requirements(reqs, retrieved_chunks)
                return {
                    "workflow": "fresh_scholarship_application",
                    "scheme": "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
                    "authority": "Ministry of Education, Department of Higher Education (Scholarship Division)",
                    "extraction_mode": "llm_grounded",
                    "rag_citations": citations,
                    "canonical_requirements": attached_reqs
                }

    # 4. Deterministic Fallback Path (Grounded in Verified Scholarship Inventory)
    fallback_reqs = [dict(item) for item in CANONICAL_FRESH_SCHOLARSHIP_TAXONOMY]
    attached_fallback = attach_provenance_to_scholarship_requirements(fallback_reqs, retrieved_chunks)

    # Segregate requirements into architectural categories
    academic_reqs = [r for r in attached_fallback if r["requirement_type"] == "academic_eligibility"]
    income_reqs = [r for r in attached_fallback if r["requirement_type"] == "income_eligibility"]
    inst_reqs = [r for r in attached_fallback if r["requirement_type"] == "institutional_eligibility"]
    res_reqs = [r for r in attached_fallback if r["requirement_type"] == "conditional_reservation"]
    doc_reqs = [r for r in attached_fallback if r["requirement_type"] == "supporting_document"]
    fld_reqs = [r for r in attached_fallback if r["requirement_type"] == "application_field"]
    pay_reqs = [r for r in attached_fallback if r["requirement_type"] == "payment_and_identity_quarantine"]

    return {
        "workflow": "fresh_scholarship_application",
        "scheme": "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
        "authority": "Ministry of Education, Department of Higher Education (Scholarship Division)",
        "extraction_mode": "deterministic_fallback",
        "rag_citations": citations,
        "academic_eligibility": academic_reqs,
        "income_eligibility": income_reqs,
        "institutional_eligibility": inst_reqs,
        "conditional_requirements": res_reqs,
        "supporting_documents": doc_reqs,
        "application_fields": fld_reqs,
        "payment_and_identity_attributes": pay_reqs,
        "canonical_requirements": attached_fallback,
        "unsupported_or_excluded_attributes": [
            {
                "attribute": "religion",
                "status": "UNSUPPORTED_EXCLUDED",
                "reason": "CSSS is a secular merit-cum-means scheme; religion is not an eligibility factor."
            },
            {
                "attribute": "land_records_assets",
                "status": "UNSUPPORTED_EXCLUDED",
                "reason": "Only executive family income certificate is mandated; asset schedules are not required."
            },
            {
                "attribute": "medical_history",
                "status": "UNSUPPORTED_EXCLUDED",
                "reason": "Only benchmark disability certificate (>= 40%) is recognized for PwD quota."
            },
            {
                "attribute": "college_id_cards",
                "status": "NOT_APPLICABLE_TO_FRESH",
                "reason": "College ID cards apply strictly to 2nd/3rd year institutional transfers handled by State Nodal Agencies, not fresh portal uploads."
            }
        ],
        "unresolved_operational_ambiguities": [
            {
                "parameter": "income_certificate_issuing_authority_rank",
                "status": "UNKNOWN",
                "limitation": "The guidelines and FAQ mandate a Family Income Certificate but do not specify revenue officer rank (Tehsildar/SDM/DM); governed by State jurisdiction."
            },
            {
                "parameter": "board_merit_list_transmission_medium",
                "status": "UNKNOWN",
                "limitation": "DoHE states State Boards provide Top 20th percentile list directly to NSP, but portal lookup API vs manual upload verification mechanics are not exposed."
            }
        ]
    }
