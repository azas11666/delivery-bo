import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"

DELEGATE_IDS = [
    979025584, 6274276105, 1191690688, 8170847197,
    6934325493, 7829041114, 5089840611, 5867751923,
    7059987819, 6907220336, 7453553320, 7317135212
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
        await update.message.reply_text("✅ تم تسجيلك كمندوب بنجاح.")
    else:
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

    masked_number = mask_phone_number(phone_number)
    request_id = str(len(active_requests))

    request = {
        "id": request_id,
        "user_id": user_id,
        "message": message.replace(phone_number, masked_number),
        "phone_number": phone_number,
        "masked_number": masked_number,
        "accepted_by": None
    }

    active_requests.append(request)
    with open("requests.json", "w", encoding="utf-8") as f:
        json.dump(active_requests, f, ensure_ascii=False, indent=2)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 قبول المشوار", callback_data=f"accept_{request_id}")]
    ])

    for delegate_id in DELEGATE_IDS:
        try:
            await context.bot.send_message(
                chat_id=delegate_id,
                text=f"🚕 طلب جديد!\n\n{request['message']}\n\n📞 رقم الجوال: {masked_number}",
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"فشل الإرسال إلى المندوب {delegate_id}: {e}")

    await update.message.reply_text("✅ تم إرسال طلبك إلى المناديب، يرجى الانتظار...")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("accept_"):
        return

    request_id = data.split("_")[1]
    for i, req in enumerate(active_requests):
        if req["id"] == request_id:
            if req["accepted_by"] is not None:
                await query.edit_message_text("❌ تم قبول هذا الطلب من مندوب آخر.")
                return

            req["accepted_by"] = query.from_user.id
            with open("requests.json", "w", encoding="utf-8") as f:
                json.dump(active_requests, f, ensure_ascii=False, indent=2)

            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"📞 رقم العميل: {req['phone_number']}"
            )

            await context.bot.send_message(
                chat_id=req["user_id"],
                text="✅ تم قبول طلبك من السائق، سيتواصل معك على الواتساب، كن بانتظاره."
            )

            await query.edit_message_reply_markup(reply_markup=None)
            return

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot is running...")
    app.run_polling()
