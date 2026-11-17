"""Generate the week 6 notebooks:
  week06_answers.ipynb - runs on the local project (src/, data/, results/)
  week06_colab.ipynb   - self-contained for Google Colab: writes the project code with %%writefile,
                         rebuilds the corpus and question sets, reruns the week 6 experiment (quick subset)
"""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

ANALYSIS = [
    md("## 1. Choosing the LLM (T26)\n\n"
       "**Qwen/Qwen3.5-4B** (Apache-2.0, not gated). It runs locally, so questions never leave the machine; the model "
       "card lists support for 201 languages and dialects; at 4B parameters (9.3 GB of weights) it fits a Colab T4 in float16. "
       "Thinking mode is switched off and decoding is greedy, so the same question always gives the same answer."),
    code("import generate\nprint(generate.__doc__)"),
    md("## 2. The grounded prompt (T27)\n\n"
       "The three passages from the week 5 search stage are numbered [1] to [3]. The model may use only those facts, "
       "must end every sentence with a citation, and must write plain language in the requested language. "
       "Titles, links and fetch dates are never written by the model: they are looked up from the citation number."),
    code("from generate import build_messages\n"
         "search = json.loads((ROOT / 'results/week6_search.json').read_text())\n"
         "example = search['M02-pl']\n"
         "for m in build_messages('Czy potrzebuję dowodu adresu, żeby zarejestrować się u lekarza rodzinnego?', example['results'], 'pl'):\n"
         "    print(f\"--- {m['role']} ---\\n{m['content'][:1500]}\\n\")"),
    md("## 3. The assistant end to end\n\n"
       "`src/assistant.py`: search (set-up F) > refusal rule 1 (reranker score below the threshold) > refusal rule 2 "
       "(yes/no check: do the passages answer the question?) > answer with citations > refusal rule 3 (model writes "
       "NO_ANSWER) > source cards > NHS 111/999 note when an NHS.uk page is cited. Loading the model takes a minute."),
    code("from assistant import Assistant\n"
         "bot = Assistant()\n\n"
         "def ask(q):\n"
         "    a = bot.ask(q)\n"
         "    print(f\"Q [{a['lang']}] {q}\\n  top reranker score {a['top_score']:.3f}  refused={a['refused']} {a['reason'] or ''}\\n\")\n"
         "    print(a['answer'])\n"
         "    for s in a['sources']:\n"
         "        print(f\"  [{s['n']}] {s['title']} > {s['heading']}\\n      {s['url']}  (fetched {s['fetched_at'][:10]})\")\n"
         "    print('\\n' + '=' * 80 + '\\n')\n\n"
         "ask('Can I be fined for taking my child on holiday during term time?')\n"
         "ask('Czy potrzebuję dowodu adresu, żeby zarejestrować się u lekarza rodzinnego?')\n"
         "ask('How do I renew my UK passport?')   # not in the corpus: should be refused"),
    md("## 4. Refusal rule 1: the relevance threshold (T28)\n\n"
       "50 unanswerable questions (`eval/unanswerable.csv`: 10 topics not in the 38 pages x 5 languages) were added to "
       "the 150 answerable ones. The threshold is 0.9 x the lowest top reranker score of any answerable question whose "
       "answer passage was retrieved, so no retrievable answer is refused at this step."),
    code("import numpy as np, matplotlib.pyplot as plt\n"
         "qs = pd.concat([pd.read_csv(ROOT / 'eval/queries.csv').assign(answerable=True),\n"
         "                pd.read_csv(ROOT / 'eval/unanswerable.csv').assign(answerable=False)])\n"
         "qs['top_score'] = [search[f'{r.qid}-{r.lang}']['results'][0]['score'] for r in qs.itertuples()]\n"
         "from assistant import THRESHOLD\n"
         "bins = np.logspace(-5, 0, 30)\n"
         "plt.figure(figsize=(8, 3.2))\n"
         "plt.hist(qs[qs.answerable].top_score, bins=bins, alpha=0.7, label='answerable (150)')\n"
         "plt.hist(qs[~qs.answerable].top_score, bins=bins, alpha=0.7, label='unanswerable (50)')\n"
         "plt.axvline(THRESHOLD, color='k', ls='--', label=f'threshold {THRESHOLD}')\n"
         "plt.xscale('log'); plt.xlabel('top reranker score (log scale)'); plt.ylabel('questions'); plt.legend(frameon=False)\n"
         "plt.tight_layout(); plt.show()\n"
         "qs.groupby('answerable').top_score.describe()[['min', '50%', 'max']].round(3)"),
    md("## 5. Refusal rule 2: why a separate yes/no check was added\n\n"
       "In the first run (v1) the model was told to write NO_ANSWER when the passages do not answer the question. "
       "For 17 of the 18 unanswerable questions that passed the threshold it did not: it explained in a sentence that "
       "the extracts do not cover the topic. The fix is a separate, short yes/no call before the answer is written."),
    code("ans = pd.read_csv(ROOT / 'results/week6_answers.csv')\n"
         "soft = ans[(~ans.answerable) & (ans['mode'] == 'direct') & (ans.reason != 'low relevance')]\n"
         "soft[['qid', 'lang', 'top_score', 'check_yes', 'answer']].head(8)"),
    code("ref = pd.read_csv(ROOT / 'results/week6_refusal.csv')\n"
         "ref[ref['mode'] == 'direct'].pivot_table(index=['answerable', 'reason'], columns='version', values='n', dropna=False).fillna(0).astype(int)"),
    md("## 6. Experiment: answer in the user's language - direct vs translate (T29)\n\n"
       "* **direct**: the LLM writes in the user's language.\n"
       "* **translate**: the LLM writes in English and NLLB translates each sentence (citations taken out and put back).\n\n"
       "The first translate run was invalid: the model kept writing in the question's language (94-100% of drafts) despite "
       "being told to write English, so the instruction is now repeated after the question. That run is kept in "
       "`results/week6_answers_v1.csv`.\n\n"
       "Automatic checks on each answer: **cited** = has valid [n] citations; **cites_answer** = a cited passage contains the "
       "question's verbatim answer phrase; **lang_ok** = written in the question's language; **refused_unanswerable** = share "
       "of the 50 unanswerable questions refused. These check form and grounding, not factual accuracy (scored by hand in week 7)."),
    code("by = pd.read_csv(ROOT / 'results/week6_by_mode.csv')\n"
         "by[by.version == 'final'].drop(columns='version').set_index(['mode', 'lang'])"),
    code("langs = ['pl', 'ro', 'ar', 'ur']\n"
         "t = by[(by.version == 'final') & by.lang.isin(langs)].pivot_table(index='lang', columns='mode', values='cites_answer').loc[langs]\n"
         "ax = t.plot.bar(figsize=(7, 3.2), rot=0)\n"
         "ax.set_ylim(0, 1); ax.set_ylabel('cites_answer'); ax.set_title('Answer cites the passage with the answer phrase')\n"
         "ax.legend(frameon=False); plt.tight_layout(); plt.show()"),
    md("### Same question, both modes\n\n"
       "Translate mode: NLLB turned *GP surgery* into *chirurgii lekarskiej* (surgery as in an operation) and "
       "*eviction* into *wydalenia* (expulsion). (Author's reading of the Polish, not native-checked.)"),
    code("for qid in ['M02', 'H06']:\n"
         "    for r in ans[(ans.qid == qid) & (ans.lang == 'pl')].itertuples():\n"
         "        if r.mode == 'translate':\n"
         "            print(f'{qid} English draft:\\n  {r.raw[:400]}\\n')\n"
         "        print(f'{qid} pl {r.mode}:\\n  {r.answer[:400]}\\n')"),
    md("## 7. What still goes wrong"),
    code("final_left = ans[(~ans.answerable) & (~ans.refused) & (ans.check_yes == True) & (ans['mode'] == 'direct')]\n"
         "print(len(final_left), 'unanswerable questions still answered (direct mode)')\n"
         "final_left[['qid', 'lang', 'question', 'answer']]"),
    md("## Findings\n\n"
       "* **No answerable question was refused** (0 of 150) by the threshold or the yes/no check.\n"
       "* **Refusal of unanswerable questions: 33 of 50 in v1, 43 of 50 with the yes/no check** (direct mode). "
       "All 7 remaining cases are answers that say in prose that the sources do not cover it; none invents an answer, "
       "but they are not clean refusals. Four are 'register a birth' in pl/ro/ar/ur, where GP-registration passages look related.\n"
       "* **Direct and translate are close** on the 120 non-English questions: 116 vs 112 cited, 101 vs 97 citing the answer "
       "passage - about one question per language. NLLB mistranslates key housing and health terms in otherwise correct answers.\n"
       "* The first translate run was invalid (the model ignored 'write in English'); fixed and rerun.\n"
       "* All answers were in the question's language in both modes (lingua).\n"
       "* Decision: use **direct** mode with refusal rules 1-3 (simpler, no NLLB term errors); week 7 hand-scores a sample of both.\n\n"
       "## Next (week 7)\n"
       "Hand-score answer accuracy and faithfulness with a rubric on a gold set, compare against a no-retrieval baseline, "
       "and use held-out questions to check the refusal threshold."),
]

