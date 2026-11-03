"""
Validation Test Suite: Phase 1 Scholarship Isolated RAG Ingestion
Verifies:
1. All three scholarship PDFs loaded.
2. Chunks retain correct source, page provenance, and document classification.
3. Scholarship index can be built, saved, loaded, and queried independently.
4. Passport index, metadata, and vectorizer files remain strictly unchanged.
"""
import sys
from pathlib import Path
import hashlib
import json

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    DATA_DIR,
    PASSPORT_REQUIREMENTS_DIR,
    FAISS_INDEX_PATH,
    METADATA_STORE_PATH,
    SCHOLARSHIP_REQUIREMENTS_DIR,
    SCHOLARSHIP_FAISS_INDEX_PATH,
    SCHOLARSHIP_METADATA_STORE_PATH,
    SCHOLARSHIP_TFIDF_MODEL_PATH
)
from src.embeddings import TFIDF_MODEL_PATH
from src.scholarship.scholarship_rag import build_or_load_scholarship_rag


def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def run_tests():
    print("\n" + "=" * 70)
    print("  PHASE 1 VALIDATION TEST: SCHOLARSHIP ISOLATED RAG INGESTION")
    print("=" * 70)

    # -----------------------------------------------------------------
    # STEP 0: Record Passport Baseline Checksums
    # -----------------------------------------------------------------
    passport_files = {
        "passport_faiss": FAISS_INDEX_PATH,
        "passport_metadata": METADATA_STORE_PATH,
        "passport_tfidf": TFIDF_MODEL_PATH,
    }
    baseline_hashes = {}
    for name, p in passport_files.items():
        if p.exists():
            baseline_hashes[name] = get_sha256(p)
            print(f"[BASELINE] {name} ({p.name}): {baseline_hashes[name][:16]}...")
        else:
            print(f"[BASELINE] {name} ({p}) does not exist.")

    # -----------------------------------------------------------------
    # STEP 1: Ingest Scholarship PDFs and Build Isolated Index
    # -----------------------------------------------------------------
    print("\n[*] Building / Loading Scholarship RAG Pipeline...")
    retriever, embedding_model, vector_store = build_or_load_scholarship_rag(force_rebuild=True)

    # -----------------------------------------------------------------
    # STEP 2: Verify All Three PDFs Loaded
    # -----------------------------------------------------------------
    assert SCHOLARSHIP_FAISS_INDEX_PATH.exists(), "Scholarship FAISS index was not created!"
    assert SCHOLARSHIP_METADATA_STORE_PATH.exists(), "Scholarship metadata file was not created!"

    with open(SCHOLARSHIP_METADATA_STORE_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\n[*] Total Chunks in Scholarship Index: {len(chunks)}")
    assert len(chunks) > 0, "No chunks found in scholarship index!"

    pdf_files_in_chunks = set()
    pages_per_pdf = {}
    classifications_per_pdf = {}

    for c in chunks:
        fn = c["file_name"]
        pdf_files_in_chunks.add(fn)
        pages_per_pdf.setdefault(fn, set()).add(c["page_number"])
        classifications_per_pdf.setdefault(fn, c.get("doc_classification"))

    print("\n[*] PDF Verification in Chunk Metadata:")
    expected_pdfs = [
        "CSSS_GUIDLINES_07022024_updated.pdf",
        "FAQ_DOHE_CSSS.pdf",
        "training_of_users_nsp.pdf"
    ]

    for epdf in expected_pdfs:
        assert epdf in pdf_files_in_chunks, f"Expected PDF missing from chunks: {epdf}"
        num_pages = len(pages_per_pdf[epdf])
        doc_class = classifications_per_pdf[epdf]
        print(f"  + {epdf}: {num_pages} distinct pages indexed | Classification: '{doc_class}'")

    # -----------------------------------------------------------------
    # STEP 3: Verify Chunk Provenance & Document Hierarchy
    # -----------------------------------------------------------------
    sample_chunk = chunks[0]
    required_keys = ["chunk_id", "text", "file_name", "page_number", "is_primary", "doc_classification", "source_priority"]
    for rk in required_keys:
        assert rk in sample_chunk, f"Missing provenance key '{rk}' in chunk: {sample_chunk}"

    print("\n[*] Verified chunk metadata structure:")
    print(f"  Sample Chunk ID: {sample_chunk['chunk_id']}")
    print(f"  Sample Source File: {sample_chunk['file_name']}")
    print(f"  Sample Page: {sample_chunk['page_number']}")
    print(f"  Sample Classification: {sample_chunk['doc_classification']}")
    print(f"  Sample Source Priority: {sample_chunk['source_priority']}")

    # -----------------------------------------------------------------
    # STEP 4: Query Scholarship Index Independently
    # -----------------------------------------------------------------
    test_query = "What is the family income limit and merit criteria for CSSS scholarship?"
    print(f"\n[*] Testing Independent Query: '{test_query}'")
    results = retriever.retrieve(test_query, top_k=3)

    assert len(results) > 0, "Retrieval returned 0 chunks!"
    print(f"[*] Retrieved {len(results)} chunks:")
    for idx, r in enumerate(results, 1):
        print(f"  [{idx}] {r['file_name']} (Page {r['page_number']}) — Priority Class: '{r['doc_classification']}'")
        print(f"      Raw Score: {r['similarity_score']} | Boosted Score: {r['boosted_score']}")
        snippet = r['text'][:120].replace('\n', ' ')
        print(f"      Snippet: {snippet}...\n")

    # Verify top result is from Guidelines or FAQ (primary/operational, not training manual)
    top_file = results[0]["file_name"].lower()
    assert "guidlines" in top_file or "faq" in top_file or "guidelines" in top_file, (
        f"Top retrieval should be from primary/operational source, got: {results[0]['file_name']}"
    )

    # -----------------------------------------------------------------
    # STEP 5: Verify Isolated Vectorizer and Model Files
    # -----------------------------------------------------------------
    embedding_method = "SentenceTransformers (dense)" if embedding_model.use_st else "TF-IDF (sparse)"
    print(f"[*] Embedding Method Actually Used: {embedding_method}")
    print(f"[*] Scholarship TF-IDF Model Path: {SCHOLARSHIP_TFIDF_MODEL_PATH}")

    if not embedding_model.use_st:
        assert SCHOLARSHIP_TFIDF_MODEL_PATH.exists(), "Scholarship TF-IDF model file missing!"
        print(f"  + Confirmed: Scholarship TF-IDF vectorizer created at {SCHOLARSHIP_TFIDF_MODEL_PATH}")

    # -----------------------------------------------------------------
    # STEP 6: Verify Passport Files Remain Unchanged (Zero Corruption)
    # -----------------------------------------------------------------
    print("\n[*] Verifying Passport Files Integrity Post-Ingestion:")
    for name, p in passport_files.items():
        if name in baseline_hashes:
            current_hash = get_sha256(p)
            assert current_hash == baseline_hashes[name], (
                f"CORRUPTION DETECTED in {p.name}! Baseline: {baseline_hashes[name]} != Current: {current_hash}"
            )
            print(f"  + PASSED: {name} ({p.name}) hash identical ({current_hash[:16]}...)")

    print("\n" + "=" * 70)
    print("  ALL PHASE 1 VALIDATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
