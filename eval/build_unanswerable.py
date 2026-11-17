"""Questions the assistant should refuse: the answer is not in the 38-page corpus.

Each topic was checked against data/processed/chunks.csv (11 Nov 2026). Two are deliberately close to
the corpus: "passport" and "birth certificate" appear only as examples of ID documents, so the search
finds related-looking passages that do not answer the question. U05 asks for medical advice, which is
out of scope. Non-English versions were written by the author (translation_status = unverified, T22).

Output: eval/unanswerable.csv (10 questions x 5 languages = 50 rows)
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

QUESTIONS = {
    "U01": {"en": "How do I renew my UK passport?",
            "pl": "Jak odnowić brytyjski paszport?",
            "ro": "Cum îmi reînnoiesc pașaportul britanic?",
            "ar": "كيف أجدد جواز سفري البريطاني؟",
            "ur": "میں اپنا برطانوی پاسپورٹ کیسے تجدید کرواؤں؟"},
    "U02": {"en": "What is the minimum wage for someone aged 21?",
            "pl": "Ile wynosi płaca minimalna dla osoby w wieku 21 lat?",
            "ro": "Care este salariul minim pentru o persoană de 21 de ani?",
            "ar": "ما هو الحد الأدنى للأجور لشخص عمره 21 عامًا؟",
            "ur": "21 سال کے شخص کے لیے کم از کم اجرت کتنی ہے؟"},
    "U03": {"en": "How do I apply for British citizenship?",
            "pl": "Jak ubiegać się o brytyjskie obywatelstwo?",
            "ro": "Cum pot aplica pentru cetățenia britanică?",
            "ar": "كيف أتقدم بطلب للحصول على الجنسية البريطانية؟",
            "ur": "میں برطانوی شہریت کے لیے درخواست کیسے دوں؟"},
    "U04": {"en": "How do I register my baby's birth?",
            "pl": "Jak zarejestrować urodzenie mojego dziecka?",
            "ro": "Cum înregistrez nașterea copilului meu?",
            "ar": "كيف أسجل ولادة طفلي؟",
            "ur": "میں اپنے بچے کی پیدائش کا اندراج کیسے کرواؤں؟"},
    "U05": {"en": "What is the best treatment for back pain?",
            "pl": "Jakie jest najlepsze leczenie bólu pleców?",
            "ro": "Care este cel mai bun tratament pentru durerea de spate?",
            "ar": "ما هو أفضل علاج لآلام الظهر؟",
            "ur": "کمر درد کا بہترین علاج کیا ہے؟"},
    "U06": {"en": "How do I get a mortgage to buy my first home?",
            "pl": "Jak dostać kredyt hipoteczny na zakup pierwszego mieszkania?",
            "ro": "Cum obțin un credit ipotecar pentru a-mi cumpăra prima locuință?",
            "ar": "كيف أحصل على قرض عقاري لشراء أول منزل لي؟",
            "ur": "میں اپنا پہلا گھر خریدنے کے لیے مارگیج کیسے حاصل کروں؟"},
    "U07": {"en": "How do I register to vote?",
            "pl": "Jak zarejestrować się do głosowania?",
            "ro": "Cum mă înscriu pentru a vota?",
            "ar": "كيف أسجل للتصويت؟",
            "ur": "میں ووٹ ڈالنے کے لیے رجسٹریشن کیسے کرواؤں؟"},
    "U08": {"en": "Do I need a TV licence to watch TV online?",
            "pl": "Czy potrzebuję licencji telewizyjnej, żeby oglądać telewizję w internecie?",
            "ro": "Am nevoie de licență TV ca să mă uit la televizor online?",
            "ar": "هل أحتاج إلى ترخيص تلفزيون لمشاهدة التلفزيون عبر الإنترنت؟",
            "ur": "کیا مجھے آن لائن ٹی وی دیکھنے کے لیے ٹی وی لائسنس کی ضرورت ہے؟"},
    "U09": {"en": "How much does a driving test cost?",
            "pl": "Ile kosztuje egzamin na prawo jazdy?",
            "ro": "Cât costă examenul pentru permisul de conducere?",
            "ar": "كم تكلفة اختبار القيادة؟",
            "ur": "ڈرائیونگ ٹیسٹ کی فیس کتنی ہے؟"},
    "U10": {"en": "Can I get a free bus pass because I am over 60?",
            "pl": "Czy mogę dostać darmowy bilet autobusowy, bo mam ponad 60 lat?",
            "ro": "Pot primi un abonament gratuit de autobuz pentru că am peste 60 de ani?",
            "ar": "هل يمكنني الحصول على تذكرة حافلة مجانية لأن عمري أكثر من 60 عامًا؟",
            "ur": "کیا مجھے 60 سال سے زیادہ عمر ہونے کی وجہ سے مفت بس پاس مل سکتا ہے؟"},
}

if __name__ == "__main__":
    out = ROOT / "eval/unanswerable.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "lang", "question", "translation_status"])
        for qid, by_lang in QUESTIONS.items():
            for lang, q in by_lang.items():
                w.writerow([qid, lang, q, "source" if lang == "en" else "unverified"])
    print("wrote", out, 5 * len(QUESTIONS), "rows")
