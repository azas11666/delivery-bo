import os
import logging
import openai
import whisper
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from openpyxl import Workbook, load_workbook
from datetime import datetime

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
openai.api_key = "YOUR_OPENAI_API_KEY"

logging.basicConfig(level=logging.INFO)
AUDIO_DIR = "audios"
EXCEL_FILE = "expenses.xlsx"

os.makedirs(AUDIO_DIR, exist_ok=True)
model = whisper.load_model("base")

if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "الوصف", "الفئة", "النوع", "المبلغ"])
    wb.save(EXCEL_FILE)

def analyze_text_with_ai(text):
    prompt = f"""
حلل الرسالة التالية واكتب النتيجة بصيغة: 
"الفئة: (مثلاً بنزين، ملابس، طعام...)
النوع: (ربح أو مصروف)
المبلغ: (رقماً بدون كتابة كلمة ريال مثلاً 40)
الوصف: (وصف مختصر)

النص: {text}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": "أنت مساعد مالي يفهم النصوص ويستخرج منها معلومات مالية بشكل منظم."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return None

def save_to_excel(category, entry_type, amount, description):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append([now, description, category, entry_type, amount])
    wb.save(EXCEL_FILE)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    file_path = os.path.join(AUDIO_DIR, f"{update.message.message_id}.ogg")
    await file.download_to_drive(file_path)

    wav_path = file_path.replace(".ogg", ".wav")
    os.system(f"ffmpeg -i {file_path} -ar 16000 -ac 1 {wav_path} -y")

    try:
        result = model.transcribe(wav_path)
        text = result["text"]
        logging.info(f"Transcribed: {text}")
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحويل الرسالة الصوتية إلى نص.")
        return

    ai_result = analyze_text_with_ai(text)
    if ai_result is None:
        await update.message.reply_text("❌ لم يتم فهم الرسالة الصوتية.")
        return

    try:
        lines = ai_result.split("\n")
        category = lines[0].split(":")[1].strip()
        entry_type = lines[1].split(":")[1].strip()
        amount = float(lines[2].split(":")[1].strip())
        description = lines[3].split(":")[1].strip()

        save_to_excel(category, entry_type, amount, description)
        await update.message.reply_text(f"✅ تم تسجيل العملية:\nالفئة: {category}\nالنوع: {entry_type}\nالمبلغ: {amount} ريال\nالوصف: {description}")
    except Exception as e:
        logging.error(f"Parse error: {e}")
        await update.message.reply_text("❌ لم يتم فهم الرسالة الصوتية. يرجى قول مثال مثل: '30 ريال بنزين'.")

async def export_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(EXCEL_FILE):
        await update.message.reply_document(document=open(EXCEL_FILE, "rb"))
    else:
        await update.message.reply_text("⚠️ لا يوجد سجل بعد.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.VOICE, voice_handler))
app.add_handler(CommandHandler("export", export_log))

print("✅ Bot started.")
app.run_polling()
