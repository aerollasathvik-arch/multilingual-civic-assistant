# Literature notes (Week 2)

Every arXiv entry below was checked against the arXiv API on 28 Oct 2026 (title, first author, year).
Use the published venue version when one exists.

| Topic | Reference | Why it matters here |
|---|---|---|
| RAG | Lewis, P. et al. (2020) *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. arXiv:2005.11401 (NeurIPS 2020) | Original RAG formulation: retrieve passages, condition generation on them. |
| RAG survey | Gao, Y. et al. (2023) *Retrieval-Augmented Generation for Large Language Models: A Survey*. arXiv:2312.10997 | Taxonomy (naive / advanced / modular RAG), chunking, reranking, evaluation. |
| RAG evaluation | Es, S. et al. (2023) *Ragas: Automated Evaluation of Retrieval Augmented Generation*. arXiv:2309.15217 | Faithfulness and answer relevance metrics; candidate automated judge alongside human scoring. |
| Sentence embeddings | Reimers, N. & Gurevych, I. (2019) *Sentence-BERT*. arXiv:1908.10084 | Basis of the sentence-transformers library used for dense retrieval. |
| Multilingual embeddings | Reimers, N. & Gurevych, I. (2020) *Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation*. arXiv:2004.09813 | Method behind `paraphrase-multilingual-MiniLM-L12-v2` (second model in week 4). |
| Multilingual embeddings | Wang, L. et al. (2024) *Multilingual E5 Text Embeddings: A Technical Report*. arXiv:2402.05672 | `multilingual-e5-base`, the main retriever; explains the `query:` / `passage:` prefixes. |
| Embedding training | Wang, L. et al. (2022) *Text Embeddings by Weakly-Supervised Contrastive Pre-training*. arXiv:2212.03533 | The E5 training approach. |
| Vector search | Johnson, J., Douze, M. & Jégou, H. (2017) *Billion-scale similarity search with GPUs*. arXiv:1702.08734 | FAISS, the vector index. |
| Machine translation | NLLB Team (2022) *No Language Left Behind: Scaling Human-Centered Machine Translation*. arXiv:2207.04672 | NLLB-200, candidate translation layer (licence CC-BY-NC-4.0: research use only). |
| Lexical retrieval | Robertson, S. & Zaragoza, H. (2009) *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval 3(4) | BM25 baseline in week 4. |

Gaps still to read for the literature review chapter (week 11): hallucination surveys, plain-language /
readability research for public information, studies of chatbots in public services, and work on
language barriers to UK health and housing services.
