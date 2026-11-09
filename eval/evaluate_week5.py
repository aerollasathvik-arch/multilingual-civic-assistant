"""Week 5 experiment: language ID, translation and reranking on the 150-query test set.

Steps
  1. Language identification accuracy (lingua, 5 languages).
  2. Translate the 120 non-English questions to English with NLLB-200 (cached to
     eval/translations_nllb.csv so a native speaker can review them too).
  3. Compare retrieval set-ups on the same nation-tagged section chunks:
       A direct                 e5 on the original question (week 4 best set-up)
       B direct+filter          A, England / UK-wide chunks only
       C translated+filter      e5 on the NLLB English translation
       D fusion+filter          reciprocal rank fusion of A and C
       E direct+filter+rerank   B, top 20 reordered by bge-reranker-v2-m3
       F fusion+filter+rerank   D, top 20 reordered by bge-reranker-v2-m3
Metrics as week 4: hit@1, hit@3, mrr@10 (gold page) and ans@3 (verbatim answer phrase in a top-3 chunk).
Outputs: results/week5_*.csv
"""
import pathlib
import sys
import time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from language import detect  # noqa: E402
from pipeline import E5, rrf  # noqa: E402
from rerank import Reranker  # noqa: E402
from retrieval import DenseRetriever  # noqa: E402
from translate import Translator  # noqa: E402

POOL = 20
OUT = ROOT / "results"


def metrics(ranked, chunks, q):
    urls = list(dict.fromkeys(chunks.url.iloc[i] for i in ranked))[:10]
    rank = urls.index(q.gold_url) + 1 if q.gold_url in urls else None
    top3 = [chunks.body.iloc[i].lower() for i in ranked[:3]]
    return {"hit@1": rank == 1, "hit@3": rank is not None and rank <= 3, "mrr@10": 1 / rank if rank else 0.0,
            "ans@3": any(q.evidence.lower() in t for t in top3),
            "top1_nation": chunks.nation.iloc[ranked[0]], "top1_url": urls[0]}


def main():
    queries = pd.read_csv(ROOT / "eval/queries.csv")
    chunks = pd.read_csv(ROOT / "data/processed/chunks.csv")
    texts = chunks.text.tolist()
    england = set(chunks.index[chunks.nation == "england"])
    OUT.mkdir(exist_ok=True)

    # 1. language identification
    queries["detected"] = [detect(q) for q in queries.question]
    lid = (queries.detected == queries.lang).groupby(queries.lang).mean().round(3)
    print("Language ID accuracy:", lid.to_dict(), "| overall", round((queries.detected == queries.lang).mean(), 3))
    lid.rename("accuracy").to_csv(OUT / "week5_language_id.csv")

    # 2. translation (cached)
    cache = ROOT / "eval/translations_nllb.csv"
    if cache.exists():
        tr = pd.read_csv(cache)
    else:
        translator, rows, t0 = Translator(), [], time.time()
        for lang, grp in queries[queries.lang != "en"].groupby("lang"):
            outs = translator.translate(grp.question.tolist(), src=lang)
            rows += [{"qid": r.qid, "lang": lang, "question": r.question, "nllb_english": o}
                     for r, o in zip(grp.itertuples(), outs)]
        tr = pd.DataFrame(rows)
        en = queries[queries.lang == "en"].set_index("qid").question
        tr["original_english"] = tr.qid.map(en)
        tr.to_csv(cache, index=False)
        print(f"translated {len(tr)} questions in {time.time() - t0:.0f}s")
    english = {(r.qid, r.lang): r.nllb_english for r in tr.itertuples()}

    # 3. retrieval set-ups
    dense = DenseRetriever(E5, texts)
    reranker = Reranker()
    rows, timing = [], {"rerank": []}
    for q in queries.itertuples():
        direct = [i for i, _ in dense.search(q.question, k=50)]
        eng_q = english.get((q.qid, q.lang), q.question)
        translated = [i for i, _ in dense.search(eng_q, k=50)] if q.lang != "en" else direct
        fused = rrf(direct, translated) if q.lang != "en" else direct
        keep = lambda r: [i for i in r if i in england]  # noqa: E731
        t0 = time.time()
        rr_direct = [i for i, _ in reranker.rerank(q.question, keep(direct)[:POOL], texts)]
        rr_fused = [i for i, _ in reranker.rerank(q.question, keep(fused)[:POOL], texts)]
        timing["rerank"].append((time.time() - t0) / 2)
        setups = {
            "A direct": direct, "B direct+filter": keep(direct), "C translated+filter": keep(translated),
            "D fusion+filter": keep(fused), "E direct+filter+rerank": rr_direct,
            "F fusion+filter+rerank": rr_fused,
        }
        for name, ranked in setups.items():
            rows.append({"system": name, "qid": q.qid, "domain": q.domain, "lang": q.lang, **metrics(ranked, chunks, q)})

    per_q = pd.DataFrame(rows)
    per_q.to_csv(OUT / "week5_per_query.csv", index=False)
    m = ["hit@1", "hit@3", "mrr@10", "ans@3"]
    overall = per_q.groupby("system")[m].mean().round(3)
    by_lang = per_q.groupby(["system", "lang"])[m].mean().round(3).reset_index()
    pd.concat([by_lang, overall.assign(lang="ALL").reset_index()]).to_csv(OUT / "week5_by_lang.csv", index=False)

    print(f"\nmean rerank time per query (20 candidates): {sum(timing['rerank']) / len(timing['rerank']):.2f}s")
    print("\nOverall (150 queries)\n", overall.to_string())
    print("\nans@3 by language\n", per_q.pivot_table(index="system", columns="lang", values="ans@3").round(2).to_string())
    print("\nhit@3 by language\n", per_q.pivot_table(index="system", columns="lang", values="hit@3").round(2).to_string())
    print("\nans@3 by domain\n", per_q.pivot_table(index="system", columns="domain", values="ans@3").round(2).to_string())
    print("\nqueries whose top chunk is for another nation:\n",
          per_q[per_q.top1_nation != "england"].groupby("system").size().to_string())


if __name__ == "__main__":
    main()
