import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"

DELEGATE_IDS = [
    979025584, 6274276105, 1191690688, 8170847197,
    6934325493, 7829041114, 5089840611, 5867751923,
    7059987819, 6907220336, 7453553320
]

active_requests = []
if os.path.exists("requests.json"):
    with open("requests.json", "r", encoding="utf-8") as f:
        active_requests = json.load(f)

def mask_phone_number(phone):
    return phone[:-5] + "*****"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DELEGATE_IDS:
        await context.bot.send_message(chat_id=user_id, text="✅ تم تسجيلك كمندوب بنجاح.")
    else:
        await context.bot.send_message(chat_id=user_id, text=
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DELEGATE_IDS:
        return

    message = update.message.text
    if len(message) > 400:
        await update.message.reply_text("⚠️ رسالتك طويلة جدًا، الرجاء تقصيرها.")
        return

    phone_number = None
    for word in message.split():
        if word.isdigit() and len(word) >= 9:
            phone_number = word
            break

    if not phone_number:
        await update.message.reply_text("❌ يرجى تضمين رقم الجوال في رسالتك.")
        return

    masked_number_



print("✅ Bot started and waiting for messages...")

