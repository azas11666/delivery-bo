import os
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from faster_whisper import WhisperModel


TOKEN = "8407369465:AAFJ8MCRIkWo02HiETILry7XeuHf81T1DBw"


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


EXCEL_FILE = "expenses.xlsx"
if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "الصنف", "المبلغ"])
    wb.save(EXCEL_FILE)


model = WhisperModel("base")


def save_to_excel(category, amount):
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), category, amount])
    wb.save(EXCEL_FILE)


def extract_expenses(text):
    import re
    pattern = r'(\d+)\s*ريال(?:.*?على)?\s*([\u0600-\u06FF]+)'
    matches = re.findall(pattern, text)
    return [(category.strip(), int(amount)) for amount, category in matches]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! أرسل المبلغ والصنف وسأسجله لك في الإكسل.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    expenses = extract_expenses(text)
    if expenses:
        for category, amount in expenses:
            save_to_excel(category, amount)
        await update.message.reply_text("تم حفظ المصروفات في الإكسل ✅")
    else:
        await update.message.reply_text("لم أتمكن من التعرف على المبلغ والصنف.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
