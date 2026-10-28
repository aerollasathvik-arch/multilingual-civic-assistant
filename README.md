# Multilingual civic assistant

MSc research prototype: a retrieval-augmented assistant that answers health, housing and schooling
questions in Polish, Romanian, Arabic, Urdu and English, using only official GOV.UK and NHS.uk pages,
with citations.

## Run
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python src/ingest.py              # crawl 38 official pages -> data/processed/pages.jsonl
.venv/bin/python src/chunk.py               # section-aware chunks   -> data/processed/chunks.csv
.venv/bin/python eval/build_queries.py      # 150-query test set     -> eval/queries.csv
.venv/bin/python eval/evaluate_retrieval.py # week 4 experiment      -> results/
.venv/bin/python docs/build_plan.py         # 12-week plan           -> docs/project-plan.xlsx
```
Notebook: `notebooks/week04_retrieval.ipynb` (regenerate with `notebooks/make_week04_notebook.py`).

## Layout
| Path | Contents |
|---|---|
| `src/` | sources, ingestion, chunking, retrievers |
| `eval/` | test set builder and retrieval experiment |
| `data/raw/` | raw API / HTML snapshots as fetched |
| `data/processed/` | pages, chunks, FAISS index |
| `results/` | experiment outputs |
| `docs/` | 12-week plan workbook, scope, evaluation plan, ethics, literature, architecture, data card, weekly reports |

Content: Crown copyright, Open Government Licence v3.0 (GOV.UK, NHS.uk).
# multilingual-civic-assistant
