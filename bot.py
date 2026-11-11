import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

TOKEN = "9297297005:AAF_5eNRkMdx3eDnLeJWn63eJR_NmKxPxFI"
CHANNEL_USERNAME = "@shoxrux_code"      # Kanal username'ingiz
ADMIN_ID = 7439126820                   # O'zingizning Telegram ID'ingiz
STARTING_BALANCE = 3000                 
REQUIRED_INVITES = 10                   
INVITE_REWARD = 3000                    
MIN_WITHDRAW = 20000                    

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- BAZA BILAN ISHLASH VA ILK SHABLONNI YARATISH ---
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
            quiz_question TEXT,
            quiz_options TEXT,
            quiz_correct_index INTEGER,
            lunch_fact TEXT,
            evening_poll_question TEXT,
            evening_poll_options TEXT
        )
    """)
    
    # Agar baza bo'sh bo'lsa, ertangi kun uchun dastlabki tayyor shablonni o'zimiz yozib qo'yamiz
    cursor.execute("SELECT COUNT(*) FROM daily_template")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO daily_template (id, morning_fact, quiz_question, quiz_options, quiz_correct_index, lunch_fact, evening_poll_question, evening_poll_options)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Python dasturlash tili dunyodagi eng tez rivojlanayotgan tillardan biri bo'lib, sun'iy intellekt va Data Science'da asosiy til hisoblanadi.",
            "Python'da ekranga matn chiqarish uchun qaysi funksiyadan foydalaniladi?",
            "print(), echo(), console.log(), write()",
            0,
            "IT mutaxassislari kuniga o'rtacha 5-6 soat kod yozishadi va qolgan vaqtini muammolarni tahlil qilishga sarflashadi.",
            "Sizningcha dasturlashni o'rganishda eng muhim qism nima?",
            "Amaliyot qilish, Nazariya o'qish, Mentor topish, Ingliz tili"
        ))
        
    conn.commit()
    conn.close()

db_start()

admin_states = {}

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, bu buyruq faqat admin uchun!")
        return
    
    # Admin panelga kirganda eski holatni tozalaymiz (qotib qolmasligi uchun)
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
    
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"⏰ Shablon kiritish vaqti: <b>16:00 dan 22:00 gacha</b>\n\n"
        f"Quyidagi tugmalar orqali boshqaring:",
        reply_markup=keyboard
    )

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_action(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_states.pop(ADMIN_ID, None)
    await message.answer("✅ Barcha jarayonlar bekor qilindi. Asosiy menyudasiz.", reply_markup=ReplyKeyboardRemove() if hasattr(Message, 'reply_markup') else None)

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
    
    # Vaqtni tekshirish (Faqat 16:00 dan 22:00 gacha ruxsat berish)
    current_hour = datetime.now().hour
    if not (16 <= current_hour < 22):
        await message.answer(
            f"⚠️ <b>Hozir shablon kiritish vaqti emas!</b>\n"
            f"Admin uchun shablon kiritish oynasi faqat har kuni **16:00 dan 22:00 gacha** ochiq bo'ladi.\n"
            f"Hozirgi soat: {datetime.now().strftime('%H:%M')}"
        )
        return

    admin_states[ADMIN_ID] = "waiting_for_template"
    await message.answer(
        "✍️ **Ertangi kun uchun shablonni yuboring:**\n\n"
        "Quyidagi 7 ta qismni `---` belgisi bilan ajratib **bitta xabarda** yuboring:\n\n"
        "1. Ertalabgi qiziqarli ma'lumot\n---\n"
        "2. Quiz (Viktorina) savoli\n---\n"
        "3. Quiz variantlari (vergul bilan: V1, V2, V3, V4)\n---\n"
        "4. To'g'ri javob raqami (0 dan 3 gacha)\n---\n"
        "5. Abetdagi (13:00) IT fakt\n---\n"
        "6. Kechki (22:00) so'rovnoma savoli\n---\n"
        "7. So'rovnoma variantlari (vergul bilan)\n\n"
        "*(Agar to'xtatishni xohlasangiz '❌ Bekor qilish' tugmasini bosing)*"
    )

# Har qanday oddiy matn yoki buyruq kelganda holatni to'g'ri boshqarish
@dp.message(F.text & ~F.command())
async def handle_admin_text(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    if admin_states.get(ADMIN_ID) != "waiting_for_template":
        # Agar admin holatda bo'lmasa, bu matnni e'tiborsiz qoldiramiz yoki yordam beramiz
        return
    
    parts = message.text.split("---")
    if len(parts) < 7:
        await message.answer("❌ Xatolik! 7 ta qismni `---` bilan ajratib to'liq yuboring. Qaytadan urinib ko'ring yoki /admin orqali chiqing.")
        return
    
    try:
        morning_fact = parts[0].strip()
        quiz_question = parts[1].strip()
        quiz_options = parts[2].strip() 
        quiz_correct = int(parts[3].strip())
        lunch_fact = parts[4].strip()
        evening_poll_q = parts[5].strip()
        evening_poll_opts = parts[6].strip() 
        
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        # Eskisini o'chiramiz va yangisini yozamiz
        cursor.execute("DELETE FROM daily_template")
        cursor.execute("""
            INSERT INTO daily_template (id, morning_fact, quiz_question, quiz_options, quiz_correct_index, lunch_fact, evening_poll_question, evening_poll_options)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (morning_fact, quiz_question, quiz_options, quiz_correct, lunch_fact, evening_poll_q, evening_poll_opts))
        conn.commit()
        conn.close()
        
        admin_states.pop(ADMIN_ID, None)
        await message.answer("✅ **Ertangi kun uchun shablon muvaffaqiyatli saqlandi!** Eskisi o'chirib yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}\nFormatni tekshirib qaytadan yuboring.")

