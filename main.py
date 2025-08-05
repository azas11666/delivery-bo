import os
import whisper
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
EXCEL_FILE = "daily_expenses.xlsx"

model = whisper.load_model("base")

if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "الفئة", "العملية", "المبلغ"])
    wb.save(EXCEL_FILE)

logging.basicConfig(level=logging.INFO)

def extract_expenses(text):
    import re
    category_keywords = {
        "سيارة": "سيارة",
        "بنزين": "سيارة",
        "ملابس": "ملابس",
        "أكل": "أكل",
        "مطعم": "أكل",
        "بيت": "سكن",
        "إيجار": "سكن"
    }
    transaction_type = "خسارة" if "صرف" in text or "دفعت" in text else "ربح"
    matches = re.findall(r'(\d+)\s*ريال', text)
    category = "أخرى"
    for word in category_keywords:
        if word in text:
            category = category_keywords[word]
            break
    amount = int(matches[0]) if matches else 0
    return category, transaction_type, amount

def save_to_excel(category, transaction_type, amount):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append([date_str, category, transaction_type, amount])
    wb.save(EXCEL_FILE)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    file_path = "voice.ogg"
    await file.download_to_drive(file_path)
    result = model.transcribe(file_path, language="ar")
    text = result["text"]
    category, transaction_type, amount = extract_expenses(text)
    save_to_excel(category, transaction_type, amount)
    await update.message.reply_text(f"✅ تم تسجيل العملية:\nالفئة: {category}\nالعملية: {transaction_type}\nالمبلغ: {amount} ريال")
    os.remove(file_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 أرسل تسجيل صوتي يحتوي على تفاصيل المصاريف ليتم تسجيلها تلقائياً.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    app.run_polling()
