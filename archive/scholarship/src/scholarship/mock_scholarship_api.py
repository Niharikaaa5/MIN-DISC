"""
Module: Mock National Scholarship Portal (NSP) & PFMS API
Simulates an external government tool API receiving ONLY approved MIN-DISC scholarship attributes.

Strictly enforces:
1. Rejection of quarantined payment credentials (raw Aadhaar, bank account, IFSC).
2. Rejection of forbidden, unnecessary, or unapproved attributes.
3. Decoupling of application submission status from payment disbursement readiness.
4. Independent payment readiness evaluation (e.g., holding payment for INACTIVE AISHE institutes per DOC-2 Q18).
5. Explicit mock disclaimers: NO real NSP, PFMS, or UIDAI government calls are made.
"""
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

app = FastAPI(
    title="Mock National Scholarship Portal (NSP) & PFMS Gateway",
    description="Simulated government API for PM-USP CSSS prototype testing. Does NOT perform real government transactions.",
    version="1.0.0"
)

# Simulated in-memory persistent database for mock applications
MOCK_APPLICATIONS_DB: Dict[str, Dict[str, Any]] = {}

QUARANTINED_PAYMENT_KEYS = {
    "aadhaar_number",
    "bank_account_number",
    "bank_ifsc",
    "aadhaar_seeding_status"
}

FORBIDDEN_PASSPORT_KEYS = {
    "passport_type",
    "country_code",
    "address_proof",
    "date_of_birth_proof",
    "academic_record"
}

FORBIDDEN_PROFILE_KEYS = {
    "family_income",
    "gap_year_flag",
    "other_scholarships_flag",
    "institution_recognized"
}

MOCK_DISCLAIMER = "SIMULATED RESPONSE: This is a synthetic mock response for MIN-DISC prototype testing. Not an actual government NSP/PFMS submission."


def reset_mock_db():
    """Resets the in-memory database for clean test runs."""
    global MOCK_APPLICATIONS_DB
    MOCK_APPLICATIONS_DB.clear()


@app.get("/health")
def health() -> Dict[str, Any]:
    """Health check endpoint for simulated NSP gateway."""
    return {
        "status": "online",
        "service": "Mock NSP / PFMS Scholarship Gateway",
        "environment": "MIN-DISC Synthetic Prototype",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mock_disclaimer": MOCK_DISCLAIMER
    }


