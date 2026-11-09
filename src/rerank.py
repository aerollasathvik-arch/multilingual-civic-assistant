"""Second-stage reranking with a multilingual cross-encoder (BAAI/bge-reranker-v2-m3, Apache-2.0).

The bi-encoder (e5) compares a question vector with pre-computed chunk vectors, which
is fast but coarse. A cross-encoder reads the question and one chunk together and
scores how well that chunk answers it; it is too slow for the whole corpus, so it
only reorders the top candidates from the first stage.
"""
from sentence_transformers import CrossEncoder

MODEL = "BAAI/bge-reranker-v2-m3"


class Reranker:
    def __init__(self, model_name=MODEL):
        self.model = CrossEncoder(model_name, max_length=512)

    def rerank(self, query, candidates, texts):
        """candidates: list of chunk ids; texts: chunk id -> text. Returns [(id, score)] best first."""
        if not candidates:
            return []
        scores = self.model.predict([(query, texts[i]) for i in candidates], batch_size=16, show_progress_bar=False)
        return sorted(zip(candidates, map(float, scores)), key=lambda x: -x[1])
