import asyncio
import logging
import sqlite3
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

TOKEN = "9297297005:AAF_5eNRkMdx3eDnLeJWn63eJR_NmKxPxFI"
CHANNEL_USERNAME = "@shoxrux_code"      
ADMIN_ID = 7439126820                   
STARTING_BALANCE = 3000                 
REQUIRED_INVITES = 10                   
INVITE_REWARD = 3000                    
MIN_WITHDRAW = 20000                    

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

UZ_TZ = pytz.timezone("Asia/Tashkent")

def get_uz_time():
    return datetime.now(UZ_TZ)

def db_start():
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 3000,
            invited_count INTEGER DEFAULT 0,
            first_name TEXT,
            username TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_template (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            morning_fact TEXT,
            lunch_poll_q TEXT,
            lunch_poll_opts TEXT,
            hacker_text TEXT,
            quiz_q TEXT,
            quiz_opts TEXT,
            quiz_correct INTEGER
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM daily_template")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO daily_template (id, morning_fact, lunch_poll_q, lunch_poll_opts, hacker_text, quiz_q, quiz_opts, quiz_correct)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "🚀 Dasturlash olamidagi eng qiziqarli faktlar va yangiliklar...",
            "Bugungi kundagi eng qiyin yo'nalish qaysi?",
            "Frontend, Backend, Mobile, AI va Data Science",
            "💀 Hackerlar tarixi va kiberxavfsizlik asoslari...",
            "Mantiqiy savol: Python tilida qaysi ma'lumot turi o'zgarmas (immutable) hisoblanadi?",
            "List, Tuple, Dictionary, Set",
            1
        ))
        
    conn.commit()
    conn.close()

db_start()

admin_states = {}

