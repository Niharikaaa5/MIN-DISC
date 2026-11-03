"""
Module: FAISS Vector Store Index
Manages FAISS index construction, persistence, and similarity search.
"""
import json
from pathlib import Path
from typing import List, Dict, Tuple
import faiss
import numpy as np

from src.config import FAISS_INDEX_PATH, METADATA_STORE_PATH


class VectorStore:
    """FAISS Vector Store wrapper."""

    def __init__(self):
        self.index = None
        self.chunks_metadata: List[Dict] = []

    def build_index(self, chunks: List[Dict], embeddings: np.ndarray):
        """Constructs FAISS IndexFlatIP (cosine similarity) from chunk embeddings."""
        if embeddings.shape[0] == 0:
            print("[WARNING] Empty embeddings provided to vector store.")
            return

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.chunks_metadata = chunks
        print(f"[*] Built FAISS vector index with {self.index.ntotal} vectors (dimension {dimension}).")

    def save(self, index_path: Path = FAISS_INDEX_PATH, metadata_path: Path = METADATA_STORE_PATH):
        """Saves FAISS index and metadata to disk."""
        if self.index is None:
            print("[WARNING] Vector store index is empty, skipping save.")
            return

        faiss.write_index(self.index, str(index_path))
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks_metadata, f, indent=2)
        print(f"[*] Saved FAISS index to {index_path} and metadata to {metadata_path}.")

    def load(self, index_path: Path = FAISS_INDEX_PATH, metadata_path: Path = METADATA_STORE_PATH) -> bool:
        """Loads FAISS index and metadata from disk if available."""
        if not index_path.exists() or not metadata_path.exists():
            return False

        try:
            self.index = faiss.read_index(str(index_path))
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.chunks_metadata = json.load(f)
            print(f"[*] Loaded FAISS index ({self.index.ntotal} vectors) from {index_path}.")
            return True
        except Exception as e:
            print(f"[ERROR] Failed loading vector store: {e}")
            return False

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Performs vector similarity search against FAISS index.
        Returns list of (chunk_dict, score) tuples.
        """
        if self.index is None or len(self.chunks_metadata) == 0:
            return []

        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx, score in zip(indices[0], distances[0]):
            if 0 <= idx < len(self.chunks_metadata):
                chunk = self.chunks_metadata[idx]
                results.append((chunk, float(score)))

        return results
