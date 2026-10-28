"""Week 4 retrieval experiment.

Compares four retrieval set-ups on the same 150 queries (30 questions x 5 languages):
  bm25            - lexical baseline over section chunks
  e5_naive150     - the original notebook set-up: e5-base on blind 150-word chunks
  e5_sections     - e5-base on heading-aware section chunks (src/chunk.py)
  minilm_sections - paraphrase-multilingual-MiniLM-L12-v2 on the same section chunks

Metrics (all at page or chunk level as named):
  hit@1, hit@3  - gold page appears in the top 1 / top 3 distinct pages
  mrr@10        - mean reciprocal rank of the gold page among the top 10 distinct pages
  ans@3         - at least one of the top 3 chunks contains the verbatim answer phrase
Outputs: results/retrieval_by_lang.csv, results/retrieval_per_query.csv
"""
import json
import pathlib
import sys
import time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retrieval import BM25Retriever, DenseRetriever  # noqa: E402

E5 = "intfloat/multilingual-e5-base"
MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def naive_chunks():
    """Reproduce the notebook: whole page text cut every 150 words, no headings."""
    rows = []
    for line in open(ROOT / "data/processed/pages.jsonl"):
        p = json.loads(line)
        words = " ".join(s["text"] for s in p["sections"]).split()
        for i in range(0, len(words), 150):
            body = " ".join(words[i:i + 150])
            rows.append({"url": p["url"], "body": body, "text": body})
    return pd.DataFrame(rows)


def score(retriever, chunks, queries, name):
    rows = []
    for q in queries.itertuples():
        hits = retriever.search(q.question, k=30)
        urls = list(dict.fromkeys(chunks.iloc[i].url for i, _ in hits))[:10]
        rank = urls.index(q.gold_url) + 1 if q.gold_url in urls else None
        top3 = [chunks.iloc[i].body.lower() for i, _ in hits[:3]]
        rows.append({
            "system": name, "qid": q.qid, "domain": q.domain, "lang": q.lang,
            "hit@1": rank == 1, "hit@3": rank is not None and rank <= 3,
            "mrr@10": 1 / rank if rank else 0.0,
            "ans@3": any(q.evidence.lower() in t for t in top3),
            "top1_url": urls[0], "top1_score": round(hits[0][1], 4),
        })
    return rows


def main():
    queries = pd.read_csv(ROOT / "eval/queries.csv")
    sections = pd.read_csv(ROOT / "data/processed/chunks.csv")
    naive = naive_chunks()
    print(f"{len(queries)} queries | section chunks {len(sections)} | naive chunks {len(naive)}")

    systems = [
        ("bm25", lambda: BM25Retriever(sections.text.tolist()), sections),
        ("e5_naive150", lambda: DenseRetriever(E5, naive.text.tolist()), naive),
        ("e5_sections", lambda: DenseRetriever(E5, sections.text.tolist()), sections),
        ("minilm_sections", lambda: DenseRetriever(MINILM, sections.text.tolist()), sections),
    ]
    rows = []
    for name, build, chunks in systems:
        t0 = time.time()
        r = build()
        rows += score(r, chunks, queries, name)
        print(f"  {name:16} done in {time.time() - t0:.0f}s")
        if name == "e5_sections":
            r.save(ROOT / "data/processed/e5_sections.faiss")

    per_q = pd.DataFrame(rows)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    per_q.to_csv(out / "retrieval_per_query.csv", index=False)
    metrics = ["hit@1", "hit@3", "mrr@10", "ans@3"]
    by_lang = per_q.groupby(["system", "lang"])[metrics].mean().round(3)
    overall = per_q.groupby("system")[metrics].mean().round(3)
    overall["lang"] = "ALL"
    table = pd.concat([by_lang.reset_index(), overall.reset_index()])
    table.to_csv(out / "retrieval_by_lang.csv", index=False)

    print("\nOverall (150 queries)\n", overall[metrics].to_string())
    print("\nhit@3 by language\n", per_q.pivot_table(index="system", columns="lang", values="hit@3").round(2).to_string())
    print("\nans@3 by language\n", per_q.pivot_table(index="system", columns="lang", values="ans@3").round(2).to_string())
    print("\nans@3 by domain\n", per_q.pivot_table(index="system", columns="domain", values="ans@3").round(2).to_string())


if __name__ == "__main__":
    main()
