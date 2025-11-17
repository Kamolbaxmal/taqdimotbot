import os
import io
import logging
import requests
from fpdf import FPDF
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# ========== ENV ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# ========== Wikipedia va PDF ==========
WIKI_API = "https://uz.wikipedia.org/w/api.php"

def fetch_wikipedia(topic: str):
    """Wikipedia dan matn va rasm URL larini oladi"""
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "extracts|pageimages",
        "exintro": True,
        "explaintext": True,
        "piprop": "original"
    }
    response = requests.get(WIKI_API, params=params)
    data = response.json()
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    text = page.get("extract", "Bu mavzu bo‘yicha ma’lumot topilmadi.")
    image_url = page.get("original", {}).get("source")
    return text, image_url

def create_pdf(topic: str) -> bytes:
    text, image_url = fetch_wikipedia(topic)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    # Matn
    for line in text.split("\n"):
        pdf.multi_cell(0, 6, line)
        pdf.ln()

    # Rasm
    if image_url:
        try:
            img_data = requests.get(image_url).content
            img_file = io.BytesIO(img_data)
            pdf.image(img_file, x=10, w=180)
        except:
            pass

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output.read()

# ========== BOT HANDLERLARI ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom!\n"
        "/make <mavzu> — mavzu bo‘yicha PDF tayyorlayman.\n"
        "Masalan:\n"
        "/make Sun'iy intellekt"
    )

async def make_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗️ Foydalanish: /make <mavzu>")
        return

    topic = " ".join(context.args)
    await update.message.reply_text(f"⏳ '{topic}' bo‘yicha PDF yaratilmoqda...")

    pdf_bytes = create_pdf(topic)
    file = io.BytesIO(pdf_bytes)
    file.name = f"{topic}.pdf"

    await update.message.reply_document(InputFile(file))
    await update.message.reply_text("✅ Tayyor!")

# ========== MAIN ==========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("make", make_presentation))
    app.run_polling()

if name == "main":
    print("Bot ishga tushdi...")
    main()
