from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "7853541575:AAEFo-9PKC7f9vSwoeIn1LR1L2TXYF2BFWI"
DELIVERY_IDS = [979025584, 6274276105, 1191690688, 8170847197]

message_tracker = {
    "accepted": False,
    "message_ids": {},
    "full_phone": ""
}

def mask_phone(phone):
    return phone[:-5] + "*****"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في بوت التوصيل. أرسل تفاصيل الطلب.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id

    if len(user_message) > 400:
        return

    phone = ""
    for word in user_message.split():
        if word.startswith("05") and word.isdigit() and len(word) >= 10:
            phone = word
            break

    if not phone:
        return

    masked_phone = mask_phone(phone)
    message_tracker["full_phone"] = phone
    message_tracker["accepted"] = False
    message_tracker["message_ids"] = {}

    buttons = [[InlineKeyboardButton("🚗 قبول المشوار", callback_data="accept")]]
    reply_markup = InlineKeyboardMarkup(buttons)

    for delegate_id in DELIVERY_IDS:
        msg = await context.bot.send_message(
            chat_id=delegate_id,
            text=f"🚕 طلب جديد!\n\n{user_message.replace(phone, masked_phone)}",
            reply_markup=reply_markup
        )
        message_tracker["message_ids"][delegate_id] = msg.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if message_tracker["accepted"]:
        await query.message.edit_reply_markup(reply_markup=None)
        return

    if query.data == "accept":
        phone_msg = message_tracker["full_phone"]
        await query.message.reply_text(f"📞 رقم الجوال:\n{phone_msg}")
        message_tracker["accepted"] = True

        for delegate_id, msg_id in message_tracker["message_ids"].items():
            if delegate_id != user_id:
                try:
                    await context.bot.delete_message(chat_id=delegate_id, message_id=msg_id)
                except:
                    pass

        await query.message.edit_reply_markup(reply_markup=None)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.add_handler(CallbackQueryHandler(button_callback))

print("Bot is running...")
app.run_polling()