# Project scope (Week 1)

## Title
A Multilingual AI Assistant for Accessing Health, Housing, and Schooling Information

## Research question
How effectively can a retrieval-augmented generation (RAG) assistant, grounded only in official UK
government sources, give accurate, understandable and correctly cited answers to health, housing and
schooling questions for people with limited English, compared with the same language model answering
without those sources?

## Objectives
1. Build a curated, dated corpus of official pages (GOV.UK, NHS.uk) for the three domains.
2. Build multilingual retrieval over that corpus and measure how often it finds the answering passage.
3. Generate answers that use only retrieved passages, with numbered citations to the source page.
4. Support questions and answers in at least three languages besides English.
5. Compare grounded vs ungrounded answers on accuracy, hallucination rate and citation correctness.
6. Run a small user study on comprehension and trust, then critically assess limits and risks.

## Scope decisions
| Decision | Choice | Reason |
|---|---|---|
| Jurisdiction | England | GOV.UK housing and school rules differ across the four nations; NHS.uk covers England. Answers must not mix nations (see week 4 failure analysis). |
| Domains | Health services access, housing rights, school admissions and attendance | As in the synopsis. Clinical/medical advice is out of scope: the assistant points to NHS 111/999 instead. |
| Sources | GOV.UK (Content API) and NHS.uk | Official, reusable under the Open Government Licence v3.0. Council pages: GOV.UK "local_transaction" pages hand off to each council; the assistant will direct users there. |
| Languages | Polish, Romanian, Urdu, Arabic (+ English) | Polish, Romanian and Urdu are three of the four most common main languages other than English in England and Wales (ONS Census 2021: Polish 1.1%, Romanian 0.8%, Panjabi 0.5%, Urdu 0.5%). Arabic adds a second right-to-left script and was in the original notebook. |
| Platform | Web app | Works on any phone browser without install; easier to test with participants. |

Source for language figures: ONS, *Language, England and Wales: Census 2021*,
https://www.ons.gov.uk/peoplepopulationandcommunity/culturalidentity/language/bulletins/languageenglandandwales/census2021
