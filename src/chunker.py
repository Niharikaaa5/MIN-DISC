"""
Module: Document Chunker
Splits page-level document text into overlapping chunks while preserving source metadata.
"""
from typing import List, Dict


def chunk_documents(documents: List[Dict], chunk_size: int = 600, overlap: int = 100) -> List[Dict]:
    """
    Splits page documents into chunk dicts with source citations metadata.

    Returns:
        List[Dict]: Chunk objects with keys:
            - chunk_id: str
            - text: str
            - file_name: str
            - page_number: int
            - is_primary: bool
    """
    chunks = []
    global_chunk_idx = 0

    for doc in documents:
        text = doc["text"]
        file_name = doc["file_name"]
        page_number = doc["page_number"]
        is_primary = doc.get("is_primary", False)
        doc_classification = doc.get("doc_classification", "primary_policy_booklet" if is_primary else "supporting_reference")
        source_priority = doc.get("source_priority", 1 if is_primary else 2)

        if len(text) <= chunk_size:
            global_chunk_idx += 1
            chunks.append({
                "chunk_id": f"chk_{global_chunk_idx:04d}",
                "text": text,
                "file_name": file_name,
                "page_number": page_number,
                "is_primary": is_primary,
                "doc_classification": doc_classification,
                "source_priority": source_priority
            })
            continue

        # Sliding window chunking
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                global_chunk_idx += 1
                chunks.append({
                    "chunk_id": f"chk_{global_chunk_idx:04d}",
                    "text": chunk_text,
                    "file_name": file_name,
                    "page_number": page_number,
                    "is_primary": is_primary,
                    "doc_classification": doc_classification,
                    "source_priority": source_priority
                })

            start += chunk_size - overlap

    print(f"[*] Created {len(chunks)} chunks from {len(documents)} document page(s).")
    return chunks
