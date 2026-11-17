"""Generate the week 7 notebooks:
  week07_evaluation.ipynb - runs on the local project (src/, eval/, results/)
  week07_colab.ipynb      - self-contained for Google Colab: writes the project code with %%writefile,
                            rebuilds the corpus and gold set, reruns the week 7 experiment (quick subset)
"""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

FINDINGS = (ROOT / "notebooks/week07_findings.md").read_text()

ANALYSIS = [
    md("## 1. The gold set (T31)\n\n"
       "100 question topics, each in 5 languages:\n\n"
       "* **calibration** (40): the week 4-6 questions. The week 6 refusal threshold was set on these.\n"
       "* **held-out** (60): new this week, never used to tune anything - 50 answerable, 10 unanswerable.\n\n"
       "Every answerable topic has a gold page, an evidence phrase copied verbatim from that page "
       "(`eval/build_gold_set.py` stops if one is missing) and a short reference answer for hand scoring."),
    code("gold = pd.read_csv(ROOT / 'eval/gold_set.csv')\n"
         "print(gold.groupby(['split', 'answerable']).size().to_string())\n"
         "gold[gold.split == 'heldout'][['qid', 'question_en', 'evidence', 'reference_answer']].head(10)"),
    code("pd.read_csv(ROOT / 'eval/heldout_unanswerable.csv').query(\"lang == 'en'\")[['qid', 'question']]"),
    md("## 2. Does the search stage hold up on new questions?\n\n"
       "Same measures as week 5 on the 250 held-out answerable questions: **hit@3** (gold page in the top 3) and "
       "**ans@3** (a top-3 passage contains the evidence phrase). Week 5 on the calibration questions: hit@3 1.000, ans@3 0.893."),
    code("ret = pd.read_csv(ROOT / 'results/week7_retrieval.csv')\n"
         "t = ret.groupby('lang')[['hit@3', 'ans@3']].mean().loc[['en', 'pl', 'ro', 'ar', 'ur']]\n"
         "t.loc['ALL'] = ret[['hit@3', 'ans@3']].mean()\n"
         "t.round(3).T"),
    md("## 3. Refusal rules on held-out questions (T28 re-checked)\n\n"
       "The week 6 assistant is used exactly as it was: threshold 0.0052 on the top reranker score, the yes/no check, "
       "and NO_ANSWER. Nothing was re-tuned."),
    code("import numpy as np, matplotlib.pyplot as plt\n"
         "from assistant import THRESHOLD\n"
         "ans = pd.read_csv(ROOT / 'results/week7_answers.csv')\n"
         "g = ans[ans.condition == 'grounded']\n"
         "bins = np.logspace(-5, 0, 30)\n"
         "plt.figure(figsize=(8, 3.2))\n"
         "plt.hist(g[g.answerable].top_score, bins=bins, alpha=0.7, label='held-out answerable (250)')\n"
         "plt.hist(g[~g.answerable].top_score, bins=bins, alpha=0.7, label='held-out unanswerable (50)')\n"
         "plt.axvline(THRESHOLD, color='k', ls='--', label=f'week 6 threshold {THRESHOLD}')\n"
         "plt.xscale('log'); plt.xlabel('top reranker score (log scale)'); plt.ylabel('questions'); plt.legend(frameon=False)\n"
         "plt.tight_layout(); plt.show()"),
    code("pd.read_csv(ROOT / 'results/week7_refusal.csv')"),
    code("print('answerable questions refused:')\n"
         "g[g.answerable & g.refused][['qid', 'lang', 'question', 'top_score', 'reason']]"),
    code("print('unanswerable questions answered:')\n"
         "g[~g.answerable & ~g.refused][['qid', 'lang', 'top_score', 'answer']]"),
    md("## 4. The ungrounded baseline (T30)\n\n"
       "Same model (Qwen3.5-4B), same audience and plain-language rules, same language instruction - but no retrieved "
       "passages and no citations. It answers from what the model learned in training."),
    code("from generate import baseline_messages\n"
         "for m in baseline_messages('How quickly must my landlord put my deposit in a protection scheme?', 'en'):\n"
         "    print(f\"--- {m['role']} ---\\n{m['content']}\\n\")"),
    code("def compare(qid, lang='en'):\n"
         "    for r in ans[(ans.qid == qid) & (ans.lang == lang)].itertuples():\n"
         "        print(f'[{r.condition}] {r.question}\\n{r.answer}\\n')\n"
         "    ref = gold[gold.qid == qid].reference_answer.iloc[0]\n"
         "    print(f'REFERENCE: {ref}\\n' + '=' * 80)\n\n"
         "for q in ['H12', 'M25', 'H25', 'U11', 'U17']:\n"
         "    compare(q)"),
    md("## 5. Automatic measures, grounded vs ungrounded\n\n"
       "These check form, not truth: accuracy and unsupported claims are scored by hand (section 6). "
       "Readability: Flesch Reading Ease (higher = easier) and Flesch-Kincaid grade for English answers only; "
       "words per sentence for every language."),
    code("by = pd.read_csv(ROOT / 'results/week7_by_condition.csv')\n"
         "by.set_index(['condition', 'lang'])"),
    md("## 6. Hand scoring: rubric and blinded sheet (T32)\n\n"
       "`docs/scoring-rubric.md` defines four scores: accuracy (correct / partly correct / incorrect / refused), "
       "unsupported claim (yes / no), citations (all correct / some wrong / none / n/a) and refusal "
       "(correct refusal / answered anyway / n/a). `eval/scoring_sheet.xlsx` has 30 items (15 held-out English topics x "
       "2 conditions), shuffled with the condition hidden, with a tab for each of two raters. Agreement is reported "
       "as percentage agreement and Cohen's kappa. The key is in `eval/scoring_key.csv`."),
    code("sheet = pd.read_excel(ROOT / 'eval/scoring_sheet.xlsx', sheet_name='rater 1')\n"
         "sheet[['item', 'question', 'reference_answer', 'answer_to_score']].head(6)"),
    md(FINDINGS),
]

