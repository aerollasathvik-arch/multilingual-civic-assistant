# Architecture (Week 2)

```
            offline (weeks 3-4)                                   online, per question (weeks 5-8)
 GOV.UK Content API ─┐                                 user question (pl / ro / ar / ur / en)
 NHS.uk HTML ────────┼─> ingest.py ─> pages.jsonl              │
                     │   (raw snapshot + dates)                ├─> language ID            (wk 5)
                     │                                         ├─> [optional] translate to English (wk 5, NLLB)
                     └─> chunk.py ─> chunks.csv                ├─> embed query ─> FAISS top-k ─> England filter (wk 5)
                         (section-aware)                       ├─> refusal check on top score (wk 6)
                              │                                ├─> LLM: answer only from passages, cite [n] (wk 6)
                              └─> embed (e5-base) ─> FAISS ────┤
                                                               └─> answer in user's language + source cards (wk 8)
```

| Component | Choice | Licence | Status |
|---|---|---|---|
| Ingestion | `requests` + `beautifulsoup4`; GOV.UK Content API (`/api/content/<path>`) | - | done |
| Chunking | Own code: one chunk per h2/h3 section, 40-200 words, 40-word overlap | - | done |
| Embeddings | `intfloat/multilingual-e5-base` (main), `paraphrase-multilingual-MiniLM-L12-v2` (comparison) | MIT / Apache-2.0 | done |
| Vector index | FAISS `IndexFlatIP` on normalised vectors (exact cosine search; corpus is small) | MIT | done |
| Lexical baseline | `rank_bm25` BM25Okapi | Apache-2.0 | done |
| Translation | `facebook/nllb-200-distilled-600M` (candidate) | CC-BY-NC-4.0 | week 5 |
| Generation | LLM API, chosen in week 6 | - | week 6 |
| Front-end | Web app, chosen in week 8 | - | week 8 |

FAISS is a vector index library rather than a database server. At 432 chunks an exact flat index is fast
enough; a vector database (e.g. Chroma, Qdrant) would only be needed for a much larger or frequently
updated corpus. This is a deliberate choice to explain in the method chapter.
