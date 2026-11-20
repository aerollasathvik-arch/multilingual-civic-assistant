"""Generate the week 8 notebooks:
  week08_frontend.ipynb - runs on the local project: tests, what the page receives, uncited answers, interface
                          text, contrast, accessibility audit and screenshots (no models needed)
  week08_colab.ipynb    - self-contained for Google Colab: writes the project code and the web page with
                          %%writefile, rebuilds the corpus, runs the tests, times live answers on a T4 GPU (T35a)
                          and opens the web app inside Colab
"""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

INTRO = md(
    "## What week 8 adds\n\n"
    "```\n"
    "browser: web/index.html + app.js + style.css + i18n.json  (5 interface languages, right-to-left for ar/ur)\n"
    "   |  POST /api/ask {\"question\": ...}\n"
    "src/app.py  (Python http.server, 127.0.0.1 only, no outside requests, questions not logged)\n"
    "   |  Assistant.ask - the week 6 assistant, unchanged (direct mode, threshold 0.0052, yes/no check)\n"
    "   v\n"
    "answer + answer language + refusal flag + NHS 111/999 note + source cards (title, section, link, 2 dates)\n"
    "```\n\n"
    "* **Answer language follows the question**; the picker sets the interface language.\n"
    "* **`[n]` markers become links** to numbered source cards with *page last updated* and *copy taken on* dates.\n"
    "* **Every answer links to official pages**: an answer the model wrote without `[n]` markers lists the pages "
    "it was written from (section 3).\n"
    "* **Model text is inserted as text, never as HTML**, so a model output cannot add links or markup.")

TESTS = [
    md("## 1. Tests (no models needed)\n\n"
       "`tests/test_app.py` runs the real server with a stub assistant: page and static files, path traversal, "
       "status, answer shape, refusal, bad requests, server errors, loading state, uncited answers. "
       "`tests/test_web.py` checks translations, labels, page structure and colour contrast."),
    code("import subprocess\n"
         "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT,\n"
         "                   capture_output=True, text=True)\n"
         "lines = [l for l in r.stderr.splitlines() if l.endswith(('ok', 'FAIL', 'ERROR')) or l.startswith(('Ran', 'OK', 'FAILED'))]\n"
         "print('\\n'.join(lines))"),
]

CONTRAST = [
    md("## 5. Colour contrast (WCAG 2.2 1.4.3 and 1.4.11)\n\n"
       "Every colour pair used in `web/style.css`. Text needs 4.5:1; borders of controls and focus indicators 3:1."),
    code("sys.path.insert(0, str(ROOT / 'tests'))\n"
         "import test_web as tw\n"
         "rows = [{'kind': kind, 'foreground': fg, 'background': bg, 'used for': where,\n"
         "         'ratio': round(tw.contrast(tw.TOKENS[fg], tw.TOKENS[bg]), 2), 'needs': need}\n"
         "        for kind, pairs, need in (('text', tw.TEXT_PAIRS, 4.5), ('non-text', tw.UI_PAIRS, 3.0))\n"
         "        for fg, bg, where in pairs]\n"
         "contrast = pd.DataFrame(rows)\n"
         "contrast['pass'] = contrast.ratio >= contrast.needs\n"
         "contrast"),
]

LOCAL_ONLY = [
    md("## 2. What the page receives\n\n"
       "`app.public()` turns an assistant result into what the browser gets. Raw model output, passages and the "
       "refusal reason stay on the server. Here two recorded week 6 answers (real model output and real search "
       "results from `results/week6_*`) are passed through it - the same replay was used for the browser checks."),
    code("import ast, re, app\n"
         "tree = ast.parse((ROOT / 'src/assistant.py').read_text())\n"
         "HEALTH_NOTE = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)\n"
         "                   and getattr(n.targets[0], 'id', '') == 'HEALTH_NOTE')\n"
         "w6 = pd.read_csv(ROOT / 'results/week6_answers.csv').query(\"mode == 'direct'\")\n"
         "search6 = json.load(open(ROOT / 'results/week6_search.json'))\n\n"
         "def replay(qid, lang):\n"
         "    r = w6[(w6.qid == qid) & (w6.lang == lang)].iloc[0]\n"
         "    res = search6[f'{qid}-{lang}']['results']\n"
         "    cited = list(dict.fromkeys(int(n) for n in re.findall(r'\\[(\\d+)\\]', r.answer) if 1 <= int(n) <= len(res)))\n"
         "    sources = [{'n': n, **res[n - 1]} for n in cited]\n"
         "    note = HEALTH_NOTE[lang] if any(s['source'] == 'NHS.uk' for s in sources) else None\n"
         "    return app.public({'lang': lang, 'refused': bool(r.refused), 'answer': r.answer, 'health_note': note,\n"
         "                       'sources': sources, 'passages': res})\n\n"
         "print(json.dumps(replay('M01', 'ar'), ensure_ascii=False, indent=1))"),
    md("## 3. Answers without citation markers\n\n"
       "About 4% of the answers given carry no `[n]` marker (6 of 150 in week 6, 10 of 248 held-out in week 7). Without a fallback the page would show such an "
       "answer with no link to any official page, which `docs/ethics-notes.md` rules out. The page now lists the "
       "pages the answer was written from (`cited: false`)."),
    code("answered = w6[~w6.refused & w6.answerable]\n"
         "t = answered.groupby('lang').agg(answers=('cited', 'size'), with_markers=('cited', 'sum'))\n"
         "t['without_markers'] = t.answers - t.with_markers\n"
         "t.loc['ALL'] = t.sum()\n"
         "t['share_without'] = (t.without_markers / t.answers).round(3)\n"
         "t.loc[['en', 'pl', 'ro', 'ar', 'ur', 'ALL']]"),
    code("u = replay('M01', 'en')\n"
         "print('cited:', u['cited'])\n"
         "print(u['answer'][:300], '...')\n"
         "pd.DataFrame(u['sources'])[['source', 'title', 'heading', 'url']]"),
    md("## 4. Interface text in five languages\n\n"
       "39 strings per language in `web/i18n.json`, written by the author and added to the native-speaker check "
       "(T22). The 111/999 line is the same text as `HEALTH_NOTE` in `src/assistant.py` (a test checks this); the "
       "example questions are M01, H02 and S06 from `eval/queries.csv`."),
    code("i18n = json.load(open(ROOT / 'web/i18n.json', encoding='utf-8'))\n"
         "keys = ['name', 'title', 'notice', 'q_hint', 'searching', 'refused_heading', 'searched_intro']\n"
         "print({lang: len(i18n[lang]) for lang in i18n['order']}, 'strings; right-to-left:', i18n['rtl'])\n"
         "pd.DataFrame({lang: [i18n[lang][k] for k in keys] for lang in i18n['order']}, index=keys)"),
]

