import os, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ========= إعداد =========
if not os.path.exists("config.txt"):
    token = input("7983588702:AAHTUVtv0xajy1jNfvxpNzsNnzarzdUNpdU")
    admin = input("7453825680")
    with open("config.txt","w") as f:
        f.write(f"{token}\n{admin}")
    print("✅ تم الحفظ – شغّل السكربت مرة ثانية")
    exit()

TOKEN, ADMIN_ID = open("config.txt").read().splitlines()
ADMIN_ID = int(ADMIN_ID)

REVIEW_USER = "@rcrff"
ASIACELL = "07773531398"

# ========= قاعدة البيانات =========
db = sqlite3.connect("data.db", check_same_thread=False)
c = db.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS prices (year INTEGER PRIMARY KEY, price INTEGER)")
c.execute("""
CREATE TABLE IF NOT EXISTS numbers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    year INTEGER,
    sold INTEGER DEFAULT 0
)
""")
db.commit()

# ========= أسعار افتراضية =========
prices = {2025:1,2024:2,2023:3,2022:4,2021:5,2020:6,2019:7,2018:8}
for y,p in prices.items():
    c.execute("INSERT OR IGNORE INTO prices VALUES (?,?)",(y,p))
db.commit()

# ========= حالات الأدمن =========
admin_state = {}   # لإضافة رقم
points_state = {}  # لإضافة نقاط

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)",(u.id,))
    db.commit()

    c.execute("SELECT balance FROM users WHERE id=?",(u.id,))
    bal = c.fetchone()[0]

    await update.message.reply_text(
        f"🇮🇶 هلا بيك بالمتجر\n\n"
        f"🆔 آيديك: `{u.id}`\n"
        f"💰 رصيدك الحالي: {bal}$\n\n"
        f"اختَر من الأزرار 👇",
        parse_mode="Markdown"
    )
    await menu(update)

