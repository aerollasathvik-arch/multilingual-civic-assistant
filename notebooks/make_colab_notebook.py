"""Generate notebooks/week04_colab.ipynb: a self-contained copy of the week 4 work for Google Colab.

It writes the project's own src/ and eval/ files into the Colab runtime with %%writefile,
re-crawls the official pages, rebuilds the test set and reruns the experiment, so nothing
needs uploading. The analysis cells are the same as notebooks/week04_retrieval.ipynb.
"""
import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ["src/sources.py", "src/ingest.py", "src/chunk.py", "src/retrieval.py",
         "eval/build_queries.py", "eval/evaluate_retrieval.py"]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("# Week 4: Multilingual retrieval over official UK guidance (Colab version)\n\n"
       "Self-contained: run **Runtime > Run all**. It installs two libraries, writes the project code, "
       "collects the 38 official pages live from GOV.UK and NHS.uk, builds the 150-question test set and "
       "reruns the week 4 experiment. A CPU runtime is enough (about 3-5 minutes; a GPU runtime is faster).\n\n"
       "Because the pages are fetched live, numbers can differ slightly from the 28 Oct 2026 run if a page has changed since."),
    code("%pip install -q sentence-transformers faiss-cpu rank-bm25"),
    md("## Project code\nThe same files as the project's `src/` and `eval/` folders."),
    code("import os, sys\nfor d in ['src', 'eval', 'data/raw', 'data/processed', 'results']:\n    os.makedirs(d, exist_ok=True)"),
]
for f in FILES:
    cells.append(code(f"%%writefile {f}\n" + (ROOT / f).read_text()))
cells += [
    md("## Build the corpus, chunks and test set"),
    code("!{sys.executable} src/ingest.py"),
    code("!{sys.executable} src/chunk.py"),
    code("!{sys.executable} eval/build_queries.py"),
    md("## Run the retrieval experiment (4 set-ups x 150 queries)"),
    code("!{sys.executable} eval/evaluate_retrieval.py 2>&1 | grep -v -i -E 'warn|unauthenticated|tqdm'"),
]

# reuse the analysis cells from the local week 4 notebook (everything after the setup cell)
local = nbf.read(ROOT / "notebooks/week04_retrieval.ipynb", as_version=4)
analysis = [(md if c.cell_type == "markdown" else code)(c.source) for c in local.cells[2:]
            if "chunk.main()" not in c.source and "RECRAWL" not in c.source
            and not c.source.startswith("## 2. Section")]
cells.append(code("import sys, json, pathlib\nimport pandas as pd\nROOT = pathlib.Path.cwd()\n"
                  "sys.path.insert(0, str(ROOT / 'src'))\npd.set_option('display.max_colwidth', 90)\n"
                  "pages = pd.DataFrame([json.loads(l) for l in open(ROOT / 'data/processed/pages.jsonl')])\n"
                  "chunks = pd.read_csv(ROOT / 'data/processed/chunks.csv')\n"
                  "pages.groupby(['source', 'domain']).agg(pages=('id', 'count'), words=('words', 'sum'))"))
cells += analysis

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
    "colab": {"provenance": []}})
out = pathlib.Path(__file__).with_name("week04_colab.ipynb")
nbf.write(nb, out)
print("wrote", out, "cells:", len(cells))
