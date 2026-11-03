"""
Module: Mock External Passport Application API (FastAPI)
Simulates an external tool API receiving ONLY approved MIN-DISC user attributes.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import requests

from src.config import MOCK_API_HOST, MOCK_API_PORT, MOCK_API_URL

app = FastAPI(title="Mock Passport Application API")


@app.get("/health")
def health():
    return {"status": "online", "service": "Mock Passport Application API"}


@app.post("/passport/apply")
def apply_passport(payload: Dict[str, Any]):
    """
    Receives user payload for Passport Application.
    Logs and inspects received fields to demonstrate minimum disclosure.
    """
    received_keys = list(payload.keys())

    # Verify no unapproved / sensitive fields were passed
    forbidden_keys = ["family_income", "bank_account", "medical_information", "employment"]
    leaked = [k for k in received_keys if k in forbidden_keys]

    if leaked:
        raise HTTPException(
            status_code=400,
            detail=f"PRIVACY VIOLATION DETECTED: External API received unauthorized sensitive attributes: {leaked}"
        )

    return {
        "status": "success",
        "message": "Mock Passport application submitted successfully.",
        "received_attributes_count": len(received_keys),
        "received_attributes": received_keys
    }


def execute_mock_api_call(approved_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct client call function to mock API (or internal service fallback).
    """
    try:
        response = requests.post(MOCK_API_URL, json=approved_payload, timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass

    # Direct internal invocation fallback if HTTP server not active
    return apply_passport(approved_payload)
