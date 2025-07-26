from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

admin_phone = "+998905837215"  # <-- Admin telefon raqami

users = {}  # user_id: {'phone': ..., 'name': ..., 'direction': ..., 'score': ...}

# Bosqichlar
(ASK_PHONE, ASK_NAME, ASK_DIRECTION, ASK_SCORE) = range(4)

directions = ["Iqtisodiyot", "Soliq", "Moliya", "Menejment", "Bank ishi", "Jahon iqtisodiyoti"]

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📞 Raqamni ulashish", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)
    await update.message.reply_text("Iltimos, telefon raqamingizni ulashing:", reply_markup=markup)
    return ASK_PHONE

# 1. Telefon raqam olish
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text("Iltimos, pastdagi tugma orqali telefon raqam ulashing.")
        return ASK_PHONE

    user_id = update.message.from_user.id
    users[user_id] = {'phone': contact.phone_number}
    await update.message.reply_text("Endi ism va familiyangizni kiriting:\nBekor qilish uchun /cancel", reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

# 2. Ism-familiya
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    users[user_id]['name'] = update.message.text

    markup = ReplyKeyboardMarkup([[d] for d in directions], resize_keyboard=True)
    await update.message.reply_text("Yo'nalishni tanlang:\nBekor qilish uchun /cancel", reply_markup=markup)
    return ASK_DIRECTION

# 3. Yo‘nalish tanlash
async def get_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    direction = update.message.text
    if direction not in directions:
        await update.message.reply_text("Iltimos, pastdagi yo'nalishlardan birini tanlang.\nBekor qilish uchun /cancel")
        return ASK_DIRECTION

    users[user_id]['direction'] = direction
    await update.message.reply_text("Endi ball kiriting (56 <= ball ≤ 100):\nBekor qilish uchun /cancel", reply_markup=ReplyKeyboardRemove())
    return ASK_SCORE

# 4. Ball olish
async def get_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        score = float(update.message.text)
        if 56 <= score <= 100:
            users[user_id]['score'] = score
            await update.message.reply_text("Ma'lumotlar saqlandi! /menu buyrug'ini bosing.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Ball 0 dan katta va 100 dan kichik bo'lishi kerak.\nBekor qilish uchun /cancel")
            return ASK_SCORE
    except ValueError:
        await update.message.reply_text("Faqat son kiriting.\nBekor qilish uchun /cancel")
        return ASK_SCORE

# MENU
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/rating - Yo'nalishingiz reytingi\n"
        "/cancel - Reytingdan chiqish\n"
        "/allratings - Barcha reytinglar (admin uchun)\n"
    )

# Reyting chiqarish
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in users or 'score' not in users[user_id]:
        await update.message.reply_text("Siz hali ro'yxatdan o'tmagansiz. /start bosing.")
        return

    direction = users[user_id]['direction']
    ranked = sorted(
        [(u['name'], u['score']) for u in users.values() if u['direction'] == direction and 'score' in u],
        key=lambda x: x[1], reverse=True
    )

    text = f"📊 {direction} yo'nalishi reytingi:\n"
    for i, (name, score) in enumerate(ranked, start=1):
        text += f"{i}. {name}  {score}\n"
    await update.message.reply_text(text+"\nFunksiyalar ro'yhatiga o'tish /menu")

# Cancel funksiyasi
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in users:
        users.pop(user_id)
        await update.message.reply_text("Siz reytingdan chiqarildingiz."+"\nFunksiyalar ro'yhatiga o'tish /menu")
    else:
        await update.message.reply_text("Siz ro'yxatda emassiz."+"\nFunksiyalar ro'yhatiga o'tish /menu")

# Adminga barcha reyting
async def allratings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = users.get(update.message.from_user.id, {}).get('phone', '')
    if phone != admin_phone:
        await update.message.reply_text("Bu funksiya faqat admin uchun."+"\nFunksiyalar ro'yhatiga o'tish /menu")
        return

    text = "🧾 Barcha yo'nalishlar bo'yicha reytinglar:\n"
    for d in directions:
        filtered = sorted(
            [(u['name'], u['score']) for u in users.values() if u.get('direction') == d and 'score' in u],
            key=lambda x: x[1], reverse=True
        )
        text += f"\n📘 {d}:\n"
        for i, (name, score) in enumerate(filtered, 1):
            text += f"{i}. {name}  {score}\n"
    await update.message.reply_text(text+"\nFunksiyalar ro'yhatiga o'tish /menu")

# Foydalanuvchilar ro‘yxati (admin uchun)
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = users.get(update.message.from_user.id, {}).get('phone', '')
    if phone != admin_phone:
        await update.message.reply_text("Bu funksiya faqat admin uchun."+"\nFunksiyalar ro'yhatiga o'tish /menu")
        return

    text = "📋 Foydalanuvchilar ro'yxati:\n\n"
    for u in users.values():
        if 'score' in u:
            text += f"{u['name']} – 📱 {u['phone']}, 📚 {u['direction']}, 🎯 {u['score']}\n"
    await update.message.reply_text(text+"\nFunksiyalar ro'yhatiga o'tish /menu")

# BOTNI ISHLATISH
app = ApplicationBuilder().token("8201520268:AAFM28fe_L4wt-Hdz373ZX5pDUIqP0kHiHs").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_PHONE: [MessageHandler(filters.CONTACT, get_phone)],
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        ASK_DIRECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_direction)],
        ASK_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_score)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("rating", rating))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(CommandHandler("allratings", allratings))
app.add_handler(CommandHandler("users", show_users))

print("Bot ishga tushdi...")
app.run_polling()