async def check_user_channel(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

# ==================== 1. BARCHA KOMANDALAR (ENG TEPADA) ====================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    admin_states.pop(message.from_user.id, None)
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 <b>Xush kelibsiz, Admin!</b>", reply_markup=ReplyKeyboardRemove())
        return

    is_sub = await check_user_channel(message.from_user.id)
    if not is_sub:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'ling.", reply_markup=kb)
    else:
        await message.answer("🎉 Xush kelibsiz! Botdan to'liq foydalanishingiz mumkin.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, bu buyruq faqat admin uchun!")
        return
    
    admin_states.pop(ADMIN_ID, None)
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id != ?", (ADMIN_ID,))
    total_users = cursor.fetchone()[0]
    conn.close()
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Kunlik shablonni yangilash")],
            [KeyboardButton(text="📊 Statistikani ko'rish"), KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    uz_now = get_uz_time()
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"⏰ Shablon kiritish vaqti: <b>16:00 dan 22:00 gacha</b>\n"
        f"🕒 Hozirgi vaqt (Toshkent): <b>{uz_now.strftime('%H:%M')}</b>",
        reply_markup=keyboard
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("✅ Barcha amallar bekor qilindi.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("hisobim"))
async def cmd_my_account(message: Message):
    admin_states.pop(message.from_user.id, None)
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Siz Adminsiz!", reply_markup=ReplyKeyboardRemove())
        return
    await message.answer("💳 Hisobingiz ma'lumotlari...", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("ℹ️ Yordam bo'limi.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("ogohlantirish"))
async def cmd_warning(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("⚠️ Ogohlantirish shartlari.", reply_markup=ReplyKeyboardRemove())

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_user_channel(user_id):
        await callback.message.delete()
        await callback.message.answer("✅ Obuna tasdiqlandi! Xush kelibsiz.")
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

# ==================== 2. ADMIN TUGMALARI VA MATNLAR ====================

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_action(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_states.pop(ADMIN_ID, None)
    await message.answer("✅ Barcha amallar bekor qilindi.", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "📊 Statistikani ko'rish")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, username, user_id, invited_count, balance FROM users WHERE user_id != ? ORDER BY invited_count DESC", (ADMIN_ID,))
    users_list = cursor.fetchall()
    conn.close()
    
    text = "👥 <b>Foydalanuvchilar ro'yxati:</b>\n\n"
    for idx, u in enumerate(users_list[:20], 1):
        text += f"{idx}. {u[0]} ({u[1] or 'Yoq'}) | 👥 {u[3]} ta | 💰 {u[4]} so'm\n"
    await message.answer(text)

@dp.message(F.text == "📝 Kunlik shablonni yangilash")
async def set_template_start(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    uz_now = get_uz_time()
    if not (16 <= uz_now.hour < 22):
        await message.answer(f"⚠️ Shablon kiritish vaqti 16:00 dan 22:00 gacha! Hozir vaqt: {uz_now.strftime('%H:%M')}")
        return

    admin_states[ADMIN_ID] = "waiting_for_template"
    await message.answer(
        "✍️ **Yangi kunlik shablonni yuboring:**\n\n"
        "Quyidagi **7 ta qismni** `---` belgisi bilan ajratib bitta xabarda yuboring:\n\n"
        "1. **09:00** - IT haqida katta qiziqarli fakt\n---\n"
        "2. **12:00** - Qiziqarli so'rovnoma savoli (Poll)\n---\n"
        "3. **12:00** - So'rovnoma variantlari (vergul bilan)\n---\n"
        "4. **18:00** - Hackerlar haqida rasm bilan yuboriladigan qiziqarli katta matn\n---\n"
        "5. **22:00** - Kuchli mantiqiy Quiz savoli\n---\n"
        "6. **22:00** - Quiz variantlari (vergul bilan)\n---\n"
        "7. **22:00** - Quiz to'g'ri javob raqami (0 dan 3 gacha)\n\n"
        "*(Bekor qilish uchun /cancel yuboring)*"
    )

@dp.message(F.text)
async def handle_admin_text(message: Message):
    if message.from_user.id != ADMIN_ID or admin_states.get(ADMIN_ID) != "waiting_for_template":
        return
    
    parts = message.text.split("---")
    if len(parts) < 7:
        await message.answer("❌ Xatolik! 7 ta qismni `---` bilan ajratib to'liq yuboring. Bekor qilish uchun /cancel yuboring.")
        return
    
    try:
        morning_fact = parts[0].strip()
        lunch_poll_q = parts[1].strip()
        lunch_poll_opts = parts[2].strip()
        hacker_text = parts[3].strip()
        quiz_q = parts[4].strip()
        quiz_opts = parts[5].strip()
        quiz_correct = int(parts[6].strip())
        
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM daily_template")
        cursor.execute("""
            INSERT INTO daily_template (id, morning_fact, lunch_poll_q, lunch_poll_opts, hacker_text, quiz_q, quiz_opts, quiz_correct)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (morning_fact, lunch_poll_q, lunch_poll_opts, hacker_text, quiz_q, quiz_opts, quiz_correct))
        conn.commit()
        conn.close()
        
        admin_states.pop(ADMIN_ID, None)
        await message.answer("✅ **Yangi kunlik shablon muvaffaqiyatli saqlandi!**", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}\nFormatni tekshirib qaytadan yuboring.")

# ==================== 3. AVTO-POSTLAR VA SERVER ====================

async def send_morning_fact():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT morning_fact FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            await bot.send_message(chat_id=CHANNEL_USERNAME, text=row[0])
    except Exception as e:
        print(f"09:00 xatolik: {e}")

async def send_lunch_poll():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT lunch_poll_q, lunch_poll_opts FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            q, opts_str = row
            options = [o.strip() for o in opts_str.split(",")]
            await bot.send_poll(chat_id=CHANNEL_USERNAME, question=q, options=options, is_anonymous=False)
    except Exception as e:
        print(f"12:00 xatolik: {e}")

async def send_hacker_post():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT hacker_text FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            text = row[0]
            hacker_photo_url = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5"
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=hacker_photo_url, caption=text)
    except Exception as e:
        print(f"18:00 xatolik: {e}")

async def send_night_quiz():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT quiz_q, quiz_opts, quiz_correct FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            q, opts_str, correct_idx = row
            options = [o.strip() for o in opts_str.split(",")]
            await bot.send_poll(
                chat_id=CHANNEL_USERNAME,
                question=q,
                options=options,
                is_anonymous=False,
                type="quiz",
                correct_option_id=correct_idx
            )
        
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM daily_template")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"22:00 xatolik: {e}")

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="hisobim", description="Hisobdagi pulni ko'rish"),
        BotCommand(command="help", description="Yordam olish"),
        BotCommand(command="ogohlantirish", description="Shartlar"),
        BotCommand(command="admin", description="Admin paneli"),
        BotCommand(command="cancel", description="Bekor qilish")
    ]
    await bot.set_my_commands(commands)

async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def main():
    await start_web_server()

    scheduler = AsyncIOScheduler(timezone=UZ_TZ)
    scheduler.add_job(send_morning_fact, "cron", hour=9, minute=0)
    scheduler.add_job(send_lunch_poll, "cron", hour=12, minute=0)
    scheduler.add_job(send_hacker_post, "cron", hour=18, minute=0)
    scheduler.add_job(send_night_quiz, "cron", hour=22, minute=0)
    scheduler.start()

    await set_bot_commands(bot)
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())