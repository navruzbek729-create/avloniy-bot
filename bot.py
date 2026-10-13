import os
import json
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
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    filters
)
from supabase import create_client, Client

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

SUPABASE_URL = "https://ebdbdpttwzxvtopjsnfn.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_jfIqYz6ZZtzBpDYC4tXULQ_Ve-FQjml"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Admin kirish ma'lumotlari
ADMIN_LOGIN = "avloniyuz"
ADMIN_PASSWORD = "avloniy"

USER_STATES = {}
ACTIVE_ADMINS = set()

# Vercel rasmiy doimiy manzili
WEBAPP_URL = "https://webapp-nine-sigma-85.vercel.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id

    # O'quvchi ro'yxatdan o'tganligini tekshirish
    student = None
    try:
        res = supabase.table("students").select("*").eq("telegram_id", tg_id).execute()
        if res.data and len(res.data) > 0:
            student = res.data[0]
    except Exception as e:
        logging.error(f"Student tekshirishda xatolik: {e}")

    # Foydalanuvchi profiliga mos WebApp URL
    user_app_url = f"{WEBAPP_URL}?tg_id={tg_id}"

    keyboard = []

    if student:
        # Ro'yxatdan o'tgan bo'lsa
        keyboard.append([InlineKeyboardButton("🚀 Web App Platformasi", web_app=WebAppInfo(url=user_app_url))])
        keyboard.append([InlineKeyboardButton("🌐 Kompyuterda ochish (Havola)", url=user_app_url)])
        keyboard.append([InlineKeyboardButton("👤 Mening Profilim & Natijalarim", callback_data="my_profile")])
        welcome_text = (
            f"Assalomu alaykum, <b>{student['full_name']}</b>!\n"
            f"Guruh: <b>{student['group_number']}</b>\n\n"
            f"📚 <b>Avloniy Ta'lim Platformasi</b>ga xush kelibsiz!\n"
            f"Quyidagi tugmalar orqali platformaga kiring yoki natijalaringizni tekshiring:"
        )
    else:
        # Ro'yxatdan o'tmagan bo'lsa
        keyboard.append([InlineKeyboardButton("📝 Ro'yxatdan o'tish (Akkaunt ochish)", callback_data="register_student")])
        keyboard.append([InlineKeyboardButton("🚀 Mehmon sifatida kirish", web_app=WebAppInfo(url=WEBAPP_URL))])
        keyboard.append([InlineKeyboardButton("🌐 Kompyuterda ochish (Havola)", url=WEBAPP_URL)])
        welcome_text = (
            f"Assalomu alaykum, {user.first_name}!\n\n"
            f"📚 <b>Avloniy Ta'lim Platformasi</b>ga xush kelibsiz.\n"
            f"Test natijalaringiz va statistikangiz saqlanib borishi uchun iltimos, <b>akkaunt oching</b>."
        )

    keyboard.append([InlineKeyboardButton("🔐 Admin sifatida kirish", callback_data="admin_login")])
    if tg_id in ACTIVE_ADMINS:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])

    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    data = query.data

    if data == "register_student":
        USER_STATES[tg_id] = {"step": "waiting_name"}
        await query.message.reply_text(
            "👤 <b>Ism va Familiyangizni kiriting:</b>\n<i>(Masalan: Omonjon Valijonov)</i>",
            parse_mode="HTML"
        )

    elif data == "my_profile":
        try:
            st_res = supabase.table("students").select("*").eq("telegram_id", tg_id).execute()
            student = st_res.data[0] if st_res.data else None

            # Natijalarni hisoblash
            res = supabase.table("user_results").select("*").eq("telegram_id", tg_id).execute()
            results = res.data or []
            total_tests = len(results)
            total_score = sum(r.get("score", 0) for r in results)

            if student:
                text = (
                    f"👤 <b>Foydalanuvchi Profili</b>\n\n"
                    f"🏷️ <b>F.I.SH:</b> {student['full_name']}\n"
                    f"🎓 <b>Guruh:</b> {student['group_number']}\n"
                    f"📊 <b>Yechilgan testlar soni:</b> {total_tests} ta\n"
                    f"⭐ <b>To'plangan ballar:</b> {total_score}\n\n"
                    f"🔗 <b>Shaxsiy havolangiz:</b>\n{WEBAPP_URL}?tg_id={tg_id}"
                )
            else:
                text = "Profil ma'lumotlari topilmadi."
            
            await query.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Platformaga o'tish", web_app=WebAppInfo(url=f"{WEBAPP_URL}?tg_id={tg_id}"))]
                ])
            )
        except Exception as e:
            await query.message.reply_text(f"Profilni yuklashda xatolik: {e}")

    elif data == "admin_login":
        USER_STATES[tg_id] = {"step": "waiting_login"}
        await query.message.reply_text("Iltimos, Admin loginini kiriting:")

    elif data == "admin_panel":
        if tg_id not in ACTIVE_ADMINS:
            await query.message.reply_text("Sizda admin huquqi yo'q!")
            return
        
        panel_keyboard = [
            [InlineKeyboardButton("➕ Yangi Fan qo'shish", callback_data="add_subject")],
            [InlineKeyboardButton("📁 Bo'limlar boshqaruvi", callback_data="manage_sections")],
            [InlineKeyboardButton("📤 Fayl yuklash & AI Test", callback_data="upload_material")],
            [InlineKeyboardButton("👥 Yangi Admin qo'shish", callback_data="add_admin_user")]
        ]
        await query.message.reply_text(
            "⚙️ <b>Avloniy Admin Boshqaruv Paneli</b>\n\nQuyidagi amallardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(panel_keyboard)
        )

    elif data == "add_subject":
        USER_STATES[tg_id] = {"step": "waiting_subject_name"}
        await query.message.reply_text("Yangi Fan nomini kiriting (masalan: <i>O'zbekiston tarixi</i>):", parse_mode="HTML")

    elif data == "upload_material":
        await query.message.reply_text(
            "📂 Iltimos, darslikning <b>PDF</b> yoki <b>Word (.docx)</b> faylini botga yuboring.\n"
            "Fayl qabul qilingach, qaysi fanga va bo'limga tegishliligi so'raladi.",
            parse_mode="HTML"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    text = update.message.text.strip()

    if tg_id in USER_STATES:
        state = USER_STATES[tg_id]
        step = state.get("step")

        # Ro'yxatdan o'tish (Ism)
        if step == "waiting_name":
            USER_STATES[tg_id] = {"step": "waiting_group", "full_name": text}
            await update.message.reply_text(
                f"Rahmat, <b>{text}</b>!\n\nEndi <b>Guruh nomini</b> kiriting:\n<i>(Istalgan nom yoki raqam kiritishingiz mumkin: masalan, 101, Tarixchilar, A-guruh, Magistr-1 va h.k.)</i>",
                parse_mode="HTML"
            )

        # Ro'yxatdan o'tish (Guruh)
        elif step == "waiting_group":
            full_name = state.get("full_name")
            group_number = text

            try:
                supabase.table("students").upsert({
                    "telegram_id": tg_id,
                    "full_name": full_name,
                    "group_number": group_number,
                    "username": update.effective_user.username
                }).execute()

                del USER_STATES[tg_id]
                user_app_url = f"{WEBAPP_URL}?tg_id={tg_id}"

                await update.message.reply_text(
                    f"🎉 <b>Akkaunt muvaffaqiyatli yaratildi!</b>\n\n"
                    f"👤 <b>F.I.SH:</b> {full_name}\n"
                    f"🎓 <b>Guruh:</b> {group_number}\n\n"
                    f"Endi barcha ishlagan testlaringiz va natijalaringiz profilingizda saqlanib boradi!\n"
                    f"Noutbuk yoki kompyuterdan kirsangiz ham ushbu havola orqali profilingiz saqlanadi.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Web App Platformasi", web_app=WebAppInfo(url=user_app_url))],
                        [InlineKeyboardButton("🌐 Kompyuter uchun Havola", url=user_app_url)]
                    ])
                )
            except Exception as e:
                await update.message.reply_text(f"Saqlashda xatolik yuz berdi: {e}")

        # Admin Login
        elif step == "waiting_login":
            if text == ADMIN_LOGIN:
                USER_STATES[tg_id] = {"step": "waiting_password"}
                await update.message.reply_text("Login to'g'ri. Endi parolni kiriting:")
            else:
                await update.message.reply_text("❌ Login noto'g'ri. Qaytadan urinib ko'ring:")

        # Admin Parol
        elif step == "waiting_password":
            if text == ADMIN_PASSWORD:
                ACTIVE_ADMINS.add(tg_id)
                del USER_STATES[tg_id]
                try:
                    supabase.table("admins").upsert({
                        "telegram_id": tg_id,
                        "username": update.effective_user.username,
                        "full_name": update.effective_user.full_name,
                        "role": "admin"
                    }).execute()
                except Exception as e:
                    logging.error(f"Admin saqlashda xato: {e}")

                await update.message.reply_text(
                    "✅ <b>Muvaffaqiyatli kirdingiz!</b> Sizga to'liq admin huquqlari berildi.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Admin Panelga o'tish", callback_data="admin_panel")]
                    ])
                )
            else:
                await update.message.reply_text("❌ Parol noto'g'ri. Qaytadan urinib ko'ring:")

        elif step == "waiting_subject_name":
            try:
                supabase.table("subjects").insert({"name": text}).execute()
                await update.message.reply_text(f"✅ <b>'{text}'</b> fani bazaga qo'shildi!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"Xatolik: {e}")
            del USER_STATES[tg_id]

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in ACTIVE_ADMINS:
        await update.message.reply_text("Faqat adminlar fayl yuklashi mumkin.")
        return

    doc = update.message.document
    file_name = doc.file_name
    file_id = doc.file_id

    await update.message.reply_text(
        f"📥 <b>Fayl qabul qilindi:</b> {file_name}\n\n"
        f"Test tuzish turini tanlang:\n"
        f"1️⃣ <b>Mavzulashtirilgan</b> (Har N ta mavzuga 35 ta A+ test)\n"
        f"2️⃣ <b>Boblashtirilgan</b> (Har bir bobga 30 ta A+ test)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Mavzulashgan (35 ta)", callback_data=f"test_topic_{file_id}")],
            [InlineKeyboardButton("Boblashgan (30 ta)", callback_data=f"test_chapter_{file_id}")]
        ])
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
    # Render uchun fon serveri
    threading.Thread(target=run_healthcheck_server, daemon=True).start()

    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8684781208:AAEAUHfJp0rA00TncD4fgt6eiuJo2GMRh9g")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

    print("Avloniy Bot 24/7 rejimda ishga tushirildi...")
    app.run_polling()

if __name__ == "__main__":
    main()