@app.post("/scholarship/apply", status_code=status.HTTP_201_CREATED)
def apply_scholarship(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Receives minimum-disclosure application payload for PM-USP CSSS.
    Validates payload integrity and privacy constraints before simulating registration.
    """
    # 1. Enforce Policy Approval Verification
    policy_meta = payload.get("policy_verification", {})
    if not policy_meta.get("policy_approved"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "POLICY_ENFORCEMENT_ERROR: Application cannot be submitted to NSP. "
                "The MIN-DISC deterministic policy engine has not approved this payload."
            )
        )

    portal_fields = payload.get("portal_application_fields", {})
    approved_docs = payload.get("approved_supporting_documents", {})

    all_received_keys = set(payload.keys()) | set(portal_fields.keys()) | set(approved_docs.keys())

    # 2. Privacy Check: Strict Payment Layer Quarantine
    leaked_payment = all_received_keys.intersection(QUARANTINED_PAYMENT_KEYS)
    if leaked_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"PRIVACY_VIOLATION_PAYMENT_CREDENTIALS: External application payload contains "
                f"quarantined payment or raw identity credentials: {sorted(list(leaked_payment))}. "
                "Aadhaar and banking details must remain strictly isolated from application forms."
            )
        )

    # 3. Privacy Check: Passport Pipeline Cross-Contamination
    leaked_passport = all_received_keys.intersection(FORBIDDEN_PASSPORT_KEYS)
    if leaked_passport:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"PRIVACY_VIOLATION_CROSS_WORKFLOW: Application payload contains passport-specific "
                f"attributes: {sorted(list(leaked_passport))}."
            )
        )

    # 4. Privacy Check: Internal Evaluation Leakage
    leaked_profile = all_received_keys.intersection(FORBIDDEN_PROFILE_KEYS)
    if leaked_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"PRIVACY_VIOLATION_INTERNAL_DATA: Application payload contains internal profile "
                f"evaluation attributes that should not be transmitted: {sorted(list(leaked_profile))}."
            )
        )

    # 5. Over-Disclosure Check: Conditional Documents
    category = portal_fields.get("caste_category", "General")
    if category == "General" and "caste_certificate" in approved_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OVER_DISCLOSURE_ERROR: Caste certificate was attached for a General category applicant. "
                "Unnecessary sensitive demographic documentation is forbidden."
            )
        )

    disability_pct = float(portal_fields.get("disability_percentage") or 0.0)
    if disability_pct < 40.0 and "disability_certificate" in approved_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OVER_DISCLOSURE_ERROR: Disability certificate was attached for an applicant with no qualifying "
                "benchmark disability. Unnecessary medical documentation is forbidden."
            )
        )

    # 6. Generate Synthetic Application ID and Record Registration
    applicant_id = payload.get("applicant_id", "UNKNOWN")
    synthetic_app_id = f"NSP-2025-CSSS-{uuid.uuid4().hex[:8].upper()}"
    
    # Store registration state separately from payment state
    aishe_status = payload.get("aishe_status", "ACTIVE")
    
    MOCK_APPLICATIONS_DB[synthetic_app_id] = {
        "application_id": synthetic_app_id,
        "applicant_id": applicant_id,
        "applicant_name": payload.get("applicant_name", portal_fields.get("applicant_name")),
        "application_status": "SUBMITTED",
        "stage": "UNDER_INSTITUTE_VERIFICATION",
        "aishe_code": portal_fields.get("aishe_code"),
        "aishe_status": aishe_status,
        "submitted_fields": list(portal_fields.keys()),
        "submitted_documents": list(approved_docs.keys()),
        "registered_at": datetime.utcnow().isoformat() + "Z",
        # Payment readiness is evaluated independently
        "payment_readiness": "PAYMENT_PENDING" if aishe_status == "INACTIVE" else "PAYMENT_READY",
        "payment_hold_reason": "Institution AISHE status is INACTIVE (DOC-2 Q18)" if aishe_status == "INACTIVE" else None
    }

    return {
        "status": "SUBMITTED",
        "application_id": synthetic_app_id,
        "message": "SIMULATED REGISTRATION: Application successfully registered on Mock NSP Portal.",
        "stage": "UNDER_INSTITUTE_VERIFICATION",
        "disclosed_fields_count": len(portal_fields),
        "disclosed_documents_count": len(approved_docs),
        "registered_at": MOCK_APPLICATIONS_DB[synthetic_app_id]["registered_at"],
        "mock_disclaimer": MOCK_DISCLAIMER
    }


@app.get("/scholarship/status/{application_id}")
def get_application_status(application_id: str) -> Dict[str, Any]:
    """
    Retrieves the simulated application registration status from Mock NSP.
    Decoupled from payment disbursement state.
    """
    record = MOCK_APPLICATIONS_DB.get(application_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID '{application_id}' not found in Mock NSP registry."
        )

    return {
        "application_id": application_id,
        "applicant_id": record["applicant_id"],
        "applicant_name": record["applicant_name"],
        "application_status": record["application_status"],
        "current_stage": record["stage"],
        "institution_aishe_code": record["aishe_code"],
        "registered_at": record["registered_at"],
        "mock_disclaimer": MOCK_DISCLAIMER
    }


@app.get("/scholarship/payment-status/{application_id}")
def get_payment_status(application_id: str) -> Dict[str, Any]:
    """
    Independently evaluates simulated payment disbursement readiness on Mock PFMS.
    Simulates operational holds (e.g., INACTIVE AISHE status per DOC-2 Q18).
    """
    record = MOCK_APPLICATIONS_DB.get(application_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID '{application_id}' not found in Mock NSP registry."
        )

    readiness = record["payment_readiness"]
    hold_reason = record["payment_hold_reason"]

    if readiness == "PAYMENT_PENDING":
        return {
            "application_id": application_id,
            "payment_status": "PAYMENT_PENDING",
            "dbt_ready": False,
            "hold_reason": hold_reason,
            "operational_guidance": "Scholarship payment will be released once institution status is updated to ACTIVE on AISHE portal (DOC-2 Q18).",
            "mock_disclaimer": MOCK_DISCLAIMER
        }
    else:
        return {
            "application_id": application_id,
            "payment_status": "PAYMENT_READY",
            "dbt_ready": True,
            "hold_reason": None,
            "operational_guidance": "Prerequisites satisfied: Institution is ACTIVE and simulated PFMS validation succeeded.",
            "mock_disclaimer": MOCK_DISCLAIMER
        }


# Direct programmatic execution client utilizing FastAPI TestClient
_test_client = TestClient(app)


def submit_mock_scholarship_application(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Direct in-memory synchronous invocation of mock apply endpoint."""
    response = _test_client.post("/scholarship/apply", json=payload)
    if response.status_code == 201:
        return response.json()
    else:
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        return {
            "status": "REJECTED",
            "status_code": response.status_code,
            "error": err.get("detail", "Mock API submission error")
        }


def get_mock_application_status(application_id: str) -> Dict[str, Any]:
    """Direct in-memory synchronous invocation of mock status endpoint."""
    response = _test_client.get(f"/scholarship/status/{application_id}")
    if response.status_code == 200:
        return response.json()
    return {"status": "ERROR", "status_code": response.status_code, "detail": response.json()}


def get_mock_payment_status(application_id: str) -> Dict[str, Any]:
    """Direct in-memory synchronous invocation of mock payment-status endpoint."""
    response = _test_client.get(f"/scholarship/payment-status/{application_id}")
    if response.status_code == 200:
        return response.json()
    return {"status": "ERROR", "status_code": response.status_code, "detail": response.json()}
