import os
import logging
from datetime import datetime
from openpyxl import Workbook, load_workbook
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import whisper
from pydub import AudioSegment

TOKEN = "YOUR_TOKEN"
ADMIN_ID = 7799549664
DELEGATE_IDS = [979025584, 6274276105]
EXCEL_FILE = "requests.xlsx"

if not os.path.exists(EXCEL_FILE):
    wb = Workbook()
    ws = wb.active
    ws.append(["التاريخ", "العميل", "المشوار", "السعر", "رقم الجوال", "المندوب"])
    wb.save(EXCEL_FILE)

logging.basicConfig(level=logging.INFO)
model = whisper.load_model("base")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً فيك ببوت *مشاوير جدة* 👋\n\n"
        "عزيزي العميل، الرجاء كتابة مشوارك بالتفاصيل التالية:\n"
        "1️⃣ *اذكر مشوارك: من فين إلى وين*\n"
        "2️⃣ *اذكر السعر المدفوع*\n"
        "3️⃣ *اذكر رقم جوالك*\n\n"
        "🟢 *اكتبها في رسالة واحدة فقط.*\n"
        "بعدها سيتم إرسال طلبك لأكثر من 100 مندوب موثوق.\n"
        "🚗 سيتواصل معك السائق عبر واتساب خلال 3 دقائق، كن بالانتظار.\n\n"
        "🔒 *ملاحظة:* رقم جوالك لن يظهر إلا للسائق الذي يقبل المشوار، لذلك ضروري تكتبه.",
        parse_mode="Markdown"
    )

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    phone = "".join(filter(str.isdigit, user_text))
    masked_phone = phone[:-5] + "*****" if len(phone) >= 5 else phone

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), update.effective_user.first_name, user_text, "", phone, ""])
    wb.save(EXCEL_FILE)

    keyboard = [
        [InlineKeyboardButton("قبول", callback_data=f"accept_{update.message.message_id}")]
    ]

    for delegate_id in DELEGATE_IDS:
        try:
            await context.bot.send_message(
                chat_id=delegate_id,
                text=f"📍 مشوار جديد:\n{user_text}\n📞 {masked_phone}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("accept_"):
        msg_id = int(query.data.split("_")[1])
        for delegate_id in DELEGATE_IDS:
            if delegate_id != query.from_user.id:
                try:
                    await context.bot.delete_message(chat_id=delegate_id, message_id=msg_id)
                except:
                    pass
        await query.edit_message_text(text=f"✅ تم قبول المشوار\n📞 رقم العميل: {query.message.text.split('📞 ')[1].replace('*****', '')}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
