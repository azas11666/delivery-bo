import os
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

# إعدادات
TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
EXCEL_FILE = "expenses.xlsx"

# إعداد سجل الأخطاء
logging.basicConfig(level=logging.INFO)

# نموذج Whisper
model = whisper.load_model("base")

# إنشاء ملف Excel إذا لم يكن موجود
if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "التصنيف", "المبلغ", "العملية"])
    wb.save(EXCEL_FILE)

# استخراج المصاريف من النص
def extract_expense(text):
    import re
    text = text.replace("ريـال", "ريال")  # إصلاح الكتابة
    pattern = r'(\d+)\s*ريال(?:.*?)(بنزين|ملابس|مطعم|سيارة|بقالة|قهوة|كهرباء|ماء|ايجار|راتب|دخل|ربح|خسارة)?'
    match = re.search(pattern, text)
    if match:
        amount = int(match.group(1))
        category = match.group(2) if match.group(2) else "غير محدد"
        operation = "ربح" if category in ["راتب", "دخل", "ربح"] else "خسارة"
        return amount, category, operation
    return None

# حفظ السجل
def save_to_excel(amount, category, operation):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append([now, category, amount, operation])
    wb.save(EXCEL_FILE)

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ أرسل رسالة صوتية تحتوي على المبلغ والتصنيف.\nمثال: '30 ريال بنزين'\nثم أرسل /export لعرض السجل.")

# أمر /export
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("❌ لا يوجد سجلات حالياً.")
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]
    if not rows:
        await update.message.reply_text("❌ لا يوجد سجلات.")
        return
    result = "📒 *سجل المصروفات:*\n"
    for row in rows:
        result += f"🕒 {row[0]} | {row[1]} | {row[2]} ريال | {row[3]}\n"
    await update.message.reply_text(result, parse_mode="Markdown")

# التعامل مع الصوت
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ogg_path = "voice.ogg"
    wav_path = "voice.wav"
    await file.download_to_drive(ogg_path)
    os.system(f"ffmpeg -i {ogg_path} -ar 16000 -ac 1 -c:a pcm_s16le {wav_path} -y")
    result = model.transcribe(wav_path)
    text = result["text"]
    expense = extract_expense(text)
    if expense:
        amount, category, operation = expense
        save_to_excel(amount, category, operation)
        await update.message.reply_text(f"✅ تم تسجيل: {amount} ريال - {category} - {operation}")
    else:
        await update.message.reply_text("❌ لم يتم فهم الرسالة الصوتية. يرجى قول مثال مثل: '30 ريال بنزين'")
    os.remove(ogg_path)
    os.remove(wav_path)

# تشغيل البوت
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    print("✅ Bot is running...")
    app.run_polling()
