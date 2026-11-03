"""
Module: Scholarship Isolated RAG Pipeline
Manages indexing and retrieval for PM-USP Central Sector Scheme of Scholarship (CSSS).
Preserves source hierarchy:
1. CSSS Guidelines: Primary scheme policy source.
2. DoHE FAQ: Official operational reference.
3. NSP Training Manual: Supplementary portal guidance.
Strictly isolated from passport vector indices and models.
"""
from pathlib import Path
from typing import List, Dict, Tuple

from src.config import (
    SCHOLARSHIP_REQUIREMENTS_DIR,
    SCHOLARSHIP_FAISS_INDEX_PATH,
    SCHOLARSHIP_METADATA_STORE_PATH,
    SCHOLARSHIP_TFIDF_MODEL_PATH
)
from src.pdf_loader import load_pdfs_from_directory
from src.chunker import chunk_documents
from src.embeddings import EmbeddingModel
from src.vector_store import VectorStore


class ScholarshipRetriever:
    """
    RAG Retriever for scholarship requirement documents.
    Implements multi-aspect query pooling and grounded source priority scoring.
    """

    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieves top-k relevant document chunks for scholarship query.
        Applies grounded source hierarchy boosts:
        - Primary Policy (Guidelines): +0.30
        - Operational Reference (FAQ): +0.20
        - Supplementary Guidance (NSP Manual): +0.00
        """
        # Primary user task query
        q1_vec = self.embedding_model.transform_query(query)

        # Scholarship requirement-aspect expansion query
        aspect_query = (
            f"{query} PM-USP CSSS scholarship eligibility criteria 80th percentile "
            "family income 4.5 lakh fresh renewal mark sheet documents to be uploaded AISHE code"
        )
        q2_vec = self.embedding_model.transform_query(aspect_query)

        # Retrieve candidates for both aspects
        results_primary = self.vector_store.search(q1_vec, top_k=top_k * 4)
        results_aspect = self.vector_store.search(q2_vec, top_k=top_k * 4)

        score_map = {}
        chunk_map = {}

        for res_list in [results_primary, results_aspect]:
            for chunk, score in res_list:
                cid = chunk["chunk_id"]
                if cid in score_map:
                    score_map[cid] = max(score_map[cid], score)
                else:
                    score_map[cid] = score
                    chunk_map[cid] = chunk

        if not score_map:
            print("[WARNING] Scholarship vector search returned 0 matches.")
            return []

        # Domain section priority markers
        section_markers = [
            "eligibility", "80th percentile", "top 20th percentile",
            "4.5 lakh", "income certificate", "rate of scholarship",
            "fresh", "renewal", "documents to be uploaded",
            "aishe", "mark sheet", "annual examination", "50% marks", "attendance"
        ]

        scored_chunks = []
        for cid, raw_score in score_map.items():
            chunk = chunk_map[cid]
            txt_lower = chunk.get("text", "").lower()
            fname_lower = chunk.get("file_name", "").lower()
            doc_class = chunk.get("doc_classification", "")

            boosted_score = raw_score

            # Grounded Source Hierarchy Boost
            if "guidlines" in fname_lower or "guidelines" in fname_lower or doc_class == "primary_scheme_policy_source":
                boosted_score += 0.30  # Primary statutory policy source
            elif "faq" in fname_lower or doc_class == "official_operational_reference":
                boosted_score += 0.20  # Official operational reference
            # Note: Supplementary portal guidance (training manual) receives no priority boost

            # Content relevance marker boost
            if any(marker in txt_lower for marker in section_markers):
                boosted_score += 0.15

            scored_chunks.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "file_name": chunk["file_name"],
                "page_number": chunk["page_number"],
                "is_primary": chunk.get("is_primary", False),
                "doc_classification": chunk.get("doc_classification", "general_reference"),
                "source_priority": chunk.get("source_priority", 99),
                "similarity_score": round(raw_score, 4),
                "boosted_score": round(boosted_score, 4)
            })

        # Sort by boosted score descending
        scored_chunks.sort(key=lambda x: x["boosted_score"], reverse=True)
        top_results = scored_chunks[:top_k]

        print(f"[*] Retrieved {len(top_results)} scholarship chunks for query: '{query}'")
        return top_results


def build_or_load_scholarship_rag(force_rebuild: bool = False) -> Tuple[ScholarshipRetriever, EmbeddingModel, VectorStore]:
    """
    Initializes or builds the isolated scholarship RAG knowledge base.
    Guarantees isolation from passport vector stores and models.
    """
    embedding_model = EmbeddingModel(tfidf_model_path=SCHOLARSHIP_TFIDF_MODEL_PATH)
    vector_store = VectorStore()

    if not force_rebuild and vector_store.load(SCHOLARSHIP_FAISS_INDEX_PATH, SCHOLARSHIP_METADATA_STORE_PATH):
        print("[*] Loaded existing isolated scholarship FAISS index.")
        return ScholarshipRetriever(vector_store, embedding_model), embedding_model, vector_store

    print("[*] Ingesting scholarship PDFs and building isolated index...")
    documents = load_pdfs_from_directory(SCHOLARSHIP_REQUIREMENTS_DIR, domain="scholarship")
    if not documents:
        raise FileNotFoundError(f"No scholarship PDFs found in {SCHOLARSHIP_REQUIREMENTS_DIR}")

    chunks = chunk_documents(documents)
    texts = [c["text"] for c in chunks]

    embeddings = embedding_model.fit_transform(texts)
    vector_store.build_index(chunks, embeddings)
    vector_store.save(SCHOLARSHIP_FAISS_INDEX_PATH, SCHOLARSHIP_METADATA_STORE_PATH)

    print(f"[*] Successfully built and saved isolated scholarship RAG ({len(chunks)} chunks).")
    return ScholarshipRetriever(vector_store, embedding_model), embedding_model, vector_store
