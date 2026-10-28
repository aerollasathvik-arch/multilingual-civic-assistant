"""Build the retrieval test set and check every answer phrase against the corpus.

Each English question has:
  gold_url - the page that answers it
  evidence - a short phrase copied verbatim from that page that contains the answer
A retrieved chunk only counts as "answer-bearing" if it contains the evidence
phrase, so a hit on the right page but the wrong section is not counted.

Translations (pl, ro, ar, ur) were written by the author and are flagged
"unverified" until a native speaker checks them.
Output: eval/queries.csv
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "https://www.gov.uk/"
N = "https://www.nhs.uk/nhs-services/"

# qid: (domain, gold_url, evidence, {lang: question})
Q = {
    "S01": ("schools", G + "schools-admissions", "close on 15 January", {
        "en": "When is the deadline to apply for a primary school place?",
        "pl": "Jaki jest termin składania wniosku o miejsce w szkole podstawowej?",
        "ro": "Care este termenul limită pentru a depune cererea pentru un loc la școala primară?",
        "ar": "ما هو الموعد النهائي للتقديم على مقعد في المدرسة الابتدائية؟",
        "ur": "پرائمری اسکول میں داخلے کی درخواست دینے کی آخری تاریخ کیا ہے؟"}),
    "S02": ("schools", G + "schools-admissions", "by 31 October", {
        "en": "What is the last date to apply for a secondary school place?",
        "pl": "Do kiedy trzeba złożyć wniosek o miejsce w szkole średniej?",
        "ro": "Până la ce dată trebuie să aplic pentru un loc la școala secundară?",
        "ar": "ما هو آخر موعد للتقديم على مقعد في المدرسة الثانوية؟",
        "ur": "سیکنڈری اسکول میں داخلے کے لیے درخواست کس تاریخ تک دینی ہوگی؟"}),
    "S03": ("schools", G + "schools-admissions", "primary schools on 16 April", {
        "en": "When will I find out which primary school my child has been offered?",
        "pl": "Kiedy dowiem się, do której szkoły podstawowej zostało przyjęte moje dziecko?",
        "ro": "Când voi afla la ce școală primară a primit loc copilul meu?",
        "ar": "متى سأعرف المدرسة الابتدائية التي قُبل فيها طفلي؟",
        "ur": "مجھے کب پتہ چلے گا کہ میرے بچے کو کون سے پرائمری اسکول میں جگہ ملی ہے؟"}),
    "S04": ("schools", G + "schools-admissions", "at least 20 school days", {
        "en": "How long do I have to appeal if my child is refused a school place?",
        "pl": "Ile mam czasu na odwołanie, jeśli moje dziecko nie dostało miejsca w szkole?",
        "ro": "Cât timp am la dispoziție să fac contestație dacă copilul meu nu a primit loc la școală?",
        "ar": "كم لدي من الوقت للاستئناف إذا رُفض طلب طفلي للحصول على مقعد في المدرسة؟",
        "ur": "اگر میرے بچے کو اسکول میں جگہ نہ ملے تو اپیل کرنے کے لیے میرے پاس کتنا وقت ہے؟"}),
    "S05": ("schools", G + "school-attendance-absence", "fined or face legal action for taking your child on holiday", {
        "en": "Can I be fined for taking my child on holiday during term time?",
        "pl": "Czy mogę dostać grzywnę za zabranie dziecka na wakacje w trakcie roku szkolnego?",
        "ro": "Pot primi amendă dacă îmi iau copilul în vacanță în timpul semestrului?",
        "ar": "هل يمكن أن أُغرَّم إذا أخذت طفلي في عطلة أثناء الفصل الدراسي؟",
        "ur": "کیا ٹرم کے دوران بچے کو چھٹیوں پر لے جانے پر مجھے جرمانہ ہو سکتا ہے؟"}),
    "S06": ("schools", G + "apply-free-school-meals", "free school meals if you get any of the following", {
        "en": "Can my child get free school meals if I receive Universal Credit?",
        "pl": "Czy moje dziecko może dostać darmowe posiłki w szkole, jeśli otrzymuję Universal Credit?",
        "ro": "Poate copilul meu să primească mese gratuite la școală dacă primesc Universal Credit?",
        "ar": "هل يمكن لطفلي الحصول على وجبات مدرسية مجانية إذا كنت أتلقى Universal Credit؟",
        "ur": "اگر مجھے Universal Credit ملتا ہے تو کیا میرے بچے کو اسکول میں مفت کھانا مل سکتا ہے؟"}),
    "S07": ("schools", G + "free-school-transport", "more than 2 miles away and the child is under 8", {
        "en": "Is school transport free if the school is far from home?",
        "pl": "Czy transport do szkoły jest darmowy, jeśli szkoła jest daleko od domu?",
        "ro": "Este transportul la școală gratuit dacă școala este departe de casă?",
        "ar": "هل المواصلات المدرسية مجانية إذا كانت المدرسة بعيدة عن المنزل؟",
        "ur": "اگر اسکول گھر سے دور ہو تو کیا اسکول کی ٹرانسپورٹ مفت ہے؟"}),
    "S08": ("schools", G + "know-when-you-can-leave-school", "16 by the end of the summer holidays", {
        "en": "At what age can my child leave school?",
        "pl": "W jakim wieku moje dziecko może skończyć szkołę?",
        "ro": "La ce vârstă poate copilul meu să termine școala?",
        "ar": "في أي عمر يمكن لطفلي ترك المدرسة؟",
        "ur": "میرا بچہ کس عمر میں اسکول چھوڑ سکتا ہے؟"}),
    "S09": ("schools", G + "children-with-special-educational-needs", "SEN support - support given in school", {
        "en": "What support can my child get for special educational needs?",
        "pl": "Jakie wsparcie może otrzymać moje dziecko ze specjalnymi potrzebami edukacyjnymi?",
        "ro": "Ce sprijin poate primi copilul meu pentru cerințe educaționale speciale?",
        "ar": "ما الدعم الذي يمكن أن يحصل عليه طفلي إذا كانت لديه احتياجات تعليمية خاصة؟",
        "ur": "خصوصی تعلیمی ضروریات والے میرے بچے کو کیا مدد مل سکتی ہے؟"}),
    "S10": ("schools", G + "complain-about-school", "different ways to complain in England", {
        "en": "How do I complain about my child's state school?",
        "pl": "Jak złożyć skargę na państwową szkołę mojego dziecka?",
        "ro": "Cum fac o plângere împotriva școlii de stat a copilului meu?",
        "ar": "كيف أقدم شكوى ضد المدرسة الحكومية التي يدرس فيها طفلي؟",
        "ur": "میں اپنے بچے کے سرکاری اسکول کے بارے میں شکایت کیسے کروں؟"}),

    "H01": ("housing", G + "guidance/renters-rights-act-overview-for-tenants", "section 21 process", {
        "en": "Can my landlord evict me without giving a reason?",
        "pl": "Czy wynajmujący może mnie eksmitować bez podania powodu?",
        "ro": "Poate proprietarul să mă evacueze fără să-mi dea un motiv?",
        "ar": "هل يمكن للمالك أن يطردني دون إبداء سبب؟",
        "ur": "کیا مالک مکان مجھے بغیر کوئی وجہ بتائے گھر سے نکال سکتا ہے؟"}),
    "H02": ("housing", G + "guidance/renters-rights-act-overview-for-tenants", "increase the rent once a year", {
        "en": "How often can my landlord increase the rent?",
        "pl": "Jak często wynajmujący może podnosić czynsz?",
        "ro": "Cât de des poate proprietarul să crească chiria?",
        "ar": "كم مرة يمكن للمالك أن يرفع الإيجار؟",
        "ur": "مالک مکان کتنی بار کرایہ بڑھا سکتا ہے؟"}),
    "H03": ("housing", G + "tenancy-deposit-protection", "Deposit Protection Service", {
        "en": "My landlord took a deposit from me. Does it have to be protected?",
        "pl": "Wynajmujący pobrał ode mnie kaucję. Czy musi ona być zabezpieczona?",
        "ro": "Proprietarul mi-a luat o garanție. Trebuie aceasta să fie protejată?",
        "ar": "أخذ المالك مني مبلغ تأمين، هل يجب أن يكون هذا التأمين محميًا؟",
        "ur": "مالک مکان نے مجھ سے ڈپازٹ لیا ہے، کیا اس ڈپازٹ کا محفوظ ہونا ضروری ہے؟"}),
    "H04": ("housing", G + "housing-benefit", "help you pay your rent", {
        "en": "How can I get help paying my rent if I am on a low income?",
        "pl": "Jak uzyskać pomoc w opłaceniu czynszu, jeśli mam niskie dochody?",
        "ro": "Cum pot primi ajutor pentru plata chiriei dacă am un venit mic?",
        "ar": "كيف أحصل على مساعدة في دفع الإيجار إذا كان دخلي منخفضًا؟",
        "ur": "کم آمدنی کی صورت میں مجھے کرایہ ادا کرنے میں مدد کیسے مل سکتی ہے؟"}),
    "H05": ("housing", G + "council-housing", "join a waiting list", {
        "en": "How do I apply for council housing?",
        "pl": "Jak złożyć wniosek o mieszkanie komunalne?",
        "ro": "Cum aplic pentru o locuință socială de la consiliul local?",
        "ar": "كيف أتقدم بطلب للحصول على سكن من المجلس المحلي؟",
        "ur": "میں کونسل کے مکان کے لیے درخواست کیسے دوں؟"}),
    "H06": ("housing", G + "homelessness-help-from-council", "homeless or about to lose your home", {
        "en": "I am about to lose my home. Can the council help me?",
        "pl": "Zaraz stracę dom. Czy lokalny urząd może mi pomóc?",
        "ro": "Sunt pe punctul de a-mi pierde locuința. Mă poate ajuta consiliul local?",
        "ar": "أنا على وشك أن أفقد منزلي، هل يمكن للمجلس المحلي مساعدتي؟",
        "ur": "میرا گھر چھننے والا ہے، کیا کونسل میری مدد کر سکتی ہے؟"}),
    "H07": ("housing", G + "private-renting", "safe and in a good state of repair", {
        "en": "Does my landlord have to keep my rented home in good repair?",
        "pl": "Czy wynajmujący musi utrzymywać wynajmowane mieszkanie w dobrym stanie technicznym?",
        "ro": "Este proprietarul obligat să mențină locuința închiriată în stare bună?",
        "ar": "هل يجب على المالك أن يحافظ على المنزل المؤجر في حالة جيدة؟",
        "ur": "کیا مالک مکان پر کرائے کے گھر کو اچھی حالت میں رکھنا لازم ہے؟"}),
    "H08": ("housing", G + "private-renting", "24 hours", {
        "en": "How much notice must my landlord give before visiting the property?",
        "pl": "Z jakim wyprzedzeniem wynajmujący musi mnie uprzedzić przed wizytą w mieszkaniu?",
        "ro": "Cu cât timp înainte trebuie să mă anunțe proprietarul dacă vrea să vină în locuință?",
        "ar": "كم من الوقت يجب أن يخطرني المالك قبل أن يزور المنزل؟",
        "ur": "گھر آنے سے پہلے مالک مکان کو مجھے کتنا پہلے اطلاع دینی چاہیے؟"}),
    "H09": ("housing", G + "council-tax", "25% off your bill", {
        "en": "Do I get a council tax discount if I live alone?",
        "pl": "Czy dostanę zniżkę na podatek lokalny, jeśli mieszkam sam?",
        "ro": "Primesc reducere la impozitul local pe locuință dacă locuiesc singur?",
        "ar": "هل أحصل على خصم في ضريبة المجلس المحلي إذا كنت أعيش وحدي؟",
        "ur": "اگر میں اکیلا رہتا ہوں تو کیا مجھے کونسل ٹیکس میں رعایت ملتی ہے؟"}),
    "H10": ("housing", G + "council-housing-association-evictions", "stop or delay the eviction", {
        "en": "What can I do if my council or housing association wants to evict me?",
        "pl": "Co mogę zrobić, jeśli lokalny urząd lub stowarzyszenie mieszkaniowe chce mnie eksmitować?",
        "ro": "Ce pot face dacă consiliul local sau asociația de locuințe vrea să mă evacueze?",
        "ar": "ماذا يمكنني أن أفعل إذا أراد المجلس المحلي أو جمعية الإسكان طردي؟",
        "ur": "اگر کونسل یا ہاؤسنگ ایسوسی ایشن مجھے گھر سے نکالنا چاہے تو میں کیا کر سکتا ہوں؟"}),

    "M01": ("health", N + "gps/how-to-register-with-a-gp-surgery/", "change your current GP surgery online", {
        "en": "How do I register with a GP surgery?",
        "pl": "Jak zarejestrować się u lekarza rodzinnego?",
        "ro": "Cum mă înregistrez la un medic de familie?",
        "ar": "كيف أسجل لدى طبيب عام؟",
        "ur": "میں جی پی کے پاس رجسٹریشن کیسے کرواؤں؟"}),
    "M02": ("health", N + "gps/how-to-register-with-a-gp-surgery/", "do not need ID, proof of address", {
        "en": "Do I need proof of address or immigration status to register with a GP?",
        "pl": "Czy potrzebuję potwierdzenia adresu lub statusu imigracyjnego, aby zarejestrować się u lekarza rodzinnego?",
        "ro": "Am nevoie de dovada adresei sau a statutului de imigrant ca să mă înregistrez la medicul de familie?",
        "ar": "هل أحتاج إلى إثبات عنوان أو إثبات وضع الهجرة للتسجيل لدى طبيب عام؟",
        "ur": "کیا جی پی کے پاس رجسٹر ہونے کے لیے مجھے پتے یا امیگریشن اسٹیٹس کا ثبوت چاہیے؟"}),
    "M03": ("health", N + "urgent-and-emergency-care-services/when-to-use-111/", "if you think you need medical help right now", {
        "en": "When should I use NHS 111?",
        "pl": "Kiedy powinienem skorzystać z NHS 111?",
        "ro": "Când ar trebui să folosesc NHS 111?",
        "ar": "متى يجب أن أستخدم خدمة NHS 111؟",
        "ur": "مجھے NHS 111 کب استعمال کرنا چاہیے؟"}),
    "M04": ("health", N + "urgent-and-emergency-care-services/when-to-go-to-ae/", "serious injuries and life-threatening emergencies", {
        "en": "When should I go to A&E?",
        "pl": "Kiedy powinienem iść na szpitalny oddział ratunkowy?",
        "ro": "Când ar trebui să merg la urgențe?",
        "ar": "متى يجب أن أذهب إلى قسم الطوارئ؟",
        "ur": "مجھے ہسپتال کے ایمرجنسی شعبے میں کب جانا چاہیے؟"}),
    "M05": ("health", N + "urgent-and-emergency-care-services/when-to-call-999/", "999 is for life-threatening emergencies", {
        "en": "When should I call 999?",
        "pl": "Kiedy powinienem dzwonić pod numer 999?",
        "ro": "Când ar trebui să sun la 999?",
        "ar": "متى يجب أن أتصل بالرقم 999؟",
        "ur": "مجھے 999 پر کب کال کرنی چاہیے؟"}),
    "M06": ("health", N + "dentists/how-to-find-an-nhs-dentist/", "Ask for an NHS appointment", {
        "en": "How can I find an NHS dentist?",
        "pl": "Jak znaleźć dentystę NHS?",
        "ro": "Cum găsesc un dentist NHS?",
        "ar": "كيف أجد طبيب أسنان تابعًا لـ NHS؟",
        "ur": "میں NHS کا ڈینٹسٹ کیسے تلاش کروں؟"}),
    "M07": ("health", N + "dentists/how-much-nhs-dental-treatment-costs/", "£27.90", {
        "en": "How much does a basic NHS dental check-up cost?",
        "pl": "Ile kosztuje podstawowy przegląd u dentysty w NHS?",
        "ro": "Cât costă un control stomatologic de bază la NHS?",
        "ar": "كم يكلف فحص الأسنان الأساسي في NHS؟",
        "ur": "NHS میں دانتوں کے بنیادی معائنے پر کتنا خرچ آتا ہے؟"}),
    "M08": ("health", N + "pharmacies/how-pharmacies-can-help/", "This is called Pharmacy First", {
        "en": "Can a pharmacy give me prescription medicine without seeing a GP?",
        "pl": "Czy apteka może wydać mi lek na receptę bez wizyty u lekarza?",
        "ro": "Poate o farmacie să-mi dea medicamente cu rețetă fără să merg la medic?",
        "ar": "هل يمكن للصيدلية أن تعطيني دواءً يحتاج إلى وصفة طبية دون أن أرى الطبيب؟",
        "ur": "کیا فارمیسی ڈاکٹر کو دکھائے بغیر مجھے نسخے والی دوا دے سکتی ہے؟"}),
    "M09": ("health", N + "help-with-health-costs/nhs-low-income-scheme-lis/", "HC2 certificate", {
        "en": "Can I get help with health costs if I have a low income?",
        "pl": "Czy mogę dostać pomoc w pokryciu kosztów leczenia, jeśli mam niskie dochody?",
        "ro": "Pot primi ajutor pentru costurile medicale dacă am venituri mici?",
        "ar": "هل يمكنني الحصول على مساعدة في التكاليف الصحية إذا كان دخلي منخفضًا؟",
        "ur": "کیا کم آمدنی کی صورت میں مجھے علاج کے اخراجات میں مدد مل سکتی ہے؟"}),
    "M10": ("health", G + "healthcare-immigration-application", "£776 per year for students", {
        "en": "How much is the immigration health surcharge for students?",
        "pl": "Ile wynosi dopłata zdrowotna dla imigrantów w przypadku studentów?",
        "ro": "Cât costă taxa de sănătate pentru imigranți în cazul studenților?",
        "ar": "كم تبلغ رسوم الرعاية الصحية للمهاجرين بالنسبة للطلاب؟",
        "ur": "طلبہ کے لیے امیگریشن ہیلتھ سرچارج کتنا ہے؟"}),
}


def main():
    pages = {}
    for line in open(ROOT / "data/processed/pages.jsonl"):
        r = json.loads(line)
        pages[r["url"]] = " ".join(s["text"] for s in r["sections"]).lower()
    bad = [(q, url) for q, (_, url, ev, _) in Q.items() if url not in pages or ev.lower() not in pages[url]]
    if bad:
        sys.exit(f"evidence not found on gold page: {bad}")
    out = ROOT / "eval/queries.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "domain", "lang", "question", "gold_url", "evidence", "translation_status"])
        for qid, (domain, url, ev, qs) in Q.items():
            for lang, text in qs.items():
                w.writerow([qid, domain, lang, text, url, ev, "source" if lang == "en" else "unverified"])
    print(f"{len(Q)} questions x {len(next(iter(Q.values()))[3])} languages -> {out.relative_to(ROOT)}; "
          f"all evidence phrases found verbatim on their gold page")


if __name__ == "__main__":
    main()
