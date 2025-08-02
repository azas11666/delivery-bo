import logging
import asyncio
import os
from datetime import datetime
from openpyxl import Workbook, load_workbook
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8407369465:AAFJ8MCRIkWoO2HiETILry7XeuHf81T1DBw"
ADMIN_ID = 7799549664

DELEGATE_IDS = [
    979025584, 1191690688, 8170847197,
    6934325493, 7829041114, 5089840611, 5867751923,
    7059987819, 6907220336, 7453553320, 7317135212,
    6545258494, 7786225278, 7029907146, 7731731836, 1097659084, 8076843839, 7313682176, 7290225311, 
]

FORBIDDEN_KEYWORDS = [
    "إجازة", "تقرير", "زواج", "مكيفات", "مكيف", "مرضية", "مراجة", "مشهد",
    "مرافق", "طبي", "متحررة", "سعر", "جميلة", "رقم", "056", "057", "058", "059",
    "http", "https", ".com", ".net", ".org", ".crypto", "ethereum", "wallet",
    "free", "claim", "airdrop", "verify", "eth", "connect", "collect", "blockchain",
    "jetacas"
]

active_requests = []
pending_users = set()
lock = asyncio.Lock()

def log_to_excel(request, driver_id):
    file_name = "trips_log.xlsx"
    headers = ["التاريخ", "رقم العميل", "الطلب", "ID العميل", "ID المندوب"]
    try:
        if not os.path.exists(file_name):
            wb = Workbook()
            ws = wb.active
            ws.append(headers)
        else:
            wb = load_workbook(file_name)
            ws = wb.active
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append([
            now,
            request["phone_number"],
            request["message"],
            request["user_id"],
            driver_id
        ])
        wb.save(file_name)
    except:
        pass

def log_client_id(user_id):
    file_path = "clients.txt"
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(user_id) + "\n")
    else:
        with open(file_path, "r+", encoding="utf-8") as f:
            lines = f.read().splitlines()
            if str(user_id) not in lines:
                f.write(str(user_id) + "\n")

async def send_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return
    file_path = "clients.txt"
    if not os.path.exists(file_path):
        await update.message.reply_text("❌ لا يوجد عملاء مسجلين.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, "rb"))

async def send_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return
    file_path = "trips_log.xlsx"
    if not os.path.exists(file_path):
        await update.message.reply_text("❌ لا يوجد حالياً ملف سجل.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, "rb"))

async def send_log_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ليس لديك صلاحية.")
        return
    file_path = "trips_log.xlsx"
    if not os.path.exists(file_path):
        await update.message.reply_text("❌ لا يوجد سجل مشاوير.")
        return
    wb = load_workbook(file_path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]
    if not rows:
        await update.message.reply_text("⚠️ لا يوجد بيانات في السجل.")
        return
    for row in rows:
        date, phone, msg, user_id, driver_id = row
        text = f"""📅 *{date}*
👤 *العميل:* `{user_id}`
📞 *رقم الجوال:* `{phone}`
📝 *الطلب:* {msg}
🚗 *المندوب:* `{driver_id}`"""
        await update.message.reply_text(text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_client_id(user_id)
    if user_id in DELEGATE_IDS:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ تم تسجيلك كمندوب بنجاح.\nإذا لم تصلك طلبات أو واجهت مشاكل تواصل معنا على: 0506260139"
        )
    else:
        await update.message.reply_text(
            "مرحباً فيك ببوت *مشاوير جدة* 👋\n\n"
            "عزيزي العميل، الرجاء كتابة مشوارك بالتفاصيل التالية:\n"
            "مثال: مشوار من الحمدانية إلى السامر مدفوع 30\n"
            "0506260****\n\n"
            "🟢 *اكتبها في رسالة واحدة فقط.*\n"
            "بعدها سيتم إرسال طلبك لأكثر من 100 مندوب موثوق.\n"
            "🚗 سيتواصل معك السائق عبر واتساب خلال 3 دقائق، كن بالانتظار.\n\n"
            "🔒 *ملاحظة:* رقم جوالك لن يظهر إلا للسائق الذي يقبل المشوار.\n"
            "❌ *لا توجد مشاوير شهرية*",
            parse_mode="Markdown"
        )

def contains_forbidden(text):
    lowered = text.lower()
    for word in FORBIDDEN_KEYWORDS:
        if word in lowered:
            return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in DELEGATE_IDS:
        return
    log_client_id(user_id)
    if user_id in pending_users:
        await update.message.reply_text("⚠️ طلبك السابق قيد المعالجة، الرجاء الانتظار.")
        return
    message = update.message
    if message.forward_date:
        await message.reply_text("❌ لا يُسمح بالرسائل المعاد توجيهها.")
        return
    if message.text != message.text.strip() or message.text != message.text.strip('\n'):
        await message.reply_text("❌ لا يوجد لصق، اكتب مشوارك بنفسك.")
        return
    if len(message.text) > 400:
        await message.reply_text("⚠️ رسالتك طويلة جدًا، الرجاء تقصيرها.")
        return
    if contains_forbidden(message.text):
        await update.message.reply_text("🚫 رسالتك تحتوي على محتوى غير مسموح به.")
        return
    phone_number = None
    for word in message.text.split():
        if word.isdigit() and len(word) >= 9:
            phone_number = word
            break
    if not phone_number:
        await update.message.reply_text("❌ يرجى تضمين رقم الجوال في رسالتك.")
        return
    pending_users.add(user_id)
    request_id = str(len(active_requests))
    request = {
        "id": request_id,
        "user_id": user_id,
        "message": message.text.replace(phone_number, "******"),
        "phone_number": phone_number,
        "accepted_by": None,
        "message_ids": {}
    }
    active_requests.append(request)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚗 قبول المشوار", callback_data=f"accept_{request_id}")]
    ])
    tasks = [context.bot.send_message(chat_id=did, text=f"🚕 طلب جديد!\n\n{request['message']}", reply_markup=keyboard) for did in DELEGATE_IDS]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            continue
        request["message_ids"][DELEGATE_IDS[i]] = response.message_id
    await update.message.reply_text("✅ تم إرسال طلبك إلى المناديب، يرجى الانتظار...")
    pending_users.discard(user_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("accept_"):
        return
    request_id = data.split("_")[1]
    async with lock:
        for request in active_requests:
            if request["id"] == request_id:
                if request["accepted_by"] is not None:
                    await query.edit_message_text("❌ تم قبول هذا الطلب من مندوب آخر.")
                    return
                request["accepted_by"] = query.from_user.id
                log_to_excel(request, query.from_user.id)
                await context.bot.send_message(chat_id=query.from_user.id, text=f"📞 رقم العميل: {request['phone_number']}")
                await context.bot.send_message(chat_id=request["user_id"], text="✅ تم قبول طلبك من السائق، سيتواصل معك على الواتساب.")
                for did, msg_id in request["message_ids"].items():
                    try:
                        await context.bot.edit_message_reply_markup(chat_id=did, message_id=msg_id, reply_markup=None)
                    except:
                        pass
                return

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("log", send_log))
    app.add_handler(CommandHandler("log_text", send_log_text))
    app.add_handler(CommandHandler("clients", send_clients))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot is running...")
    app.run_polling()
