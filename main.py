import os
import re
import sys
import logging
import ffmpeg
import whisper
from datetime import datetime, timedelta
from collections import defaultdict
from openpyxl import Workbook, load_workbook
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7799549664"))
EXCEL_FILE = "expenses.xlsx"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def ensure_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = "Expenses"
        ws.append(["التاريخ", "النوع", "الفئة", "الوصف", "المبلغ", "الدائن/المدين", "المستخدم"])
        wb.save(EXCEL_FILE)

def append_row(kind, category, desc, amount, user):
    ensure_excel()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    direction = "مدين" if kind == "صرف" else "دائن"
    ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kind, category, desc, float(amount), direction, user or ""])
    wb.save(EXCEL_FILE)

def load_rows():
    ensure_excel()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            continue
        dt = row[0]
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except:
                continue
        rows.append({"datetime": dt, "kind": row[1], "category": row[2], "desc": row[3], "amount": float(row[4] or 0)})
    return rows

def summarize(period="day"):
    rows = load_rows()
    now = datetime.now()
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime.min
    total_exp, total_inc = 0.0, 0.0
    for r in rows:
        if r["datetime"] >= start:
            if r["kind"] == "صرف":
                total_exp += r["amount"]
            else:
                total_inc += r["amount"]
    net = total_inc - total_exp
    sign = "ربح" if net >= 0 else "خسارة"
    return f"📊 ملخص {period}\n- المصروفات: {total_exp:.2f} ريال\n- الأرباح: {total_inc:.2f} ريال\n- الصافي: {abs(net):.2f} ريال ({sign})"

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
def normalize_numbers(text): return text.translate(ARABIC_DIGITS).replace(",", ".")
def extract_amount(text):
    t = normalize_numbers(text)
    m = re.search(r'(\d+(?:\.\d+)?)', t)
    return float(m.group(1)) if m else None

EXPENSE_WORDS = {"صرف", "مصروف", "دفعت", "اشتريت", "سحبت", "رسوم"}
INCOME_WORDS = {"ربح", "دخل", "كسبت", "حول", "وصلني", "مبيعات", "بيع"}
CATEGORY_MAP = {"بنزين": "سيارة", "سيارة": "سيارة", "صيانة": "صيانة", "قهوة": "أكل وشرب", "شاي": "أكل وشرب", "مطعم": "أكل وشرب", "أكل": "أكل وشرب", "أجرة": "نقل", "تاكسي": "نقل", "كهرب": "فواتير", "كهرباء": "فواتير", "ماء": "فواتير", "نت": "اتصالات", "سوا": "اتصالات", "زين": "اتصالات", "stc": "اتصالات", "اتصال": "اتصالات", "جوال": "اتصالات", "سوبرماركت": "تموين", "بقالة": "تموين", "مرسول": "أرباح مرسول"}

def detect_kind(text):
    t = text.replace("ـ", "").lower()
    if any(w in t for w in EXPENSE_WORDS): return "صرف"
    if any(w in t for w in INCOME_WORDS): return "ربح"
    if any(k in t for k in CATEGORY_MAP.keys()): return "صرف"
    return None

def detect_category(text):
    t = text.lower()
    for kw, cat in CATEGORY_MAP.items():
        if kw in t: return cat
    return "غير مصنّف"

whisper_model = whisper.load_model(WHISPER_MODEL_NAME)

def convert_ogg_to_wav(src_path, dst_path):
    ffmpeg.input(src_path).output(dst_path, ar=16000, ac=1).overwrite_output().run(quiet=True)

def transcribe_audio(path):
    result = whisper_model.transcribe(path, language="ar")
    return (result.get("text") or "").strip()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل نص أو صوت فيه المبلغ والفئة لتسجيل المصروفات أو الأرباح.")

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_excel()
    with open(EXCEL_FILE, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=EXCEL_FILE))

async def sum_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arg = (context.args[0].lower() if context.args else "day")
    if arg not in ("day", "week", "month", "all"): arg = "day"
    await update.message.reply_text(summarize(arg))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_sentence(update.message.text.strip(), update)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    v = update.message.voice or update.message.audio
    if not v: return
    file = await context.bot.get_file(v.file_id)
    ogg_path = f"/tmp/{v.file_unique_id}.ogg"
    wav_path = f"/tmp/{v.file_unique_id}.wav"
    await file.download_to_drive(custom_path=ogg_path)
    convert_ogg_to_wav(ogg_path, wav_path)
    text = transcribe_audio(wav_path)
    await process_sentence(text, update)
    for p in (ogg_path, wav_path):
        try: os.remove(p)
        except: pass

async def process_sentence(text, update):
    kind = detect_kind(text) or "صرف"
    amount = extract_amount(text)
    category = detect_category(text)
    if not amount:
        await update.message.reply_text("اذكر المبلغ.")
        return
    append_row(kind, category, text, amount, update.effective_user.first_name)
    await update.message.reply_text(f"تم تسجيل {kind}: {category} - {amount:.2f} ريال ✅")

def main():
    ensure_excel()
    if TOKEN == "": sys.exit(1)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("export", export_cmd))
    app.add_handler(CommandHandler("sum", sum_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
