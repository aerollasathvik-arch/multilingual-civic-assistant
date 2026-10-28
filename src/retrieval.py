"""Dense and lexical retrievers over the chunk table.

Dense: sentence-transformers model + FAISS inner-product index on normalised
vectors (= cosine similarity). E5 models need "query: " / "passage: " prefixes.
Lexical: BM25 (rank_bm25), used as a non-neural baseline.
"""
import re

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class DenseRetriever:
    def __init__(self, model_name, texts):
        self.model = SentenceTransformer(model_name)
        self.e5 = "e5" in model_name.lower()
        passages = [("passage: " + t) if self.e5 else t for t in texts]
        emb = self.model.encode(passages, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(np.asarray(emb, dtype="float32"))

    def search(self, query, k=10):
        q = self.model.encode([("query: " + query) if self.e5 else query], normalize_embeddings=True)
        scores, ids = self.index.search(np.asarray(q, dtype="float32"), k)
        return list(zip(ids[0].tolist(), scores[0].tolist()))

    def save(self, path):
        faiss.write_index(self.index, str(path))


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class BM25Retriever:
    def __init__(self, texts):
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])

    def search(self, query, k=10):
        scores = self.bm25.get_scores(tokenize(query))
        ids = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in ids]