# --- AVTO-POSTLAR (YUBORILIB BO'LINGACH BAZADAN O'CHIB KETADI) ---
async def send_morning_post():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT morning_fact, quiz_question, quiz_options, quiz_correct_index FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print("Ertalabgi shablon topilmadi (shablon kiritilmagan).")
            return
        
        fact, q_text, opts_str, correct_idx = row
        options = [o.strip() for o in opts_str.split(",")]
        
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=f"🌅 <b>Ertalabgi IT Ma'lumot:</b>\n\n{fact}")
        await bot.send_poll(
            chat_id=CHANNEL_USERNAME,
            question=q_text,
            options=options,
            is_anonymous=False,
            type="quiz",
            correct_option_id=correct_idx
        )
        print("Ertalabgi ma'lumot va quiz kanalga yuborildi!")
    except Exception as e:
        print(f"Xatolik: {e}")

async def send_lunch_post():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT lunch_fact FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return
        
        lunch_fact = row[0]
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=f"🎯 <b>Kunduzgi Qiziqarli IT Fakt (Obet):</b>\n\n{lunch_fact}")
        print("Kunduzgi fakt yuborildi!")
    except Exception as e:
        print(f"Xatolik: {e}")

async def send_evening_poll():
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT evening_poll_question, evening_poll_options FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return
        
        poll_q, opts_str = row
        options = [o.strip() for o in opts_str.split(",")]
        
        await bot.send_poll(
            chat_id=CHANNEL_USERNAME,
            question=poll_q,
            options=options,
            is_anonymous=False
        )
        
        # Kechki so'rovnoma yuborib bo'lingach, shu kunlik shablon bazadan TO'LIQ O'CHIRILADI!
        # Shunda takroran yuborilishining oldi olinadi va ertangi kun uchun bo'shatiladi.
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM daily_template")
        conn.commit()
        conn.close()
        
        print("Kechki so'rovnoma yuborildi va ishlatilgan shablon bazadan o'chirildi!")
    except Exception as e:
        print(f"Xatolik: {e}")

# --- MENYU BUYRUQLARI ---
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="hisobim", description="Hisobdagi pulni ko'rish"),
        BotCommand(command="help", description="Yordam olish"),
        BotCommand(command="ogohlantirish", description="Shartlar"),
        BotCommand(command="admin", description="Admin paneli"),
        BotCommand(command="cancel", description="Jarayonni to'xtatish")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("✅ Barcha amallar bekor qilindi.")

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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Har qanday holatda ham /start bosilganda admin xotiradagi kiritish rejimini tozalaymiz
    admin_states.pop(message.from_user.id, None)
    
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("👑 <b>Xush kelibsiz, Admin!</b>\nShablonlarni boshqarish uchun /admin buyrug'ini bosing.")
        return
    # Qolgan foydalanuvchilar qismi...
    is_subscribed = await check_user_channel(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer("⚠️ Botdan foydalanish uchun kanalimizga a'zo bo'ling.", reply_markup=keyboard)
    else:
        await message.answer("🎉 Xush kelibsiz! Botdan to'liq foydalanishingiz mumkin.")

@dp.message(Command("hisobim"))
async def cmd_my_account(message: Message):
    admin_states.pop(message.from_user.id, None) # Holatni tozalash
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Siz Adminsiz!")
        return
    await message.answer("💳 Hisobingiz ma'lumotlari...")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("ℹ️ Yordam bo'limi.")

@dp.message(Command("ogohlantirish"))
async def cmd_warning(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("⚠️ Ogohlantirish shartlari.")

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

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(send_morning_post, "cron", hour=9, minute=0)
    scheduler.add_job(send_lunch_post, "cron", hour=13, minute=0)
    scheduler.add_job(send_evening_post_trigger := send_evening_poll, "cron", hour=22, minute=0)
    scheduler.start()

    await set_bot_commands(bot)
    print("Bot yangilangan xavfsiz shablon tizimi bilan ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())