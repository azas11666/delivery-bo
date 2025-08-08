import os
import logging
import datetime
import asyncio
import whisper
from tempfile import NamedTemporaryFile

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from openpyxl import Workbook, load_workbook
from pydub import AudioSegment

# ================== CONFIG ==================
TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
EXCEL_FILE = "expenses.xlsx"
# ============================================

logging.basicConfig(level=logging.INFO)

# Whisper CPU-only (خفيف وثابت على الاستضافة)
model = whisper.load_model("small")  # غيّر إلى "tiny" لو تبي أخف
WHISPER_ARGS = {"language": "ar", "fp16": False}

# إنشاء ملف الإكسل لو ما وُجد
if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses"
    ws.append(["التاريخ", "الوصف", "المبلغ", "التصنيف", "النوع"])
    wb.save(EXCEL_FILE)


def parse_text(text: str):
    """يستخرج المبلغ + التصنيف + النوع من نص عام."""
    import re

    amount = ""
    m = re.search(r"(\d{1,6})\s*ريال", text)
    if m:
        amount = m.group(1)

    # تصنيف تقريبي
    t = text
    if any(k in t for k in ["بنزين", "وقود", "محطة", "سيارة"]):
        category = "السيارة"
    elif any(k in t for k in ["ملابس", "تيشيرت", "بنطلون", "عباية"]):
        category = "الملابس"
    elif any(k in t for k in ["مطعم", "عشاء", "غداء", "برغر", "بيتزا", "قهوة", "ستاربكس"]):
        category = "مطاعم/قهوة"
    elif any(k in t for k in ["دخل", "حوّلت", "حوّل", "ربح", "مكسب"]):
        category = "دخل"
    else:
        category = "غير مصنف"

    tx_type = "ربح" if category == "دخل" or any(k in t for k in ["دخل", "ربح"]) else "خسارة"
    return amount, category, tx_type


def save_row(desc: str, amount: str, category: str, tx_type: str):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append([now, desc, amount, category, tx_type])
    wb.save(EXCEL_FILE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ أرسل رسالة صوتية بتفاصيل المصروف بصيغة عامة، مثل:\n"
        "«دفعت 40 ريال بنزين»، أو «قهوة بـ 15 ريال»، وسأفهمها وأسجّلها.\n\n"
        "📄 للأرشيف أرسل: /report"
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(EXCEL_FILE):
        await update.message.reply_text("لا يوجد سجل حتى الآن.")
        return
    await update.message.reply_document(InputFile(EXCEL_FILE))


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        voice = update.message.voice
        if not voice:
            return

        tg_file = await context.bot.get_file(voice.file_id)

        # حمّل الملف إلى مسار مؤقت .ogg (Telegram = OGG/Opus)
        with NamedTemporaryFile(delete=False, suffix=".ogg") as ogg_f:
            await tg_file.download_to_drive(ogg_f.name)
            ogg_path = ogg_f.name

        # حوّله إلى wav عبر ffmpeg (pydub)
        with NamedTemporaryFile(delete=False, suffix=".wav") as wav_f:
            wav_path = wav_f.name
        AudioSegment.from_file(ogg_path, format="ogg").export(wav_path, format="wav")

        # تفريغ النص
        result = model.transcribe(wav_path, **WHISPER_ARGS)
        text = (result.get("text") or "").strip()

        # نظّف المؤقتات
        try:
            os.remove(ogg_path)
        except Exception:
            pass
        try:
            os.remove(wav_path)
        except Exception:
            pass

        if not text:
            await update.message.reply_text("❌ لم أفهم التسجيل. حاول أن تذكر مبلغًا وكلمة مثل «ريال».")
            return

        amount, category, tx_type = parse_text(text)
        if not amount:
            await update.message.reply_text(
                f"🗒️ نص مُستخرج:\n{text}\n\n"
                "❌ لم أجد مبلغًا بصيغة «XX ريال». أعد المحاولة واذكر المبلغ."
            )
            return

        save_row(text, amount, category, tx_type)
        await update.message.reply_text(
            f"✅ تم التسجيل:\n"
            f"• الوصف: {text}\n"
            f"• المبلغ: {amount} ريال\n"
            f"• التصنيف: {category}\n"
            f"• النوع: {tx_type}"
        )

    except Exception as e:
        logging.exception("voice error")
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الصوت. جرّب مرة أخرى.")


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
