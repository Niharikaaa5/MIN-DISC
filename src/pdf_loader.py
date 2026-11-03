"""
Module: PDF Text Extractor
Extracts page-level text and source metadata from Passport requirement PDFs.
"""
from pathlib import Path
from typing import List, Dict
import pypdf


def load_pdfs_from_directory(directory_path: Path, domain: str = "passport") -> List[Dict]:
    """
    Scans directory for PDF files and extracts text page-by-page.
    
    Returns a list of dicts:
    [
        {
            "file_name": str,
            "file_path": str,
            "page_number": int,
            "text": str,
            "is_primary": bool,
            "doc_classification": str,
            "source_priority": int
        },
        ...
    ]
    """
    if not directory_path.exists():
        raise FileNotFoundError(f"PDF directory not found: {directory_path}")

    pdf_files = list(directory_path.glob("*.pdf"))
    if not pdf_files:
        print(f"[WARNING] No PDF files found in {directory_path}")
        return []

    documents = []

    for pdf_path in pdf_files:
        file_name = pdf_path.name
        fn_lower = file_name.lower()

        # Document classification & source priority
        if domain == "scholarship":
            if "guidlines" in fn_lower or "guidelines" in fn_lower:
                is_primary = True
                doc_classification = "primary_scheme_policy_source"
                source_priority = 1
            elif "faq" in fn_lower:
                is_primary = False
                doc_classification = "official_operational_reference"
                source_priority = 2
            elif "training" in fn_lower or "nsp" in fn_lower:
                is_primary = False
                doc_classification = "supplementary_portal_guidance"
                source_priority = 3
            else:
                is_primary = False
                doc_classification = "general_reference"
                source_priority = 4
        else:
            # Default / Passport domain
            is_primary = "official passport" in fn_lower or "instruction" in fn_lower
            doc_classification = "primary_policy_booklet" if is_primary else "supporting_reference"
            source_priority = 1 if is_primary else 2

        try:
            reader = pypdf.PdfReader(str(pdf_path))
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                clean_text = text.strip()
                if clean_text:
                    documents.append({
                        "file_name": file_name,
                        "file_path": str(pdf_path),
                        "page_number": page_idx + 1,
                        "text": clean_text,
                        "is_primary": is_primary,
                        "doc_classification": doc_classification,
                        "source_priority": source_priority
                    })
        except Exception as e:
            print(f"[ERROR] Failed to read PDF {file_name}: {e}")

    print(f"[*] Loaded {len(documents)} pages across {len(pdf_files)} PDF file(s).")
    return documents
