import os
import re
import logging
import whisper
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
from openpyxl import Workbook, load_workbook

TOKEN = "ضع_توكن_البوت_هنا"
EXCEL_FILE = "expenses.xlsx"
model = whisper.load_model("base")

logging.basicConfig(level=logging.INFO)

if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "النص", "المبلغ", "التصنيف", "العملية"])
    wb.save(EXCEL_FILE)

KEYWORDS_CATEGORIES = {
    "بنزين": "سيارة", "سيارة": "سيارة", "مواقف": "سيارة",
    "كهرب": "كهرباء", "ماء": "ماء", "فاتورة": "كهرباء",
    "قهوة": "مشروبات", "مطعم": "أكل", "غداء": "أكل", "عشاء": "أكل",
    "بقالة": "مواد غذائية", "ملابس": "ملابس",
    "راتب": "دخل", "دخل": "دخل", "ربح": "دخل"
}

def extract_info(text):
    amount_match = re.search(r"(\d+)\s*ريال", text)
    amount = int(amount_match.group(1)) if amount_match else None
    category = "غير محدد"
    operation = "خسارة"

    for keyword, cat in KEYWORDS_CATEGORIES.items():
        if keyword in text:
            category = cat
            if cat == "دخل":
                operation = "ربح"
            break

    return amount, category, operation

def save_to_excel(text, amount, category, operation):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append([now, text, amount, category, operation])
    wb.save(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ أرسل رسالة صوتية أو نصية تحتوي على المبلغ والتفاصيل.\nمثال: 'دفعت 30 ريال بنزين' أو سجل صوت.")

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("❌ لا يوجد سجلات.")
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]
    if not rows:
        await update.message.reply_text("❌ لا يوجد سجلات.")
        return
    result = "📒 *سجل المصروفات:*\n"
    for row in rows[-10:]:
        result += f"🕒 {row[0]} | {row[2]} ريال | {row[3]} | {row[4]}\n"
    await update.message.reply_text(result, parse_mode="Markdown")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = "voice.ogg"
    wav_path = "voice.wav"
    await file.download_to_drive(ogg_path)
    os.system(f"ffmpeg -i {ogg_path} -ar 16000 -ac 1 -c:a pcm_s16le {wav_path} -y")
    result = model.transcribe(wav_path)
    text = result["text"].strip()
    amount, category, operation = extract_info(text)
    if amount:
        save_to_excel(text, amount, category, operation)
        await update.message.reply_text(f"✅ تم تسجيل: {amount} ريال - {category} - {operation}")
    else:
        await update.message.reply_text("❌ لم يتم التعرف على المبلغ. أعد المحاولة بوضوح.")
    os.remove(ogg_path)
    os.remove(wav_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    amount, category, operation = extract_info(text)
    if amount:
        save_to_excel(text, amount, category, operation)
        await update.message.reply_text(f"✅ تم تسجيل_
