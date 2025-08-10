import os, re, logging
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

EXCEL_FILE = "/data/expenses.xlsx"

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

INCOME_WORDS = {
    # Arabic
    "مكسب","ربح","ارباح","أرباح","دخل","ايراد","إيراد","ايرادات","مدفوعات",
    # English
    "profit","gain","gains","income","revenue","payments","payment"
}

CURRENCY_WORDS = {"ريال","رس","ر.س","sar","rs","riyal","riyals"}

EXCEL_TRIGGERS = {"excel","اكسل","السجل","الملف"}

CATEGORIES = {
    "الأكل": ["اكل","طعام","غدا","عشا","عشاء","فطور","سحور","طبخ","مطعم","وجبه","سندوتش",
              "شاورما","بيتزا","رز","كبسه","بقاله","بقالة","سوبرماركت","تميس","فواكه","خضار",
              "food","meal","breakfast","lunch","dinner","grocery","groceries","restaurant"],
    "المشروبات": ["قهوه","قهوة","شاي","عصير","مويه","ماء","بيبسي","كولا","موكا","كابتشينو",
                   "لاتيه","نسكافيه","حليب","drinks","drink","coffee","tea","juice","water","soda"],
    "المواصلات": ["بنزين","وقود","تاكسي","تكسي","اوبر","أوبر","كريم","مواصلات","باركينج",
                   "مواقف","باص","قطار","تذاكر","ديزل","gas","gasoline","fuel","uber","careem",
                   "taxi","parking","transport"],
    "الفواتير": ["فاتوره","فاتورة","فواتير","كهرب","كهرباء","مويه","ماء","انترنت","نت","جوال",
                 "هاتف","الياف","رسوم","ضريبه","ضريبة","بلديه","بلدية","bill","bills","electricity",
                 "internet","water","phone","tax","fees"],
    "التسوق": ["ملابس","قميص","بنطال","بنطلون","حذاء","جزمه","عطر","عطور","شنطه","حقيبه",
               "اكسسوار","ساعه","shopping","clothes","shoes","perfume","bag","watch","accessories"],
    "الصحة": ["مستشفى","مستوصف","صيدليه","صيدلية","دواء","علاج","تحاليل","تحليل","اسنان",
              "طبيب","نظارات","health","hospital","clinic","pharmacy","medicine","dentist","glasses"],
    "السكن": ["ايجار","إيجار","سكن","شقه","شقة","بيت","فندق","غرفه","غرفة","قسط","rent",
              "hotel","apartment","room","housing","installment"],
    "الترفيه": ["سينما","فيلم","العاب","ألعاب","بلايستيشن","ps","ملاهي","رحله","رحلة","طلعه",
                "طلعة","كشتة","كشته","مقهى","كوفي","entertainment","cinema","movie","games",
                "playstation","outing","trip","cafe","coffee shop"],
    "الصيانة": ["صيانه","صيانة","اصلاح","إصلاح","قطع غيار","زيت","غيار زيت","كفر","كفرات",
                "ميكانيكي","سباك","كهربائي","maintenance","repair","parts","oil","tires","mechanic"],
    "الهدايا": ["هديه","هدية","عيديه","عيدية","هدايا","تبرع","صدقه","صدقة","gift","donation","charity"],
    "التعليم": ["مدرسه","مدرسة","جامعه","جامعة","دوره","دورة","كورس","كتاب","كتب",
                "رسوم دراسيه","رسوم دراسية","school","university","course","books","tuition"],
}

PRIORITY = list(CATEGORIES.keys())

def ensure_workbook():
    if not os.path.exists(EXCEL_FILE):
        os.makedirs(os.path.dirname(EXCEL_FILE), exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Expenses"
        ws.append(["التاريخ", "الوقت", "النوع", "القسم", "المبلغ", "النص"])
        wb.save(EXCEL_FILE)

def now_ksa():
    return datetime.utcnow() + timedelta(hours=3)

def normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.translate(ARABIC_DIGITS)
    s = (s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
           .replace("ة","ه").replace("ى","ي").replace("ؤ","و").replace("ئ","ي")
           .replace("ٔ","").replace("ـ",""))
    return s

def tokens(s: str):
    s = normalize(s)
    return [w for w in re.split(r"[^a-z\u0600-\u06FF0-9]+", s) if w]

def extract_amount(text: str):
    t = normalize(text)
    m = re.search(r"-?\d+(?:[.,]\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except:
        return None

def detect_type(text: str, amount: float | None) -> str:
    toks = set(tokens(text))
    if toks & {normalize(w) for w in INCOME_WORDS}:
        return "مكسب"
    if amount is not None and amount < 0:
        return "صرف"
    return "صرف"

def classify_category(text: str) -> str:
    toks = tokens(text)
    joined = " ".join(toks)
    # تجاهل كلمات النوع والعملة
    ignore = {normalize(w) for w in INCOME_WORDS} | {normalize(w) for w in CURRENCY_WORDS}
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, kws in CATEGORIES.items():
        for kw in kws:
            k = normalize(kw)
            if k in ignore:
                continue
            if k in joined:
                scores[cat] += 1
            else:
                for t in toks:
                    if k in t or t in k:
                        scores[cat] += 1
                        break
    best, best_score = "غير محدد", 0
    for cat in PRIORITY:
        if scores[cat] > best_score:
            best, best_score = cat, scores[cat]
    return best if best_score > 0 else "غير محدد"

def save_row(date_str: str, time_str: str, tx_type: str, category: str, amount: float, raw: str):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([date_str, time_str, tx_type, category, amount, raw])
    wb.save(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل أي جملة فيها رقم. مثال: 50 بنزين / profit 100 / 30 food\nواكتب 'excel' لإرسال ملف السجل.")

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_workbook()
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("لا يوجد ملف.")
        return
    with open(EXCEL_FILE, "rb") as f:
        await update.message.reply_document(f, filename=os.path.basename(EXCEL_FILE), caption="سجل المصروفات")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if normalize(text) in EXCEL_TRIGGERS:
        await export_excel(update, context)
        return

    amount = extract_amount(text)
    if amount is None:
        await update.message.reply_text("أرسل رسالة تحتوي رقم المبلغ. مثال: 30 السيارة أو profit 50")
        return

    tx_type = detect_type(text, amount)
    category = classify_category(text)

    now = now_ksa()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    save_row(date_str, time_str, tx_type, category, amount, text)

    await update.message.reply_text(
        f"تم ✅\nالنوع: {tx_type}\nالقسم: {category}\nالمبلغ: {amount:g}\nالتاريخ: {date_str} {time_str}"
    )

def main():
    ensure_workbook()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("الرجاء ضبط متغير البيئة BOT_TOKEN.")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("excel", export_excel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
