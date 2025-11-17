import os
import io
import logging
from telegram import Update, InputFile, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv
from fpdf import FPDF

# ========== ENV ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# Foydalanuvchi rasm va state saqlash
user_data = {}
ASK_NAME = 1

# ========== BOT HANDLERLARI ==========
def get_keyboard():
    keyboard = [
        [KeyboardButton("📷 Rasm yuborish"), KeyboardButton("✅ Tayyorla")],
        [KeyboardButton("ℹ️ Info"), KeyboardButton("❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"photos": []}
    await update.message.reply_text(
        "🎉 Salom! Bot ishlayapti!\nRasmlarni yuboring va tugmalardan foydalaning.",
        reply_markup=get_keyboard()
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"photos": []}

    if not update.message.photo:
        await update.message.reply_text("❗️ Iltimos, faqat rasm yuboring.")
        return

    photo = update.message.photo[-1]
    file_obj = await photo.get_file()
    bio = io.BytesIO()
    await file_obj.download(out=bio)
    bio.seek(0)

    user_data[user_id]["photos"].append(bio)
    await update.message.reply_text(f"✅ Rasm qabul qilindi. Siz hozir {len(user_data[user_id]['photos'])} rasm yubordingiz.")

async def finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photos = user_data.get(user_id, {}).get("photos", [])
    if not photos:
        await update.message.reply_text("❗️ Siz hali hech qanday rasm yubormagansiz.")
        return ConversationHandler.END

    await update.message.reply_text("📛 PDF faylga qanday ism qo‘yaylik?")
    return ASK_NAME

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photos = user_data.get(user_id, {}).get("photos", [])
    file_name = update.message.text.strip()
    if not file_name:
        file_name = "output"

    pdf = FPDF()
    for bio in photos:
        pdf.add_page()
        pdf.image(bio, x=10, y=10, w=180)

    pdf_bytes = io.BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)

    file = InputFile(pdf_bytes, filename=f"{file_name}.pdf")
    await update.message.reply_document(file)
    await update.message.reply_text(f"✅ Tayyor! PDF fayl nomi: {file_name}.pdf")

    user_data[user_id]["photos"] = []
    return ConversationHandler.END

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot ishlayapti!\n"
        "📍 Render hosting\n✅ Python 3\n🎯 Telegram Bot API"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Jarayon bekor qilindi.")
    user_data[update.effective_user.id] = {"photos": []}
    return ConversationHandler.END

# ========== MAIN ==========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✅ Tayyorla"), finish_handler)],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)]},
        fallbacks=[MessageHandler(filters.Regex("❌ Bekor qilish"), cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Regex("ℹ️ Info"), info))
    app.add_handler(conv_handler)

    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if name == "main":
    main()