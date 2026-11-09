"""Generate the week 5 notebooks:
  week05_pipeline.ipynb - runs on the local project (src/, data/, results/)
  week05_colab.ipynb    - self-contained for Google Colab: writes the project code with %%writefile,
                          rebuilds the corpus and test set, reruns the week 5 experiment
"""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

ANALYSIS = [
    md("## 1. Language identification\n\n"
       "`src/language.py` uses lingua restricted to the five project languages. Arabic and Urdu share a script, "
       "so restricting the set matters most for those two."),
    code("from language import detect\n"
         "for q in ['How do I register with a GP surgery?', 'Jak zarejestrować się u lekarza rodzinnego?',\n"
         "          'Cum mă înregistrez la un medic de familie?', 'كيف أسجل لدى طبيب عام؟', 'میں جی پی کے پاس رجسٹریشن کیسے کرواؤں؟']:\n"
         "    print(detect(q), '|', q)\n"
         "pd.read_csv(ROOT / 'results/week5_language_id.csv')"),
    md("## 2. Translation to English (NLLB-200)\n\n"
       "`src/translate.py` splits text into sentences first: NLLB is trained on single sentences and silently "
       "dropped the second sentence of two-sentence questions before this fix."),
    code("tr = pd.read_csv(ROOT / 'eval/translations_nllb.csv')\n"
         "tr[tr.qid.isin(['M01', 'H06'])][['qid', 'lang', 'question', 'nllb_english']]"),
    md("Manual review of all 120 translations (by the author, not a native speaker): **11 change the meaning** "
       "and **8 lose a key term**. Most errors are in housing vocabulary (deposit, evict)."),
    code("review = pd.read_csv(ROOT / 'eval/translation_review.csv')\n"
         "print(review.issue.value_counts().to_string())\n"
         "review[review.issue == 'meaning changed'][['qid', 'lang', 'nllb_english', 'note']]"),
    md("## 3. England filter\n\n"
       "`src/chunk.py` tags each section by the UK nation named in its heading. Six chunks are for Scotland, Wales "
       "or Northern Ireland; search keeps England / UK-wide chunks only."),
    code("chunks = pd.read_csv(ROOT / 'data/processed/chunks.csv')\n"
         "print(chunks.nation.value_counts().to_string())\n"
         "chunks[chunks.nation != 'england'][['title', 'heading', 'nation']]"),
    md("## 4. Full search pipeline\n\n"
       "`src/pipeline.py`: detect language > translate > search with both the original and the English question > "
       "fuse the two lists (reciprocal rank fusion) > keep England chunks > rerank the top 20 with "
       "bge-reranker-v2-m3 > top 3 passages."),
    code("from pipeline import SearchPipeline\n"
         "pipe = SearchPipeline()\n\n"
         "def show(q):\n"
         "    r = pipe.search(q)\n"
         "    print(f\"Q [{r['lang']}] {q}\\n   NLLB English: {r['english_query']}\")\n"
         "    for x in r['results']:\n"
         "        print(f\"   - {x['title']} > {x['heading'][:60]}  [{x['nation']}]\\n     {x['text'][:140]}...\")\n"
         "    print()\n\n"
         "show('At what age can my child leave school?')             # week 4 returned the Scotland rule first\n"
         "show('هل يمكن للمالك أن يطردني دون إبداء سبب؟')              # Arabic: NLLB says 'fire me', search still finds eviction rules\n"
         "show('میرا گھر چھننے والا ہے، کیا کونسل میری مدد کر سکتی ہے؟')  # Urdu: NLLB says 'collapse', search still finds homelessness help"),
    md("## 5. Experiment: six set-ups on the 150-query test set\n\n"
       "Same metrics as week 4. **ans@3** = a top-3 chunk contains the verbatim answer phrase. "
       "Regenerate with `python eval/evaluate_week5.py`."),
    code("res = pd.read_csv(ROOT / 'results/week5_by_lang.csv')\n"
         "res[res.lang == 'ALL'].drop(columns='lang').set_index('system')"),
    code("per_q = pd.read_csv(ROOT / 'results/week5_per_query.csv')\n"
         "langs = ['en', 'pl', 'ro', 'ar', 'ur']\n"
         "per_q.pivot_table(index='system', columns='lang', values='ans@3').round(2)[langs]"),
    code("import matplotlib.pyplot as plt\n"
         "show_sys = ['A direct', 'C translated+filter', 'E direct+filter+rerank', 'F fusion+filter+rerank']\n"
         "t = per_q[per_q.system.isin(show_sys)].pivot_table(index='lang', columns='system', values='ans@3').loc[langs, show_sys]\n"
         "ax = t.plot.bar(figsize=(8, 3.5), rot=0, width=0.8)\n"
         "ax.set_ylabel('ans@3'); ax.set_ylim(0, 1); ax.set_title('Answer-bearing chunk in top 3, by query language')\n"
         "ax.legend(frameon=False, ncol=2, fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.12))\n"
         "plt.tight_layout(); plt.show()"),
    code("print('queries whose top chunk is for another UK nation:')\n"
         "per_q[per_q.top1_nation != 'england'].groupby('system').size()"),
    md("## Findings\n\n"
       "* Language ID was correct for all 150 test questions (clean, full sentences; real users may mix languages).\n"
       "* Translating first helps Urdu most (ans@3 0.47 to 0.73) even though 19 of 120 translations have errors.\n"
       "* Reranking gives the largest single gain (0.68 to 0.87 with the filter).\n"
       "* The chosen set-up, **F fusion+filter+rerank**, reaches hit@3 1.00 and ans@3 0.89, with all five languages at 0.87 or above.\n"
       "* No top result comes from another UK nation's rules once the filter is on.\n\n"
       "## Next (week 6)\n"
       "Give the top passages to an LLM, answer only from them with numbered citations, refuse when nothing relevant is found, "
       "and return the answer in the user's language."),
]

