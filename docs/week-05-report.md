# Week 5 report: language detection, translation, England filter and reranking

## Aim
Make the search stage handle the user's language properly and return the passage that actually answers
the question, so that answer generation in week 6 starts from the right evidence.

## Work done
| Step | What was built | File |
|---|---|---|
| 1 | **Language identification** with lingua (Apache-2.0), restricted to en/pl/ro/ar/ur | `src/language.py` |
| 2 | **Translation** to English with NLLB-200 distilled 600M (CC-BY-NC-4.0), sentence by sentence | `src/translate.py` |
| 3 | **Nation tagging**: each section tagged England or Scotland/Wales/Northern Ireland from its heading; short sections only merged within the same nation | `src/chunk.py` |
| 4 | **Reranking** of the top 20 candidates with the multilingual cross-encoder bge-reranker-v2-m3 (Apache-2.0) | `src/rerank.py` |
| 5 | **Search pipeline**: detect > translate > search with original and English question > reciprocal rank fusion (Cormack et al. 2009, k = 60) > England filter > rerank > top 3 with title, heading, URL and dates | `src/pipeline.py` |
| 6 | **Experiment**: six set-ups on the same 150 queries as week 4 | `eval/evaluate_week5.py` |
| 7 | **Translation review**: all 120 NLLB translations read and classified | `eval/translation_review.csv` |
| 8 | Notebooks (local and self-contained Colab) | `notebooks/week05_*.ipynb` |

## Results (150 queries: 30 questions x en/pl/ro/ar/ur)

| Set-up | hit@1 | hit@3 | MRR@10 | ans@3 |
|---|---|---|---|---|
| A direct (week 4 best) | 0.813 | 0.960 | 0.892 | 0.667 |
| B direct + England filter | 0.787 | 0.953 | 0.875 | 0.680 |
| C translated + filter | 0.833 | 0.973 | 0.907 | 0.747 |
| D fusion + filter | 0.833 | 0.980 | 0.906 | 0.713 |
| E direct + filter + rerank | 0.920 | 0.993 | 0.956 | 0.867 |
| **F fusion + filter + rerank** | **0.940** | **1.000** | **0.969** | **0.893** |

ans@3 by language:

| Set-up | en | pl | ro | ar | ur |
|---|---|---|---|---|---|
| A direct | 0.77 | 0.70 | 0.67 | 0.73 | 0.47 |
| C translated + filter | 0.80 | 0.70 | 0.70 | 0.80 | 0.73 |
| E direct + filter + rerank | 0.90 | 0.87 | 0.80 | 0.90 | 0.87 |
| F fusion + filter + rerank | 0.90 | 0.90 | 0.87 | 0.90 | 0.90 |

Other measurements:
- Language ID: 150 / 150 correct.
- Top result from another UK nation's rules: 4 queries with set-up A, 0 with any filtered set-up.
- Speed on a laptop CPU (Apple silicon): reranking 20 candidates about 0.7 s per query; NLLB translation
  of 120 questions 22 s. A full pipeline search took 0.7 s (English) to 4.4 s (first translated query).

## Findings
1. **Reranking is the biggest single gain.** With the filter on, ans@3 rose from 0.680 to 0.867. The
   week 4 problem (right page, wrong section) is mostly solved by reading the question and passage together.
2. **Translation helps, but NLLB makes real errors.** Of 120 translations, 11 change the meaning and 8 lose
   a key term (`eval/translation_review.csv`). Housing words are the weak point: "deposit" became
   "insurance money", "bail" or "warranty"; "evict" became "fire". Translating first still lifted Urdu
   from 0.47 to 0.73 because the English page vocabulary is matched more directly.
3. **Fusion makes translation errors survivable.** Set-up F searches with both the original and the
   translated question and reranks against the original question, so a bad translation cannot remove
   the right passage. Example: Arabic "Can my landlord evict me without a reason?" was translated as
   "Can the owner fire me...", and F still returned the Renters' Rights Act eviction rules first.
4. **NLLB drops sentences.** Before the fix, "I'm about to lose my home. Can the council help me?" came
   back as only "I'm about to lose my house." in Polish and Romanian. Translating sentence by sentence
   fixed this. This matters even more in week 6, when multi-sentence answers are translated back.
5. **The England filter removes the wrong-nation problem.** "At what age can my child leave school?" now
   returns the England rule ("last Friday in June if you'll be 16 by the end of the summer holidays").
   The filter slightly lowers hit@1 for set-up B (0.813 to 0.787) because page-level hit@1 had been
   rewarding the Scotland section of the correct page.

## Limitations
- The non-English test questions and the translation review were written by the author, not native
  speakers (task T22 still open).
- Language ID was tested on clean, full sentences. Real users may type short or mixed-language questions.
- ans@3 is strict (one verbatim answer phrase per question), so all figures are lower bounds.
- 30 questions per language: differences under about 0.07 (two questions) are not meaningful.
- NLLB's licence is non-commercial.

## Decision
Use **set-up F** (fusion + England filter + rerank) as the search stage for week 6.

## Next week (week 6)
Choose the LLM, write the grounded prompt (answer only from the retrieved passages, numbered citations,
plain language), add a refusal rule when nothing relevant is retrieved, and return the answer in the
user's language.
