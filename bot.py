import os
import logging
import io
from dotenv import load_dotenv
from PIL import Image
from telegram import InputFile, Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ===== Load env =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)  # admin chat_id

# ===== Logging =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not ADMIN_ID:
    raise SystemExit("BOT_TOKEN yoki ADMIN_ID .env da yo'q")

# ===== User temporary storage =====
USER_PHOTOS = {}

# ===== Keyboard buttons =====
keyboard = ReplyKeyboardMarkup(
    [["Start", "Finish"]],
    resize_keyboard=True
)

# ===== Commands =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tayyor turibman 😊\nRasmlarni yig‘ish uchun Start bosing.",
        reply_markup=keyboard
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.lower()

    if text == "start":
        USER_PHOTOS[user_id] = []
        await update.message.reply_text("Start bosildi. Rasmlarni yuboring 📸")
        return

    if text == "finish":
        if user_id not in USER_PHOTOS or len(USER_PHOTOS[user_id]) == 0:
            await update.message.reply_text("Rasm yo‘qku 😅 Avval rasm yuboring.")
            return

        await update.message.reply_text("PDF uchun nom kiriting:")
        context.user_data["waiting_for_name"] = True
        return

# ===== Handle text (PDF name) =====
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        text = update.message.text

        if not context.user_data.get("waiting_for_name"):
            # Oddiy matn — e'lon qilmoqchi bo'lsangiz boshqa ishlov bering
            return

        pdf_name = text.strip() + ".pdf"
        photos = USER_PHOTOS.get(user_id, [])

        img_list = []
        for b in photos:
            b.seek(0)  # <--- MUHIM: har safar boshidan o'qish
            img = Image.open(b).convert("RGB")
            img_list.append(img)

        pdf_bytes = io.BytesIO()
        if len(img_list) == 1:
            img_list[0].save(pdf_bytes, format="PDF")
        else:
            img_list[0].save(pdf_bytes, format="PDF", save_all=True, append_images=img_list[1:])

        pdf_bytes.seek(0)

        # Foydalanuvchiga yuborish
        await update.message.reply_document(
            document=InputFile(pdf_bytes, filename=pdf_name)
        )

        # Adminga yuborish uchun pointerni boshiga qaytaramiz
        pdf_bytes.seek(0)
        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=InputFile(pdf_bytes, filename=f"{update.message.from_user.full_name}_{pdf_name}")
        )

        # Tozalash
        USER_PHOTOS[user_id] = []
        context.user_data["waiting_for_name"] = False

        # PIL obyektlarini yopish (garov)
        for im in img_list:
            im.close()

    except Exception as e:
        logger.exception("text_handler da xato:")
        await update.message.reply_text("PDF yaratishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

# ===== Handle photos =====
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        if user_id not in USER_PHOTOS:
            await update.message.reply_text("Avval Start bosing 😄")
            return

        photo = update.message.photo[-1]
        file = await photo.get_file()

        bio = io.BytesIO()
        await file.download_to_memory(out=bio)
        bio.seek(0)

        # Har bir foydalanuvchi uchun BytesIO ni saqlaymiz
        USER_PHOTOS[user_id].append(bio)

        # Foydalanuvchiga qabul qilindi
        await update.message.reply_text("Rasm qabul qilindi 📥")

        # Adminga ulashish uchun nusxasini yuboramiz (yoki bio.seek(0) qilamiz)
        # Ehtiyot: yuborganidan keyin pointer oxirga suriladi, shuning uchun yuborishdan oldin seek(0)
        send_bio = io.BytesIO(bio.getvalue())  # nusxa yaratish, originalga ta'sir qilmaydi
        send_bio.seek(0)
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=send_bio,
            caption=f"Rasm {update.message.from_user.full_name} dan olindi"
        )

    except Exception as e:
        logger.exception("photo_handler da xato:")
        await update.message.reply_text("Rasmni qabul qilishda xatolik yuz berdi. Iltimos qayta yuboring.")

# ===== Main =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^(Start|Finish)$"), handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