LOCAL_HEAD = [
    md("# Week 5: Language detection, translation, England filter and reranking\n\n"
       "Runs on the project pipeline in `src/`. The week 5 experiment results are read from `results/`."),
    code("import sys, pathlib\nimport pandas as pd\n"
         "ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\npd.set_option('display.max_colwidth', 90)"),
]

FILES = ["src/sources.py", "src/ingest.py", "src/chunk.py", "src/retrieval.py", "src/language.py",
         "src/translate.py", "src/rerank.py", "src/pipeline.py", "eval/build_queries.py", "eval/evaluate_week5.py"]
COLAB_HEAD = [
    md("# Week 5: Language detection, translation, England filter and reranking (Colab version)\n\n"
       "Self-contained: choose **Runtime > Change runtime type > T4 GPU** (recommended), then **Runtime > Run all**.\n"
       "It writes the project code, collects the 38 official pages live, builds the 150-question test set and reruns the "
       "week 5 experiment. It downloads three models (about 5 GB in total), so the first run takes roughly 10 minutes on a GPU.\n\n"
       "Pages are fetched live, so numbers can differ slightly from the 2 Nov 2026 run if a page has changed. "
       "The manual translation review (section 2) refers to the 2 Nov translations."),
    code("%pip install -q sentence-transformers faiss-cpu rank-bm25 lingua-language-detector sentencepiece"),
    code("import os, sys\nfor d in ['src', 'eval', 'data/raw', 'data/processed', 'results']:\n    os.makedirs(d, exist_ok=True)"),
]
COLAB_HEAD += [code(f"%%writefile {f}\n" + (ROOT / f).read_text()) for f in FILES]
COLAB_HEAD += [
    code("%%writefile eval/translation_review.csv\n" + (ROOT / "eval/translation_review.csv").read_text()),
    code("!{sys.executable} src/ingest.py"),
    code("!{sys.executable} src/chunk.py"),
    code("!{sys.executable} eval/build_queries.py"),
    code("!{sys.executable} eval/evaluate_week5.py 2>&1 | grep -v -i -E 'warn|unauthenticated|Loading weights'"),
    code("import pathlib\nimport pandas as pd\nROOT = pathlib.Path.cwd()\nsys.path.insert(0, str(ROOT / 'src'))\n"
         "pd.set_option('display.max_colwidth', 90)"),
]

meta = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
for name, head, extra in [("week05_pipeline.ipynb", LOCAL_HEAD, {}),
                          ("week05_colab.ipynb", COLAB_HEAD, {"colab": {"provenance": []}, "accelerator": "GPU"})]:
    cells = head + [(md if c.cell_type == "markdown" else code)(c.source) for c in ANALYSIS]
    nbf.write(nbf.v4.new_notebook(cells=cells, metadata={**meta, **extra}), pathlib.Path(__file__).with_name(name))
    print("wrote", name, len(cells), "cells")