AUDIT = [
    md("## 6. Accessibility audit in the browser (T35)\n\n"
       "axe-core 4.10.2 with the WCAG 2.0, 2.1 and 2.2 A/AA rules plus best practice, run in Chrome in 10 page "
       "states (the server answering from recorded week 6 outputs). `no_horizontal_scroll` at 320 px is the "
       "reflow check (= 400% zoom on a 1280 px screen). Manual checks still to do: VoiceOver/NVDA and real phones "
       "(`docs/accessibility.md`)."),
    code("pd.read_json(ROOT / 'docs/week08-figures/axe-results.json').drop(columns='detail')"),
    md("## 7. Screenshots\n\n"
       "English cited answer (desktop), Arabic answer with the NHS 111/999 box (phone), Urdu answer (phone) and the "
       "refusal view in the Polish interface (phone)."),
    code("from IPython.display import Image, display\n"
         "for name, width in [('3-en-cited-desktop', 640), ('4-ar-answer-phone', 300), ('5-ur-answer-phone', 300),\n"
         "                    ('6-pl-refusal-phone', 300)]:\n"
         "    print(name)\n"
         "    display(Image(filename=str(ROOT / f'docs/week08-figures/{name}.png'), width=width))"),
]

FINDINGS = md(
    "## Findings\n\n"
    "1. **The page works in all five languages.** The answer block takes the answer's own language and direction, "
    "so an Arabic question in the English interface gets a right-to-left Arabic answer; English titles and links "
    "inside Arabic and Urdu pages stay left-to-right.\n"
    "2. **Accessibility (automated):** 0 axe violations in 10 states, lowest text contrast 6.54:1, no horizontal "
    "scroll at 320 px. Screen readers and real phones are still to check.\n"
    "3. **Uncited answers** (about 4%: 6/150 in week 6, 10/248 in week 7) now still link to official pages.\n"
    "4. **Live answers on the laptop were too slow this week.** Another virtual machine was using about 9 of the 15 "
    "CPU cores; NLLB on the CPU took over 3 minutes per sentence (0.3 s on the Apple GPU, now used by the web app) "
    "and Qwen did not produce 10 tokens in 150 s. Week 6 on the same laptop: about 19 s per answer. The Colab "
    "notebook times live answers on a T4 GPU (T35a); time the study machine again before week 9 sessions.\n\n"
    "Full write-up: `docs/week-08-report.md`; accessibility details: `docs/accessibility.md`.")

