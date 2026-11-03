"""
Module: RAG Retriever
Queries vector store and retrieves relevant requirement chunks, prioritizing official booklet documents.
"""
from typing import List, Dict
from src.embeddings import EmbeddingModel
from src.vector_store import VectorStore


class Retriever:
    """RAG Retriever that queries FAISS, prioritizing official instruction booklet chunks and requirement tables."""

    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieves top-k relevant document chunks for user query.
        Combines multi-aspect query vector pooling, primary source boosting,
        and requirement section priority scoring.
        """
        # Primary user task query
        q1_vec = self.embedding_model.transform_query(query)

        # Requirement-aspect search query to capture supporting document tables and section specifications
        req_aspect_query = f"{query} Fresh Passport Adult Ordinary Case Table 2 Table 3 required supporting documents list proof specifications Case No."
        q2_vec = self.embedding_model.transform_query(req_aspect_query)

        # Retrieve candidates for both aspects
        results_primary = self.vector_store.search(q1_vec, top_k=top_k * 4)
        results_aspect = self.vector_store.search(q2_vec, top_k=top_k * 4)

        score_map = {}
        chunk_map = {}

        # Pool raw similarity scores taking maximum across aspect queries
        for res_list in [results_primary, results_aspect]:
            for chunk, score in res_list:
                cid = chunk["chunk_id"]
                if cid in score_map:
                    score_map[cid] = max(score_map[cid], score)
                else:
                    score_map[cid] = score
                    chunk_map[cid] = chunk

        if not score_map:
            print("[WARNING] Vector search returned 0 matches.")
            return []

        # Domain section priority markers in official documentation
        section_markers = [
            "table 2", "table 3", "table-2", "table-3",
            "list of supporting documents", "documents to be submitted",
            "list of categories of applicants", "case no.", "fresh passport"
        ]

        scored_chunks = []
        for cid, raw_score in score_map.items():
            chunk = chunk_map[cid]
            txt_lower = chunk.get("text", "").lower()

            boosted_score = raw_score

            # Boost 1: Official booklet primary source priority
            if chunk.get("is_primary", False):
                boosted_score += 0.20

            # Boost 2: Requirement section table priority
            if any(marker in txt_lower for marker in section_markers):
                boosted_score += 0.25

            scored_chunks.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "file_name": chunk["file_name"],
                "page_number": chunk["page_number"],
                "is_primary": chunk.get("is_primary", False),
                "similarity_score": round(raw_score, 4),
                "boosted_score": round(boosted_score, 4)
            })

        # Sort by boosted score descending
        scored_chunks.sort(key=lambda x: x["boosted_score"], reverse=True)
        top_results = scored_chunks[:top_k]

        print(f"[*] Retrieved {len(top_results)} relevant document chunks for query: '{query}'")
        return top_results

