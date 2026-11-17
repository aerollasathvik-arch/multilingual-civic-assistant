"""Week 6 assistant: question in any supported language -> cited answer from official pages, or a refusal.

    question
      -> search stage (pipeline.py, set-up F from week 5): top 3 passages + reranker score
      -> refusal rule 1: top reranker score below THRESHOLD -> refuse without calling the LLM
      -> refusal rule 2: a separate yes/no LLM call says the passages do not answer it -> refuse
      -> LLM answers only from the 3 passages, citing [n]          (generate.py)
      -> refusal rule 3: the LLM replies NO_ANSWER -> refuse
      -> answer language: "direct"    = the LLM writes in the user's language
                          "translate" = the LLM writes in English, NLLB translates it
      -> source cards for the cited passages (title, section, link, date fetched)
      -> health note (NHS 111 / 999) whenever an NHS.uk page is cited

Citations are numbers chosen by the LLM; titles, links and dates always come from the corpus, so the
model can never invent a URL.
"""
from generate import NO_ANSWER, Generator, citations, CITATION
from pipeline import SearchPipeline
from translate import split_sentences

# Calibrated in eval/evaluate_week6.py on 150 answerable and 50 unanswerable questions.
THRESHOLD = 0.0052  # 0.9 x lowest top score of an answerable question whose answer was retrieved

# Fixed messages (written by the author; part of the native-speaker check, task T22).
REFUSAL = {
    "en": "I could not find an answer to this in the official GOV.UK and NHS pages I use. "
          "Please check GOV.UK or NHS.uk, or contact your local council.",
    "pl": "Nie udało mi się znaleźć odpowiedzi na to pytanie na oficjalnych stronach GOV.UK i NHS. "
          "Sprawdź GOV.UK lub NHS.uk albo skontaktuj się z lokalnym urzędem (council).",
    "ro": "Nu am găsit un răspuns la această întrebare în paginile oficiale GOV.UK și NHS. "
          "Vă rugăm să verificați GOV.UK sau NHS.uk ori să contactați consiliul local.",
    "ar": "لم أجد إجابة عن هذا السؤال في صفحات GOV.UK وNHS الرسمية. "
          "يُرجى مراجعة GOV.UK أو NHS.uk، أو التواصل مع المجلس المحلي.",
    "ur": "مجھے سرکاری GOV.UK اور NHS صفحات میں اس سوال کا جواب نہیں ملا۔ "
          "براہ کرم GOV.UK یا NHS.uk دیکھیں، یا اپنی مقامی کونسل سے رابطہ کریں۔",
}
HEALTH_NOTE = {
    "en": "If you need medical help now, call 111. In an emergency, call 999.",
    "pl": "Jeśli potrzebujesz pilnej pomocy medycznej, zadzwoń pod numer 111. W nagłym wypadku dzwoń pod 999.",
    "ro": "Dacă aveți nevoie urgent de ajutor medical, sunați la 111. În caz de urgență, sunați la 999.",
    "ar": "إذا كنت بحاجة إلى مساعدة طبية الآن، اتصل بالرقم 111. في حالات الطوارئ، اتصل بالرقم 999.",
    "ur": "اگر آپ کو ابھی طبی مدد کی ضرورت ہے تو 111 پر کال کریں۔ ہنگامی صورت میں 999 پر کال کریں۔",
}


def translate_answer(translator, english, lang):
    """Translate an English answer sentence by sentence, keeping each sentence's [n] citations.

    Citation markers are taken out before translation (NLLB may drop or garble them) and put back
    at the end of the translated sentence."""
    out = []
    for sent in split_sentences(english):
        marks = "".join(f"[{n}]" for n in CITATION.findall(sent))
        text = CITATION.sub("", sent).replace(" .", ".").strip()
        if text:
            out.append((translator.translate([text], src="en", tgt=lang)[0] + " " + marks).strip())
        elif marks and out:  # markers split off on their own belong to the previous sentence
            out[-1] += " " + marks
    return " ".join(out)


class Assistant:
    def __init__(self, pipeline=None, generator=None, threshold=THRESHOLD, mode="direct"):
        self.pipeline = pipeline or SearchPipeline()
        self.generator = generator or Generator()
        self.threshold = threshold
        self.mode = mode

    def refuse(self, base, reason):
        return {**base, "refused": True, "reason": reason, "answer": REFUSAL[base["lang"]], "sources": []}

    def answer_from(self, search, question, mode=None):
        """Answer from an existing search result (lets the evaluation reuse one search for both modes)."""
        mode = mode or self.mode
        lang, passages = search["lang"], search["results"]
        top = passages[0]["score"] if passages else 0.0
        base = {"question": question, "lang": lang, "mode": mode, "english_query": search["english_query"],
                "top_score": top, "raw": ""}
        if top < self.threshold:
            return self.refuse(base, "low relevance")
        if not self.generator.answerable(question, passages):
            return self.refuse(base, "check: not in sources")
        answer_lang = lang if mode == "direct" else "en"
        raw = self.generator.answer(question, passages, answer_lang, pivot=answer_lang != lang)
        base["raw"] = raw
        if NO_ANSWER in raw:
            return self.refuse(base, "model: not in sources")
        text = raw if answer_lang == lang else translate_answer(self.pipeline.translator, raw, lang)
        cited = [n for n in citations(text) if 1 <= n <= len(passages)]
        sources = [{"n": n, **{k: passages[n - 1][k] for k in ("title", "heading", "url", "source", "fetched_at")}}
                   for n in cited]
        if any(s["source"] == "NHS.uk" for s in sources):
            text += "\n\n" + HEALTH_NOTE[lang]
        return {**base, "refused": False, "reason": None, "answer": text, "sources": sources,
                "passages": passages}

    def ask(self, question, lang=None, mode=None):
        return self.answer_from(self.pipeline.search(question, k=3, lang=lang), question, mode)
