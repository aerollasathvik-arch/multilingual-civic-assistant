"""Week 7 gold set: 100 question topics with reference answers, split into calibration and held-out.

  calibration (40 topics) - the week 4-6 questions: 30 answerable (eval/queries.csv) and 10 unanswerable
                            (eval/unanswerable.csv). The week 6 refusal threshold was set on these.
  held-out    (60 topics) - new in week 7: 50 answerable (S11-S26, H11-H27, M11-M27) and 10 unanswerable
                            (U11-U20). Never used to tune anything; used to check the refusal rules and,
                            in week 9, for the grounded vs ungrounded comparison.

Every answerable topic has
  gold_url         - the page that answers it
  evidence         - a phrase copied verbatim from that page (checked below; the build stops if one is missing)
  reference_answer - a short answer written by the author from that page's text, used by the scoring rubric
Unanswerable topics were checked against the corpus (11-16 Nov 2026): the topic is absent, or only mentioned
in passing without an answer (U12 National Insurance number, U14 student loan, U17 Carer's Allowance).

Non-English questions were written by the author (translation_status = unverified, task T22).
Outputs: eval/heldout_queries.csv, eval/heldout_unanswerable.csv, eval/gold_set.csv
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "https://www.gov.uk/"
N = "https://www.nhs.uk/nhs-services/"
GP = N + "gps/how-to-register-with-a-gp-surgery/"
GPA = N + "gps/gp-appointments-and-bookings/"
U111 = N + "urgent-and-emergency-care-services/when-to-use-111/"
AE = N + "urgent-and-emergency-care-services/when-to-go-to-ae/"
C999 = N + "urgent-and-emergency-care-services/when-to-call-999/"
DENT = N + "dentists/how-much-nhs-dental-treatment-costs/"
PHARM = N + "pharmacies/how-pharmacies-can-help/"
LIS = N + "help-with-health-costs/nhs-low-income-scheme-lis/"
ABROAD = (N + "visiting-or-moving-to-england/"
          "how-to-access-nhs-services-in-england-if-you-are-visiting-from-abroad/")
VACC = "https://www.nhs.uk/vaccinations/nhs-vaccinations-and-when-to-have-them/"
PREG = "https://www.nhs.uk/pregnancy/finding-out/what-to-do-when-you-find-out-you-are-pregnant/"

# Reference answers for the 30 calibration questions (questions and evidence are in eval/build_queries.py).
CALIBRATION_REFERENCE = {
    "S01": "Applications open in September and close on 15 January. You apply through your local council, "
           "a year before your child can start school.",
    "S02": "You must apply by 31 October. Applications usually open on 1 September.",
    "S03": "Councils send primary school offers on 16 April (the next working day if that is a weekend or "
           "bank holiday).",
    "S04": "The admission authority must allow you at least 20 school days to appeal from when it sends "
           "the decision letter.",
    "S05": "Yes. You can be fined or face legal action. The council can fine each parent £80, rising to £160 "
           "if not paid within 21 days.",
    "S06": "Yes, if your household income is £7,400 a year or less (after tax, not counting benefits). From "
           "the 2026 to 2027 school year, any family on Universal Credit qualifies, whatever the income.",
    "S07": "Yes, if it is the nearest suitable school and it is more than 2 miles away (child under 8) or "
           "more than 3 miles away (child 8 or over), or there is no safe walking route, or the child cannot "
           "walk because of SEND or a mobility problem.",
    "S08": "On the last Friday in June if they will be 16 by the end of the summer holidays. Until 18 they "
           "must stay in education, start an apprenticeship, or work or volunteer 20 hours a week with "
           "part-time education or training.",
    "S09": "SEN support in school (for example speech therapy), or an education, health and care (EHC) plan "
           "for more complex needs, up to age 25. Talk to the school's SENCO.",
    "S10": "Talk to the school first. If that does not solve it, use the school's formal complaints "
           "procedure; after that you can complain to the Department for Education or Ofsted.",
    "H01": "No. From 1 May 2026 the 'no fault' section 21 process ended. The landlord must give a legal "
           "reason (a ground for possession) and the correct notice, usually 4 months.",
    "H02": "Once a year, and not in the first 12 months of a new tenancy. The landlord must use Form 4A and "
           "give at least 2 months' notice. You can challenge an increase above market rent.",
    "H03": "Yes, if you have an assured periodic tenancy and the deposit was taken on or after 6 April 2007. "
           "It must go into a government-approved scheme within 30 days.",
    "H04": "Housing Benefit can help pay rent if you are unemployed, on a low income or claiming benefits, but "
           "new claims are only possible at State Pension age or in supported, sheltered or temporary housing. "
           "Most people claim Universal Credit instead.",
    "H05": "Apply through your local council. You usually join a waiting list, and councils decide who gets "
           "housing using points or bands based on need.",
    "H06": "Yes. Contact the local council for help and advice if you are homeless or about to lose your home.",
    "H07": "Yes. The landlord must keep the property safe and in a good state of repair, and is always "
           "responsible for the structure, heating, hot water, gas, wiring and sanitary fittings.",
    "H08": "At least 24 hours' notice, at a reasonable time of day, unless it is an emergency.",
    "H09": "Yes, 25% off the bill if you live on your own. You need to apply.",
    "H10": "You may be able to stop or delay it. Get advice from Citizens Advice or Shelter and check if you "
           "can get legal aid. The landlord must give written notice and needs a court order.",
    "M01": "Online through the NHS website (or the NHS App to change surgery), or with a paper form or the "
           "surgery's own website. It is free.",
    "M02": "No. You only need basic information such as your name, date of birth and address. You do not "
           "need ID, proof of address or proof of immigration status.",
    "M03": "When you think you need medical help right now but it is not life-threatening, or you are not "
           "sure where to go. Use 111 online (age 5 and over) or call 111.",
    "M04": "For serious injuries and life-threatening emergencies.",
    "M05": "For life-threatening emergencies, such as serious road accidents, strokes and heart attacks.",
    "M06": "Contact any NHS dentist and ask for an NHS appointment. If you cannot find one, contact your "
           "local integrated care board (ICB).",
    "M07": "A Band 1 check-up (examination, X-rays if needed, scaling) costs £27.90.",
    "M08": "Yes, through Pharmacy First, for some conditions such as sore throat, earache, sinusitis, "
           "impetigo, infected insect bites, UTIs and shingles (age limits apply).",
    "M09": "Yes, through the NHS Low Income Scheme if your savings are under £16,000 (£23,250 in a care "
           "home). It gives full help (HC2) or partial help (HC3).",
    "M10": "£776 per year for students and their dependants.",
}

# Held-out answerable: qid -> (domain, gold_url, evidence, reference_answer, {lang: question})
HELDOUT = {
    # ---------- schools ----------
    "S11": ("schools", G + "schools-admissions", "start reception full-time in september after their fourth birthday",
            "Most children start reception full-time in the September after their fourth birthday.", {
        "en": "At what age does my child start school?",
        "pl": "W jakim wieku moje dziecko zaczyna szkołę?",
        "ro": "La ce vârstă începe copilul meu școala?",
        "ar": "في أي عمر يبدأ طفلي المدرسة؟",
        "ur": "میرا بچہ کس عمر میں اسکول شروع کرتا ہے؟"}),
    "S12": ("schools", G + "schools-admissions", "class size is limited to 30",
            "In reception, year 1 and year 2 classes are limited to 30 children.", {
        "en": "How many children can be in an infant class?",
        "pl": "Ile dzieci może być w klasie dla najmłodszych uczniów (infant class)?",
        "ro": "Câți copii pot fi într-o clasă pentru cei mici (infant class)?",
        "ar": "كم عدد الأطفال المسموح به في صف الأطفال الصغار (infant class)؟",
        "ur": "چھوٹے بچوں کی کلاس (infant class) میں کتنے بچے ہو سکتے ہیں؟"}),
    "S13": ("schools", G + "schools-admissions", "the local council must provide a place at another school",
            "Yes. If your child is not offered any of the schools you applied for, the council must provide a "
            "place at another school, usually the nearest one with places.", {
        "en": "What happens if my child does not get a place at any school I applied for?",
        "pl": "Co się stanie, jeśli moje dziecko nie dostanie miejsca w żadnej szkole, do której złożyłem wniosek?",
        "ro": "Ce se întâmplă dacă copilul meu nu primește loc la niciuna dintre școlile la care am aplicat?",
        "ar": "ماذا يحدث إذا لم يحصل طفلي على مقعد في أي مدرسة تقدمت إليها؟",
        "ur": "اگر میرے بچے کو کسی بھی اسکول میں جگہ نہ ملے جہاں میں نے درخواست دی تھی تو کیا ہوگا؟"}),
    "S14": ("schools", G + "schools-admissions", "for at least the first term of each school year",
            "The admission authority must keep a waiting list open for at least the first term of each school "
            "year.", {
        "en": "How long does a school have to keep its waiting list open?",
        "pl": "Jak długo szkoła musi prowadzić listę oczekujących?",
        "ro": "Cât timp trebuie o școală să păstreze deschisă lista de așteptare?",
        "ar": "إلى متى يجب على المدرسة أن تُبقي قائمة الانتظار مفتوحة؟",
        "ur": "اسکول کو اپنی ویٹنگ لسٹ کتنے عرصے تک کھلی رکھنی ہوتی ہے؟"}),
    "S15": ("schools", G + "school-attendance-absence", "if you do not pay the fine in 28 days",
            "If you do not pay the fine in 28 days you may be taken to court, where you could be fined up to "
            "£2,500, get a community order or a jail sentence of up to 3 months.", {
        "en": "What happens if I do not pay a school absence fine?",
        "pl": "Co się stanie, jeśli nie zapłacę grzywny za nieobecność dziecka w szkole?",
        "ro": "Ce se întâmplă dacă nu plătesc amenda pentru absența copilului de la școală?",
        "ar": "ماذا يحدث إذا لم أدفع غرامة غياب طفلي عن المدرسة؟",
        "ur": "اگر میں اسکول سے غیر حاضری کا جرمانہ ادا نہ کروں تو کیا ہوگا؟"}),
    "S16": ("schools", G + "school-attendance-absence", "you have advance permission from the school",
            "Only if they are too ill to go in, or you have advance permission from the school.", {
        "en": "When is my child allowed to miss school?",
        "pl": "Kiedy moje dziecko może opuścić zajęcia w szkole?",
        "ro": "Când are voie copilul meu să lipsească de la școală?",
        "ar": "متى يُسمح لطفلي بالتغيب عن المدرسة؟",
        "ur": "میرے بچے کو کب اسکول سے غیر حاضر رہنے کی اجازت ہے؟"}),
    "S17": ("schools", G + "apply-free-school-meals", "reception class year 1 year 2",
            "Yes. Children in reception, year 1 and year 2 at a government-funded school can get free school "
            "meals.", {
        "en": "Can my child in reception get free school meals?",
        "pl": "Czy moje dziecko w zerówce (reception) może dostać darmowe posiłki w szkole?",
        "ro": "Poate copilul meu din clasa reception să primească mese gratuite la școală?",
        "ar": "هل يمكن لطفلي في صف الروضة (reception) الحصول على وجبات مدرسية مجانية؟",
        "ur": "کیا ریسیپشن کلاس میں میرے بچے کو اسکول میں مفت کھانا مل سکتا ہے؟"}),
    "S18": ("schools", G + "free-school-transport", "more than 3 miles away and the child is 8 or over",
            "For a child aged 8 or over, free transport applies if the nearest suitable school is more than 3 "
            "miles away (other conditions can also qualify).", {
        "en": "My child is 9. How far away must the school be to get free school transport?",
        "pl": "Moje dziecko ma 9 lat. Jak daleko musi być szkoła, żeby przysługiwał darmowy transport?",
        "ro": "Copilul meu are 9 ani. Cât de departe trebuie să fie școala ca să primească transport gratuit?",
        "ar": "عمر طفلي 9 سنوات. ما المسافة التي يجب أن تبعدها المدرسة للحصول على نقل مدرسي مجاني؟",
        "ur": "میرا بچہ 9 سال کا ہے۔ مفت اسکول ٹرانسپورٹ کے لیے اسکول کتنا دور ہونا چاہیے؟"}),
    "S19": ("schools", G + "school-uniform", "more than 3 items of branded school uniform",
            "From September 2026 schools should not require more than 3 branded items (4 for secondary and "
            "middle schools if one is a tie).", {
        "en": "How many branded uniform items can a school make me buy?",
        "pl": "Ile elementów mundurka z logo szkoły szkoła może kazać mi kupić?",
        "ro": "Câte articole de uniformă cu sigla școlii mă poate obliga școala să cumpăr?",
        "ar": "كم عدد قطع الزي المدرسي التي تحمل شعار المدرسة التي يمكن للمدرسة أن تُلزمني بشرائها؟",
        "ur": "اسکول مجھے اسکول کے لوگو والی یونیفارم کی کتنی اشیاء خریدنے پر مجبور کر سکتا ہے؟"}),
    "S20": ("schools", G + "children-with-special-educational-needs", "within 16 weeks",
            "The local authority must tell you within 16 weeks whether an EHC plan will be made; the final "
            "plan is due within 20 weeks of the request.", {
        "en": "How long does the council take to decide on an EHC plan?",
        "pl": "Ile czasu ma samorząd na decyzję w sprawie planu EHC?",
        "ro": "Cât timp are consiliul local ca să decidă asupra unui plan EHC?",
        "ar": "كم من الوقت يستغرق المجلس المحلي لاتخاذ قرار بشأن خطة EHC؟",
        "ur": "کونسل کو EHC پلان کے بارے میں فیصلہ کرنے میں کتنا وقت لگتا ہے؟"}),
    "S21": ("schools", G + "children-with-special-educational-needs",
            "you can ask your local authority to carry out an assessment",
            "Yes. You can ask your local authority to carry out an EHC needs assessment.", {
        "en": "Can I ask the council to assess my child for an EHC plan?",
        "pl": "Czy mogę poprosić samorząd o ocenę potrzeb mojego dziecka w celu przyznania planu EHC?",
        "ro": "Pot cere consiliului local să evalueze copilul meu pentru un plan EHC?",
        "ar": "هل يمكنني أن أطلب من المجلس المحلي تقييم طفلي للحصول على خطة EHC؟",
        "ur": "کیا میں کونسل سے اپنے بچے کا EHC پلان کے لیے جائزہ لینے کی درخواست کر سکتا ہوں؟"}),
    "S22": ("schools", G + "types-of-school", "free schools are funded by the government but are not run by the local authority",
            "Free schools are funded by the government but not run by the local authority. They are "
            "all-ability, can change term lengths and do not have to follow the national curriculum.", {
        "en": "What is a free school?",
        "pl": "Czym jest szkoła typu free school?",
        "ro": "Ce este o școală de tip free school?",
        "ar": "ما هي المدرسة من نوع free school؟",
        "ur": "فری اسکول (free school) کیا ہوتا ہے؟"}),
    "S23": ("schools", G + "types-of-school", "academies do not charge fees",
            "No. Academies are funded directly by the government and do not charge fees.", {
        "en": "Do academies charge school fees?",
        "pl": "Czy akademie (academies) pobierają opłaty za naukę?",
        "ro": "Academiile (academies) percep taxe școlare?",
        "ar": "هل تفرض مدارس الأكاديمية (academies) رسومًا دراسية؟",
        "ur": "کیا اکیڈمی اسکول فیس لیتے ہیں؟"}),
    "S24": ("schools", G + "school-term-holiday-dates", "holiday dates on your local council",
            "Term, half term and holiday dates are on your local council's website.", {
        "en": "Where can I find my child's school holiday dates?",
        "pl": "Gdzie znajdę daty ferii i przerw szkolnych mojego dziecka?",
        "ro": "Unde găsesc datele vacanțelor școlare ale copilului meu?",
        "ar": "أين أجد مواعيد العطل المدرسية لطفلي؟",
        "ur": "مجھے اپنے بچے کی اسکول کی چھٹیوں کی تاریخیں کہاں ملیں گی؟"}),
    "S25": ("schools", G + "know-when-you-can-leave-school", "stay in full-time education, for example at a college",
            "Until 18 they must stay in full-time education, start an apprenticeship, or spend 20 hours or "
            "more a week working or volunteering while in part-time education or training.", {
        "en": "My child left school at 16. What must they do until they are 18?",
        "pl": "Moje dziecko skończyło szkołę w wieku 16 lat. Co musi robić do 18. roku życia?",
        "ro": "Copilul meu a terminat școala la 16 ani. Ce trebuie să facă până la 18 ani?",
        "ar": "ترك طفلي المدرسة في سن 16. ما الذي يجب عليه فعله حتى يبلغ 18 عامًا؟",
        "ur": "میرے بچے نے 16 سال کی عمر میں اسکول چھوڑ دیا۔ 18 سال کی عمر تک اسے کیا کرنا ہوگا؟"}),
    "S26": ("schools", G + "complain-about-school", "within 6 months of the discrimination taking place",
            "You must send a disability discrimination complaint to the SEND tribunal within 6 months of the "
            "discrimination. It is free.", {
        "en": "How long do I have to complain to the SEND tribunal about disability discrimination at school?",
        "pl": "Ile mam czasu na złożenie skargi do trybunału SEND w sprawie dyskryminacji z powodu niepełnosprawności w szkole?",
        "ro": "Cât timp am ca să depun o plângere la tribunalul SEND pentru discriminare pe motiv de dizabilitate la școală?",
        "ar": "ما المدة المتاحة لي لتقديم شكوى إلى محكمة SEND بشأن التمييز بسبب الإعاقة في المدرسة؟",
        "ur": "اسکول میں معذوری کی بنیاد پر امتیاز کی شکایت SEND ٹریبونل میں کرنے کے لیے میرے پاس کتنا وقت ہے؟"}),
    # ---------- housing ----------
    "H11": ("housing", G + "private-renting", "rent for the year is less than £50,000",
            "Up to 5 weeks' rent if the yearly rent is under £50,000, or 6 weeks' rent if it is £50,000 or "
            "more. A holding deposit can be up to one week's rent.", {
        "en": "What is the most a landlord can ask for as a deposit?",
        "pl": "Jaką maksymalną kaucję może pobrać wynajmujący?",
        "ro": "Care este garanția maximă pe care o poate cere proprietarul?",
        "ar": "ما هو الحد الأقصى لمبلغ التأمين الذي يمكن أن يطلبه المالك؟",
        "ur": "مالک مکان زیادہ سے زیادہ کتنا ڈپازٹ مانگ سکتا ہے؟"}),
    "H12": ("housing", G + "tenancy-deposit-protection", "within 30 days of getting it",
            "Your landlord or letting agent must put the deposit in a government-approved scheme within 30 days "
            "of getting it.", {
        "en": "How quickly must my landlord put my deposit in a protection scheme?",
        "pl": "W jakim terminie wynajmujący musi umieścić moją kaucję w systemie ochrony depozytów?",
        "ro": "În cât timp trebuie proprietarul să pună garanția mea într-o schemă de protecție?",
        "ar": "خلال كم من الوقت يجب على المالك إيداع مبلغ التأمين في نظام حماية؟",
        "ur": "مالک مکان کو میرا ڈپازٹ کتنے دنوں میں تحفظ کی اسکیم میں رکھنا ہوتا ہے؟"}),
    "H13": ("housing", G + "tenancy-deposit-protection", "within 10 days of you both agreeing",
            "The landlord must return the deposit within 10 days of you both agreeing how much you will get back.", {
        "en": "How long does my landlord have to give my deposit back when I move out?",
        "pl": "Ile czasu ma wynajmujący na zwrot kaucji, gdy się wyprowadzam?",
        "ro": "Cât timp are proprietarul ca să-mi returneze garanția când mă mut?",
        "ar": "كم من الوقت لدى المالك لإعادة مبلغ التأمين عندما أغادر السكن؟",
        "ur": "جب میں گھر چھوڑوں تو مالک مکان کے پاس میرا ڈپازٹ واپس کرنے کے لیے کتنا وقت ہے؟"}),
    "H14": ("housing", G + "guidance/renters-rights-act-overview-for-tenants", "end it by giving 2 months",
            "You can end an assured periodic tenancy by giving 2 months' notice in writing, and you keep paying "
            "rent during the notice period.", {
        "en": "How much notice do I need to give to leave my rented home?",
        "pl": "Z jakim wyprzedzeniem muszę wypowiedzieć umowę najmu, żeby się wyprowadzić?",
        "ro": "Cu cât timp înainte trebuie să anunț că mă mut din locuința închiriată?",
        "ar": "ما مدة الإشعار التي يجب أن أقدمها لمغادرة المنزل المستأجر؟",
        "ur": "کرائے کا گھر چھوڑنے کے لیے مجھے کتنا پہلے نوٹس دینا ہوگا؟"}),
    "H15": ("housing", G + "guidance/renters-rights-act-overview-for-tenants", "a maximum of 1 month",
            "Nothing before you sign the tenancy agreement; after signing, a maximum of 1 month's rent in advance.", {
        "en": "How much rent can a landlord ask me to pay in advance?",
        "pl": "Ile czynszu z góry może żądać wynajmujący?",
        "ro": "Cât din chirie îmi poate cere proprietarul să plătesc în avans?",
        "ar": "كم من الإيجار يمكن للمالك أن يطلب مني دفعه مقدمًا؟",
        "ur": "مالک مکان مجھ سے کتنا کرایہ پیشگی ادا کرنے کا کہہ سکتا ہے؟"}),
    "H16": ("housing", G + "guidance/renters-rights-act-overview-for-tenants", "you can ask to keep a pet in the property",
            "Yes, you can ask. The landlord must consider the request and should give a reason if they refuse.", {
        "en": "Can I keep a pet in my rented home?",
        "pl": "Czy mogę trzymać zwierzę w wynajmowanym mieszkaniu?",
        "ro": "Pot ține un animal de companie în locuința închiriată?",
        "ar": "هل يمكنني تربية حيوان أليف في المنزل المستأجر؟",
        "ur": "کیا میں کرائے کے گھر میں پالتو جانور رکھ سکتا ہوں؟"}),
    "H17": ("housing", G + "guidance/renters-rights-act-overview-for-tenants",
            "cannot refuse to rent a property to a tenant who is on benefits",
            "No. A landlord cannot refuse to rent to a tenant because they are on benefits or have children.", {
        "en": "Can a landlord refuse to rent to me because I get benefits?",
        "pl": "Czy wynajmujący może odmówić mi wynajmu, bo pobieram zasiłki?",
        "ro": "Poate un proprietar să refuze să-mi închirieze pentru că primesc ajutoare sociale?",
        "ar": "هل يمكن للمالك أن يرفض تأجيري لأنني أحصل على إعانات؟",
        "ur": "کیا مالک مکان مجھے اس وجہ سے کرایہ پر گھر دینے سے انکار کر سکتا ہے کہ میں بینیفٹس لیتا ہوں؟"}),
    "H18": ("housing", G + "private-renting", "environmental health department at your local council",
            "Contact the environmental health department at your local council. It must act if the problems "
            "could harm you.", {
        "en": "My landlord will not do the repairs. Who can help me?",
        "pl": "Wynajmujący nie chce zrobić napraw. Kto może mi pomóc?",
        "ro": "Proprietarul nu vrea să facă reparațiile. Cine mă poate ajuta?",
        "ar": "المالك لا يقوم بالإصلاحات. من يمكنه مساعدتي؟",
        "ur": "میرا مالک مکان مرمت نہیں کر رہا۔ میری مدد کون کر سکتا ہے؟"}),
    "H19": ("housing", G + "private-renting", "annual gas safety check",
            "Yes. A registered engineer must do an annual gas safety check, and the landlord must give you a "
            "copy before you move in or within 28 days of the check.", {
        "en": "Does my landlord have to do a gas safety check?",
        "pl": "Czy wynajmujący musi przeprowadzać kontrolę bezpieczeństwa instalacji gazowej?",
        "ro": "Este proprietarul obligat să facă o verificare a siguranței instalației de gaz?",
        "ar": "هل يجب على المالك إجراء فحص لسلامة الغاز؟",
        "ur": "کیا مالک مکان کو گیس کی حفاظتی جانچ کروانی ضروری ہے؟"}),
    "H20": ("housing", G + "private-renting-evictions", "fine of up to £40,000",
            "Local councils can prosecute landlords or give a fine of up to £40,000 for harassment or illegal "
            "eviction.", {
        "en": "How much can a landlord be fined for illegally evicting a tenant?",
        "pl": "Jaką grzywnę może dostać wynajmujący za nielegalną eksmisję najemcy?",
        "ro": "Ce amendă poate primi un proprietar pentru evacuarea ilegală a unui chiriaș?",
        "ar": "ما قيمة الغرامة التي يمكن فرضها على المالك بسبب الإخلاء غير القانوني للمستأجر؟",
        "ur": "کرایہ دار کو غیر قانونی طور پر نکالنے پر مالک مکان کو کتنا جرمانہ ہو سکتا ہے؟"}),
    "H21": ("housing", G + "private-renting-evictions", "withholding keys",
            "Harassment can include stopping services like electricity, withholding keys, refusing repairs, "
            "threats, threatening to change the locks and opening or taking post.", {
        "en": "What counts as harassment by a landlord?",
        "pl": "Co jest uważane za nękanie ze strony wynajmującego?",
        "ro": "Ce se consideră hărțuire din partea proprietarului?",
        "ar": "ما الذي يُعد تحرشًا أو مضايقة من قبل المالك؟",
        "ur": "مالک مکان کی طرف سے ہراسانی میں کیا شامل ہے؟"}),
    "H22": ("housing", G + "housing-benefit", "reduced by 14%",
            "In council or social housing, Housing Benefit is reduced by 14% of the eligible rent for 1 spare "
            "bedroom and 25% for 2 or more.", {
        "en": "Will my Housing Benefit go down if I have a spare bedroom?",
        "pl": "Czy mój dodatek mieszkaniowy zostanie obniżony, jeśli mam wolną sypialnię?",
        "ro": "Îmi va scădea Housing Benefit dacă am un dormitor liber?",
        "ar": "هل ستنخفض إعانة السكن (Housing Benefit) إذا كان لدي غرفة نوم إضافية؟",
        "ur": "اگر میرے پاس ایک فالتو بیڈروم ہو تو کیا میرا ہاؤسنگ بینیفٹ کم ہو جائے گا؟"}),
    "H23": ("housing", G + "universal-credit", "around 5 weeks to get your first payment",
            "It usually takes around 5 weeks. You can apply for an advance if you need money while you wait.", {
        "en": "How long does it take to get the first Universal Credit payment?",
        "pl": "Ile czasu trzeba czekać na pierwszą wypłatę Universal Credit?",
        "ro": "Cât durează până primesc prima plată Universal Credit?",
        "ar": "كم من الوقت يستغرق الحصول على أول دفعة من Universal Credit؟",
        "ur": "یونیورسل کریڈٹ کی پہلی ادائیگی ملنے میں کتنا وقت لگتا ہے؟"}),
    "H24": ("housing", G + "universal-credit", "£16,000 or less in money, savings and investments",
            "You must have £16,000 or less in money, savings and investments. Over £6,000 reduces the payment.", {
        "en": "How much savings can I have and still claim Universal Credit?",
        "pl": "Ile oszczędności mogę mieć, żeby nadal ubiegać się o Universal Credit?",
        "ro": "Câte economii pot avea ca să pot solicita în continuare Universal Credit?",
        "ar": "ما مقدار المدخرات التي يمكنني امتلاكها مع الاستمرار في المطالبة بـ Universal Credit؟",
        "ur": "یونیورسل کریڈٹ کے لیے درخواست دیتے ہوئے میرے پاس زیادہ سے زیادہ کتنی بچت ہو سکتی ہے؟"}),
    "H25": ("housing", G + "universal-credit", "£303.94 a month for each child",
            "£303.94 a month for each child who lives with you, with an extra £47.94 for a first child born "
            "before 6 April 2017.", {
        "en": "How much extra Universal Credit do I get for each child?",
        "pl": "Ile dodatkowych pieniędzy z Universal Credit dostaję na każde dziecko?",
        "ro": "Câți bani în plus primesc din Universal Credit pentru fiecare copil?",
        "ar": "كم أحصل من مبلغ إضافي في Universal Credit عن كل طفل؟",
        "ur": "یونیورسل کریڈٹ میں ہر بچے کے لیے مجھے کتنی اضافی رقم ملتی ہے؟"}),
    "H26": ("housing", G + "council-tax", "a full-time student do not have to pay council tax",
            "Households where everyone is a full-time student do not have to pay Council Tax. If you get a "
            "bill, apply for an exemption.", {
        "en": "Do students have to pay Council Tax?",
        "pl": "Czy studenci muszą płacić Council Tax?",
        "ro": "Studenții trebuie să plătească Council Tax?",
        "ar": "هل يجب على الطلاب دفع ضريبة المجلس (Council Tax)؟",
        "ur": "کیا طلبہ کو کونسل ٹیکس ادا کرنا پڑتا ہے؟"}),
    "H27": ("housing", G + "council-tax", "over 12 months instead of 10",
            "Yes. Contact your council straight away; it can spread payments over 12 months instead of 10.", {
        "en": "I am struggling to pay my Council Tax. Can I pay it over 12 months?",
        "pl": "Mam problem z płaceniem Council Tax. Czy mogę rozłożyć płatności na 12 miesięcy?",
        "ro": "Îmi este greu să plătesc Council Tax. Pot să-l plătesc în 12 luni?",
        "ar": "أواجه صعوبة في دفع ضريبة المجلس. هل يمكنني دفعها على 12 شهرًا؟",
        "ur": "مجھے کونسل ٹیکس ادا کرنے میں مشکل ہو رہی ہے۔ کیا میں اسے 12 مہینوں میں ادا کر سکتا ہوں؟"}),
    # ---------- health ----------
    "M11": ("health", GP, "usually be within 5 days",
            "You should be told when you are registered, usually within 5 days of the surgery getting your "
            "details, but it may take longer.", {
        "en": "How long does it take to be registered with a GP after I apply online?",
        "pl": "Ile trwa rejestracja u lekarza rodzinnego po złożeniu wniosku online?",
        "ro": "Cât durează înregistrarea la medicul de familie după ce aplic online?",
        "ar": "كم من الوقت يستغرق التسجيل لدى الطبيب العام بعد التقديم عبر الإنترنت؟",
        "ur": "آن لائن درخواست دینے کے بعد جی پی کے ساتھ رجسٹریشن میں کتنا وقت لگتا ہے؟"}),
    "M12": ("health", GP, "temporary patient for up to 3 months",
            "Yes. You can register with a GP surgery as a temporary patient for up to 3 months using a "
            "temporary services form.", {
        "en": "Can I see a GP if I am only staying in an area for a few weeks?",
        "pl": "Czy mogę pójść do lekarza rodzinnego, jeśli przebywam w danej okolicy tylko kilka tygodni?",
        "ro": "Pot merge la un medic de familie dacă stau într-o zonă doar câteva săptămâni?",
        "ar": "هل يمكنني رؤية طبيب عام إذا كنت سأبقى في منطقة ما لبضعة أسابيع فقط؟",
        "ur": "اگر میں کسی علاقے میں صرف چند ہفتے رہ رہا ہوں تو کیا میں جی پی سے مل سکتا ہوں؟"}),
    "M13": ("health", GP, "write to you within 14 days to explain why",
            "Yes. If a GP surgery refuses to register you, it must write to you within 14 days to explain why.", {
        "en": "If a GP surgery refuses to register me, do they have to tell me why?",
        "pl": "Jeśli przychodnia odmówi mi rejestracji, czy musi podać powód?",
        "ro": "Dacă un cabinet de medicină de familie refuză să mă înregistreze, trebuie să-mi spună de ce?",
        "ar": "إذا رفضت عيادة الطبيب العام تسجيلي، هل يجب أن تخبرني بالسبب؟",
        "ur": "اگر جی پی سرجری مجھے رجسٹر کرنے سے انکار کرے تو کیا انہیں وجہ بتانی ہوگی؟"}),
    "M14": ("health", GPA, "saturdays between 9am and 5pm",
            "Yes. You can see a healthcare professional on weekday evenings 6.30pm to 8pm and on Saturdays 9am "
            "to 5pm.", {
        "en": "Can I get a GP appointment in the evening or at the weekend?",
        "pl": "Czy mogę umówić się do lekarza rodzinnego wieczorem lub w weekend?",
        "ro": "Pot primi o programare la medicul de familie seara sau în weekend?",
        "ar": "هل يمكنني الحصول على موعد مع الطبيب العام في المساء أو في عطلة نهاية الأسبوع؟",
        "ur": "کیا مجھے شام یا ہفتے کے آخر میں جی پی کی اپائنٹمنٹ مل سکتی ہے؟"}),
    "M15": ("health", U111, "111 online is for people aged 5 and over",
            "No. 111 online is for people aged 5 and over; call 111 for a child under 5.", {
        "en": "Can I use 111 online for my 3-year-old?",
        "pl": "Czy mogę skorzystać z 111 online dla mojego 3-letniego dziecka?",
        "ro": "Pot folosi 111 online pentru copilul meu de 3 ani?",
        "ar": "هل يمكنني استخدام خدمة 111 عبر الإنترنت لطفلي البالغ من العمر 3 سنوات؟",
        "ur": "کیا میں اپنے 3 سالہ بچے کے لیے 111 آن لائن استعمال کر سکتا ہوں؟"}),
    "M16": ("health", U111, "emergency supply of regularly prescribed medicine",
            "Yes. 111 online can send a request to a local pharmacy for an emergency supply of your regular "
            "medicine until you can get your repeat prescription.", {
        "en": "I have run out of my regular medicine. Can 111 help?",
        "pl": "Skończyły mi się leki, które stale przyjmuję. Czy 111 może pomóc?",
        "ro": "Am rămas fără medicamentele pe care le iau regulat. Mă poate ajuta 111?",
        "ar": "نفد دوائي الذي أتناوله بانتظام. هل يمكن لخدمة 111 مساعدتي؟",
        "ur": "میری باقاعدہ دوا ختم ہو گئی ہے۔ کیا 111 مدد کر سکتا ہے؟"}),
    "M17": ("health", AE, "do not drive to a&e",
            "No. Do not drive to A&E. Ask someone to drive you or call 999 for an ambulance.", {
        "en": "Should I drive myself to A&E?",
        "pl": "Czy powinienem sam pojechać samochodem na SOR (A&E)?",
        "ro": "Ar trebui să conduc singur până la urgențe (A&E)?",
        "ar": "هل يجب أن أقود السيارة بنفسي إلى قسم الطوارئ (A&E)؟",
        "ur": "کیا مجھے خود گاڑی چلا کر A&E جانا چاہیے؟"}),
    "M18": ("health", C999, "calling 999 does not always mean an ambulance will be sent",
            "No. Calling 999 does not always mean an ambulance is sent; you may be told to make your own way "
            "to A&E or be seen elsewhere.", {
        "en": "If I call 999, will an ambulance always come?",
        "pl": "Czy jeśli zadzwonię pod 999, zawsze przyjedzie karetka?",
        "ro": "Dacă sun la 999, va veni întotdeauna o ambulanță?",
        "ar": "إذا اتصلت بالرقم 999، هل ستأتي سيارة إسعاف دائمًا؟",
        "ur": "اگر میں 999 پر کال کروں تو کیا ایمبولینس ہمیشہ آئے گی؟"}),
    "M19": ("health", DENT, "within 2 months, you do not have to pay extra",
            "If the further treatment within 2 months is in the same or a lower band, you do not pay extra; a "
            "higher band means paying the higher fee.", {
        "en": "Do I have to pay again if I need more dental treatment a few weeks later?",
        "pl": "Czy muszę płacić ponownie, jeśli po kilku tygodniach potrzebuję dalszego leczenia stomatologicznego?",
        "ro": "Trebuie să plătesc din nou dacă am nevoie de tratament stomatologic suplimentar după câteva săptămâni?",
        "ar": "هل يجب أن أدفع مرة أخرى إذا احتجت إلى علاج أسنان إضافي بعد بضعة أسابيع؟",
        "ur": "اگر مجھے چند ہفتوں بعد دانتوں کا مزید علاج چاہیے تو کیا مجھے دوبارہ ادائیگی کرنی ہوگی؟"}),
    "M20": ("health", DENT, "your false teeth (dentures) need to be repaired",
            "No, repairing dentures is free. If they cannot be repaired, you pay for new ones.", {
        "en": "Do I have to pay to get my dentures repaired on the NHS?",
        "pl": "Czy muszę płacić za naprawę protezy zębowej w NHS?",
        "ro": "Trebuie să plătesc pentru repararea protezei dentare la NHS?",
        "ar": "هل يجب أن أدفع لإصلاح طقم أسناني لدى NHS؟",
        "ur": "کیا NHS میں ڈینچر (مصنوعی دانت) کی مرمت کے لیے مجھے ادائیگی کرنی ہوگی؟"}),
    "M21": ("health", PHARM, "take it to your pharmacy to be disposed of safely",
            "Do not put it in the bin or flush it away. Take it to a pharmacy to be disposed of safely.", {
        "en": "What should I do with old medicines I no longer need?",
        "pl": "Co zrobić ze starymi lekami, których już nie potrzebuję?",
        "ro": "Ce ar trebui să fac cu medicamentele vechi de care nu mai am nevoie?",
        "ar": "ماذا أفعل بالأدوية القديمة التي لم أعد بحاجة إليها؟",
        "ur": "مجھے پرانی دواؤں کا کیا کرنا چاہیے جن کی اب ضرورت نہیں؟"}),
    "M22": ("health", PREG, "maternity exemption (matex) certificate",
            "Yes. Ask your midwife or GP about the maternity exemption (MATEX) certificate, which gives free NHS "
            "prescriptions and free dental care.", {
        "en": "Can I get free prescriptions while I am pregnant?",
        "pl": "Czy w ciąży mogę dostawać leki na receptę za darmo?",
        "ro": "Pot primi medicamente gratuite pe rețetă cât sunt însărcinată?",
        "ar": "هل يمكنني الحصول على الأدوية الموصوفة مجانًا أثناء الحمل؟",
        "ur": "کیا حمل کے دوران مجھے نسخے کی دوائیں مفت مل سکتی ہیں؟"}),
    "M23": ("health", LIS, "£16,000 for everyone else",
            "Your savings, investments or property (not your home) must not be over £16,000, or £23,250 if you "
            "live permanently in a care home.", {
        "en": "What is the savings limit for the NHS Low Income Scheme?",
        "pl": "Jaki jest limit oszczędności w programie NHS Low Income Scheme?",
        "ro": "Care este limita de economii pentru NHS Low Income Scheme?",
        "ar": "ما هو حد المدخرات في برنامج NHS Low Income Scheme؟",
        "ur": "NHS لو انکم اسکیم کے لیے بچت کی حد کیا ہے؟"}),
    "M24": ("health", LIS, "complete an hc1 form",
            "Apply online, or by post using an HC1 form sent to the address on the form.", {
        "en": "How do I apply for the NHS Low Income Scheme by post?",
        "pl": "Jak złożyć wniosek do NHS Low Income Scheme pocztą?",
        "ro": "Cum aplic prin poștă pentru NHS Low Income Scheme?",
        "ar": "كيف أتقدم بطلب للانضمام إلى NHS Low Income Scheme عبر البريد؟",
        "ur": "میں ڈاک کے ذریعے NHS لو انکم اسکیم کے لیے کیسے درخواست دوں؟"}),
    "M25": ("health", ABROAD, "are exempt from charges",
            "Yes. A&E services are free to everyone, but emergency treatment after being admitted to hospital "
            "is not included.", {
        "en": "I am visiting England. Is A&E free for me?",
        "pl": "Jestem w Anglii z wizytą. Czy SOR (A&E) jest dla mnie darmowy?",
        "ro": "Sunt în vizită în Anglia. Este gratuit serviciul de urgențe (A&E) pentru mine?",
        "ar": "أنا في زيارة إلى إنجلترا. هل خدمة الطوارئ (A&E) مجانية بالنسبة لي؟",
        "ur": "میں انگلینڈ کے دورے پر ہوں۔ کیا A&E میرے لیے مفت ہے؟"}),
    "M26": ("health", ABROAD, "charged at 150% of the national nhs rate",
            "If you are not ordinarily resident and must pay for NHS hospital treatment, you are charged 150% "
            "of the national NHS rate.", {
        "en": "How much do overseas visitors pay for NHS hospital treatment?",
        "pl": "Ile płacą osoby przyjezdne z zagranicy za leczenie szpitalne w NHS?",
        "ro": "Cât plătesc vizitatorii din străinătate pentru tratamentul în spitalele NHS?",
        "ar": "كم يدفع الزوار من الخارج مقابل العلاج في مستشفيات NHS؟",
        "ur": "بیرون ملک سے آنے والے افراد NHS اسپتال کے علاج کے لیے کتنی ادائیگی کرتے ہیں؟"}),
    "M27": ("health", VACC, "around 20 weeks pregnant",
            "The whooping cough (pertussis) vaccine is offered around 20 weeks of pregnancy.", {
        "en": "When should I have the whooping cough vaccine in pregnancy?",
        "pl": "Kiedy w ciąży należy przyjąć szczepionkę przeciw krztuścowi?",
        "ro": "Când ar trebui să fac vaccinul împotriva tusei convulsive în sarcină?",
        "ar": "متى يجب أن أتلقى لقاح السعال الديكي أثناء الحمل؟",
        "ur": "حمل کے دوران کالی کھانسی کی ویکسین کب لگوانی چاہیے؟"}),
}

UNANSWERABLE = {
    "U11": {"en": "How do I apply for a Blue Badge for disabled parking?",
            "pl": "Jak ubiegać się o Blue Badge, czyli kartę parkingową dla osób niepełnosprawnych?",
            "ro": "Cum aplic pentru un Blue Badge pentru parcarea persoanelor cu dizabilități?",
            "ar": "كيف أتقدم بطلب للحصول على Blue Badge لمواقف ذوي الإعاقة؟",
            "ur": "معذور افراد کی پارکنگ کے لیے بلیو بیج (Blue Badge) کی درخواست کیسے دوں؟"},
    "U12": {"en": "How do I get a National Insurance number?",
            "pl": "Jak uzyskać numer National Insurance?",
            "ro": "Cum obțin un număr National Insurance?",
            "ar": "كيف أحصل على رقم التأمين الوطني (National Insurance)؟",
            "ur": "میں نیشنل انشورنس نمبر کیسے حاصل کروں؟"},
    "U13": {"en": "How much is Child Benefit per week?",
            "pl": "Ile wynosi tygodniowo Child Benefit (zasiłek na dziecko)?",
            "ro": "Cât este Child Benefit (alocația pentru copii) pe săptămână?",
            "ar": "كم تبلغ إعانة الطفل (Child Benefit) أسبوعيًا؟",
            "ur": "چائلڈ بینیفٹ ہفتہ وار کتنا ہے؟"},
    "U14": {"en": "How do I apply for a student loan for university?",
            "pl": "Jak złożyć wniosek o kredyt studencki na studia?",
            "ro": "Cum aplic pentru un împrumut pentru studenți pentru facultate?",
            "ar": "كيف أتقدم بطلب للحصول على قرض طلابي للدراسة الجامعية؟",
            "ur": "یونیورسٹی کے لیے اسٹوڈنٹ لون کی درخواست کیسے دوں؟"},
    "U15": {"en": "How do I report a pothole in my road?",
            "pl": "Jak zgłosić dziurę w jezdni na mojej ulicy?",
            "ro": "Cum raportez o groapă în carosabil pe strada mea?",
            "ar": "كيف أبلغ عن حفرة في الطريق في شارعي؟",
            "ur": "میں اپنی سڑک میں گڑھے کی اطلاع کیسے دوں؟"},
    "U16": {"en": "My rubbish bin was not collected this week. What should I do?",
            "pl": "W tym tygodniu nie odebrano moich śmieci. Co powinienem zrobić?",
            "ro": "Gunoiul meu nu a fost ridicat săptămâna aceasta. Ce ar trebui să fac?",
            "ar": "لم تُجمع حاوية القمامة الخاصة بي هذا الأسبوع. ماذا أفعل؟",
            "ur": "اس ہفتے میرا کوڑا نہیں اٹھایا گیا۔ مجھے کیا کرنا چاہیے؟"},
    "U17": {"en": "How do I apply for Carer's Allowance?",
            "pl": "Jak złożyć wniosek o Carer's Allowance (zasiłek dla opiekuna)?",
            "ro": "Cum aplic pentru Carer's Allowance (indemnizația de îngrijitor)?",
            "ar": "كيف أتقدم بطلب للحصول على بدل مقدم الرعاية (Carer's Allowance)؟",
            "ur": "کیئررز الاؤنس کے لیے درخواست کیسے دوں؟"},
    "U18": {"en": "How do I change my name by deed poll?",
            "pl": "Jak zmienić nazwisko za pomocą deed poll?",
            "ro": "Cum îmi schimb numele prin deed poll?",
            "ar": "كيف أغير اسمي عن طريق وثيقة deed poll؟",
            "ur": "میں ڈیڈ پول کے ذریعے اپنا نام کیسے تبدیل کروں؟"},
    "U19": {"en": "Can I get a free hearing aid on the NHS?",
            "pl": "Czy mogę dostać darmowy aparat słuchowy w NHS?",
            "ro": "Pot primi gratuit un aparat auditiv prin NHS?",
            "ar": "هل يمكنني الحصول على سماعة أذن طبية مجانية من NHS؟",
            "ur": "کیا مجھے NHS سے مفت سننے کا آلہ مل سکتا ہے؟"},
    "U20": {"en": "How long is statutory maternity leave?",
            "pl": "Jak długo trwa ustawowy urlop macierzyński?",
            "ro": "Cât durează concediul de maternitate legal?",
            "ar": "ما هي مدة إجازة الأمومة القانونية؟",
            "ur": "قانونی زچگی کی چھٹی کتنی طویل ہوتی ہے؟"},
}


def main():
    pages = {}
    for line in open(ROOT / "data/processed/pages.jsonl"):
        r = json.loads(line)
        pages[r["url"]] = " ".join(s["text"] for s in r["sections"]).lower()
    bad = [(q, url, ev) for q, (_, url, ev, _, _) in HELDOUT.items() if url not in pages or ev.lower() not in pages[url]]
    if bad:
        sys.exit("evidence not found on gold page:\n" + "\n".join(map(str, bad)))
    langs = ["en", "pl", "ro", "ar", "ur"]
    assert all(list(qs) == langs for *_, qs in HELDOUT.values()) and all(list(q) == langs for q in UNANSWERABLE.values())

    with open(ROOT / "eval/heldout_queries.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "domain", "lang", "question", "gold_url", "evidence", "translation_status"])
        for qid, (domain, url, ev, _, qs) in HELDOUT.items():
            for lang, text in qs.items():
                w.writerow([qid, domain, lang, text, url, ev, "source" if lang == "en" else "unverified"])
    with open(ROOT / "eval/heldout_unanswerable.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["qid", "lang", "question", "translation_status"])
        for qid, qs in UNANSWERABLE.items():
            for lang, text in qs.items():
                w.writerow([qid, lang, text, "source" if lang == "en" else "unverified"])

    # One row per topic (English question), the reference used by the scoring rubric.
    cal = list(csv.DictReader(open(ROOT / "eval/queries.csv", encoding="utf-8")))
    cal_un = list(csv.DictReader(open(ROOT / "eval/unanswerable.csv", encoding="utf-8")))
    rows = []
    for r in cal:
        if r["lang"] == "en":
            rows.append(["calibration", r["qid"], r["domain"], True, r["question"], r["gold_url"], r["evidence"],
                         CALIBRATION_REFERENCE[r["qid"]], "answer"])
    for r in cal_un:
        if r["lang"] == "en":
            rows.append(["calibration", r["qid"], "", False, r["question"], "", "", "", "refuse"])
    for qid, (domain, url, ev, ref, qs) in HELDOUT.items():
        rows.append(["heldout", qid, domain, True, qs["en"], url, ev, ref, "answer"])
    for qid, qs in UNANSWERABLE.items():
        rows.append(["heldout", qid, "", False, qs["en"], "", "", "", "refuse"])
    with open(ROOT / "eval/gold_set.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "qid", "domain", "answerable", "question_en", "gold_url", "evidence",
                    "reference_answer", "expected"])
        w.writerows(rows)
    n_ans = sum(r[3] for r in rows)
    print(f"gold set: {len(rows)} topics ({n_ans} answerable, {len(rows) - n_ans} unanswerable); "
          f"held-out: {len(HELDOUT)} answerable + {len(UNANSWERABLE)} unanswerable x 5 languages; "
          "all evidence phrases found verbatim on their gold page")


if __name__ == "__main__":
    main()
