import sqlite3
import html
import time
import asyncio
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# البيانات الخاصة بك
# ---------------------------------------------------------
OWNER_ID = 7900000866  # المالك الأساسي الوحيد
ADMIN_IDS = [7900000866, 8759077518]
BOT_TOKEN = "8923688220:AAF9jNQXFJDF3jzBFHQhwZdqUl7xABDx8jY"

DEVELOPER_USERNAME = "@moooooooo_0039"
DEVELOPER_TAG = "@body_eljoker_id"
ADMIN_USERNAME = "@moooooooo_0039"

COLOR_EMOJIS = ["🔴", "🟢", "🔷", "👑", "⚡", "💎", "🔥", "🚀", "🟡", "🟣"]

CATEGORIES_CACHE = []
CACHE_TIME = 0
USER_COOLDOWNS = {}

def invalidate_cache():
    global CATEGORIES_CACHE
    CATEGORIES_CACHE = []

# ---------------------------------------------------------
# قاعدة البيانات الفائقة السرعة
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("bot_database.db", timeout=5)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            points_required INTEGER DEFAULT 0,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            points INTEGER DEFAULT 0,
            warnings INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            join_date INTEGER DEFAULT 0,
            invited_by INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            item_id INTEGER,
            PRIMARY KEY (user_id, item_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY,
            points INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forced_channels (
            channel_username TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'off')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_points', '2')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('daily_points', '5')")
    
    for admin_id in ADMIN_IDS:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))

    conn.commit()
    conn.close()

init_db()

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res is not None
    except Exception:
        return False

def log_action(user_id, action):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_logs (user_id, action, timestamp) VALUES (?, ?, ?)", (user_id, action, int(time.time())))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_setting(key, default):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = cursor.fetchone()
        conn.close()
        return int(res[0]) if res and res[0].isdigit() else default
    except Exception:
        return default

def is_maintenance_mode():
    return str(get_setting('maintenance', 'off')).lower() in ['on', '1']

def is_banned(user_id):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res is not None
    except Exception:
        return False

def check_rate_limit(user_id):
    if is_admin(user_id):
        return True
    current_time = time.time()
    last_time = USER_COOLDOWNS.get(user_id, 0)
    if current_time - last_time < 0.2:
        return False
    USER_COOLDOWNS[user_id] = current_time
    return True

# ---------------------------------------------------------
# إدارة الأدمن الجدد (للمالك فقط)
# ---------------------------------------------------------
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص لمالك البوت الأساسي فقط.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ الاستخدام الصحيح:\n<code>/addadmin <USER_ID></code>", parse_mode="HTML")
        return
    new_admin_id = int(context.args[0])
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"👑 تم تعيين المستخدم <code>{new_admin_id}</code> كأدمن جديد بنجاح!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {e}")

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص لمالك البوت الأساسي فقط.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ الاستخدام الصحيح:\n<code>/deladmin <USER_ID></code>", parse_mode="HTML")
        return
    target_id = int(context.args[0])
    if target_id == OWNER_ID:
        await update.message.reply_text("❌ لا يمكنك حذف المالك الأساسي.")
        return
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🗑️ تم إزالة المستخدم <code>{target_id}</code> من قائمة الأدمنز بنجاح!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {e}")

async def check_user_subscription(bot, user_id):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_username FROM forced_channels")
        channels = cursor.fetchall()
        conn.close()

        if not channels:
            return True, []

        not_subscribed = []
        for ch in channels:
            ch_username = ch[0]
            try:
                member = await bot.get_chat_member(chat_id=ch_username, user_id=user_id)
                if member.status in ['left', 'kicked']:
                    not_subscribed.append(ch_username)
            except Exception:
                not_subscribed.append(ch_username)
        
        return len(not_subscribed) == 0, not_subscribed
    except Exception:
        return True, []

