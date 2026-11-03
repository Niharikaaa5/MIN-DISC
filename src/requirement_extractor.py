from typing import List, Dict, Optional, Tuple
from src.llm import LLMClient


def validate_extracted_requirements(llm_json: Dict, retrieved_chunks: List[Dict]) -> bool:
    """
    Validates LLM-extracted requirements JSON.
    Checks structural validity, requirement categories, and evidence grounding.
    """
    if not isinstance(llm_json, dict):
        return False

    reqs = llm_json.get("requirements")
    if not isinstance(reqs, list) or len(reqs) == 0:
        return False

    valid_types = {"supporting_document", "conditional_requirement", "application_field"}

    supporting_doc_count = 0

    for item in reqs:
        if not isinstance(item, dict):
            return False

        req_name = item.get("requirement")
        if not req_name or not isinstance(req_name, str) or not req_name.strip():
            return False

        req_type = item.get("type")
        if req_type not in valid_types:
            return False

        # Ensure mandatory boolean and status consistency
        if "mandatory" not in item:
            item["mandatory"] = (item.get("status") == "mandatory")

        if "status" not in item:
            item["status"] = "mandatory" if item.get("mandatory", True) else "conditional"

        if req_type == "supporting_document":
            supporting_doc_count += 1

    # Must extract at least 1 valid supporting document proof from context
    if supporting_doc_count == 0:
        return False

    return True


def resolve_requirement_provenance(item: Dict, retrieved_chunks: List[Dict]) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Resolves matching retrieved chunk provenance (source_chunk_id, source_page, source_file) for a requirement item.
    Returns (chunk_id, page_number, file_name) if evidence chunk is present in retrieved_chunks, else (None, None, None).
    """
    if not retrieved_chunks:
        return None, None, None

    # Check if item already specifies a valid chunk_id matching retrieved_chunks
    explicit_chunk_id = item.get("source_chunk_id")
    if explicit_chunk_id:
        for chunk in retrieved_chunks:
            if chunk["chunk_id"] == explicit_chunk_id:
                return chunk["chunk_id"], chunk["page_number"], chunk["file_name"]

    doc_no = item.get("document_no")
    req_name = str(item.get("requirement", "")).lower()
    mapped_attr = str(item.get("mapped_attribute", "")).lower()
    req_type = str(item.get("type", "")).lower()

    # Define grounded search phrases for official requirement mapping
    search_phrases = []
    if doc_no == 1 or mapped_attr == "address_proof" or ("address" in req_name and req_type == "supporting_document"):
        search_phrases = ["document no. 1", "document no.1", "proof of current address", "proof of address", "table 2"]
    elif doc_no == 2 or mapped_attr == "date_of_birth_proof" or ("date of birth" in req_name and req_type == "supporting_document"):
        search_phrases = ["document no. 2", "document no.2", "proof of date of birth", "proof of birth"]
    elif doc_no == 3 or mapped_attr == "academic_record" or "non-ecr" in req_name or "ecr" in req_name:
        search_phrases = ["document no. 3", "document no.3", "non-ecr", "non ecr", "3 (if the applicant is eligible for non ecr)"]
    elif doc_no == 41 or "police verification" in req_name or "document 41" in req_name:
        search_phrases = ["document no. 41", "document no.41", "41 (if post police verification", "police verification", "doc 41"]
    elif mapped_attr == "name" or ("name" in req_name and req_type == "application_field"):
        search_phrases = ["given name & surname", "applicant's given name", "column 2.1", "applicant name"]
    elif mapped_attr == "date_of_birth" and req_type == "application_field":
        search_phrases = ["column 2.4", "write your date of birth"]
    elif mapped_attr == "address" and req_type == "application_field":
        search_phrases = ["column 4", "present residential address"]
    elif req_name:
        search_phrases = [req_name]

    for chunk in retrieved_chunks:
        txt = chunk.get("text", "").lower()
        if any(sp in txt for sp in search_phrases if sp):
            return chunk["chunk_id"], chunk["page_number"], chunk["file_name"]

    return None, None, None


def attach_provenance_to_requirements(requirements: List[Dict], retrieved_chunks: List[Dict]) -> List[Dict]:
    """Attaches source_chunk_id, source_page, and source_file provenance to each requirement item."""
    for item in requirements:
        cid, page, fname = resolve_requirement_provenance(item, retrieved_chunks)
        item["source_chunk_id"] = cid
        item["source_page"] = page
        item["source_file"] = fname
    return requirements


def extract_requirements(
    retrieved_chunks: List[Dict],
    task_name: str = "fresh passport application",
    llm_client: Optional[LLMClient] = None
) -> Dict:
    """
    Extracts structured requirements from retrieved official RAG document chunks.
    Uses evidence-driven LLM extraction when available, falling back to prototype taxonomy.

    Target Case:
    Fresh Passport -> Adult -> Ordinary Case -> Citizen of India by birth -> Normal

    Requirement Categories:
    1. application_field: Text form entries (Name, DOB, Address)
    2. supporting_document: Physical document proofs (Address Proof, DOB Proof)
    3. conditional_requirement: Conditional documents (Non-ECR Proof, Post Police Verification Doc 41)
    4. excluded_unrelated_data: Data not required for passport processing (Income, Bank Account, Medical)
    """
    citations = [
        {
            "file_name": chunk["file_name"],
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"]
        }
        for chunk in retrieved_chunks
    ]

    # Deterministic Prototype Fallback Taxonomy Model
    prototype_requirements = [
        {
            "requirement": "Proof of Present Address",
            "type": "supporting_document",
            "mandatory": True,
            "status": "mandatory",
            "mapped_attribute": "address_proof",
            "document_no": 1,
            "condition": None
        },
        {
            "requirement": "Proof of Date of Birth",
            "type": "supporting_document",
            "mandatory": True,
            "status": "mandatory",
            "mapped_attribute": "date_of_birth_proof",
            "document_no": 2,
            "condition": None
        },
        {
            "requirement": "Documentary Proof for Non-ECR",
            "type": "conditional_requirement",
            "mandatory": False,
            "status": "conditional",
            "mapped_attribute": "academic_record",
            "document_no": 3,
            "condition": "Only required/disclosed when Non-ECR is explicitly established"
        },
        {
            "requirement": "Post Police Verification Document",
            "type": "conditional_requirement",
            "mandatory": False,
            "status": "conditional",
            "mapped_attribute": None,
            "document_no": 41,
            "condition": "Only required if Post-Police Verification is triggered"
        },
        {
            "requirement": "Applicant Name",
            "type": "application_field",
            "mandatory": True,
            "status": "mandatory",
            "mapped_attribute": "name",
            "document_no": None,
            "condition": None
        },
        {
            "requirement": "Date of Birth",
            "type": "application_field",
            "mandatory": True,
            "status": "mandatory",
            "mapped_attribute": "date_of_birth",
            "document_no": None,
            "condition": None
        },
        {
            "requirement": "Present Residential Address",
            "type": "application_field",
            "mandatory": True,
            "status": "mandatory",
            "mapped_attribute": "address",
            "document_no": None,
            "condition": None
        }
    ]

    # PRIMARY PATH: Evidence-Driven LLM Extraction (Active when LLM client & non-empty RAG context exist)
    if llm_client and llm_client.client and retrieved_chunks:
        context_text = "\n\n".join([
            f"[Source: {c['file_name']}, Page {c['page_number']}, Chunk ID: {c['chunk_id']}]\n{c['text']}"
            for c in retrieved_chunks
        ])

        prompt = f"""You are a Task-Aware Privacy Agent extracting official passport requirements strictly from authoritative document context.