LOCAL_HEAD = [
    md("# Week 8: Accessible web front-end\n\n"
       "Runs on the local project (`src/app.py`, `web/`, `tests/`). No models are loaded: the server is tested with a "
       "stub assistant, and recorded week 6 answers are replayed through it.\n\n"
       "Start the real app with `python src/app.py` and open http://127.0.0.1:8000 (models load in about 1.5 min)."),
    code("import sys, json, pathlib\nimport pandas as pd\n"
         "ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "pd.set_option('display.max_colwidth', 120)"),
    INTRO,
]

SRC = ["src/sources.py", "src/ingest.py", "src/chunk.py", "src/retrieval.py", "src/language.py", "src/translate.py",
       "src/rerank.py", "src/pipeline.py", "src/generate.py", "src/assistant.py", "src/app.py",
       "eval/build_queries.py", "web/index.html", "web/app.js", "web/style.css", "web/i18n.json",
       "tests/test_app.py", "tests/test_web.py"]

COLAB_HEAD = [
    md("# Week 8: Accessible web front-end (Colab version)\n\n"
       "Self-contained: choose **Runtime > Change runtime type > T4 GPU**, then **Runtime > Run all**.\n"
       "It writes the project code and the web page, collects the 38 official pages live, runs the tests, times "
       "live answers on the GPU (task T35a) and opens the web app in a new browser tab through Colab.\n\n"
       "Downloads four models (about 15 GB). Pages are fetched live, so answers can differ slightly from the local run.\n\n"
       "**Ethics note:** in Colab the questions are processed on a Google virtual machine. Use this for development "
       "and timing only, not with study participants unless they have been told (`docs/ethics-notes.md`)."),
    code("%pip install -q -U transformers sentence-transformers faiss-cpu rank-bm25 lingua-language-detector sentencepiece"),
    code("import os, sys\nfor d in ['src', 'eval', 'web', 'tests', 'data/raw', 'data/processed', 'results']:\n"
         "    os.makedirs(d, exist_ok=True)"),
]
COLAB_HEAD += [code(f"%%writefile {f}\n" + (ROOT / f).read_text(encoding="utf-8")) for f in SRC]
COLAB_HEAD += [
    code("!{sys.executable} src/ingest.py"),
    code("!{sys.executable} src/chunk.py"),
    code("!{sys.executable} eval/build_queries.py"),
    code("import json, pathlib\nimport pandas as pd\nROOT = pathlib.Path.cwd()\nsys.path.insert(0, str(ROOT / 'src'))\n"
         "import torch\npd.set_option('display.max_colwidth', 120)\nprint('GPU:', torch.cuda.is_available())"),
    INTRO,
]

LIVE = [
    md("## 2. Live answers and timing on the GPU (T35a)\n\n"
       "The week 6 assistant, unchanged. Three topics (M01 GP registration, H02 rent increases, S06 free school "
       "meals) in all five languages, plus two questions the sources do not cover. Week 6 on the laptop: about 19 s "
       "per answer that was not refused."),
    code("import time\nfrom assistant import Assistant\n"
         "t0 = time.time(); bot = Assistant(); print(f'models loaded in {time.time() - t0:.0f} s')"),
    code("q = pd.read_csv('eval/queries.csv')\n"
         "jobs = [(r.qid, r.lang, r.question) for r in q[q.qid.isin(['M01', 'H02', 'S06'])].itertuples()]\n"
         "jobs += [('X1', 'en', 'How do I renew my UK passport?'), ('X2', 'ur', 'میں برطانوی پاسپورٹ کی تجدید کیسے کروں؟')]\n"
         "rows = []\n"
         "for qid, lang, question in jobs:\n"
         "    t0 = time.time(); a = bot.ask(question)\n"
         "    rows.append({'qid': qid, 'lang': lang, 'detected': a['lang'], 'seconds': round(time.time() - t0, 1),\n"
         "                 'refused': a['refused'], 'sources': len(a['sources']), 'answer': a['answer'][:160]})\n"
         "    print(qid, lang, rows[-1]['seconds'], 's', 'refused' if a['refused'] else '')\n"
         "live = pd.DataFrame(rows)\n"
         "print('median seconds, answered:', live[~live.refused].seconds.median(),\n"
         "      '| refused:', live[live.refused].seconds.median())\n"
         "live"),
    md("## 3. Open the web app\n\n"
       "The server runs inside this notebook on port 8000 and reuses the models loaded above. Colab shows a link that "
       "only you can open (it goes through your Google login, not the open internet). Try the language picker and an "
       "Arabic or Urdu question. Stop it with the last cell."),
    code("import threading, app\n"
         "backend = app.Backend(lambda: bot).start()\n"
         "server = app.make_server(backend, host='127.0.0.1', port=8000)\n"
         "threading.Thread(target=server.serve_forever, daemon=True).start()\n"
         "from google.colab import output\n"
         "output.serve_kernel_port_as_window(8000, path='/?lang=ar')"),
    code("server.shutdown(); server.server_close(); print('stopped')"),
]

meta = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
LOCAL = LOCAL_HEAD + TESTS + LOCAL_ONLY + CONTRAST + AUDIT + [FINDINGS]
COLAB = COLAB_HEAD + TESTS + LIVE + [md(CONTRAST[0].source.replace("## 5.", "## 4.")), CONTRAST[1]] + [FINDINGS]
for name, cells, extra in [("week08_frontend.ipynb", LOCAL, {}),
                           ("week08_colab.ipynb", COLAB, {"colab": {"provenance": []}, "accelerator": "GPU"})]:
    out = [(md if c.cell_type == "markdown" else code)(c.source) for c in cells]
    nbf.write(nbf.v4.new_notebook(cells=out, metadata={**meta, **extra}), pathlib.Path(__file__).with_name(name))
    print("wrote", name, len(out), "cells")
