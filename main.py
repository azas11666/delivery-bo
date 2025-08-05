import os
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
import whisper

TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
EXCEL_FILE = "expenses_log.xlsx"
model = whisper.load_model("base")
logging.basicConfig(level=logging.INFO)

if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "العملية", "الصنف", "المبلغ"])
    wb.save(EXCEL_FILE)

def extract_expenses(text):
    import re
    pattern = r"(ربح|خسارة)\s+(\d+)\s*ريال(?:.*?على)?\s*([\u0600-\u06FF]+)"
    matches = re.findall(pattern, text)
    return [(op, int(amount), category.strip()) for op, amount, category in matches]

def save_to_excel(expenses):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    for op, amount, category in expenses:
        ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), op, category, amount])
    wb.save(EXCEL_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ أرسل تسجيل صوتي يحتوي على تفاصيل المصاريف مثل: خسارة 40 ريال على البنزين")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    path = "voice.ogg"
    await file.download_to_drive(path)
    import subprocess
    wav_path = "voice.wav"
    subprocess.run(["ffmpeg", "-i", path, wav_path, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = model.transcribe(wav_path, language="ar")
    text = result["text"]
    expenses = extract_expenses(text)
    if expenses:
        save_to_excel(expenses)
        await update.message.reply_text("✅ تم تسجيل المصاريف بنجاح")
    else:
        await update.message.reply_text("❌ لم يتم التعرف على مصاريف في التسجيل")

async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(EXCEL_FILE):
        await update.message.reply_document(document=open(EXCEL_FILE, "rb"))
    else:
        await update.message.reply_text("❌ لا يوجد سجل حتى الآن.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", export_excel))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("✅ Bot is running...")
    app.run_polling()
