"""
Module: Embedding Engine
Generates dense or sparse vector representations for text chunks.
Supports SentenceTransformers with TF-IDF fallback for maximum reliability.
"""
import pickle
from pathlib import Path
from typing import List, Optional
import numpy as np

from src.config import DATA_DIR, EMBEDDING_BACKEND

TFIDF_MODEL_PATH = DATA_DIR / "tfidf_vectorizer.pkl"


class EmbeddingModel:
    """Embedding model wrapper with automatic fallback and configurable backend."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        tfidf_model_path: Optional[Path] = None,
        backend: Optional[str] = None
    ):
        self.model_name = model_name
        self.tfidf_model_path = Path(tfidf_model_path) if tfidf_model_path else TFIDF_MODEL_PATH
        self.backend = (backend or EMBEDDING_BACKEND or "tfidf").lower()
        self.use_st = False
        self.st_model = None
        self.tfidf_vectorizer = None

        if self.backend == "tfidf":
            # Fast-path: Directly use TF-IDF vectorizer without attempting PyTorch / SentenceTransformers import
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf_vectorizer = TfidfVectorizer(stop_words="english")
            if self.tfidf_model_path.exists():
                try:
                    with open(self.tfidf_model_path, "rb") as f:
                        self.tfidf_vectorizer = pickle.load(f)
                    if hasattr(self.tfidf_vectorizer, "_tfidf"):
                        tfidf = self.tfidf_vectorizer._tfidf
                        if hasattr(tfidf, "_idf_diag") and not hasattr(tfidf, "idf_"):
                            tfidf.idf_ = tfidf._idf_diag.diagonal()
                    print(f"[*] Loaded fitted TF-IDF vectorizer from {self.tfidf_model_path}.")
                except Exception as e:
                    print(f"[NOTE] Could not load pre-fitted TF-IDF vectorizer: {e}")
        else:
            # Attempt SentenceTransformers initialization if explicitly configured
            try:
                from sentence_transformers import SentenceTransformer
                self.st_model = SentenceTransformer(model_name)
                self.use_st = True
                print(f"[*] Initialized SentenceTransformers ({model_name}).")
            except Exception as e:
                print(f"[NOTE] SentenceTransformers fallback active ({e}). Using TF-IDF vectorizer.")
                from sklearn.feature_extraction.text import TfidfVectorizer
                self.tfidf_vectorizer = TfidfVectorizer(stop_words="english")
                if self.tfidf_model_path.exists():
                    try:
                        with open(self.tfidf_model_path, "rb") as f:
                            self.tfidf_vectorizer = pickle.load(f)
                        if hasattr(self.tfidf_vectorizer, "_tfidf"):
                            tfidf = self.tfidf_vectorizer._tfidf
                            if hasattr(tfidf, "_idf_diag") and not hasattr(tfidf, "idf_"):
                                tfidf.idf_ = tfidf._idf_diag.diagonal()
                        print(f"[*] Loaded fitted TF-IDF vectorizer from {self.tfidf_model_path}.")
                    except Exception:
                        pass

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of text strings into numpy float32 array."""
        if not texts:
            return np.array([], dtype=np.float32)

        if self.use_st and self.st_model is not None:
            embeddings = self.st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.astype(np.float32)
        else:
            matrix = self.tfidf_vectorizer.fit_transform(texts).toarray()
            # Save fitted TFIDF vectorizer to configured path
            self.tfidf_model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tfidf_model_path, "wb") as f:
                pickle.dump(self.tfidf_vectorizer, f)

            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            return matrix.astype(np.float32)

    def transform_query(self, query: str) -> np.ndarray:
        """Embeds a single query string into numpy float32 2D array."""
        if self.use_st and self.st_model is not None:
            emb = self.st_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            return emb.astype(np.float32)
        else:
            if not hasattr(self.tfidf_vectorizer, "vocabulary_"):
                # If vectorizer is unfitted, fit on default query text
                self.tfidf_vectorizer.fit([query])

            matrix = self.tfidf_vectorizer.transform([query]).toarray()
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            return matrix.astype(np.float32)
