"""Week 7 experiment: held-out check of the search stage and refusal rules, and the ungrounded baseline.

Questions: the held-out half of the gold set (eval/build_gold_set.py), never used for tuning:
  50 answerable topics x 5 languages (eval/heldout_queries.csv)    = 250
  10 unanswerable topics x 5 languages (eval/heldout_unanswerable.csv) = 50

Steps
  1. Search every question with the week 5 pipeline (cached to results/week7_search.json) and measure
     hit@3 (gold page in the top 3) and ans@3 (a top-3 passage contains the evidence phrase), as in week 5.
  2. Grounded answers: the week 6 assistant exactly as it is (direct mode, threshold 0.0052 fixed in
     week 6, yes/no check, NO_ANSWER). Nothing is re-tuned, so the refusal figures are a fair test.
  3. Ungrounded baseline (T30): the same model, same style rules, no retrieved passages.
  4. Automatic measures for both conditions: refused, cited / cites_answer (grounded only), answer in the
     question's language (lingua), length, words per sentence, and Flesch Reading Ease / Flesch-Kincaid grade
     for English answers (textstat). Accuracy and unsupported claims are scored by hand with
     docs/scoring-rubric.md, using the blinded sheet written by step 5.
  5. Scoring sheet: 15 held-out English topics (12 answerable, 3 unanswerable, fixed random seed) x 2
     conditions, shuffled, condition hidden -> eval/scoring_sheet.xlsx; key in eval/scoring_key.csv.

Answers are cached row by row in results/week7_answers.csv, so the run can be resumed.
Run: python eval/evaluate_week7.py            (about 3 hours on an Apple-silicon laptop)
     python eval/evaluate_week7.py --quick    (8 topics x 5 languages)
Output: results/week7_*.csv, eval/scoring_sheet.xlsx, eval/scoring_key.csv
"""
import argparse
import json
import pathlib
import random
import re
import sys
import time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch  # noqa: F401  (import before faiss on macOS, see retrieval.py)
import textstat
from language import detect
from pipeline import SearchPipeline
from generate import citations, CITATION
from translate import split_sentences

SEARCH_CACHE = ROOT / "results/week7_search.json"
ANSWERS = ROOT / "results/week7_answers.csv"
QUICK = ["S11", "S15", "H12", "H23", "M11", "M25", "U11", "U17"]


def norm(s):
    return " ".join(str(s).replace("’", "'").lower().split())


def load_questions():
    a = pd.read_csv(ROOT / "eval/heldout_queries.csv")
    a["answerable"] = True
    u = pd.read_csv(ROOT / "eval/heldout_unanswerable.csv")
    u["answerable"], u["evidence"], u["gold_url"], u["domain"] = False, "", "", ""
    return pd.concat([a, u], ignore_index=True)


def run_search(qs, pipe):
    cache = json.loads(SEARCH_CACHE.read_text()) if SEARCH_CACHE.exists() else {}
    for r in qs.itertuples():
        key = f"{r.qid}-{r.lang}"
        if key not in cache:
            cache[key] = pipe.search(r.question, k=3, lang=r.lang)
    SEARCH_CACHE.write_text(json.dumps(cache, ensure_ascii=False, default=str))
    return cache


def retrieval_table(qs, search):
    rows = []
    for r in qs[qs.answerable].itertuples():
        res = search[f"{r.qid}-{r.lang}"]["results"]
        rows.append({"qid": r.qid, "lang": r.lang, "hit@3": any(p["url"] == r.gold_url for p in res),
                     "ans@3": any(norm(r.evidence) in norm(p["text"]) for p in res),
                     "top_score": res[0]["score"]})
    return pd.DataFrame(rows)


def answer_text(answer):
    """The answer without citation markers and without the appended health note."""
    return CITATION.sub("", answer.split("\n\n")[0]).replace(" .", ".").strip()


def text_measures(text, lang):
    sents = [s for s in split_sentences(text) if s.strip()]
    words = len(text.split())
    out = {"words": words, "words_per_sentence": round(words / max(len(sents), 1), 1),
           "flesch_reading_ease": None, "fk_grade": None}
    if lang == "en" and words:
        out["flesch_reading_ease"] = round(textstat.flesch_reading_ease(text), 1)
        out["fk_grade"] = round(textstat.flesch_kincaid_grade(text), 1)
    return out


