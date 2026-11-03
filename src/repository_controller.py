"""
Module: Task-Aware User Repository Controller
Simulates a personal cloud storage repository (e.g. Google Drive) containing synthetic user documents.
Enforces Task-Aware Access Minimisation:
1. Inspects metadata without opening file content.
2. Applies default-deny access control: only files strictly justified by verified task requirements can be opened.
3. Completely blocks sensitive categories (medical, financial, tax) from being opened.
4. Produces an explainable Access Decision Log and calculates Access Minimisation Metrics.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.config import USER_REPOSITORIES_FILE


class AccessDeniedError(PermissionError):
    """Raised when an unauthorized attempt is made to fetch document content."""
    pass


class RepositoryAccessController:
    """
    Manages access to personal documents in the simulated user storage repository.
    Enforces task-aware access minimisation and default-deny security policies.
    """

    # Categories strictly forbidden from being opened for passport tasks
    FORBIDDEN_CATEGORIES = {
        "health_medical",
        "financial_banking",
        "financial_tax"
    }

    # Document types authorized for passport verification tasks
    AUTHORIZED_DOCUMENT_TYPES = {
        "proof_of_address",
        "proof_of_date_of_birth",
        "proof_of_non_ecr",
        "academic_certificate"
    }

    def __init__(self, repositories_path: Optional[Path] = None):
        self.repo_file = repositories_path or USER_REPOSITORIES_FILE
        self._repositories = self._load_repositories()
        self.access_log: List[Dict[str, Any]] = []

    def _load_repositories(self) -> Dict[str, Any]:
        """Loads repository data from JSON file."""
        if not self.repo_file.exists():
            return {}
        with open(self.repo_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_user_repository(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns the repository record for a given user ID."""
        return self._repositories.get(user_id)

    def list_repository_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Lists file metadata for all documents in the user's repository.
        Returns METADATA ONLY: file name, ID, category, document type, issuer, date, tags.
        Does NOT expose extracted data or document content.
        """
        user_repo = self.get_user_repository(user_id)
        if not user_repo:
            return []

        metadata_list = []
        for f in user_repo.get("files", []):
            meta = {
                "file_id": f["file_id"],
                "file_name": f["file_name"],
                "category": f["category"],
                "document_type": f["document_type"],
                "secondary_document_type": f.get("secondary_document_type"),
                "issuer": f["issuer"],
                "issue_date": f["issue_date"],
                "tags": list(f.get("tags", []))
            }
            metadata_list.append(meta)

        self.access_log.append({
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": "METADATA_INSPECTED",
            "files_inspected_count": len(metadata_list),
            "reason": "Inspected file metadata to determine requirement relevance without opening contents."
        })

        return metadata_list

    def search_repository_metadata(
        self,
        user_id: str,
        document_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches user repository file metadata without loading document contents.
        """
        all_metadata = self.list_repository_files(user_id)
        matched = []

        for meta in all_metadata:
            # Match document type
            if document_types:
                doc_type_match = (
                    meta["document_type"] in document_types
                    or meta.get("secondary_document_type") in document_types
                )
                if not doc_type_match:
                    continue

            # Match tags
            if tags:
                tag_match = any(t.lower() in [mt.lower() for mt in meta["tags"]] for t in tags)
                if not tag_match:
                    continue

            # Match textual query
            if query:
                q_lower = query.lower()
                text_match = (
                    q_lower in meta["file_name"].lower()
                    or q_lower in meta["issuer"].lower()
                    or any(q_lower in t.lower() for t in meta["tags"])
                )
                if not text_match:
                    continue

            matched.append(meta)

        return matched

    def fetch_document_content(
        self,
        user_id: str,
        file_id: str,
        requirement_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Default-deny document content fetcher.
        Opens and returns full document content ONLY if authorized for the requirement.
        Blocks and records unauthorized or sensitive access attempts.
        """
        user_repo = self.get_user_repository(user_id)
        if not user_repo:
            raise AccessDeniedError(f"User repository for '{user_id}' does not exist.")

        target_file = next((f for f in user_repo.get("files", []) if f["file_id"] == file_id), None)
        if not target_file:
            raise AccessDeniedError(f"File '{file_id}' not found in user repository.")

        category = target_file.get("category", "")
        doc_type = target_file.get("document_type", "")
        sec_doc_type = target_file.get("secondary_document_type", "")
        is_sensitive = category in self.FORBIDDEN_CATEGORIES

        # DEFAULT-DENY CHECK 1: Forbidden sensitive categories
        if is_sensitive:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "file_id": file_id,
                "file_name": target_file["file_name"],
                "category": category,
                "action": "BLOCKED_ACCESS_ATTEMPT",
                "status": "BLOCKED",
                "requirement_id": requirement_id,
                "reason": f"Access denied by default-deny access controller: sensitive category '{category}' is forbidden for passport verification."
            }
            self.access_log.append(log_entry)
            raise AccessDeniedError(
                f"ACCESS DENIED: File '{target_file['file_name']}' is classified as sensitive '{category}'. "
                f"Task does not justify health, banking, or tax data access."
            )

        # DEFAULT-DENY CHECK 2: Authorized document types for passport tasks
        is_authorized_type = (
            doc_type in self.AUTHORIZED_DOCUMENT_TYPES
            or sec_doc_type in self.AUTHORIZED_DOCUMENT_TYPES
        )
        if not is_authorized_type:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "file_id": file_id,
                "file_name": target_file["file_name"],
                "category": category,
                "action": "BLOCKED_ACCESS_ATTEMPT",
                "status": "BLOCKED",
                "requirement_id": requirement_id,
                "reason": f"Access denied: document type '{doc_type}' is not an authorized supporting document type."
            }
            self.access_log.append(log_entry)
            raise AccessDeniedError(
                f"ACCESS DENIED: File '{target_file['file_name']}' with type '{doc_type}' is not authorized."
            )

        # AUTHORIZED FETCH
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "file_id": file_id,
            "file_name": target_file["file_name"],
            "category": category,
            "action": "AUTHORIZED_FETCH",
            "status": "ACCESSED",
            "requirement_id": requirement_id,
            "reason": f"Authorized content fetch to satisfy verified requirement: {requirement_id}"
        }
        self.access_log.append(log_entry)

        return target_file

    def retrieve_documents_for_requirements(
        self,
        user_id: str,
        extracted_requirements: Dict[str, Any],
        requires_non_ecr: bool = False
    ) -> Dict[str, Any]:
        """
        Coordinates task-aware document selection:
        1. Evaluates verified task requirements (Address, DOB, Non-ECR).
        2. Inspects repository file metadata without opening contents.
        3. Opens ONLY authorized files that directly satisfy active requirements.
        4. Generates an explainable Access Decision Log for all files.
        5. Computes access minimisation metrics.
        """
        user_repo = self.get_user_repository(user_id)
        if not user_repo:
            return {
                "user_id": user_id,
                "accessed_documents": {},
                "missing_documents": ["address_proof", "date_of_birth_proof"],
                "access_decision_log": [],
                "metrics": {
                    "total_repository_files": 0,
                    "inspected_metadata_files": 0,
                    "accessed_files_count": 0,
                    "unopened_files_count": 0,
                    "access_reduction_percentage": 0.0
                }
            }

        files = user_repo.get("files", [])
        accessed_documents = {}
        access_decision_log = []
        missing_documents = []

        # Determine target requirements
        needs_address = True
        needs_dob = True
        needs_non_ecr = requires_non_ecr

        found_address = False
        found_dob = False
        found_non_ecr = False

        for f in files:
            file_id = f["file_id"]
            file_name = f["file_name"]
            cat = f["category"]
            doc_type = f["document_type"]
            sec_doc_type = f.get("secondary_document_type")
            has_valid_token = f.get("token") is not None

            # 1. Address Proof
            if needs_address and not found_address and doc_type == "proof_of_address" and has_valid_token:
                try:
                    content = self.fetch_document_content(user_id, file_id, requirement_id="proof_of_address")
                    accessed_documents["proof_of_address"] = content
                    found_address = True
                    access_decision_log.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "category": cat,
                        "document_type": doc_type,
                        "decision": "ACCESSED",
                        "status": "AUTHORIZED",
                        "justification": f"Opened to satisfy mandatory requirement: Proof of Present Address ({f['issuer']}).",
                        "opened": True
                    })
                    continue
                except AccessDeniedError:
                    pass

            # 2. Date of Birth Proof
            if needs_dob and not found_dob and doc_type == "proof_of_date_of_birth" and has_valid_token:
                try:
                    content = self.fetch_document_content(user_id, file_id, requirement_id="proof_of_date_of_birth")
                    accessed_documents["proof_of_date_of_birth"] = content
                    found_dob = True
                    access_decision_log.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "category": cat,
                        "document_type": doc_type,
                        "decision": "ACCESSED",
                        "status": "AUTHORIZED",
                        "justification": f"Opened to satisfy mandatory requirement: Proof of Date of Birth ({f['issuer']}).",
                        "opened": True
                    })
                    continue
                except AccessDeniedError:
                    pass

            # 3. Non-ECR Proof (Conditional)
            if needs_non_ecr and not found_non_ecr and (sec_doc_type == "proof_of_non_ecr" or doc_type == "academic_certificate") and has_valid_token:
                try:
                    content = self.fetch_document_content(user_id, file_id, requirement_id="proof_of_non_ecr")
                    accessed_documents["proof_of_non_ecr"] = content
                    found_non_ecr = True
                    access_decision_log.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "category": cat,
                        "document_type": doc_type,
                        "decision": "ACCESSED",
                        "status": "AUTHORIZED",
                        "justification": f"Opened to satisfy conditional requirement: Non-ECR Documentary Proof ({f['issuer']}).",
                        "opened": True
                    })
                    continue
                except AccessDeniedError:
                    pass

            # If not accessed, determine the privacy reason why it remained UNOPENED
            decision = "NOT_ACCESSED"
            opened = False

            if cat == "health_medical":
                status = "PROTECTED_SENSITIVE"
                justification = "Sensitive medical health record. The passport application task does not require or justify health data access."
            elif cat == "financial_banking":
                status = "PROTECTED_SENSITIVE"
                justification = "Sensitive financial record. Bank account statements are not required for standard adult passport verification."
            elif cat == "financial_tax":
                status = "PROTECTED_SENSITIVE"
                justification = "Confidential tax record. Income tax returns are not required for standard adult passport verification."
            elif cat == "employment":
                status = "PROTECTED_IRRELEVANT"
                justification = "Employment / curriculum vitae document. Irrelevant for identity and address proof in standard passport application."
            elif doc_type == "unverified_draft":
                status = "REJECTED_UNVERIFIED"
                justification = "Unsigned draft document lacks statutory validity for official passport address proof."
            elif doc_type == "unverified_personal_record":
                status = "REJECTED_UNVERIFIED"
                justification = "Informal personal notes lack statutory validity for date of birth verification."
            elif doc_type in ["academic_certificate", "activity_certificate"] and not needs_non_ecr:
                status = "PROTECTED_UNNEEDED"
                justification = "Academic / activity record not opened because Non-ECR documentary proof was not requested."
            else:
                status = "NOT_REQUIRED"
                justification = "Document is not required for verified passport application requirements."

            access_decision_log.append({
                "file_id": file_id,
                "file_name": file_name,
                "category": cat,
                "document_type": doc_type,
                "decision": decision,
                "status": status,
                "justification": justification,
                "opened": opened
            })

        # Track missing mandatory requirements
        if not found_address:
            missing_documents.append("address_proof")
        if not found_dob:
            missing_documents.append("date_of_birth_proof")
        if needs_non_ecr and not found_non_ecr:
            missing_documents.append("academic_record")

        # Compute Access Minimisation Metrics
        total_files = len(files)
        inspected_files = total_files
        accessed_count = len([d for d in access_decision_log if d["decision"] == "ACCESSED"])
        unopened_count = total_files - accessed_count
        access_reduction_pct = (
            round((unopened_count / total_files) * 100, 1) if total_files > 0 else 0.0
        )

        return {
            "user_id": user_id,
            "accessed_documents": accessed_documents,
            "missing_documents": missing_documents,
            "access_decision_log": access_decision_log,
            "metrics": {
                "total_repository_files": total_files,
                "inspected_metadata_files": inspected_files,
                "accessed_files_count": accessed_count,
                "unopened_files_count": unopened_count,
                "access_reduction_percentage": access_reduction_pct
            }
        }
