import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")


# Bosqichlar
PHONE, NAME, FIELD, SCORE = range(4)

# Admin raqami
ADMIN_PHONE = "+998905837215"  # o'zingizni raqamingiz

# Yo'nalishlar
FIELDS = ["Iqtisodiyot", "Soliq", "Moliya", "Menejment", "Bank ishi", "Jahon iqtisodiyoti"]

# Logger
logging.basicConfig(level=logging.INFO)

# SQLite DB ulash
def init_db():
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone TEXT,
        name TEXT,
        field TEXT,
        score REAL
    )''')
    conn.commit()
    conn.close()

init_db()

# Boshlanish
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_btn = KeyboardButton("📞 Raqam yuborish", request_contact=True)
    await update.message.reply_text(
        "Raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return PHONE

# Telefon
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    context.user_data["phone"] = contact.phone_number
    await update.message.reply_text("Ism va familiyangizni yuboring (masalan: Ali Valiyev):\nBekor qilish uchun /cancel")
    return NAME

# Ism-familiya
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(
        "Yo'nalishni tanlang:",
        reply_markup=ReplyKeyboardMarkup(
            [[field] for field in FIELDS], resize_keyboard=True
        )
    )
    return FIELD

# Yo‘nalish
async def get_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["field"] = update.message.text
    await update.message.reply_text("Balingizni kiriting (0 < x ≤ 100):")
    return SCORE

# Ball
async def get_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        score = float(update.message.text)
        if not 56 <= score <= 100:
            raise ValueError
        context.user_data["score"] = score

        # Saqlash
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (update.effective_user.id,))
        cur.execute('''INSERT INTO users (user_id, phone, name, field, score)
                       VALUES (?, ?, ?, ?, ?)''', (
            update.effective_user.id,
            context.user_data["phone"],
            context.user_data["name"],
            context.user_data["field"],
            context.user_data["score"]
        ))
        conn.commit()
        conn.close()

        await update.message.reply_text("Ma'lumotlaringiz saqlandi ✅\n/menu buyrug'i orqali davom eting")
        return ConversationHandler.END
    except:
        await update.message.reply_text("Ball noto'g'ri kiritildi. Qayta urinib ko'ring.")
        return SCORE

# Menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start  - Qayta boshlash uchun \n"
                                    "/rating - Reyting\n"
                                    "/cancel - Ma'lumotlarni o'chirish")
                                   # "/all - Hamma reytinglar (faqat admin)\n"
                                  #  "/users - Foydalanuvchilar ro'yxati (faqat admin)")

# Reyting
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT field FROM users WHERE user_id = ?", (update.effective_user.id,))
    row = cur.fetchone()
    if row:
        field = row[0]
        cur.execute("SELECT name, score FROM users WHERE field = ? ORDER BY score DESC", (field,))
        result = cur.fetchall()
        text = f"📊 {field} bo'yicha reyting:\n"
        for i, (name, score) in enumerate(result, start=1):
            text += f"{i}. {name} — {score}\n"
        await update.message.reply_text(text+"\nMenuga o'tish uchun /menu")
    else:
        await update.message.reply_text("Avval ro'yxatdan o'ting."+"\nMenuga o'tish uchun /menu")
    conn.close()

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (update.effective_user.id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("Ma'lumotlaringiz o'chirildi ❌"+"\nMenuga o'tish uchun /menu")

# Hamma reyting (admin)
async def all_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT field FROM users GROUP BY field")
    fields = cur.fetchall()
    text = "📊 Hamma yo'nalishlar reytingi:\n"
    for (field,) in fields:
        text += f"\n🟦 {field}:\n"
        cur.execute("SELECT name, score FROM users WHERE field = ? ORDER BY score DESC", (field,))
        for i, (name, score) in enumerate(cur.fetchall(), 1):
            text += f"{i}. {name} — {score}\n"
    await update.message.reply_text(text+"\nMenuga o'tish uchun /menu")
    conn.close()

# Foydalanuvchilar (admin)
async def user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("db.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT name, phone, field, score FROM users")
    rows = cur.fetchall()
    text = "👥 Foydalanuvchilar ro‘yxati:\n\n"
    for i, row in enumerate(rows, 1):
        name, phone, field, score = row
        text += f"{i}. {name} | {phone} | {field} | {score}\n"
    await update.message.reply_text(text+"\nMenuga o'tish uchun /menu")
    conn.close()

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_field)],
            SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_score)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("all", all_rating))
    app.add_handler(CommandHandler("users", user_list))

    print("Bot ishlayapti...")
    app.run_polling()