async def check_or_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if is_admin(user_id):
        return True
    
    is_subbed, unsubbed_channels = await check_user_subscription(context.bot, user_id)
    if not is_subbed:
        keyboard = []
        for ch in unsubbed_channels:
            clean_ch = ch.replace('@', '')
            keyboard.append([InlineKeyboardButton("🔔 اشترك في القناة", url=f"https://t.me/{clean_ch}")])
        keyboard.append([InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")])
        
        sub_msg = (
            "⚠️ <b>عذراً، يجب عليك الاشتراك في القنوات الإجبارية التالية لاستخدام البوت:</b>\n\n"
            "اشترك في القنوات ثم اضغط على زر التحقق أدناه لتفعيل حسابك 🔓"
        )
        
        if update.message:
            await update.message.reply_text(sub_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        elif update.callback_query:
            try:
                await update.callback_query.answer("❌ يجب الاشتراك في جميع القنوات أولاً!", show_alert=True)
                await update.callback_query.message.reply_text(sub_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            except Exception:
                pass
        return False
    return True

async def add_forced_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) or not context.args:
        return
    ch = context.args[0].strip()
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO forced_channels (channel_username) VALUES (?)", (ch,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تمت إضافة القناة <code>{ch}</code> بنجاح!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def remove_forced_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) or not context.args:
        return
    ch = context.args[0].strip()
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM forced_channels WHERE channel_username = ?", (ch,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"🗑️ تمت إزالة القناة <code>{ch}</code> بنجاح!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

def get_cached_categories():
    global CATEGORIES_CACHE, CACHE_TIME
    current_time = time.time()
    if not CATEGORIES_CACHE or (current_time - CACHE_TIME > 10):
        try:
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories")
            CATEGORIES_CACHE = cursor.fetchall()
            conn.close()
            CACHE_TIME = current_time
        except Exception:
            pass
    return CATEGORIES_CACHE

def save_or_update_user(user_id, full_name, username, referrer_id=0):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (user_id, full_name, username, points, warnings, last_daily, join_date, invited_by) VALUES (?, ?, ?, 0, 0, 0, ?, ?)", 
                           (user_id, full_name, username, int(time.time()), referrer_id))
            conn.commit()
            if referrer_id and referrer_id != user_id:
                ref_pts = get_setting('referral_points', 2)
                cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (ref_pts, referrer_id))
                conn.commit()
        else:
            cursor.execute("UPDATE users SET full_name = ?, username = ? WHERE user_id = ?", (full_name, username, user_id))
            conn.commit()
        conn.close()
    except Exception:
        pass

def get_user_points(user_id):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else 0
    except Exception:
        return 0

async def send_long_text(chat_id, context, text: str):
    max_length = 4000
    if len(text) <= max_length:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    else:
        for i in range(0, len(text), max_length):
            await context.bot.send_message(chat_id=chat_id, text=text[i:i + max_length], parse_mode="HTML")

def get_main_keyboard(user_id):
    categories = get_cached_categories()
    keyboard = [[KeyboardButton(f"{COLOR_EMOJIS[idx % len(COLOR_EMOJIS)]}  {cat[0]}  {COLOR_EMOJIS[idx % len(COLOR_EMOJIS)]}")] for idx, cat in enumerate(categories)]
    
    keyboard.append([KeyboardButton("🎁 لوحة النقاط الشخصية"), KeyboardButton("💼 رصيدي الحالي")])
    keyboard.append([KeyboardButton("⭐ أدوات المفضلة"), KeyboardButton("🔎 بحث سريع عن أداة")])
    keyboard.append([KeyboardButton("💸 ارسال النقاط"), KeyboardButton("🎁 الهدية اليومية (كل 24 ساعة)")])
    keyboard.append([KeyboardButton("🚨 تبليغ عن مشكلة"), KeyboardButton("🎯 طلب أداة/ثغرة خاصة (Bounty)")])
    keyboard.append([KeyboardButton("🛠️ الدعم الفني")])

    if is_admin(user_id):
        keyboard.append([KeyboardButton("➕ إضافة قسم أمني جديد"), KeyboardButton("📝 إضافة أداة أو ثغرة")])
        keyboard.append([KeyboardButton("💰 تعديل سعر أداة"), KeyboardButton("❌ حذف عنصر")])
        keyboard.append([KeyboardButton("🗑️ حذف قسم"), KeyboardButton("📢 إضافة قناة إجبارية")])
        keyboard.append([KeyboardButton("❌ حذف قناة إجبارية"), KeyboardButton("📢 إذاعة عامة للشامل")])
        keyboard.append([KeyboardButton("📊 إحصائيات النظام"), KeyboardButton("👑 نشطاء البوت (Top Users)")])
        keyboard.append([KeyboardButton("🚫 حظر مستخدم"), KeyboardButton("✅ إلغاء حظر مستخدم")])
        m_status = "🔴 إيقاف وضع الصيانة" if is_maintenance_mode() else "🟢 تفعيل وضع الصيانة"
        keyboard.append([KeyboardButton(m_status)])

    # أزرار مخصصة للمالك فقط (7900000866)
    if is_owner(user_id):
        keyboard.append([KeyboardButton("👑 تعيين أدمن جديد"), KeyboardButton("🗑️ حذف أدمن")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def daily_backup_task(application):
    await asyncio.sleep(10)
    while True:
        try:
            if os.path.exists("bot_database.db"):
                with open("bot_database.db", "rb") as db_f, open(__file__, "rb") as script_f:
                    await application.bot.send_document(chat_id=OWNER_ID, document=db_f, caption="📦 نسخة احتياطية لقاعدة البيانات")
                    await application.bot.send_document(chat_id=OWNER_ID, document=script_f, caption="💻 نسخة احتياطية للسكربت")
        except Exception:
            pass
        await asyncio.sleep(86400)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if not check_rate_limit(user_id):
        return

    if is_banned(user_id) or (is_maintenance_mode() and not is_admin(user_id)):
        return

    if not await check_or_block(update, context):
        return

    referrer_id = 0
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])

    save_or_update_user(user_id, user.full_name or "مستخدم", f"@{user.username}" if user.username else "لا يوجد", referrer_id)
    log_action(user_id, "/start")
    user_points = get_user_points(user_id)
    
    full_name = html.escape(user.full_name or "مستخدم")
    username = f"@{html.escape(user.username)}" if user.username else "لا يوجد"

    welcome_msg = (
        f"🛡️ <b>CYBER SECURITY BOT</b>\n\n"
        f"مرحباً بك يا <b>{full_name}</b> في منصة الأمن السيبراني والتحليل التقني. ⚡\n\n"
        f"🔐 <b>معلومات المستخدم:</b>\n"
        f"- 👤 الاسم: <code>{full_name}</code>\n"
        f"- 🆔 اسم المستخدم: <code>{username}</code>\n"
        f"- 🔢 المعرّف (ID): <code>{user_id}</code>\n"
        f"- 💎 رصيدك الحالي: <code>{user_points} نقطة</code>\n\n"
        f"💻 <b>الأقسام المتاحة:</b>\n"
        f"- 🔎 أدوات الفحص الأمني.\n"
        f"- 🌐 تحليل الشبكات.\n"
        f"- 🧪 مختبر الاختبار الأخلاقي.\n"
        f"- 🛠️ أدوات المطورين.\n"
        f"- 📚 مكتبة الأكواد والشروحات.\n\n"
        f"⚠️ <b>تُستخدم الأدوات لاختبار الأنظمة المملوكة لك أو المصرّح لك بفحصها.</b>\n\n"
        f"اختر القسم المطلوب من القائمة بالأسفل."
    )
    await update.message.reply_text(welcome_msg, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_rate_limit(update.effective_user.id):
        return
    if not await check_or_block(update, context):
        return
    help_text = (
        "📖 <b>دليل الاستخدام ومساعدة البوت:</b>\n\n"
        "• استخدم القائمة للتنقل السريع.\n"
        "• اشحن الأكواد عبر: <code>/redeem <الكود></code>\n"
        "• تواصل مع الإدارة عبر زر <b>تبليغ عن مشكلة</b>."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def redeem_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        return
    if is_banned(user_id) or not await check_or_block(update, context):
        return
    if not context.args:
        await update.message.reply_text("⚠️ أرسل الكود بالشكل التالي:\n<code>/redeem CODE</code>", parse_mode="HTML")
        return
    code = context.args[0].strip()
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM gift_codes WHERE code = ?", (code,))
        res = cursor.fetchone()
        if not res:
            conn.close()
            await update.message.reply_text("❌ الكود غير صالح.")
            return
        pts = res[0]
        cursor.execute("DELETE FROM gift_codes WHERE code = ?", (code,))
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (pts, user_id))
        conn.commit()
        conn.close()
        log_action(user_id, f"Redeemed {code}")
        await update.message.reply_text(f"🎉 تم شحن الكود بنجاح وأضيف لرصيدك +{pts} نقطة!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not context.args:
        return
    try:
        target_id = int(context.args[0])
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, username, points, warnings FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        conn.close()
        if res:
            await update.message.reply_text(f"👤 <b>معلومات المستخدم:</b>\n- الاسم: {res[0]}\n- اليوزر: {res[1]}\n- النقاط: {res[2]}\n- الإنذارات: {res[3]}/3", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ غير موجود.")
    except ValueError:
        pass

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not context.args:
        await update.message.reply_text("⚠️ الاستخدام: <code>/log <ID></code>", parse_mode="HTML")
        return
    try:
        target_id = int(context.args[0])
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT action, timestamp FROM user_logs WHERE user_id = ? ORDER BY id DESC LIMIT 10", (target_id,))
        logs = cursor.fetchall()
        conn.close()
        if logs:
            msg = f"📜 <b>سجل النشاط ({target_id}):</b>\n\n"
            for act, ts in logs:
                t_str = time.strftime('%H:%M:%S', time.localtime(ts))
                msg += f"• <code>{t_str}</code>: {act}\n"
            await update.message.reply_text(msg, parse_mode="HTML")
        else:
            await update.message.reply_text("❌ لا يوجد سجل.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not context.args:
        return
    try:
        target_id = int(context.args[0])
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (target_id,))
        cursor.execute("SELECT warnings FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        warns = res[0] if res else 1
        if warns >= 3:
            cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (target_id,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"🚨 وصل المستخدم {target_id} إلى 3 إنذارات وتم حظره!")
        else:
            conn.commit()
            conn.close()
            await update.message.reply_text(f"⚠️ إنذار للمستخدم {target_id} ({warns}/3)")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def add_points_to_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or len(context.args) < 2:
        return
    try:
        target_id, pts = int(context.args[0]), int(context.args[1])
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (pts, target_id))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تمت إضافة {pts} نقطة للمستخدم {target_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def make_gift_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or len(context.args) < 2:
        return
    code, pts = context.args[0].strip(), int(context.args[1])
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO gift_codes (code, points) VALUES (?, ?)", (code, pts))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم إنشاء الكود {code} بقيمة {pts} نقطة.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def manual_backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        if os.path.exists("bot_database.db"):
            with open("bot_database.db", "rb") as db_f:
                await update.message.reply_document(document=db_f, caption="📦 نسخة احتياطية فورية.")
        with open(__file__, "rb") as script_f:
            await update.message.reply_document(document=script_f, caption="💻 نسخة السكربت.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        return

    if is_banned(user_id):
        return

    if not await check_or_block(update, context):
        return

    text = update.message.text

    if text in ["رجوع", "إلغاء", "/cancel", "🔙 العودة للقائمة الرئيسية"]:
        context.user_data.clear()
        await start(update, context)
        return

    if text == "🎁 لوحة النقاط الشخصية":
        context.user_data.clear()
        user_points = get_user_points(user_id)
        ref_pts = get_setting('referral_points', 2)
        ref_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(
            f"🎁 <b>لوحة النقاط ودعوة الأصدقاء:</b>\n\n"
            f"💎 رصيدك الحالي: <code>{user_points} نقطة</code>\n"
            f"🎁 ستحصل على <b>+{ref_pts} نقاط</b> لكل شخص يدخل عبر رابطك!\n\n"
            f"🔗 <b>رابط الدعوة الخاص بك:</b>\n<code>{ref_link}</code>", 
            parse_mode="HTML"
        )
        return

    if text == "💼 رصيدي الحالي":
        context.user_data.clear()
        await update.message.reply_text(f"💼 رصيدك الحالي: <b>{get_user_points(user_id)} نقطة</b> 💎", parse_mode="HTML")
        return

    if text == "⭐ أدوات المفضلة":
        context.user_data.clear()
        try:
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT i.title FROM favorites f JOIN items i ON f.item_id = i.id WHERE f.user_id = ?", (user_id,))
            favs = cursor.fetchall()
            conn.close()
            if not favs:
                await update.message.reply_text("⭐ ليس لديك أي أدوات في قائمة المفضلة حالياً.")
                return
            fav_keyboard = [[KeyboardButton(f[0])] for f in favs]
            fav_keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
            await update.message.reply_text("⭐ <b>قائمة أدواتك المفضلة المحفوظة:</b>", reply_markup=ReplyKeyboardMarkup(fav_keyboard, resize_keyboard=True), parse_mode="HTML")
        except Exception:
            pass
        return

    if text == "🎁 الهدية اليومية (كل 24 ساعة)":
        context.user_data.clear()
        daily_pts = get_setting('daily_points', 5)
        current_time = int(time.time())
        try:
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
            res = cursor.fetchone()
            last_daily = res[0] if res else 0

            if current_time - last_daily < 86400:
                conn.close()
                await update.message.reply_text("⏳ عذراً، استلمت الهدية مسبقاً. انتظر حتى يكتمل الوقت.")
                return

            cursor.execute("UPDATE users SET last_daily = ?, points = points + ? WHERE user_id = ?", (current_time, daily_pts, user_id))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"🎁 تم استلام الهدية بنجاح +{daily_pts} نقطة!")
        except Exception:
            pass
        return

    if text == "🛠️ الدعم الفني":
        context.user_data.clear()
        await update.message.reply_text(f"🛠️ الدعم الفني:\n- المطور: {DEVELOPER_USERNAME}", parse_mode="HTML")
        return

    if text == "🔎 بحث سريع عن أداة":
        context.user_data.clear()
        context.user_data['waiting_for'] = 'search'
        await update.message.reply_text("🔎 أرسل اسم أو كلمة مفتاحية للبحث:", reply_markup=ReplyKeyboardRemove())
        return

    if text == "💸 ارسال النقاط":
        context.user_data.clear()
        context.user_data['waiting_for'] = 'give_id'
        await update.message.reply_text("💸 أرسل آيدي (ID) الشخص المراد التحويل له:", reply_markup=ReplyKeyboardRemove())
        return

    if text == "🚨 تبليغ عن مشكلة":
        context.user_data.clear()
        context.user_data['waiting_for'] = 'report'
        await update.message.reply_text("🚨 أرسل تفاصيل البلاغ برسالة واحدة:", reply_markup=ReplyKeyboardRemove())
        return

    if text == "🎯 طلب أداة/ثغرة خاصة (Bounty)":
        context.user_data.clear()
        context.user_data['waiting_for'] = 'bounty'
        await update.message.reply_text("🎯 أرسل تفاصيل الطلب برساّلة واحدة:", reply_markup=ReplyKeyboardRemove())
        return

    # أزرار تحكم المالك فقط
    if is_owner(user_id):
        if text == "👑 تعيين أدمن جديد":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'add_admin_id'
            await update.message.reply_text("👑 أرسل آيدي (ID) المستخدم لتعيينه أدمن:", reply_markup=ReplyKeyboardRemove())
            return
        if text == "🗑️ حذف أدمن":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM admins WHERE user_id != ?", (OWNER_ID,))
                admins_list = cursor.fetchall()
                conn.close()
                if not admins_list:
                    await update.message.reply_text("❌ لا يوجد أدمنز إضافيون للحذف.")
                    return
                keyboard = [[KeyboardButton(str(adm[0]))] for adm in admins_list]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("🗑️ اختر أو أرسل آيدي الأدمن المراد إزالته:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'del_admin_id'
            except Exception:
                pass
            return

    if is_admin(user_id):
        if text == "➕ إضافة قسم أمني جديد":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'add_cat'
            await update.message.reply_text("✏️ أرسل اسم القسم الجديد:", reply_markup=ReplyKeyboardRemove())
            return
        if text == "📝 إضافة أداة أو ثغرة":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories")
                cats = cursor.fetchall()
                conn.close()
                if not cats:
                    await update.message.reply_text("❌ أضف قسماً أولاً.")
                    return
                keyboard = [[KeyboardButton(c[0])] for c in cats]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("اختر القسم لإضافة الأداة:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'select_cat'
            except Exception:
                pass
            return
        if text == "💰 تعديل سعر أداة":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM items")
                items = cursor.fetchall()
                conn.close()
                if not items:
                    await update.message.reply_text("❌ لا توجد أدوات لتعديل سعرها.")
                    return
                keyboard = [[KeyboardButton(i[0])] for i in items]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("اختر الأداة المراد تعديل سعر نقاطها:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'edit_price_select_item'
            except Exception:
                pass
            return
        if text == "🗑️ حذف قسم":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories")
                cats = cursor.fetchall()
                conn.close()
                if not cats:
                    await update.message.reply_text("❌ لا توجد أقسام.")
                    return
                keyboard = [[KeyboardButton(c[0])] for c in cats]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("اختر القسم المراد حذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'del_cat'
            except Exception:
                pass
            return
        if text == "❌ حذف عنصر":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM items")
                items = cursor.fetchall()
                conn.close()
                if not items:
                    await update.message.reply_text("❌ لا توجد عناصر.")
                    return
                keyboard = [[KeyboardButton(i[0])] for i in items]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("اختر العنصر المراد حذفه:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'del_item'
            except Exception:
                pass
            return
        if text == "📢 إضافة قناة إجبارية":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'add_channel'
            await update.message.reply_text("📢 أرسل يوزر القناة (مثال: @ChannelUsername):", reply_markup=ReplyKeyboardRemove())
            return
        if text == "❌ حذف قناة إجبارية":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT channel_username FROM forced_channels")
                channels = cursor.fetchall()
                conn.close()
                if not channels:
                    await update.message.reply_text("❌ لا توجد قنوات إجبارية مضافة حالياً.")
                    return
                keyboard = [[KeyboardButton(ch[0])] for ch in channels]
                keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text("اختر القناة المراد حذفها:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                context.user_data['waiting_for'] = 'del_channel'
            except Exception:
                pass
            return
        if text == "📢 إذاعة عامة للشامل":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'broadcast'
            await update.message.reply_text("📢 أرسل رسالة الإذاعة للجميع:", reply_markup=ReplyKeyboardRemove())
            return
        if text == "📊 إحصائيات النظام":
            context.user_data.clear()
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            u = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM items")
            i = cursor.fetchone()[0]
            conn.close()
            await update.message.reply_text(f"📊 إحصائيات البوت:\n- المستخدمين: {u}\n- الأدوات: {i}")
            return
        if text == "👑 نشطاء البوت (Top Users)":
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT full_name, points FROM users ORDER BY points DESC LIMIT 5")
                top_users = cursor.fetchall()
                conn.close()
                msg = "👑 <b>أكثر 5 أعضاء تفاعلاً وجمعاً للنقاط:</b>\n\n"
                for idx, (fname, pts) in enumerate(top_users, 1):
                    msg += f"{idx}. <b>{html.escape(fname)}</b> — <code>{pts} نقطة</code>\n"
                await update.message.reply_text(msg, parse_mode="HTML")
            except Exception:
                pass
            return
        if text == "🚫 حظر مستخدم":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'ban'
            await update.message.reply_text("🚫 أرسل آيدي المستخدم للحظر:", reply_markup=ReplyKeyboardRemove())
            return
        if text == "✅ إلغاء حظر مستخدم":
            context.user_data.clear()
            context.user_data['waiting_for'] = 'unban'
            await update.message.reply_text("✅ أرسل آيدي المستخدم لإلغاء الحظر:", reply_markup=ReplyKeyboardRemove())
            return

    # معالجة حالات الانتظار
    waiting_mode = context.user_data.get('waiting_for')
    if waiting_mode:
        if waiting_mode == 'add_admin_id' and is_owner(user_id):
            context.user_data.clear()
            if not text.isdigit():
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقاماً:")
                return
            new_id = int(text)
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"👑 تم تعيين المستخدم <code>{new_id}</code> كأدمن جديد بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'del_admin_id' and is_owner(user_id):
            context.user_data.clear()
            if not text.isdigit():
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقاماً:")
                return
            target_id = int(text)
            if target_id == OWNER_ID:
                await update.message.reply_text("❌ لا يمكنك حذف المالك الأساسي.")
                await start(update, context)
                return
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"🗑️ تم إزالة المستخدم <code>{target_id}</code> من قائمة الأدمنز بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'select_cat' and is_admin(user_id):
            cat_name = text.strip()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
                res = cursor.fetchone()
                conn.close()
                if not res:
                    await update.message.reply_text("❌ القسم غير موجود. اختر قسماً صحيحاً من القائمة:")
                    return
                context.user_data['item_category_id'] = res[0]
                context.user_data['waiting_for'] = 'item_title'
                await update.message.reply_text("📝 أرسل الآن عنوان الأداة أو الثغرة:", reply_markup=ReplyKeyboardRemove())
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            return

        if waiting_mode == 'item_title' and is_admin(user_id):
            context.user_data['item_title'] = text.strip()
            context.user_data['waiting_for'] = 'item_content'
            await update.message.reply_text("💻 أرسل الآن محتوى الأداة أو الشرح أو السكربت:")
            return

        if waiting_mode == 'item_content' and is_admin(user_id):
            context.user_data['item_content'] = text.strip()
            context.user_data['waiting_for'] = 'item_points'
            await update.message.reply_text("💎 أرسل الآن عدد النقاط المطلوبة لفتح الأداة (اكتب 0 إذا كانت مجانية):")
            return

        if waiting_mode == 'item_points' and is_admin(user_id):
            if not text.isdigit():
                await update.message.reply_text("❌ الرجاء إدخال رقم صحيح للنقاط:")
                return
            points_req = int(text)
            cat_id = context.user_data.get('item_category_id')
            title = context.user_data.get('item_title')
            content = context.user_data.get('item_content')
            context.user_data.clear()

            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO items (category_id, title, content, points_required) VALUES (?, ?, ?, ?)", 
                               (cat_id, title, content, points_req))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ تمت إضافة العنصر (<b>{html.escape(title)}</b>) بنجاح برصيد {points_req} نقطة!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ أثناء الحفظ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'edit_price_select_item' and is_admin(user_id):
            item_title = text.strip()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT id, points_required FROM items WHERE title = ?", (item_title,))
                res = cursor.fetchone()
                conn.close()
                if not res:
                    await update.message.reply_text("❌ هذه الأداة غير موجودة، اختر أداة صحيحة من القائمة:")
                    return
                context.user_data['edit_price_item_id'] = res[0]
                context.user_data['waiting_for'] = 'edit_price_new_value'
                await update.message.reply_text(f"💎 الأداة (<b>{html.escape(item_title)}</b>) سعرها الحالي: {res[1]} نقطة.\nأرسل السعر أو عدد النقاط الجديد:", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            return

        if waiting_mode == 'edit_price_new_value' and is_admin(user_id):
            if not text.isdigit():
                await update.message.reply_text("❌ الرجاء إدخال رقم صحيح لعدد النقاط:")
                return
            new_pts = int(text)
            item_id = context.user_data.get('edit_price_item_id')
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("UPDATE items SET points_required = ? WHERE id = ?", (new_pts, item_id))
                conn.commit()
                cursor.execute("SELECT title FROM items WHERE id = ?", (item_id,))
                t_res = cursor.fetchone()
                item_name = t_res[0] if t_res else "الأداة"
                conn.close()
                await update.message.reply_text(f"✅ تم تحديث سعر الأداة (<b>{html.escape(item_name)}</b>) ليصبح <code>{new_pts} نقطة</code> بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'broadcast' and is_admin(user_id):
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users")
                all_users = cursor.fetchall()
                conn.close()
                count = 0
                for u in all_users:
                    try:
                        await context.bot.send_message(chat_id=u[0], text=f"📢 <b>إعلان هام من الإدارة:</b>\n\n{html.escape(text)}", parse_mode="HTML")
                        count += 1
                    except Exception:
                        pass
                await update.message.reply_text(f"✅ تم إرسال الإذاعة بنجاح إلى {count} مستخدم.")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ في الإذاعة: {e}")
            await start(update, context)
            return

        if waiting_mode == 'ban' and is_admin(user_id):
            context.user_data.clear()
            if not text.isdigit():
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقاماً:")
                return
            b_id = int(text)
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (b_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"🚫 تم حظر المستخدم {b_id} بنجاح.")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'unban' and is_admin(user_id):
            context.user_data.clear()
            if not text.isdigit():
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقاماً:")
                return
            u_id = int(text)
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (u_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {u_id} بنجاح.")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'del_item' and is_admin(user_id):
            item_title = text.strip()
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM items WHERE title = ?", (item_title,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"🗑️ تم حذف العنصر (<b>{html.escape(item_title)}</b>) بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'search':
            context.user_data.clear()
            q = text.strip()
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT title, content FROM items WHERE title LIKE ? OR content LIKE ?", (f"%{q}%", f"%{q}%"))
            res = cursor.fetchall()
            conn.close()
            if res:
                msg = f"🔎 نتائج البحث عن ({q}):\n\n"
                for t, c in res[:5]:
                    msg += f"📌 <b>{html.escape(t)}</b>\n{html.escape(c[:100])}...\n\n"
                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.message.reply_text("❌ لم يتم العثور على نتائج.")
            await start(update, context)
            return

        if waiting_mode == 'give_id':
            if not text.isdigit():
                await update.message.reply_text("❌ الآيدي يجب أن يكون أرقاماً فقط:")
                return
            context.user_data['give_target_id'] = int(text)
            context.user_data['waiting_for'] = 'give_amount'
            await update.message.reply_text("💎 أرسل الآن عدد النقاط:")
            return

        if waiting_mode == 'give_amount':
            if not text.isdigit():
                await update.message.reply_text("❌ أدخل رقماً صحيحاً:")
                return
            amount, target_id = int(text), context.user_data.get('give_target_id')
            context.user_data.clear()
            
            if not is_admin(user_id) and get_user_points(user_id) < amount:
                await update.message.reply_text("❌ رصيدك غير كافٍ.")
                await start(update, context)
                return

            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                if not is_admin(user_id):
                    cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, user_id))
                cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ تم تحويل {amount} نقطة بنجاح!")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'report':
            context.user_data.clear()
            for aid in ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=aid, text=f"🚨 بلاغ من ({user_id}):\n{html.escape(text)}")
                except Exception:
                    pass
            await update.message.reply_text("✅ تم إرسال البلاغ للإدارة.")
            await start(update, context)
            return

        if waiting_mode == 'bounty':
            context.user_data.clear()
            for aid in ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=aid, text=f"🎯 طلب أداة خاصة (Bounty) من ({user_id}):\n{html.escape(text)}")
                except Exception:
                    pass
            await update.message.reply_text("✅ تم إرسال طلبك للمطورين بنجاح.")
            await start(update, context)
            return

        if waiting_mode == 'add_cat' and is_admin(user_id):
            context.user_data.clear()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (text.strip(),))
                conn.commit()
                conn.close()
                invalidate_cache()
                await update.message.reply_text(f"✅ تمت إضافة القسم ({html.escape(text)}) بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'add_channel' and is_admin(user_id):
            context.user_data.clear()
            ch = text.strip()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO forced_channels (channel_username) VALUES (?)", (ch,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ تمت إضافة القناة <code>{ch}</code> بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'del_channel' and is_admin(user_id):
            context.user_data.clear()
            ch = text.strip()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM forced_channels WHERE channel_username = ?", (ch,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"🗑️ وتمت إزالة القناة <code>{ch}</code> بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

        if waiting_mode == 'del_cat' and is_admin(user_id):
            context.user_data.clear()
            cat_name = text.strip()
            try:
                conn = sqlite3.connect("bot_database.db", timeout=3)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM categories WHERE name = ?", (cat_name,))
                conn.commit()
                conn.close()
                invalidate_cache()
                await update.message.reply_text(f"🗑️ وتم حذف القسم <b>({html.escape(cat_name)})</b> بنجاح!", parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {e}")
            await start(update, context)
            return

    # التصفح السريع للأقسام والأدوات
    try:
        conn = sqlite3.connect("bot_database.db", timeout=3)
        cursor = conn.cursor()
        clean_text = text
        for emoji in COLOR_EMOJIS + ["🔹", "📌", "📁", "🔴", "🟢"]:
            clean_text = clean_text.replace(emoji, "")
        clean_text = clean_text.strip()

        cursor.execute("SELECT id, name FROM categories WHERE name = ?", (clean_text,))
        cat_res = cursor.fetchone()

        if cat_res:
            cat_id, cat_name = cat_res
            cursor.execute("SELECT title FROM items WHERE category_id = ?", (cat_id,))
            items = cursor.fetchall()
            conn.close()
            if items:
                sub_keyboard = [[KeyboardButton(f"{COLOR_EMOJIS[i % len(COLOR_EMOJIS)]}  {item[0]}")] for i, item in enumerate(items)]
                sub_keyboard.append([KeyboardButton("🔙 العودة للقائمة الرئيسية")])
                await update.message.reply_text(f"📂 <b>قسم: {html.escape(cat_name)}</b>", reply_markup=ReplyKeyboardMarkup(sub_keyboard, resize_keyboard=True), parse_mode="HTML")
            else:
                await update.message.reply_text("❌ لا توجد عناصر في هذا القسم.")
            return

        cursor.execute("SELECT id, content, points_required FROM items WHERE title = ?", (clean_text,))
        item_res = cursor.fetchone()

        if item_res:
            item_id, content, points_req = item_res
            if is_admin(user_id):
                await send_long_text(update.effective_chat.id, context, content)
                conn.close()
                return

            if points_req == 0:
                conn.close()
                fav_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_{item_id}")]
                ])
                await update.message.reply_text(f"✅ تم فتح الأداة بنجاح: <b>{html.escape(clean_text)}</b>", reply_markup=fav_keyboard, parse_mode="HTML")
                await send_long_text(update.effective_chat.id, context, content)
                return

            if get_user_points(user_id) < points_req:
                await update.message.reply_text(f"❌ رصيدك غير كافٍ! المطلوب: {points_req} نقطة.")
                conn.close()
                return

            conn.close()
            confirm_keyboard = [[InlineKeyboardButton("✅ تأكيد الشراء", callback_data=f"buy_{item_id}"), InlineKeyboardButton("❌ إلغاء", callback_data="cancel_buy")]]
            await update.message.reply_text(f"🛒 تأكيد شراء أداة: <b>{html.escape(clean_text)}</b>\nالسعر: <b>{points_req} نقطة</b>", reply_markup=InlineKeyboardMarkup(confirm_keyboard), parse_mode="HTML")
            return

        conn.close()
    except Exception:
        pass

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, user_id = query.data, query.from_user.id

    if data == "cancel_buy":
        await query.edit_message_text("❌ تم إلغاء الشراء.")
        return

    if data.startswith("fav_"):
        try:
            item_id = int(data.split("_")[1])
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO favorites (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
            conn.commit()
            conn.close()
            await query.answer("⭐ تمت إضافة الأداة إلى المفضلة بنجاح!", show_alert=True)
        except Exception:
            pass
        return

    if data.startswith("buy_"):
        try:
            item_id = int(data.split("_")[1])
            conn = sqlite3.connect("bot_database.db", timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT title, content, points_required FROM items WHERE id = ?", (item_id,))
            item = cursor.fetchone()

            if not item:
                conn.close()
                await query.edit_message_text("❌ هذه الأداة لم تعد موجودة.")
                return

            title, content, points_req = item
            if not is_admin(user_id) and get_user_points(user_id) < points_req:
                conn.close()
                await query.edit_message_text("❌ رصيدك غير كافٍ.")
                return

            if not is_admin(user_id) and points_req > 0:
                cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (points_req, user_id))
                conn.commit()

            conn.close()
            fav_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f"fav_{item_id}")]
            ])
            await query.edit_message_text(f"✅ تم الشراء بنجاح لأداة: <b>{html.escape(title)}</b>", reply_markup=fav_keyboard, parse_mode="HTML")
            await send_long_text(query.message.chat_id, context, content)
        except Exception:
            pass

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    is_subbed, _ = await check_user_subscription(context.bot, user_id)
    if is_subbed:
        await query.answer("✅ تم التحقق بنجاح وتفعيل البوت!", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(chat_id=user_id, text="🎉 أهلاً بك! تم فتح القائمة الرئيسية:", reply_markup=get_main_keyboard(user_id))
    else:
        await query.answer("❌ عذراً، لم تقم بالاشتراك في جميع القنوات بعد!", show_alert=True)

async def post_init(application):
    default_commands = [
        BotCommand("start", "🚀 تشغيل البوت وإظهار القائمة الرئيسية"),
        BotCommand("help", "📖 دليل الاستخدام ومساعدة البوت"),
        BotCommand("redeem", "🎟️ شحن كود الهدايا"),
        BotCommand("user", "👤 معلومات مستخدم محدد"),
        BotCommand("log", "📜 سجل نشاط المستخدم"),
        BotCommand("warn", "⚠️ إنذار مستخدم"),
        BotCommand("addpoints", "🎁 إضافة نقاط لمستخدم"),
        BotCommand("makecode", "🎟️ إنشاء كود هدية جديد"),
        BotCommand("addadmin", "👑 إضافة أدمن جديد (للمالك فقط)"),
        BotCommand("deladmin", "🗑️ حذف أدمن (للمالك فقط)"),
        BotCommand("addchannel", "📢 إضافة قناة للاشتراك الإجباري"),
        BotCommand("delchannel", "❌ حذف قناة من الاشتراك الإجباري"),
        BotCommand("backup", "📦 سحب نسخة احتياطية فورية"),
        BotCommand("cancel", "❌ إلغاء وتصفير الحالة الحالية"),
    ]
    try:
        await application.bot.set_my_commands(default_commands)
    except Exception:
        pass
    application.create_task(daily_backup_task(application))

# ---------------------------------------------------------
# التشغيل الفائق السرعة
# ---------------------------------------------------------
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .read_timeout(5)
        .write_timeout(5)
        .connect_timeout(5)
        .pool_timeout(5)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", start))
    app.add_handler(CommandHandler("backup", manual_backup_command))
    app.add_handler(CommandHandler("user", user_info_command))
    app.add_handler(CommandHandler("log", log_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("addpoints", add_points_to_user_command))
    app.add_handler(CommandHandler("makecode", make_gift_code_command))
    app.add_handler(CommandHandler("redeem", redeem_code_command))
    app.add_handler(CommandHandler("addadmin", add_admin_command))
    app.add_handler(CommandHandler("deladmin", remove_admin_command))
    app.add_handler(CommandHandler("addchannel", add_forced_channel_command))
    app.add_handler(CommandHandler("delchannel", remove_forced_channel_command))
    
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(buy_|cancel_buy|fav_)"))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 تم تشغيل البوت بأقصى سرعة واستقرار...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