LOCAL_HEAD = [
    md("# Week 6: Grounded answers with citations, refusal and answer language\n\n"
       "Runs on the project in `src/`. Experiment results are read from `results/` "
       "(regenerate with `python eval/evaluate_week6.py`)."),
    code("import sys, json, pathlib\nimport pandas as pd\n"
         "ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\nimport torch  # before faiss on macOS\n"
         "pd.set_option('display.max_colwidth', 120)"),
]

FILES = ["src/sources.py", "src/ingest.py", "src/chunk.py", "src/retrieval.py", "src/language.py",
         "src/translate.py", "src/rerank.py", "src/pipeline.py", "src/generate.py", "src/assistant.py",
         "eval/build_queries.py", "eval/build_unanswerable.py", "eval/evaluate_week6.py"]
COLAB_HEAD = [
    md("# Week 6: Grounded answers with citations, refusal and answer language (Colab version)\n\n"
       "Self-contained: choose **Runtime > Change runtime type > T4 GPU**, then **Runtime > Run all**.\n"
       "It writes the project code, collects the 38 official pages live, builds the 150 answerable and 50 unanswerable "
       "questions, calibrates the refusal threshold on all 200 and generates answers for a 10-topic subset "
       "(`--quick`, 50 questions in both modes). Remove `--quick` to run all 200 (much longer).\n\n"
       "It downloads four models (about 15 GB in total; Qwen3.5-4B alone is about 9 GB). Pages are fetched live, so "
       "numbers can differ slightly from the 11 Nov 2026 run. Text in sections 5-7 describes the full local run."),
    code("%pip install -q -U transformers sentence-transformers faiss-cpu rank-bm25 lingua-language-detector sentencepiece"),
    code("import os, sys\nfor d in ['src', 'eval', 'data/raw', 'data/processed', 'results']:\n    os.makedirs(d, exist_ok=True)"),
]
COLAB_HEAD += [code(f"%%writefile {f}\n" + (ROOT / f).read_text()) for f in FILES]
COLAB_HEAD += [
    code("!{sys.executable} src/ingest.py"),
    code("!{sys.executable} src/chunk.py"),
    code("!{sys.executable} eval/build_queries.py"),
    code("!{sys.executable} eval/build_unanswerable.py"),
    code("!{sys.executable} -u eval/evaluate_week6.py --quick 2>&1 | grep -v -i -E 'warn|unauthenticated|Loading weights|falling back'"),
    code("import json, pathlib\nimport pandas as pd\nROOT = pathlib.Path.cwd()\nsys.path.insert(0, str(ROOT / 'src'))\n"
         "import torch\npd.set_option('display.max_colwidth', 120)"),
]

meta = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
for name, head, extra in [("week06_answers.ipynb", LOCAL_HEAD, {}),
                          ("week06_colab.ipynb", COLAB_HEAD, {"colab": {"provenance": []}, "accelerator": "GPU"})]:
    cells = head + [(md if c.cell_type == "markdown" else code)(c.source) for c in ANALYSIS]
    nbf.write(nbf.v4.new_notebook(cells=cells, metadata={**meta, **extra}), pathlib.Path(__file__).with_name(name))
    print("wrote", name, len(cells), "cells")
