"""Week 6 experiment: grounded answers, refusal rule and answer language.

Questions: 150 answerable (eval/queries.csv: 30 questions x 5 languages, each with a verbatim answer
phrase on its gold page) + 50 unanswerable (eval/unanswerable.csv: 10 topics not in the corpus).

Steps
  1. Search every question once with the week 5 pipeline (set-up F); cache to results/week6_search.json.
  2. Refusal rule 1: look at the reranker score of the top passage for answerable vs unanswerable
     questions and set the threshold just below the lowest score of any answerable question whose
     answer passage was retrieved, so no retrievable answer is refused at this step.
  3. Generate answers with Qwen3.5-4B in two modes (task T29):
       direct    - the LLM writes in the user's language
       translate - the LLM writes in English and NLLB translates it (non-English questions only)
     Answers are cached row by row in results/week6_answers.csv, so the run can be resumed.
     This first run ("v1") refused only on the threshold or on the model writing NO_ANSWER.
  3b. The v1 answers showed the model often explains in prose that the extracts do not answer the
     question instead of writing NO_ANSWER. Refusal rule 2 was therefore added: a separate yes/no call
     ("do the extracts answer the question?"), cached in results/week6_check.csv. Decoding is greedy and
     the answer prompt is unchanged, so an answer that passes the check is the same as in v1; the final
     result is v1 plus a refusal wherever the check says NO.
  3c. The first translate-mode run was invalid: although told to write in English, the model wrote in the
     question's language in 94-100% of answers, so NLLB was "translating" Polish, Romanian, Arabic or Urdu
     as if it were English, and citation markers split off on their own were dropped. Both were fixed
     (English instruction repeated after the question; stray markers kept) and translate mode was rerun.
     The invalid run is kept in results/week6_answers_v1.csv.
  4. Automatic checks per answer:
       refused        - the assistant refused (low relevance or the model said NO_ANSWER)
       cited          - at least one [n] citation, and every number refers to a given passage
       cites_answer   - a cited passage contains the question's verbatim answer phrase
       lang_ok        - the answer is in the question's language (lingua)
     These are checks of form and grounding, not of factual accuracy; accuracy is scored by hand with
     the week 7 rubric.
Run: python eval/evaluate_week6.py            (all 200 questions; about 2.5 hours on an Apple-silicon laptop)
     python eval/evaluate_week6.py --quick    (answers for 10 question topics x 5 languages only;
                                               the threshold is still calibrated on all 200)
Output: results/week6_by_mode.csv, results/week6_refusal.csv, results/week6_answers.csv
"""
import argparse
import json
import pathlib
import sys
import time

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch  # noqa: F401  (import before faiss on macOS, see retrieval.py)
from language import detect
from pipeline import SearchPipeline
from generate import citations, CITATION

SEARCH_CACHE = ROOT / "results/week6_search.json"
ANSWERS = ROOT / "results/week6_answers.csv"
CHECK = ROOT / "results/week6_check.csv"
QUICK = ["S01", "S05", "H03", "H06", "M01", "M04", "U01", "U03", "U04", "U07"]


def norm(s):
    return " ".join(str(s).replace("’", "'").lower().split())


def load_questions():
    a = pd.read_csv(ROOT / "eval/queries.csv")
    a["answerable"] = True
    u = pd.read_csv(ROOT / "eval/unanswerable.csv")
    u["answerable"], u["evidence"] = False, ""
    return pd.concat([a, u], ignore_index=True)


def run_search(qs, pipe):
    if SEARCH_CACHE.exists():
        return json.loads(SEARCH_CACHE.read_text())
    out = {}
    for r in qs.itertuples():
        out[f"{r.qid}-{r.lang}"] = pipe.search(r.question, k=3, lang=r.lang)
    SEARCH_CACHE.write_text(json.dumps(out, ensure_ascii=False, default=str))
    return out


def calibrate(qs, search):
    rows = []
    for r in qs.itertuples():
        s = search[f"{r.qid}-{r.lang}"]
        found = r.answerable and any(norm(r.evidence) in norm(p["text"]) for p in s["results"])
        rows.append({"qid": r.qid, "lang": r.lang, "answerable": r.answerable, "answer_retrieved": found,
                     "top_score": s["results"][0]["score"]})
    df = pd.DataFrame(rows)
    lowest = df[df.answer_retrieved].top_score.min()
    threshold = float(f"{lowest * 0.9:.3g}")  # 10% margin below the lowest retrievable answer
    return df, threshold


