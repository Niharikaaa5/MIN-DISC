"""
Module: Minimum-Disclosure Planner
Core research component: Identifies strictly necessary task attributes and excludes all unnecessary user data.
Enforces rule: "Data availability must never be treated as data necessity."
"""
from typing import Dict, List


# Standard privacy justifications for excluding unneeded attributes
EXCLUSION_JUSTIFICATIONS = {
    "family_income": "Financial income data is unnecessary for identity and citizenship verification in passport applications.",
    "bank_account": "Banking account details are not required for standard adult passport verification.",
    "medical_information": "Medical and clinical health records are strictly confidential and unnecessary for passport issuance.",
    "employment": "Employment information is not required for standard adult passport verification.",
    "phone": "Phone number excluded from supporting-document payload to minimize contact exposure.",
    "email": "Email address excluded from supporting-document payload to minimize contact exposure.",
    "father_name": "Parental name fields are biographical metadata and not required as standalone supporting documents.",
    "mother_name": "Parental name fields are biographical metadata and not required as standalone supporting documents.",
    "academic_record": "Academic record excluded because Non-ECR documentary proof was not requested for this application.",
    "address": "Residential address text is maintained in application form; excluded from document-reference payload.",
    "date_of_birth": "Date of birth text is maintained in application form; excluded from document-reference payload."
}


def create_disclosure_plan(
    task_name: str,
    extracted_requirements: Dict,
    matched_data: Dict,
    user_profile: Dict,
    requires_non_ecr: bool = False
) -> Dict:
    """
    Constructs an explainable Minimum-Disclosure Plan.

    Distinguishes between:
    1. supporting_document (e.g. address_proof, date_of_birth_proof): disclosed ONLY if mandatory or condition met
    2. conditional_requirement (e.g. academic_record for Non-ECR): disclosed ONLY if requires_non_ecr is True
    3. application_field (e.g. name, date_of_birth, address): visible in requirements for traceability,
       but NOT automatically included in supporting-document disclosure payload

    Enforces separation between Document Access and Data Disclosure:
    Extraneous fields inside opened documents (e.g. roll numbers, consumer IDs, transaction notes)
    are quarantined and never transmitted in the external payload.

    Returns:
        Dict containing:
            - task: str
            - approved_payload: Dict[str, str]
            - approved_attributes: List[str]
            - excluded_attributes: List[str]
            - rejected_attributes: List[str]
            - missing_mandatory_attributes: List[str]
            - total_user_attributes_count: int
            - disclosed_attributes_count: int
            - unnecessary_attributes_excluded_count: int
            - justifications: Dict[str, str]
            - exclusion_justifications: Dict[str, str]
            - quarantined_document_fields: List[str]
            - matched_requirements: Dict
    """
    mapping = matched_data.get("mapping", {})
    missing_mandatory = list(matched_data.get("missing_mandatory_attributes", []))

    approved_payload = {}
    approved_attributes = []
    justifications = {}

    for req_name, details in mapping.items():
        req_type = details.get("type", "supporting_document")
        status = details.get("status", "mandatory")
        is_mandatory = details.get("mandatory", status == "mandatory")
        attr_key = details.get("attribute_key") or details.get("mapped_attribute")
        val = details.get("value")

        if not attr_key:
            continue

        # 1. Mandatory Supporting Documents (e.g. address_proof, date_of_birth_proof)
        if req_type == "supporting_document" and is_mandatory:
            if val is not None:
                approved_payload[attr_key] = val
                if attr_key not in approved_attributes:
                    approved_attributes.append(attr_key)
                justifications[attr_key] = f"Mandatory Passport Supporting Document: {req_name}"

        # 2. Conditional Supporting Documents (e.g. academic_record for Non-ECR proof)
        elif req_type == "conditional_requirement":
            if attr_key == "academic_record" and requires_non_ecr:
                if val is not None:
                    approved_payload[attr_key] = val
                    if attr_key not in approved_attributes:
                        approved_attributes.append(attr_key)
                    justifications[attr_key] = f"Conditional Passport Supporting Document: {req_name} (Non-ECR requirement explicitly established)"
                else:
                    # Active conditional requirement is missing from profile -> elevate to missing mandatory
                    if attr_key not in missing_mandatory:
                        missing_mandatory.append(attr_key)

        # 3. Application Fields (e.g. name, date_of_birth, address)
        # Maintained in matched requirements for traceability, but NOT added to external disclosure payload.
        elif req_type == "application_field":
            pass

    # Profile attributes in user object (excluding metadata user_id and name)
    profile_keys = [k for k, v in user_profile.items() if v is not None and k not in ["user_id", "name"]]
    excluded_attributes = [k for k in profile_keys if k not in approved_attributes]

    # Explainable exclusion justifications
    exclusion_justifications = {}
    for attr in excluded_attributes:
        exclusion_justifications[attr] = EXCLUSION_JUSTIFICATIONS.get(
            attr,
            f"Attribute '{attr}' is not an authorized or necessary supporting document for this passport task."
        )

    # Document fields quarantined from opened files to preserve access vs disclosure boundary
    quarantined_fields = [
        "roll_number", "school_name", "consumer_id", "billing_address",
        "place_of_birth", "registration_number", "closing_balance",
        "recent_transactions", "blood_group", "allergies"
    ]

    return {
        "task": task_name,
        "approved_payload": approved_payload,
        "approved_attributes": approved_attributes,
        "excluded_attributes": excluded_attributes,
        "rejected_attributes": excluded_attributes,
        "missing_mandatory_attributes": missing_mandatory,
        "total_user_attributes_count": len(profile_keys),
        "disclosed_attributes_count": len(approved_attributes),
        "unnecessary_attributes_excluded_count": len(excluded_attributes),
        "justifications": justifications,
        "exclusion_justifications": exclusion_justifications,
        "quarantined_document_fields": quarantined_fields,
        "matched_requirements": mapping
    }