LOCAL_HEAD = [
    md("# Week 7: Gold set, ungrounded baseline, scoring rubric and held-out checks\n\n"
       "Runs on the project in `src/` and `eval/`. Results are read from `results/` "
       "(regenerate with `python eval/build_gold_set.py` and `python eval/evaluate_week7.py`)."),
    code("import sys, json, pathlib\nimport pandas as pd\n"
         "ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\nimport torch  # before faiss on macOS\n"
         "pd.set_option('display.max_colwidth', 120)"),
]

FILES = ["src/sources.py", "src/ingest.py", "src/chunk.py", "src/retrieval.py", "src/language.py",
         "src/translate.py", "src/rerank.py", "src/pipeline.py", "src/generate.py", "src/assistant.py",
         "eval/build_queries.py", "eval/build_unanswerable.py", "eval/build_gold_set.py", "eval/evaluate_week7.py"]
COLAB_HEAD = [
    md("# Week 7: Gold set, ungrounded baseline, scoring rubric and held-out checks (Colab version)\n\n"
       "Self-contained: choose **Runtime > Change runtime type > T4 GPU**, then **Runtime > Run all**.\n"
       "It writes the project code, collects the 38 official pages live, builds the gold set (checking every evidence "
       "phrase against the live pages), searches all 300 held-out questions and generates grounded and ungrounded "
       "answers for an 8-topic subset (`--quick`). Remove `--quick` to answer all 300 (several hours).\n\n"
       "Downloads four models (about 15 GB). Pages are fetched live, so numbers can differ slightly from the "
       "16 Nov 2026 run, and the build stops if a page no longer contains an evidence phrase. Sections 3-7 describe "
       "the full local run; the quick run does not write the scoring sheet."),
    code("%pip install -q -U transformers sentence-transformers faiss-cpu rank-bm25 lingua-language-detector sentencepiece textstat openpyxl"),
    code("import os, sys\nfor d in ['src', 'eval', 'data/raw', 'data/processed', 'results']:\n    os.makedirs(d, exist_ok=True)"),
]
COLAB_HEAD += [code(f"%%writefile {f}\n" + (ROOT / f).read_text()) for f in FILES]
COLAB_HEAD += [
    code("!{sys.executable} src/ingest.py"),
    code("!{sys.executable} src/chunk.py"),
    code("!{sys.executable} eval/build_queries.py"),
    code("!{sys.executable} eval/build_unanswerable.py"),
    code("!{sys.executable} eval/build_gold_set.py"),
    code("!{sys.executable} -u eval/evaluate_week7.py --quick 2>&1 | grep -v -i -E 'warn|unauthenticated|Loading weights|falling back'"),
    code("import json, pathlib\nimport pandas as pd\nROOT = pathlib.Path.cwd()\nsys.path.insert(0, str(ROOT / 'src'))\n"
         "import torch\npd.set_option('display.max_colwidth', 120)"),
]

meta = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
for name, head, extra, cells in [
        ("week07_evaluation.ipynb", LOCAL_HEAD, {}, ANALYSIS),
        # the quick Colab run writes no scoring sheet, so its section 6 cells are left out
        ("week07_colab.ipynb", COLAB_HEAD, {"colab": {"provenance": []}, "accelerator": "GPU"},
         [c for c in ANALYSIS if "scoring_sheet.xlsx', sheet_name" not in c.source])]:
    out = head + [(md if c.cell_type == "markdown" else code)(c.source) for c in cells]
    nbf.write(nbf.v4.new_notebook(cells=out, metadata={**meta, **extra}), pathlib.Path(__file__).with_name(name))
    print("wrote", name, len(out), "cells")