def strip_extras(text):
    return CITATION.sub("", text.split("\n\n")[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="generate answers for a 10-topic subset only")
    quick = ap.parse_args().quick
    from assistant import Assistant
    from generate import Generator

    qs = load_questions()
    pipe = SearchPipeline()
    search = run_search(qs, pipe)
    scores, threshold = calibrate(qs, search)
    print("top reranker score, median by group:")
    print(scores.groupby("answerable").top_score.describe()[["min", "50%", "max"]].round(3).to_string())
    print(f"threshold = {threshold}")

    done = pd.read_csv(ANSWERS) if ANSWERS.exists() else pd.DataFrame()
    have = set(zip(done.qid, done.lang, done["mode"])) if len(done) else set()
    bot = Assistant(pipeline=pipe, generator=Generator(), threshold=threshold)
    rows = done.to_dict("records") if len(done) else []
    gen_qs = qs[qs.qid.isin(QUICK)] if quick else qs
    jobs = [(r, m) for r in gen_qs.itertuples() for m in ("direct", "translate")
            if not (m == "translate" and r.lang == "en") and (r.qid, r.lang, m) not in have]
    print(len(jobs), "answers to generate")
    for n, (r, mode) in enumerate(jobs, 1):
        t0 = time.time()
        s = search[f"{r.qid}-{r.lang}"]
        a = bot.answer_from(s, r.question, mode)
        cited = citations(a["answer"]) if not a["refused"] else []
        valid = bool(cited) and all(1 <= c <= len(s["results"]) for c in cited)
        cites_answer = r.answerable and any(norm(r.evidence) in norm(s["results"][c - 1]["text"])
                                            for c in cited if 1 <= c <= len(s["results"]))
        rows.append({"qid": r.qid, "lang": r.lang, "mode": mode, "answerable": r.answerable,
                     "question": r.question, "top_score": a["top_score"], "refused": a["refused"],
                     "reason": a["reason"], "cited": valid, "cites_answer": cites_answer,
                     "lang_ok": (not a["refused"]) and detect(strip_extras(a["answer"])) == r.lang,
                     "answer": a["answer"], "raw": a["raw"], "seconds": round(time.time() - t0, 1)})
        if n % 10 == 0 or n == len(jobs):
            pd.DataFrame(rows).to_csv(ANSWERS, index=False)
            print(f"{n}/{len(jobs)}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(ANSWERS, index=False)

    # Refusal rule 2: yes/no answerability check (only for questions that pass the threshold).
    check = pd.read_csv(CHECK) if CHECK.exists() else pd.DataFrame(columns=["qid", "lang", "check_yes"])
    have = set(zip(check.qid, check.lang))
    new = []
    for r in gen_qs.itertuples():
        s = search[f"{r.qid}-{r.lang}"]
        if (r.qid, r.lang) not in have and s["results"][0]["score"] >= threshold:
            new.append({"qid": r.qid, "lang": r.lang, "check_yes": bot.generator.answerable(r.question, s["results"])})
    check = pd.concat([check, pd.DataFrame(new)], ignore_index=True)
    check.to_csv(CHECK, index=False)

    df = df.drop(columns=["check_yes"], errors="ignore").merge(check, on=["qid", "lang"], how="left")
    df.to_csv(ANSWERS, index=False)
    summarise(df, threshold)


def apply_check(df):
    """Final pipeline = v1 plus a refusal wherever the yes/no check said NO."""
    df = df.copy()
    blocked = (~df.refused) & (df.check_yes == False)  # noqa: E712  (NaN = not checked, below threshold)
    df.loc[blocked, ["refused", "cited", "cites_answer", "lang_ok"]] = [True, False, False, False]
    df.loc[blocked, "reason"] = "check: not in sources"
    return df


def summarise(df, threshold):
    out, refusal = [], []
    # v1 (no yes/no check) exists only for answers generated before the check was added: the original
    # direct-mode run. A fresh run (e.g. Colab) uses the check throughout, so only "final" is reported.
    pre_check = df[df["mode"] == "direct"]
    versions = [("final", apply_check(df), ("direct", "translate"))]
    if len(pre_check) and not (pre_check.reason == "check: not in sources").any():
        versions.insert(0, ("v1", df, ("direct",)))
    for version, d, modes in versions:
        by, ref = summarise_one(d[d["mode"].isin(modes)], modes)
        out.append(by.assign(version=version))
        refusal.append(ref.assign(version=version))
    by, ref = pd.concat(out), pd.concat(refusal)
    by.to_csv(ROOT / "results/week6_by_mode.csv", index=False)
    ref.to_csv(ROOT / "results/week6_refusal.csv", index=False)
    print(f"threshold {threshold}")
    print(by.to_string(index=False))
    print(ref.to_string(index=False))


def summarise_one(df, modes):
    ans, un = df[df.answerable], df[~df.answerable]
    rows = []
    for mode in modes:
        for lang in ["ALL", "en", "pl", "ro", "ar", "ur"]:
            if mode == "translate" and lang == "en":
                continue
            a = ans[(ans["mode"] == mode) & ((ans.lang == lang) | (lang == "ALL"))]
            u = un[(un["mode"] == mode) & ((un.lang == lang) | (lang == "ALL"))]
            if mode == "translate" and lang == "ALL":
                a, u = a[a.lang != "en"], u[u.lang != "en"]
            given = a[~a.refused]
            rows.append({"mode": mode, "lang": lang, "n_answerable": len(a),
                         "answered": round(1 - a.refused.mean(), 3),
                         "cited": round(given.cited.mean(), 3),
                         "cites_answer": round(given.cites_answer.mean(), 3),
                         "lang_ok": round(given.lang_ok.mean(), 3),
                         "n_unanswerable": len(u), "refused_unanswerable": round(u.refused.mean(), 3),
                         "sec_per_answer": round(df[(df["mode"] == mode) & ~df.refused].seconds.mean(), 1)})
    by = pd.DataFrame(rows)
    ref = df.groupby(["mode", "answerable", "reason"], dropna=False).size().rename("n").reset_index()
    return by, ref


if __name__ == "__main__":
    main()