def scoring_sheet(df):
    """Blinded sheet for hand scoring (pilot and second rater): condition hidden, order shuffled."""
    gold = pd.read_csv(ROOT / "eval/gold_set.csv")
    gold = gold[gold.split == "heldout"]
    rng = random.Random(7)
    topics = rng.sample(sorted(gold[gold.answerable].qid), 12) + rng.sample(sorted(gold[~gold.answerable].qid), 3)
    en = df[(df.lang == "en") & df.qid.isin(topics)]
    items = [r for r in en.itertuples()]
    rng.shuffle(items)
    sheet, key = [], []
    for n, r in enumerate(items, 1):
        g = gold[gold.qid == r.qid].iloc[0]
        sheet.append({"item": n, "question": r.question,
                      "reference_answer": g.reference_answer if g.answerable else "(not covered by the 38 pages: should be refused)",
                      "source_page": g.gold_url if g.answerable else "", "answer_to_score": r.answer,
                      "accuracy": "", "unsupported_claim": "", "citations": "", "refusal": "", "notes": ""})
        key.append({"item": n, "qid": r.qid, "condition": r.condition})
    with pd.ExcelWriter(ROOT / "eval/scoring_sheet.xlsx") as xw:
        for rater in ("rater 1", "rater 2"):
            pd.DataFrame(sheet).to_excel(xw, sheet_name=rater, index=False)
    pd.DataFrame(key).to_csv(ROOT / "eval/scoring_key.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="answers for an 8-topic subset only")
    quick = ap.parse_args().quick
    from assistant import Assistant
    from generate import Generator

    qs = load_questions()
    if quick:
        qs = qs[qs.qid.isin(QUICK)].reset_index(drop=True)
    pipe = SearchPipeline()
    search = run_search(qs, pipe)
    ret = retrieval_table(qs, search)
    ret.to_csv(ROOT / "results/week7_retrieval.csv", index=False)
    print("held-out retrieval (answerable):")
    print(ret.groupby("lang")[["hit@3", "ans@3"]].mean().round(3).T.assign(ALL=ret[["hit@3", "ans@3"]].mean().round(3)).to_string())

    done = pd.read_csv(ANSWERS) if ANSWERS.exists() else pd.DataFrame()
    have = set(zip(done.qid, done.lang, done.condition)) if len(done) else set()
    rows = done.to_dict("records") if len(done) else []
    bot = Assistant(pipeline=pipe, generator=Generator(), mode="direct")
    jobs = [(r, c) for r in qs.itertuples() for c in ("grounded", "ungrounded") if (r.qid, r.lang, c) not in have]
    print(len(jobs), "answers to generate", flush=True)
    for n, (r, cond) in enumerate(jobs, 1):
        t0 = time.time()
        s = search[f"{r.qid}-{r.lang}"]
        if cond == "grounded":
            a = bot.answer_from(s, r.question, "direct")
            refused, reason, answer = a["refused"], a["reason"], a["answer"]
        else:
            refused, reason, answer = False, None, bot.generator.answer_ungrounded(r.question, r.lang)
        cited = citations(answer) if cond == "grounded" and not refused else []
        valid = bool(cited) and all(1 <= c <= len(s["results"]) for c in cited)
        cites_answer = bool(r.answerable) and any(norm(r.evidence) in norm(s["results"][c - 1]["text"])
                                                  for c in cited if 1 <= c <= len(s["results"]))
        text = answer_text(answer)
        rows.append({"qid": r.qid, "lang": r.lang, "condition": cond, "answerable": r.answerable,
                     "question": r.question, "top_score": s["results"][0]["score"], "refused": refused,
                     "reason": reason, "cited": valid, "cites_answer": cites_answer,
                     "lang_ok": (not refused) and detect(text) == r.lang,
                     **(text_measures(text, r.lang) if not refused else {}),
                     "answer": answer, "seconds": round(time.time() - t0, 1)})
        if n % 10 == 0 or n == len(jobs):
            pd.DataFrame(rows).to_csv(ANSWERS, index=False)
            print(f"{n}/{len(jobs)}", flush=True)

    df = pd.DataFrame(rows)
    df = df[df.set_index(["qid", "lang"]).index.isin(qs.set_index(["qid", "lang"]).index)]
    summarise(df)
    if not quick:
        scoring_sheet(df)


def summarise(df):
    out = []
    for cond in ("grounded", "ungrounded"):
        for lang in ["ALL", "en", "pl", "ro", "ar", "ur"]:
            d = df[(df.condition == cond) & ((df.lang == lang) | (lang == "ALL"))]
            a, u = d[d.answerable], d[~d.answerable]
            given = a[~a.refused]
            out.append({"condition": cond, "lang": lang, "n_answerable": len(a),
                        "answerable_refused": round(a.refused.mean(), 3),
                        "cited": round(given.cited.mean(), 3) if cond == "grounded" else None,
                        "cites_answer": round(given.cites_answer.mean(), 3) if cond == "grounded" else None,
                        "lang_ok": round(given.lang_ok.mean(), 3),
                        "words": round(given.words.mean(), 1),
                        "words_per_sentence": round(given.words_per_sentence.mean(), 1),
                        "flesch_reading_ease": round(given.flesch_reading_ease.mean(), 1) if lang in ("en", "ALL") else None,
                        "fk_grade": round(given.fk_grade.mean(), 1) if lang in ("en", "ALL") else None,
                        "n_unanswerable": len(u), "unanswerable_refused": round(u.refused.mean(), 3),
                        "sec_per_answer": round(d[~d.refused].seconds.mean(), 1)})
    by = pd.DataFrame(out)
    by.to_csv(ROOT / "results/week7_by_condition.csv", index=False)
    ref = (df[df.condition == "grounded"].groupby(["answerable", "reason"], dropna=False).size()
           .rename("n").reset_index())
    ref.to_csv(ROOT / "results/week7_refusal.csv", index=False)
    print(by.to_string(index=False))
    print(ref.to_string(index=False))


if __name__ == "__main__":
    main()
