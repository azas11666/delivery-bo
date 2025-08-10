import os, re, logging
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

EXCEL_FILE = "/data/expenses.xlsx"

# ---------- utils ----------
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

TYPE_EXPENSE = {"صرف","مصروف","مصروفات","دفع","سداد","شراء"}
TYPE_INCOME  = {"مكسب","دخل","ايراد","إيراد","ربح","ارباح","أرباح"}

CURRENCY_WORDS = {"ريال","رس","ر.س","sar"}

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

def normalize_ar(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.translate(ARABIC_DIGITS)
    s = (s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
           .replace("ة","ه").replace("ى","ي").replace("ؤ","و").replace("ئ","ي")
           .replace("ٔ","").replace("ـ",""))
    return s

def arabic_words(s: str):
    return re.findall(r"[\u0600-\u06FF]+", normalize_ar(s))

def detect_type(text: str, amount: float | None) -> str:
    toks = set(arabic_words(text))
    if toks & TYPE_INCOME:
        return "مكسب"
    if toks & TYPE_EXPENSE:
        return "صرف"
    if amount is not None and amount < 0:
        return "صرف"
    return "صرف"  # افتراضي

def extract_amount(text: str):
    t = normalize_ar(text)
    m = re.search(r"-?\d+(?:[.,]\d+)?", t)
    if not m:
        return None
    val = m.group(0).replace(",", ".")
    try:
        return float(val)
    except:
        return None

def extract_category(text: str) -> str:
    words = arabic_words(text)
    out = []
    for w in words:
        if w in TYPE_EXPENSE or w in TYPE_INCOME or w in CURRENCY_WORDS:
            continue
        out.append(w)
    if not out:
        return "غير محدد"
    # خذ 1-3 كلمات كاسم للقسم
    return " ".join(out[:3])

def save_row(date_str: str, time_str: str, tx_type: str, category: str, amount: float, raw: str):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([date_str, time_str, tx_type, category, amount, raw])
    wb.save(EXCEL_FILE)

# ---------- handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اكتب: 30 السيارة / صرف 25 قهوه / مكسب 50 مرسول")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    amount = extract_amount(text)
    if amount is None:
        await update.message.reply_text("لم أجد مبلغًا. مثال: 30 السيارة أو مكسب 50 مرسول")
        return
    tx_type = detect_type(text, amount)
    category = extract_category(text)

    now = now_ksa()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    save_row(date_str, time_str, tx_type, category, amount, text)

    await update.message.reply_text(
        f"تم ✅\nالنوع: {tx_type}\nالقسم: {category}\nالمبلغ: {amount:g}\nالتاريخ: {date_str} {time_str}"
    )

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_workbook()
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("ما لقيت الملف.")
        return
    with open(EXCEL_FILE, "rb") as f:
        await update.message.reply_document(f, filename=os.path.basename(EXCEL_FILE), caption="سجل المصروفات")

# ---------- main ----------
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
