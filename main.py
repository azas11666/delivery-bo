import json
import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "7853541575:AAEFo-9PKC7f9vSwoeIn1LR1L2TXYF2BFWI"

DELEGATE_IDS = [979025584, 6274276105]
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
        await context.bot.send_message(chat_id=user_id, text="مرحبًا! أرسل تفاصيل المشوار لعرضها على المناديب.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DELEGATE_IDS:
        return

    text = update.message.text
    phone_match = re.search(r'(?:\+?966|0)?5\d{8}', text)
    phone = phone_match.group(0) if phone_match else None
    masked_phone = mask_phone_number(phone) if phone else "📞 لم يتم العثور على رقم"

    filtered_message = text.replace(phone, "").strip() if phone else text

    request = {
        "original_message": filtered_message,
        "full_phone": phone or "📞 لم يتم العثور على رقم",
        "accepted_by": None,
        "message_ids": {}
    }

    active_requests.append(request)

    with open("requests.json", "w", encoding="utf-8") as f:
        json.dump(active_requests, f, ensure_ascii=False, indent=2)

    index = len(active_requests) - 1

    for delegate_id in DELEGATE_IDS:
        message = await context.bot.send_message(
            chat_id=delegate_id,
            text=f"🚕 طلب جديد!\n\n{filtered_message}\n\nرقم الجوال: {masked_phone}",
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton("🚗 قبول المشوار", callback_data=f"accept:{index}:{phone}")
            )
        )
        request["message_ids"][str(delegate_id)] = message.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    delegate_id = query.from_user.id

    try:
        _, index_str, phone = query.data.split(":")
        index = int(index_str)
    except:
        return

    if index >= len(active_requests):
        return

    request = active_requests[index]

    if request["accepted_by"] is None:
        request["accepted_by"] = delegate_id
        await context.bot.send_message(chat_id=delegate_id, text=f"📞 رقم العميل: {request['full_phone']}")

        for other_delegate_id, msg_id in request["message_ids"].items():
            if int(other_delegate_id) != delegate_id:
                try:
                    await context.bot.delete_message(chat_id=int(other_delegate_id), message_id=msg_id)
                except:
                    pass

        with open("requests.json", "w", encoding="utf-8") as f:
            json.dump(active_requests, f, ensure_ascii=False, indent=2)

async def remind_delegates(application):
    while True:
        for delegate_id in DELEGATE_IDS:
            try:
                await application.bot.send_message(
                    chat_id=delegate_id,
                    text="📣 عزيزي المندوب الرجاء الانتباه للبوت بشكل مستمر لحصولك على مشوار"
                )
            except:
                continue
        await asyncio.sleep(1800)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_callback))



print("✅ Bot is running...")
app.run_polling()