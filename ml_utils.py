# ml_utils.py
"""
Utilities for embedding-based lightweight tool inference.
Uses sentence-transformers when available. If not available, everything
falls back to heuristics implemented in tool_extractor.py.
"""
from typing import List, Tuple, Optional
import math

try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_ST_MODEL = True
except Exception:
    SentenceTransformer = None
    util = None
    _HAS_ST_MODEL = False

_MODEL_NAME = "all-MiniLM-L6-v2"  # small and fast model

class EmbeddingModel:
    def __init__(self):
        self.model = None
        self.template_embeddings = None
        self.templates = None
        if _HAS_ST_MODEL:
            try:
                self.model = SentenceTransformer(_MODEL_NAME)
            except Exception:
                # model load may fail if offline; set to None and fallback
                self.model = None

    def available(self) -> bool:
        return self.model is not None

    def encode(self, texts: List[str]):
        if not self.available():
            raise RuntimeError("Embedding model not available")
        return self.model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    def encode_single(self, text: str):
        return self.encode([text])[0]

    def prepare_templates(self, templates: List[str]):
        """
        Pre-compute embeddings for templates (tool-purpose prototypes).
        """
        if not self.available():
            return
        self.templates = templates
        self.template_embeddings = self.encode(templates)

    def best_template(self, text: str) -> Tuple[Optional[str], float]:
        """
        Return best matching template and cosine similarity score (0..1).
        """
        if not self.available():
            return None, 0.0
        emb = self.encode_single(text)
        cos_scores = util.pytorch_cos_sim(emb, self.template_embeddings)[0]
        best_idx = int(cos_scores.argmax().cpu().numpy())
        score = float(cos_scores[best_idx].cpu().numpy())
        return self.templates[best_idx], score

# Small helper (pure python) for confidence scaling
def scale_confidence(sim: float, floor=0.15, ceiling=0.98) -> float:
    """Map similarity (which is roughly -1..1 but here 0..1) to calibrated confidence (0..1)."""
    # ensure sim in [0,1]
    s = max(0.0, min(1.0, sim))
    # small mapping to emphasize higher sims
    c = floor + (ceiling - floor) * (s ** 1.8)
    return round(max(0.0, min(1.0, c)), 2)
