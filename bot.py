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
from ai_generator import extract_text_from_pdf, extract_text_from_docx, generate_questions_with_ai

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

SUPABASE_URL = "https://ebdbdpttwzxvtopjsnfn.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_jfIqYz6ZZtzBpDYC4tXULQ_Ve-FQjml"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

ADMIN_LOGIN = "avloniyuz"
ADMIN_PASSWORD = "avloniy"

USER_STATES = {}
ACTIVE_ADMINS = set()

WEBAPP_URL = "https://webapp-nine-sigma-85.vercel.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id

    student = None
    try:
        res = supabase.table("students").select("*").eq("telegram_id", tg_id).execute()
        if res.data and len(res.data) > 0:
            student = res.data[0]
    except Exception as e:
        logging.error(f"Student tekshirishda xato: {e}")

    user_app_url = f"{WEBAPP_URL}?tg_id={tg_id}"
    keyboard = []

    if student:
        keyboard.append([InlineKeyboardButton("🚀 Web App Platformasi", web_app=WebAppInfo(url=user_app_url))])
        keyboard.append([InlineKeyboardButton("🌐 Kompyuterda ochish (Havola)", url=user_app_url)])
        keyboard.append([InlineKeyboardButton("👤 Mening Profilim & Natijalarim", callback_data="my_profile")])
        welcome_text = (
            f"Assalomu alaykum, <b>{student['full_name']}</b>!\n"
            f"Guruh: <b>{student['group_number']}</b>\n\n"
            f"📚 <b>Avloniy Ta'lim Platformasi</b>ga xush kelibsiz!"
        )
    else:
        keyboard.append([InlineKeyboardButton("📝 Ro'yxatdan o'tish (Akkaunt ochish)", callback_data="register_student")])
        keyboard.append([InlineKeyboardButton("🚀 Mehmon sifatida kirish", web_app=WebAppInfo(url=WEBAPP_URL))])
        keyboard.append([InlineKeyboardButton("🌐 Kompyuterda ochish (Havola)", url=WEBAPP_URL)])
        welcome_text = (
            f"Assalomu alaykum, {user.first_name}!\n\n"
            f"📚 <b>Avloniy Ta'lim Platformasi</b>ga xush kelibsiz.\n"
            f"Natijalaringiz saqlanib borishi uchun iltimos, <b>akkaunt oching</b>."
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
        await query.message.reply_text("👤 <b>Ism va Familiyangizni kiriting:</b>", parse_mode="HTML")

    elif data == "my_profile":
        try:
            st_res = supabase.table("students").select("*").eq("telegram_id", tg_id).execute()
            student = st_res.data[0] if st_res.data else None
            res = supabase.table("user_results").select("*").eq("telegram_id", tg_id).execute()
            results = res.data or []
            total_tests = len(results)
            total_score = sum(r.get("score", 0) for r in results)

            if student:
                text = (
                    f"👤 <b>Foydalanuvchi Profili</b>\n\n"
                    f"🏷️ <b>F.I.SH:</b> {student['full_name']}\n"
                    f"🎓 <b>Guruh:</b> {student['group_number']}\n"
                    f"📊 <b>Yechilgan testlar:</b> {total_tests} ta\n"
                    f"⭐ <b>To'plangan ball:</b> {total_score}\n\n"
                    f"🔗 <b>Shaxsiy havola:</b>\n{WEBAPP_URL}?tg_id={tg_id}"
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
            await query.message.reply_text(f"Xatolik: {e}")

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
            [InlineKeyboardButton("📚 Darsliklar yuklash & AI Test", callback_data="start_upload_book")]
        ]
        await query.message.reply_text(
            "⚙️ <b>Avloniy Admin Boshqaruv Paneli</b>\n\nQuyidagi amallardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(panel_keyboard)
        )

    elif data == "add_subject":
        USER_STATES[tg_id] = {"step": "waiting_subject_name"}
        await query.message.reply_text("Yangi Fan nomini kiriting (masalan: <i>Ona tili</i> yoki <i>Tarix</i>):", parse_mode="HTML")

    # 1. Bo'limlar boshqaruvi: Fanlar ro'yxatini chiqarish
    elif data == "manage_sections":
        try:
            subs = supabase.table("subjects").select("*").order("name").execute().data or []
            if not subs:
                await query.message.reply_text("Hozircha fanlar mavjud emas. Avval '➕ Yangi Fan qo'shish' tugmasini bosing.")
                return
            
            keyboard = []
            for s in subs:
                keyboard.append([InlineKeyboardButton(f"📘 {s['name']}", callback_data=f"sel_sub_sec_{s['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
            
            await query.message.reply_text(
                "📁 <b>Qaysi fanga yangi bo'lim qo'shmoqchisiz?</b> Fanni tanlang:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await query.message.reply_text(f"Xatolik: {e}")

    # 2. Fan tanlangandan so'ng bo'lim nomini so'rash
    elif data.startswith("sel_sub_sec_"):
        subject_id = data.replace("sel_sub_sec_", "")
        USER_STATES[tg_id] = {"step": "waiting_section_title", "subject_id": subject_id}
        await query.message.reply_text(
            "✍️ <b>Yangi bo'lim nomini kiriting:</b>\n<i>(Istalgan nom: masalan, 1-Bob. Qadimgi davr yoki Fonetika bo'limi)</i>",
            parse_mode="HTML"
        )

    # 3. Darslik yuklash: Avval fanni tanlash
    elif data == "start_upload_book":
        try:
            subs = supabase.table("subjects").select("*").order("name").execute().data or []
            if not subs:
                await query.message.reply_text("Avval fan qo'shing.")
                return
            
            keyboard = []
            for s in subs:
                keyboard.append([InlineKeyboardButton(f"📘 {s['name']}", callback_data=f"up_sub_{s['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])

            await query.message.reply_text(
                "📚 <b>1-qadam: Darslik qaysi fanga tegishli?</b> Fanni tanlang:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await query.message.reply_text(f"Xatolik: {e}")

    # 4. Fanni tanladi -> Endi o'sha fanning bo'limlarini tanlash
    elif data.startswith("up_sub_"):
        subject_id = data.replace("up_sub_", "")
        try:
            secs = supabase.table("sections").select("*").eq("subject_id", subject_id).execute().data or []
            if not secs:
                await query.message.reply_text("Bu fanda hali bo'limlar yo'q! Avval '📁 Bo'limlar boshqaruvi'dan bo'lim qo'shing.")
                return

            keyboard = []
            for sec in secs:
                keyboard.append([InlineKeyboardButton(f"📂 {sec['title']}", callback_data=f"up_sec_{sec['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="start_upload_book")])

            await query.message.reply_text(
                "📂 <b>2-qadam: Qaysi bo'limga darslik yuklaysiz?</b> Bo'limni tanlang:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await query.message.reply_text(f"Xatolik: {e}")

    # 5. Bo'lim tanlandi -> Endi fayl yuborishni so'rash
    elif data.startswith("up_sec_"):
        section_id = data.replace("up_sec_", "")
        USER_STATES[tg_id] = {"step": "waiting_doc_upload", "section_id": section_id}
        await query.message.reply_text(
            "📤 <b>3-qadam: Darslik faylini yuboring:</b>\n"
            "Iltimos, darslikning <b>PDF</b> yoki <b>Word (.docx)</b> faylini botga yuboring.",
            parse_mode="HTML"
        )

    # 6. Test turi tanlanganda AI test tuzish
    elif data.startswith("gen_test_"):
        # Format: gen_test_topic_fileId_sectionId yoki gen_test_chapter_fileId_sectionId
        parts = data.split("_")
        test_type = parts[2] # 'topic' yoki 'chapter'
        file_id = parts[3]
        section_id = parts[4]

        count = 35 if test_type == "topic" else 30
        type_name = "Mavzulashtirilgan (35 ta)" if test_type == "topic" else "Boblashtirilgan (30 ta)"

        status_msg = await query.message.reply_text(
            f"⏳ <b>AI {type_name} A+ zanjirli testlarni yaratmoqda...</b>\n"
            f"Iltimos, 15-30 soniya kuting...",
            parse_mode="HTML"
        )

        try:
            # Faylni yuklab olish
            bot_file = await context.bot.get_file(file_id)
            os.makedirs("downloads", exist_ok=True)
            local_path = os.path.join("downloads", f"{file_id}.tmp")
            await bot_file.download_to_drive(local_path)

            # Matnni ajratish
            text = extract_text_from_pdf(local_path)
            if not text:
                text = extract_text_from_docx(local_path)

            if not text:
                await status_msg.edit_text("❌ Fayldan matnni ajratib bo'lmadi.")
                return

            # AI orqali savollar tuzish
            questions = generate_questions_with_ai(text, test_type=test_type, count=count)

            if not questions:
                await status_msg.edit_text("❌ AI savollarni yaratishda xatolik berdi yoki GEMINI_API_KEY ulanmagan.")
                return

            # Supabase ga test saqlash
            t_res = supabase.table("tests").insert({
                "section_id": section_id,
                "title": f"A+ Darajadagi {type_name} Test",
                "test_type": test_type,
                "questions_count": len(questions),
                "difficulty": "A+",
                "is_chain": True
            }).execute()

            test_id = t_res.data[0]["id"]

            # Savollarni saqlash
            q_inserts = []
            for q in questions:
                q_inserts.append({
                    "test_id": test_id,
                    "question_number": q.get("question_number", 1),
                    "chain_group": q.get("chain_group", "Zanjir-1"),
                    "question_text": q.get("question_text", ""),
                    "options": q.get("options", {}),
                    "correct_answer": q.get("correct_answer", "A"),
                    "explanation": q.get("explanation", "")
                })

            supabase.table("questions").insert(q_inserts).execute()

            await status_msg.edit_text(
                f"🎉 <b>Muvaffaqiyatli yakunlandi!</b>\n\n"
                f"✅ Jami <b>{len(questions)} ta</b> A+ darajadagi zanjirli testlar yaratildi va bazaga saqlandi!\n"
                f"O'quvchilar Web App platformasida bu testni darhol yechishlari mumkin.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Web App da ko'rish", web_app=WebAppInfo(url=WEBAPP_URL))]
                ])
            )
        except Exception as e:
            await status_msg.edit_text(f"Xatolik: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    text = update.message.text.strip()

    if tg_id in USER_STATES:
        state = USER_STATES[tg_id]
        step = state.get("step")

        if step == "waiting_name":
            USER_STATES[tg_id] = {"step": "waiting_group", "full_name": text}
            await update.message.reply_text(
                f"Rahmat, <b>{text}</b>!\n\nEndi <b>Guruh nomini</b> kiriting:\n<i>(Istalgan nom yoki raqam)</i>",
                parse_mode="HTML"
            )

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
                    f"🎓 <b>Guruh:</b> {group_number}",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Web App Platformasi", web_app=WebAppInfo(url=user_app_url))]
                    ])
                )
            except Exception as e:
                await update.message.reply_text(f"Xatolik: {e}")

        elif step == "waiting_login":
            if text == ADMIN_LOGIN:
                USER_STATES[tg_id] = {"step": "waiting_password"}
                await update.message.reply_text("Login to'g'ri. Endi parolni kiriting:")
            else:
                await update.message.reply_text("❌ Login noto'g'ri. Qaytadan urinib ko'ring:")

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
                    pass

                await update.message.reply_text(
                    "✅ <b>Muvaffaqiyatli kirdingiz!</b> Sizga to'liq admin huquqlari berildi.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Admin Panelga o'tish", callback_data="admin_panel")]
                    ])
                )
            else:
                await update.message.reply_text("❌ Parol noto'g'ri.")

        elif step == "waiting_subject_name":
            try:
                supabase.table("subjects").insert({"name": text}).execute()
                await update.message.reply_text(f"✅ <b>'{text}'</b> fani bazaga qo'shildi!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"Xatolik: {e}")
            del USER_STATES[tg_id]

        elif step == "waiting_section_title":
            subject_id = state.get("subject_id")
            try:
                supabase.table("sections").insert({
                    "subject_id": subject_id,
                    "title": text
                }).execute()
                await update.message.reply_text(f"✅ <b>'{text}'</b> bo'limi muvaffaqiyatli qo'shildi!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"Xatolik: {e}")
            del USER_STATES[tg_id]

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if tg_id not in ACTIVE_ADMINS:
        await update.message.reply_text("Faqat adminlar darslik yuklashi mumkin.")
        return

    doc = update.message.document
    file_name = doc.file_name
    file_id = doc.file_id

    # Agar admin oldindan bo'limni tanlagan bo'lsa
    state = USER_STATES.get(tg_id, {})
    section_id = state.get("section_id")

    if not section_id:
        await update.message.reply_text(
            "⚠️ Iltimos, avval Admin Paneldan <b>'📚 Darsliklar yuklash & AI Test'</b> tugmasini bosib fanni va bo'limni tanlang, so'ngra fayl tashlang.",
            parse_mode="HTML"
        )
        return

    # Bo'limga darslik sifatida saqlash
    try:
        supabase.table("materials").insert({
            "section_id": section_id,
            "title": file_name,
            "file_url": file_id,
            "file_type": "pdf" if file_name.endswith(".pdf") else "docx"
        }).execute()
    except Exception as e:
        logging.error(f"Material saqlashda xato: {e}")

    del USER_STATES[tg_id]

    await update.message.reply_text(
        f"📥 <b>Darslik qabul qilindi:</b> {file_name}\n\n"
        f"Endi ushbu darslik bo'yicha AI test tuzish turini tanlang:\n"
        f"1️⃣ <b>Mavzulashtirilgan</b> (35 ta A+ test)\n"
        f"2️⃣ <b>Boblashtirilgan</b> (30 ta A+ test)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Mavzulashgan (35 ta)", callback_data=f"gen_test_topic_{file_id}_{section_id}")],
            [InlineKeyboardButton("Boblashgan (30 ta)", callback_data=f"gen_test_chapter_{file_id}_{section_id}")]
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
