"""Generate notebooks/week04_retrieval.ipynb from the project pipeline (run, then execute with nbconvert)."""
import pathlib

import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("# Week 4: Multilingual retrieval over official UK guidance\n\n"
       "Project: *A Multilingual AI Assistant for Accessing Health, Housing, and Schooling Information*.\n\n"
       "This notebook runs on the project pipeline in `src/` instead of copying code into cells:\n"
       "1. Load the corpus collected in week 3 (38 GOV.UK and NHS.uk pages)\n"
       "2. Split it into section-aware chunks\n"
       "3. Build a multilingual search index (multilingual-e5-base + FAISS)\n"
       "4. Search in five languages\n"
       "5. Report the week 4 retrieval experiment and its failure cases"),
    code("import sys, json, pathlib\n"
         "import pandas as pd\n"
         "ROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' else pathlib.Path.cwd()\n"
         "sys.path.insert(0, str(ROOT / 'src'))\n"
         "pd.set_option('display.max_colwidth', 90)"),
    md("## 1. Corpus\n\nCollected by `src/ingest.py` (GOV.UK Content API + NHS.uk pages). "
       "Set `RECRAWL = True` to fetch the live pages again."),
    code("RECRAWL = False\n"
         "if RECRAWL:\n"
         "    import ingest; ingest.main()\n"
         "pages = pd.DataFrame([json.loads(l) for l in open(ROOT / 'data/processed/pages.jsonl')])\n"
         "print(len(pages), 'pages, crawled', pages.fetched_at.iloc[0])\n"
         "pages.groupby(['source', 'domain']).agg(pages=('id', 'count'), words=('words', 'sum'))"),
    md("Publisher dates are not a reliable sign of how current a page is. The eviction guide still says it was "
       "published in 2015, but its text already describes the Renters' Rights Act changes from 1 May 2026."),
    code("ev = pages[pages.title.str.startswith('Private renting for tenants')].iloc[0]\n"
         "text = ' '.join(s['text'] for s in ev.sections)\n"
         "print('public_updated_at:', ev.public_updated_at, '| mentions of \"1 May 2026\":', text.count('1 May 2026'))"),
    md("## 2. Section-aware chunks\n\nOne chunk per page section (40-200 words, 40-word overlap). "
       "Each chunk starts with `page title - section heading:` so the model sees the context."),
    code("import chunk; chunk.main()\n"
         "chunks = pd.read_csv(ROOT / 'data/processed/chunks.csv')\n"
         "chunks[['title', 'heading', 'words']].sample(5, random_state=1)"),
    md("## 3. Multilingual index"),
    code("from retrieval import DenseRetriever\n"
         "e5 = DenseRetriever('intfloat/multilingual-e5-base', chunks.text.tolist())\n"
         "print('chunks indexed:', e5.index.ntotal)\n\n"
         "def show(question, k=3):\n"
         "    print('Q:', question)\n"
         "    for i, s in e5.search(question, k):\n"
         "        c = chunks.iloc[i]\n"
         "        print(f'  {s:.3f}  {c.title} > {c.heading}\\n         {c.url}')\n"
         "    print()"),
    code("show('How do I apply for a primary school place for my child?')   # English\n"
         "show('Jak zarejestrować się u lekarza rodzinnego?')                 # Polish: how do I register with a GP?\n"
         "show('Poate proprietarul să mă evacueze fără să-mi dea un motiv?')  # Romanian: can my landlord evict me without a reason?\n"
         "show('هل يمكن للمالك أن يطردني من المنزل؟')                         # Arabic: can my landlord evict me?\n"
         "show('میرا گھر چھننے والا ہے، کیا کونسل میری مدد کر سکتی ہے؟')      # Urdu: I am about to lose my home, can the council help?"),
    md("## 4. Retrieval experiment\n\n"
       "Test set `eval/queries.csv`: 30 questions (10 per domain) in English, Polish, Romanian, Arabic and Urdu = 150 queries. "
       "Each question has a gold page and an **answer phrase copied verbatim** from that page.\n\n"
       "* **hit@3**: gold page in the top 3 pages\n"
       "* **ans@3**: a top-3 chunk contains the answer phrase (strict: other wording may also answer)\n\n"
       "Four set-ups: BM25 keyword search, the original notebook set-up (e5 on blind 150-word chunks), "
       "e5 on section chunks, and MiniLM on section chunks. Run `python eval/evaluate_retrieval.py` to regenerate."),
    code("res = pd.read_csv(ROOT / 'results/retrieval_by_lang.csv')\n"
         "res[res.lang == 'ALL'].drop(columns='lang').set_index('system')"),
    code("per_q = pd.read_csv(ROOT / 'results/retrieval_per_query.csv')\n"
         "per_q.pivot_table(index='system', columns='lang', values=['hit@3', 'ans@3']).round(2)"),
    code("import matplotlib.pyplot as plt\n"
         "order = ['bm25', 'e5_naive150', 'e5_sections', 'minilm_sections']\n"
         "langs = ['en', 'pl', 'ro', 'ar', 'ur']\n"
         "t = per_q.pivot_table(index='lang', columns='system', values='ans@3').loc[langs, order]\n"
         "ax = t.plot.bar(figsize=(8, 3.5), rot=0, width=0.8)\n"
         "ax.set_ylabel('ans@3'); ax.set_ylim(0, 1); ax.set_title('Answer-bearing chunk in top 3, by query language')\n"
         "ax.legend(frameon=False, ncol=4, fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.12))\n"
         "plt.tight_layout(); plt.show()"),
    md("## 5. Failure cases\n\n"
       "**Wrong nation.** For *At what age can my child leave school?* the top chunk is the Scotland rule. "
       "The page is right, but the answer would be wrong for someone in England."),
    code("show('At what age can my child leave school?')"),
    md("**Right page, not the answering section.** Page-level hit@3 is 0.96 but ans@3 is 0.67. Some of the gap is the "
       "strict phrase match (the top chunks for *Can my landlord evict me without giving a reason?* do explain that a "
       "reason is now needed), and some is real: the chunk with the answer ranks below other sections of the same page."),
    code("e = per_q[per_q.system == 'e5_sections']\n"
         "print('hit@3 but no answer phrase in top 3:', ((e['hit@3']) & (~e['ans@3'])).sum(), 'of', len(e))\n"
         "e.groupby('lang')[['hit@3', 'ans@3']].mean().round(2).loc[langs]"),
    md("## Next steps (week 5)\n\n"
       "* Tag chunks by UK nation and filter to England by default.\n"
       "* Native-speaker check of the Polish, Romanian, Arabic and Urdu test questions.\n"
       "* Compare direct multilingual retrieval with translating the question to English first (NLLB-200).\n"
       "* Try reranking the top 20 chunks to close the gap between hit@3 and ans@3, especially for Urdu."),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = pathlib.Path(__file__).with_name("week04_retrieval.ipynb")
nbf.write(nb, out)
print("wrote", out)
