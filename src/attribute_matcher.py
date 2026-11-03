"""
Module: User Attribute Matcher
Maps extracted task requirements to specific user profile attribute keys via explicit rules.
Respects typed requirements: application_field, supporting_document, and conditional_requirement.
"""
from typing import Dict, List, Optional, Any


EXPLICIT_REQUIREMENT_MAPPINGS = {
    "proof of present address": "address_proof",
    "proof of date of birth": "date_of_birth_proof",
    "non-ecr documentary proof": "academic_record",
    "documentary proof for non-ecr category": "academic_record",
    "non-ecr proof": "academic_record",
    "applicant name": "name",
    "date of birth": "date_of_birth",
    "present residential address": "address"
}


def match_user_attributes(
    extracted_requirements: Dict,
    user_profile: Dict,
    accessed_documents: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Maps extracted task requirements to corresponding user profile attribute keys.
    Respects requirement categories:
    - supporting_document: physical proof documents
    - conditional_requirement: conditional document proofs (e.g. Non-ECR proof, Doc 41)
    - application_field: text form fields (Name, DOB, Address)

    When accessed_documents from the RepositoryAccessController is provided,
    supporting document tokens are verified against actually opened repository files.

    Returns:
        Dict containing:
            - mapping: Dict[str, Dict]
            - matched_attribute_keys: List[str]
            - missing_mandatory_attributes: List[str]
            - available_user_attributes: List[str]
            - repository_verified: bool
    """
    req_list = extracted_requirements.get("requirements", [])

    mapping = {}
    matched_keys = []
    missing_mandatory = []

    for req in req_list:
        req_name = req.get("requirement", "").strip()
        req_type = req.get("type", "supporting_document")
        status = req.get("status", "mandatory" if req.get("mandatory", True) else "conditional")
        is_mandatory = req.get("mandatory", status == "mandatory")
        attr_key = req.get("mapped_attribute")
        doc_no = req.get("document_no")
        condition = req.get("condition")

        # Fallback for requirement patterns if mapped_attribute is not explicitly set in req dict
        if not attr_key:
            req_lower = req_name.lower()
            for pattern, key in EXPLICIT_REQUIREMENT_MAPPINGS.items():
                if pattern in req_lower:
                    attr_key = key
                    break

        doc_file = None
        doc_file_id = None
        accessed_from_repo = False

        if accessed_documents is not None and req_type in ["supporting_document", "conditional_requirement"]:
            # Verify against repository accessed documents
            if attr_key == "address_proof":
                doc = accessed_documents.get("proof_of_address")
                if doc:
                    attr_val = doc.get("token")
                    doc_file = doc.get("file_name")
                    doc_file_id = doc.get("file_id")
                    accessed_from_repo = True
                else:
                    attr_val = None
            elif attr_key == "date_of_birth_proof":
                doc = accessed_documents.get("proof_of_date_of_birth")
                if doc:
                    attr_val = doc.get("token")
                    doc_file = doc.get("file_name")
                    doc_file_id = doc.get("file_id")
                    accessed_from_repo = True
                else:
                    attr_val = None
            elif attr_key == "academic_record":
                doc = accessed_documents.get("proof_of_non_ecr") or accessed_documents.get("academic_certificate")
                if doc:
                    attr_val = doc.get("token")
                    doc_file = doc.get("file_name")
                    doc_file_id = doc.get("file_id")
                    accessed_from_repo = True
                else:
                    attr_val = None
            else:
                attr_val = user_profile.get(attr_key) if attr_key else None
        else:
            # Fallback directly to user_profile
            attr_val = user_profile.get(attr_key) if attr_key else None

        present_in_profile = attr_val is not None and str(attr_val).strip() != ""

        mapping[req_name] = {
            "attribute_key": attr_key,
            "mapped_attribute": attr_key,
            "type": req_type,
            "status": status,
            "mandatory": is_mandatory,
            "present_in_profile": present_in_profile,
            "value": attr_val,
            "condition": condition,
            "document_no": doc_no,
            "accessed_from_repository": accessed_from_repo,
            "document_file": doc_file,
            "document_file_id": doc_file_id
        }

        if attr_key and present_in_profile:
            if attr_key not in matched_keys:
                matched_keys.append(attr_key)

        # Track missing mandatory attributes ONLY for mandatory supporting documents
        # Do NOT convert application_field or conditional_requirement into missing mandatory supporting documents
        if req_type == "supporting_document" and is_mandatory:
            if attr_key and not present_in_profile:
                if attr_key not in missing_mandatory:
                    missing_mandatory.append(attr_key)

    available_keys = [
        k for k, v in user_profile.items()
        if v is not None and k not in ["user_id", "name"]
    ]

    return {
        "mapping": mapping,
        "matched_attribute_keys": matched_keys,
        "missing_mandatory_attributes": missing_mandatory,
        "available_user_attributes": available_keys,
        "repository_verified": accessed_documents is not None
    }
