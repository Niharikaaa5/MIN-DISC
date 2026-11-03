"""
Module: User Attribute Matcher
Maps extracted task requirements to specific user profile attribute keys via explicit rules.
Respects typed requirements: application_field, supporting_document, and conditional_requirement.
"""
from typing import Dict, List, Optional


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


def match_user_attributes(extracted_requirements: Dict, user_profile: Dict) -> Dict:
    """
    Maps extracted task requirements to corresponding user profile attribute keys.
    Respects requirement categories:
    - supporting_document: physical proof documents
    - conditional_requirement: conditional document proofs (e.g. Non-ECR proof, Doc 41)
    - application_field: text form fields (Name, DOB, Address)

    Returns:
        Dict containing:
            - mapping: Dict[str, Dict]
            - matched_attribute_keys: List[str]
            - missing_mandatory_attributes: List[str]
            - available_user_attributes: List[str]
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

        attr_val = user_profile.get(attr_key) if attr_key else None
        present_in_profile = attr_val is not None and attr_val != ""

        mapping[req_name] = {
            "attribute_key": attr_key,
            "mapped_attribute": attr_key,
            "type": req_type,
            "status": status,
            "mandatory": is_mandatory,
            "present_in_profile": present_in_profile,
            "value": attr_val,
            "condition": condition,
            "document_no": doc_no
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
        "available_user_attributes": available_keys
    }
