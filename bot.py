import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    WebAppInfo
)
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

WEBAPP_URL = "https://webapp-nine-sigma-85.vercel.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        f"📚 <b>Avloniy Ta'lim va A+ Testlar Platformasi</b>ga xush kelibsiz.\n\n"
        f"📖 <b>Qisqacha Yo'riqnoma:</b>\n"
        f"1️⃣ <b>O'quvchilar uchun:</b> Ilovaga kiring va <i>'Ro'yxatdan o'tish'</i> orqali ismingiz hamda guruhingizni kiriting. Tizim sizga shaxsiy login va parol beradi. Darsliklar asosidagi A+ testlarni yeching va natijalaringizni to'plang!\n\n"
        f"2️⃣ <b>Adminlar uchun:</b> Ilova ichida <i>'Kirish'</i> tugmasini bosib, Admin logini (<code>avloniyuz</code>) va paroli (<code>avloniy</code>) bilan kiring. Barcha fanlar, bo'limlar va darsliklarni to'g'ridan-to'g'ri ilova ichidan qo'shishingiz va boshqarishingiz mumkin.\n\n"
        f"Platformani ochish uchun quyidagi tugmani bosing 👇"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚀 Avloniy Platformasini Ochish", web_app=WebAppInfo(url=WEBAPP_URL))
        ],
        [
            InlineKeyboardButton("🌐 Kompyuterda Ochish (Web Link)", url=WEBAPP_URL)
        ]
    ]

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Avloniy Bot is running 24/7!")

def run_healthcheck_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def main():
    threading.Thread(target=run_healthcheck_server, daemon=True).start()

    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8684781208:AAEAUHfJp0rA00TncD4fgt6eiuJo2GMRh9g")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Avloniy Yo'naltiruvchi Bot ishga tushirildi...")
    app.run_polling()

if __name__ == "__main__":
    main()