# ========= MENU =========
async def menu(update):
    c.execute("SELECT year,price FROM prices ORDER BY year DESC")
    kb = [[InlineKeyboardButton(f"📅 {y} | 💵 {p}$", callback_data=f"buy_{y}")]
          for y,p in c.fetchall()]

    kb.append([InlineKeyboardButton("💳 شحن رصيد", callback_data="charge")])

    if update.effective_user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin")])

    await update.message.reply_text(
        "📦 اختر سنة الرقم:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ========= BUY =========
async def buy(q, year):
    uid = q.from_user.id

    c.execute("SELECT price FROM prices WHERE year=?",(year,))
    price = c.fetchone()[0]

    c.execute("SELECT balance FROM users WHERE id=?",(uid,))
    bal = c.fetchone()[0]

    if bal < price:
        await q.answer(
            f"❌ ما عندك رصيد كافي\n"
            f"💰 رصيدك الحالي: {bal}$\n"
            f"💳 اشحن رصيدك وجرب مرة ثانية",
            show_alert=True
        )
        return

    c.execute("SELECT id,number FROM numbers WHERE year=? AND sold=0",(year,))
    row = c.fetchone()
    if not row:
        await q.answer("❌ نفذت الأرقام لهالسنة", show_alert=True)
        return

    nid, num = row
    c.execute("UPDATE users SET balance=balance-? WHERE id=?",(price,uid))
    c.execute("UPDATE numbers SET sold=1 WHERE id=?",(nid,))
    db.commit()

    await q.message.reply_text(
        f"✅ تم التسليم بنجاح\n\n"
        f"📱 الرقم:\n`{num}`\n\n"
        f"💰 المتبقي: {bal-price}$",
        parse_mode="Markdown"
    )

# ========= شحن =========
async def charge(q):
    user = q.from_user
    await q.message.reply_text(
        f"💳 شحن الرصيد:\n\n"
        f"📞 آسياسيل: {ASIACELL}\n"
        f"👤 الحساب: {REVIEW_USER}\n\n"
        "حوّل المبلغ وبعث سكرين هنا 📸"
    )
    await q.bot.send_message(
        chat_id=REVIEW_USER,
        text=f"🔔 طلب شحن جديد\n👤 @{user.username}\n🆔 {user.id}"
    )

# ========= استقبال السِكرين =========
async def receive_photo(update: Update, context):
    user = update.effective_user
    await context.bot.send_photo(
        chat_id=REVIEW_USER,
        photo=update.message.photo[-1].file_id,
        caption=f"📸 سكرين تحويل\n👤 @{user.username}\n🆔 {user.id}"
    )
    await update.message.reply_text("✅ السِكرين وصل، انتظر شحن الرصيد")

# ========= لوحة الأدمن =========
async def admin_panel(q):
    if q.from_user.id != ADMIN_ID: return
    kb = [
        [InlineKeyboardButton("➕ إضافة رقم", callback_data="addnum")],
        [InlineKeyboardButton("➕ إضافة نقاط", callback_data="addpoints")],
        [InlineKeyboardButton("💰 تعديل الأسعار", callback_data="prices")],
        [InlineKeyboardButton("📦 المخزون", callback_data="stock")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    await q.message.reply_text("⚙️ لوحة الأدمن", reply_markup=InlineKeyboardMarkup(kb))

# ========= إضافة رقم =========
async def add_number_start(q):
    admin_state[q.from_user.id] = "wait_number"
    await q.message.reply_text("✏️ أرسل الرقم:")

async def choose_year(q, year):
    num = admin_state.get(q.from_user.id)
    if not num: return
    c.execute("INSERT INTO numbers VALUES (NULL,?,?,0)",(num,year))
    db.commit()
    admin_state.pop(q.from_user.id)
    await q.message.reply_text("✅ تم إضافة الرقم بنجاح")

# ========= إضافة نقاط =========
async def add_points_start(q):
    points_state[q.from_user.id] = {}
    await q.message.reply_text("🆔 أرسل آيدي الشخص:")

# ========= استقبال نصوص الأدمن =========
async def admin_text_handler(update: Update, context):
    uid = update.effective_user.id
    text = update.message.text

    # إضافة رقم
    if admin_state.get(uid) == "wait_number":
        admin_state[uid] = text
        kb = [[InlineKeyboardButton(str(y), callback_data=f"year_{y}")] for y in prices]
        await update.message.reply_text("📅 اختر السنة:", reply_markup=InlineKeyboardMarkup(kb))
        return

    # إضافة نقاط
    if uid in points_state:
        state = points_state[uid]

        if "user_id" not in state:
            if not text.isdigit():
                await update.message.reply_text("❌ آيدي غير صحيح")
                return
            state["user_id"] = int(text)
            await update.message.reply_text("💰 أرسل عدد النقاط:")
            return

        if "amount" not in state:
            if not text.isdigit():
                await update.message.reply_text("❌ المبلغ غير صحيح")
                return
            amount = int(text)
            target = state["user_id"]

            c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)",(target,))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,target))
            db.commit()

            points_state.pop(uid)
            await update.message.reply_text("✅ تم شحن النقاط بنجاح")
            return

# ========= الأزرار =========
async def buttons(update: Update, context):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("buy_"):
        await buy(q, int(q.data.split("_")[1]))
    elif q.data == "charge":
        await charge(q)
    elif q.data == "admin":
        await admin_panel(q)
    elif q.data == "addnum":
        await add_number_start(q)
    elif q.data == "addpoints":
        await add_points_start(q)
    elif q.data.startswith("year_"):
        await choose_year(q, int(q.data.split("_")[1]))
    elif q.data == "back":
        await start(q.message, context)

# ========= تشغيل =========
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))
app.add_handler(MessageHandler(filters.PHOTO, receive_photo))

print("✅ البوت شغّال – فول ومرتب")
app.run_polling()