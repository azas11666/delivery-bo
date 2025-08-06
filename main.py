import logging
import os
import datetime
import openai
import whisper
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from openpyxl import Workbook, load_workbook
from tempfile import NamedTemporaryFile
from pydub import AudioSegment

# إعداد التوكن الصحيح
TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
openai.api_key = os.getenv("OPENAI_API_KEY")

# إعداد النموذج
model = whisper.load_model("base")

# ملف الإكسل
EXCEL_FILE = "expenses.xlsx"
if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "الوصف", "المبلغ", "التصنيف", "النوع"])
    wb.save(EXCEL_FILE)

# تسجيل الدخول
logging.basicConfig(level=logging.INFO)

# تصنيف الكلام العام
def analyze_text(text):
    import re

    amount_match = re.search(r"\b(\d{1,5})\s*ريال\b", text)
    amount = amount_match.group(1) if amount_match else ""

    if "بنزين" in text or "سيارة" in text:
        category = "السيارة"
    elif "ملابس" in text:
        category = "الملابس"
    elif "ربح" in text or "دخل" in text:
        category = "عام"
    else:
        category = "غير مصنف"

    if "ربح" in text or "دخل" in text:
        type_ = "ربح"
    else:
        type_ = "خسارة"

    return amount, category, type_

# حفظ في الاكسل
def save_to_excel(date, desc, amount, category, type_):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([date, desc, amount, category, type_])
    wb.save(EXCEL_FILE)

# عند استلام رسالة صوتية
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        voice_ogg = await file.download_to_drive()

        audio = AudioSegment.from_ogg(voice_ogg.name)
        with NamedTemporaryFile(delete=False, suffix=".wav") as f:
            audio.export(f.name, format="wav")
            result = model.transcribe(f.name, language="ar")

        text = result["text"]
        amount, category, type_ = analyze_text(text)

        if not amount:
            await update.message.reply_text("❌ لم يتم فهم الرسالة الصوتية. يرجى قول مثال مثل: '30 ريال بنزين'")
            return

        save_to_excel(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), text, amount, category, type_)
        await update.message.reply_text(f"✅ تم تسجيل المصروف:\n- الوصف: {text}\n- المبلغ: {amount} ريال\n- التصنيف: {category}\n- النوع: {type_}")
    except Exception as e:
        await update.message.reply_text("حدث خطأ أثناء معالجة الصوت.")
        logging.error(e)

# عند استلام /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ أرسل تسجيل صوتي يحتوي على تفاصيل المصروف، وسأقوم بتحليله وتسجيله في ملف الإكسل.")

# عرض السجل
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_document(InputFile(EXCEL_FILE))

# تشغيل البوت
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    app.run_polling()
