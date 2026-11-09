"""Week 5 search pipeline: question in any supported language -> best official passages.

    question
      -> detect language                       (language.py)
      -> translate to English if not English   (translate.py, optional)
      -> dense retrieval, original + English   (retrieval.py, e5 + FAISS)
      -> fuse the two ranked lists (RRF)
      -> keep England / UK-wide chunks only     (nation tag from chunk.py)
      -> rerank top candidates                  (rerank.py, optional)
      -> top k passages with title, heading, URL and dates for citation
"""
import pathlib

import pandas as pd

from language import detect
from retrieval import DenseRetriever

ROOT = pathlib.Path(__file__).resolve().parents[1]
E5 = "intfloat/multilingual-e5-base"
RRF_K = 60  # standard constant from Cormack et al. (2009)


def rrf(*ranked_lists, k=RRF_K):
    """Reciprocal rank fusion: combine ranked lists of ids into one ranking."""
    score = {}
    for ranked in ranked_lists:
        for rank, i in enumerate(ranked, start=1):
            score[i] = score.get(i, 0.0) + 1.0 / (k + rank)
    return sorted(score, key=lambda i: -score[i])


class SearchPipeline:
    def __init__(self, chunks=None, translate=True, rerank=True, england_only=True, pool=20):
        self.chunks = chunks if chunks is not None else pd.read_csv(ROOT / "data/processed/chunks.csv")
        self.texts = self.chunks.text.tolist()
        self.retriever = DenseRetriever(E5, self.texts)
        self.allowed = set(self.chunks.index[self.chunks.nation == "england"]) if england_only else None
        self.pool = pool
        self.translator = None
        if translate:
            from translate import Translator
            self.translator = Translator()
        self.reranker = None
        if rerank:
            from rerank import Reranker
            self.reranker = Reranker()

    def _dense(self, query, n):
        return [i for i, _ in self.retriever.search(query, k=n)]

    def search(self, question, k=3, lang=None):
        lang = lang or detect(question)
        english = question
        lists = [self._dense(question, 50)]
        if self.translator and lang != "en":
            english = self.translator.translate([question], src=lang)[0]
            lists.append(self._dense(english, 50))
        ranked = rrf(*lists) if len(lists) > 1 else lists[0]
        if self.allowed is not None:
            ranked = [i for i in ranked if i in self.allowed]
        ranked = ranked[:self.pool]
        if self.reranker:
            ranked = [i for i, _ in self.reranker.rerank(question, ranked, self.texts)]
        results = []
        for i in ranked[:k]:
            c = self.chunks.iloc[i]
            results.append({"chunk": int(i), "title": c.title, "heading": c.heading, "url": c.url,
                            "source": c.source, "nation": c.nation, "public_updated_at": c.public_updated_at,
                            "fetched_at": c.fetched_at, "text": c.body})
        return {"lang": lang, "english_query": english, "results": results}
