# Week 4 report: review of the week 4 notebook and retrieval results

## 1. Is the week 4 notebook aligned with the project?
**Yes, in direction.** `week4_demo.ipynb` does the right things for this stage of a RAG project: official
sources only (GOV.UK Content API, NHS.uk), a central dataset, multilingual embeddings
(`intfloat/multilingual-e5-base` with the correct `query:`/`passage:` prefixes), a FAISS index, and a
first multilingual test. Its listed next steps (NLLB translation, grounded generation with citations, a
refusal rule, an ungrounded baseline, ~50 pages / ~100 questions, ethics approval) match the synopsis.

**Gaps found and fixed this week:**

| # | Issue in the notebook | Evidence | Fix |
|---|---|---|---|
| 1 | Test label pointed at a page without the answer | "When is the deadline to apply for a primary school place?" labelled `apply-for-primary-school-place`, a 41-word council hand-off page. The deadline ("close on 15 January") is on `schools-admissions`. | Every test question now has a verbatim answer phrase checked against the gold page; new **ans@3** metric |
| 2 | Health under-represented | 2 health pages vs 6 schools and 6 housing | 14 health pages (12 NHS.uk + 2 GOV.UK); 38 pages total |
| 3 | NHS text included menus, related links; lead sentence lost | `<main>` text kept navigation; the "999 is for life-threatening emergencies..." sentence sits outside `<article>` | Article only, asides/nav removed, lead text added back |
| 4 | GOV.UK council pages missed fields | `need_to_know` not read | All text fields of each GOV.UK format read |
| 5 | Blind 150-word chunks | Cut mid-sentence and across sections; no heading context | Section-aware chunks with title + heading prefix |
| 6 | Date column mixed formats and was misleading | ISO dates for GOV.UK, "28 July 2025" for NHS; eviction page shows 2015 despite 2026 content | ISO dates throughout + `fetched_at` on every record |
| 7 | Only 10 test questions, one per language mix | Too few to compare set-ups | 30 questions x 5 languages = 150 queries |
| 8 | Code only in the notebook | Hard to reuse in weeks 5-9 | Pipeline in `src/`, notebook calls it |

## 2. Experiment
150 queries (`eval/queries.csv`), four set-ups, same corpus (`eval/evaluate_retrieval.py`).

| System | hit@1 | hit@3 | MRR@10 | ans@3 |
|---|---|---|---|---|
| BM25 (keyword) | 0.300 | 0.400 | 0.353 | 0.227 |
| e5, blind 150-word chunks (notebook set-up) | 0.660 | 0.867 | 0.773 | 0.633 |
| **e5, section chunks** | **0.813** | **0.960** | **0.893** | 0.667 |
| MiniLM, section chunks | 0.753 | 0.940 | 0.846 | **0.673** |

hit@3 by query language:

| System | en | pl | ro | ar | ur |
|---|---|---|---|---|---|
| BM25 | 0.97 | 0.30 | 0.13 | 0.30 | 0.30 |
| e5, blind chunks | 0.93 | 0.93 | 0.87 | 0.83 | 0.77 |
| e5, section chunks | 1.00 | 1.00 | 0.93 | 0.97 | 0.90 |
| MiniLM, section chunks | 0.97 | 0.93 | 0.97 | 0.93 | 0.90 |

## 3. Findings
1. **Multilingual dense retrieval is necessary.** BM25 works in English (hit@3 0.97) but collapses for
   other languages (0.13-0.30) because the words do not overlap. Both multilingual models stay at 0.90 or above.
2. **Section-aware chunking helps.** Same model, same corpus: hit@3 rose from 0.867 to 0.960 and pages
   missed fell from 20 to 6 of 150. hit@1 rose from 0.660 to 0.813.
3. **Finding the page is not the same as finding the answer.** With e5 on section chunks, 44 of 150
   queries found the right page in the top 3 but no chunk with the answer phrase. ans@3 is a strict
   lower bound (other wording can answer too), so this gap needs human relevance judgments before it is
   reported as a final figure. It is the main thing to improve before generation.
4. **Urdu is the weakest language** (ans@3 0.47 with e5), and 4 of the 6 page misses were Urdu or Arabic.
5. **Wrong-nation risk.** For "At what age can my child leave school?" the top chunk is the Scotland rule.
   Without a nation filter the assistant could give a correct answer for the wrong country.
6. **Two pages can answer the same question.** The 3 non-English misses for "Can my landlord evict me
   without giving a reason?" retrieved the GOV.UK eviction guide, which also covers the 1 May 2026
   changes. Single-gold-page labels undercount these; week 7 adds graded relevance.

**Caution on the numbers:** each language has 30 questions, so a difference of 0.03 is one question.
Differences between e5 and MiniLM are within that noise; the BM25 gap and the chunking gain are not.
Non-English questions were written by the author and still need a native-speaker check.

## 4. Decision for week 5
Keep `multilingual-e5-base` on section chunks as the main retriever. Next: nation tagging and an England
filter, a native-speaker check of the translations, translate-then-retrieve vs direct retrieval, and a
reranking step to close the page-vs-answer gap.