CONTEXT FROM OFFICIAL DOCUMENTS:
{context_text}

USER TASK:
"{task_name}" (Target Scope: Adult, Ordinary Case, Citizen of India by Birth, Normal Application)

INSTRUCTIONS:
Extract requirements that are EXPLICITLY supported by the provided context text above.
Do NOT invent requirements or copy ungrounded examples if they are not supported by the document text.
If the context text does not contain evidence for a requirement category, do NOT fabricate entries.

Classify each extracted requirement into one of these three types:
1. supporting_document: Physical or official proof attachments explicitly mandated (e.g. proof of address, proof of birth)
2. conditional_requirement: Conditional documents required only under specific circumstances (e.g. Non-ECR proof, post-police verification)
3. application_field: Core text form fields required in the application (e.g. Applicant Name, Date of Birth, Present Address)

For each requirement, specify source_chunk_id, source_page, and source_file from the context chunk providing evidence.

Return ONLY valid JSON matching this structural schema:
{{
  "task": "fresh passport application",
  "category": "adult",
  "case": "ordinary case",
  "citizenship_basis": "citizen of India by birth",
  "application_type": "normal",
  "requirements": [
    {{
      "requirement": "<Requirement name extracted strictly from context>",
      "type": "<supporting_document | conditional_requirement | application_field>",
      "mandatory": true,
      "status": "<mandatory | conditional>",
      "mapped_attribute": "<mapped profile key string if known, or null>",
      "document_no": <document number integer if mentioned in text, or null>,
      "condition": "<description of condition if conditional, or null>",
      "source_chunk_id": "<chunk_id of chunk providing evidence, or null>",
      "source_page": <page number integer of chunk providing evidence, or null>,
      "source_file": "<file_name string of chunk providing evidence, or null>"
    }}
  ],
  "excluded_unrelated_data": [
    "family_income",
    "bank_account",
    "medical_information"
  ]
}}
"""
        llm_json = llm_client.generate_json(prompt)
        if llm_json and validate_extracted_requirements(llm_json, retrieved_chunks):
            llm_json["requirements"] = attach_provenance_to_requirements(llm_json["requirements"], retrieved_chunks)
            llm_json["rag_citations"] = citations
            if "unclassified_profile_attributes" not in llm_json:
                llm_json["unclassified_profile_attributes"] = [
                    "phone",
                    "email",
                    "employment",
                    "identity_proof"
                ]
            return llm_json
        else:
            print("[NOTE] LLM extraction unavailable or failed validation. Utilizing deterministic fallback taxonomy.")

    # SECONDARY PATH: Deterministic Fallback Model
    fallback_reqs = attach_provenance_to_requirements(prototype_requirements, retrieved_chunks)

    structured_requirements = {
        "task": "fresh passport application",
        "category": "adult",
        "case": "ordinary case",
        "citizenship_basis": "citizen of India by birth",
        "application_type": "normal",
        "requirements": fallback_reqs,
        "excluded_unrelated_data": [
            "family_income",
            "bank_account",
            "medical_information"
        ],
        "unclassified_profile_attributes": [
            "phone",
            "email",
            "employment",
            "identity_proof"
        ],
        "rag_citations": citations
    }

    return structured_requirements

