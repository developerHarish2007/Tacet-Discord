import os
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

class SemanticTextMatcher:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.doc_ids: List[int] = []
        self.documents: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self._init_model()

    def _init_model(self):
        """Loads local sentence-transformers model 'all-MiniLM-L6-v2'"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading Semantic Text Matcher ({self.model_name})...")
            self.model = SentenceTransformer(self.model_name)
            print("Loaded sentence-transformers model successfully.")
        except Exception as e:
            print(f"Warning: Could not load sentence-transformers ({e}). Using semantic fallback vectorizer.")
            self.model = None

    def embed_text(self, text: str) -> np.ndarray:
        """Computes 384-dimensional L2-normalized semantic vector for text"""
        if not text:
            return np.zeros(384, dtype=np.float32)

        if self.model is not None:
            emb = self.model.encode(text, convert_to_numpy=True)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            return emb.astype(np.float32)

        # Fallback Hashed Word Vector (384 dimensions)
        tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
        vec = np.zeros(384, dtype=np.float32)
        for token in tokens:
            idx = abs(hash(token)) % 384
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def fit_documents(self, docs_with_ids: List[Tuple[int, str]]):
        """
        docs_with_ids: list of (doc_id, text_content)
        Embeds all incident records once at load time.
        """
        if not docs_with_ids:
            self.doc_ids = []
            self.documents = []
            self.embeddings = None
            return

        self.doc_ids = [d[0] for d in docs_with_ids]
        self.documents = [d[1] for d in docs_with_ids]

        if self.model is not None:
            raw_embs = self.model.encode(self.documents, convert_to_numpy=True, batch_size=64, show_progress_bar=False)
            norms = np.linalg.norm(raw_embs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = (raw_embs / norms).astype(np.float32)
        else:
            vecs = [self.embed_text(d[1]) for d in docs_with_ids]
            self.embeddings = np.vstack(vecs).astype(np.float32)

    def add_document(self, doc_id: int, text_content: str):
        """Adds a single newly added senior record to the semantic vector store"""
        new_emb = self.embed_text(text_content).reshape(1, -1)
        self.doc_ids.append(doc_id)
        self.documents.append(text_content)

        if self.embeddings is None or self.embeddings.size == 0:
            self.embeddings = new_emb
        else:
            self.embeddings = np.vstack([self.embeddings, new_emb])

    def query(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Embeds query text and retrieves top_k matching records by cosine similarity.
        """
        if self.embeddings is None or len(self.doc_ids) == 0 or not query_text:
            return []

        query_vec = self.embed_text(query_text)
        
        # Cosine similarity (dot product of L2-normalized vectors)
        similarities = np.dot(self.embeddings, query_vec)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.05:
                results.append({
                    "id": self.doc_ids[idx],
                    "similarity_score": round(score, 4)
                })

        return results
