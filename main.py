import os, re, logging
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

EXCEL_FILE = "expenses.xlsx"

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

CATEGORIES = {
    "الأكل": [
        "اكل","طعام","غدا","عشا","عشاء","فطور","سحور","طبخ","مطعم","وجبه","سندوتش","برجر","برقر",
        "شاورما","كبسه","رز","سمبوسه","بيتزا","معصوب","بقاله","بقالة","سوبرماركت","تميس","فواكه","خضار"
    ],
    "المشروبات": [
        "قهوه","قهوة","شاي","عصير","مويه","ماء","بيبسي","كولا","مشروب","موكا","كابتشينو","لاتيه","نسكافيه","حليب"
    ],
    "المواصلات": [
        "بنزين","وقود","تاكسي","تكسي","اوبر","أوبر","كريم","مواصلات","باركينج","مواقف","موقف","باص","قطار","تذاكر","ديزل"
    ],
    "التسوق": [
        "ملابس","قميص","تيشيرت","بنطال","بنطلون","حذاء","جزمه","عطر","عطور","شنطه","حقيبه","اكسسوار","ساعه"
    ],
    "الفواتير": [
        "فاتوره","فاتورة","فواتير","كهرب","كهرباء","مويه","ماء","انترنت","انترنِت","نت","جوال","هاتف",
        "دي اس ال","الياف","رسوم","ضريبه","ضريبة","بلديه","بلدية"
    ],
    "السكن": [
        "ايجار","إيجار","أجار","rent","سكن","شقه","شقة","بيت","فندق","غرفه","غرفة","قسط","دفعة"
    ],
    "الصحة": [
        "مستشفى","مستوصف","صيدليه","صيدلية","دواء","علاج","تحاليل","تحليل","اسنان","أسنان","طبيب","نظارات"
    ],
    "الترفيه": [
        "سينما","فيلم","العاب","ألعاب","بلايستيشن","ps","ملاهي","رحله","رحلة","طلعه","طلعة","كشتة","كشته","مقهى","كوفي"
    ],
    "الاشتراكات": [
        "اشتراك","عضويه","عضوية","نتفلكس","شاهد","شاهد vip","يوتيوب بريميوم","spotify","سبوتفاي","apple music","بلايستيشن بلس"
    ],
    "الهدايا": [
        "هديه","هدية","عيديه","عيدية","هدايا","تبرع","صدقه","صدقة"
    ],
    "الصيانة": [
        "صيانه","صيانة","اصلاح","إصلاح","قطع غيار","زيت","غيار زيت","كفر","كفرات","ميكانيكي","سباك","كهربائي"
    ],
    "التعليم": [
        "مدرسه","مدرسة","جامعه","جامعة","دوره","دورة","كورس","كتاب","كتب","رسوم دراسيه","رسوم دراسية"
    ],
}

PRIORITY = list(CATEGORIES.keys())  # ترتيب أولوية التصنيف عند التعادل

def ensure_workbook():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = "Expenses"
        ws.append(["التاريخ", "الوقت", "القسم", "المبلغ", "النص"])
        wb.save(EXCEL_FILE)

def now_ksa():
    return datetime.utcnow() + timedelta(hours=3)

def normalize_ar(s: str) -> str:
    s = s.strip().lower()
    s = s.translate(ARABIC_DIGITS)
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ة","ه").replace("ى","ي").replace("ؤ","و").replace("ئ","ي").replace("ٔ","")
    s = s.replace("ـ","")
    return s

def tokenize_ar(s: str):
    s = normalize_ar(s)
    return [w for w in re.split(r"[^a-z\u0600-\u06FF0-9]+", s) if w]

def classify_category(text: str) -> str:
    tokens = tokenize_ar(text)
    text_norm = " ".join(tokens)
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, kws in CATEGORIES.items():
        for kw in kws:
            k = normalize_ar(kw)
            # عدّ ظهور الكلمة كـ substring أو token
            if k in text_norm:
                scores[cat] += 1
            else:
                for t in tokens:
                    if k in t or t in k:
                        scores[cat] += 1
                        break
    best = "غير محدد"
    best_score = 0
    for cat in PRIORITY:
        if scores[cat] > best_score:
            best_score = scores[cat]
            best = cat
    return best if best_score > 0 else "غير محدد"

def extract_amount(text: str):
    t = normalize_ar(text)
    m = re.search(r"-?\d+(?:[.,]\d+)?", t)
    if not m:
        return None
    amt = m.group(0).replace(",", ".")
    try:
        return float(amt)
    except:
        return None

def save_row(date_str: str, time_str: str, category: str, amount: float, raw: str):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([date_str, time_str, category, amount, raw])
    wb.save(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اكتب مثل: صرف 50 غدا / 20 قهوه / 35 بنزين")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    amount = extract_amount(text)
    if amount is None:
        await update.message.reply_text("لم أجد مبلغًا. مثال: 50 اكل")
        return
    category = classify_category(text)
    now = now_ksa()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    save_row(date_str, time_str, category, amount, text)
    await update.message.reply_text(f"تم ✅\nالقسم: {category}\nالمبلغ: {amount:g}\nالتاريخ: {date_str} {time_str}")

def main():
    ensure_workbook()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("الرجاء ضبط متغير البيئة BOT_TOKEN.")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
