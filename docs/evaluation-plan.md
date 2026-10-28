# Evaluation plan (Week 1, updated Week 4)

## Stage 1 - Retrieval (done in week 4)
Test set: `eval/queries.csv`, 30 questions (10 per domain) x 5 languages = 150 queries.
Each question has a gold page and a short **answer phrase copied verbatim from that page**
(`eval/build_queries.py` refuses to run if any phrase is missing).

| Metric | Meaning |
|---|---|
| hit@1, hit@3 | Gold page is the first / in the top three distinct pages |
| MRR@10 | 1 / rank of the gold page among the top ten pages |
| ans@3 | At least one of the top three chunks contains the answer phrase. Strict lower bound: other wording can also answer. |

Why ans@3 was added: the original notebook marked "When is the deadline to apply for a primary school
place?" as correct when it found `apply-for-primary-school-place`, but that page has no deadline (it is a
council hand-off page). The deadline ("close on 15 January") is on `schools-admissions`.

## Stage 2 - Answers (weeks 6-9)
Same LLM, two conditions: **grounded** (retrieved passages + citation instructions) and **ungrounded**
(question only). Gold set grows to ~100 questions with reference answers, including unanswerable and
out-of-scope ones.

| Metric | How |
|---|---|
| Factual accuracy | Each answer scored correct / partly correct / incorrect against the reference answer |
| Hallucination rate | Share of answers containing a claim not supported by the cited source (grounded) or by the official page (ungrounded) |
| Citation correctness | Share of citations whose source actually supports the sentence it is attached to |
| Refusal quality | Correct refusals on unanswerable questions; wrong refusals on answerable ones |
| Readability | Readability score of the English answer before translation (exact formula chosen in week 6) |

A second rater scores a random sample to report agreement. Automated judges (e.g. RAGAS, Es et al. 2023)
may be used only alongside human scoring, not instead of it.

## Stage 3 - User study (week 9, after ethics approval)
Small group of adults whose first language is one of the target languages. Task-based: find an answer
with the assistant, then answer comprehension questions and a short trust and usability questionnaire.
Results are reported as descriptive statistics and themes, not as general claims.
