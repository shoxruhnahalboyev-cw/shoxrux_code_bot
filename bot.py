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

TOKEN = "9297297005:AAGTgrLeGC_TeXUAx0s8KOL9WccjCVEaQkQ"
CHANNEL_USERNAME = "@shoxrux_code"      # Kanal username'ingiz
ADMIN_ID = 7439126820                   # O'zingizning Telegram ID'ingiz
STARTING_BALANCE = 3000                 # Boshlang'ich summa (3 ming)
REQUIRED_INVITES = 10                   # 10 ta do'st kerak
INVITE_REWARD = 3000                    # 10 ta do'st uchun beriladigan summa
MIN_WITHDRAW = 20000                    # Pul yechish uchun minimal summa

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- BAZA BILAN ISHLASH (SHABLONLAR BILAN) ---
def db_start():
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
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
    
    # Faqat 1 ta kunlik shablon turadigan jadval (Eskisi o'chib yangisi yoziladi)
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
    
    conn.commit()
    conn.close()

db_start()

# --- ADMIN PANEL: SHABLONNI O'ZGARTIRISH (STATE YOUTE YOKi ODDIY 1 QADAMLI DIALOG) ---
# Admin shablon kiritishi uchun vaqtinchalik xotira
admin_states = {}

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, bu buyruq faqat admin uchun!")
        return
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id != ?", (ADMIN_ID,))
    total_users = cursor.fetchone()[0]
    conn.close()
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Kunlik shablonni yangilash")],
            [KeyboardButton(text="📊 Statistikani ko'rish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n\n"
        f"Quyidagi tugmalar orqali botni boshqaring:",
        reply_markup=keyboard
    )

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
    admin_states[ADMIN_ID] = "waiting_for_template"
    await message.answer(
        "✍️ **Yangi kunlik shablonni yuboring:**\n\n"
        "Ma'lumotlarni quyidagi tartibda `---` belgisi bilan ajratib bitta xabarda yuboring:\n\n"
        "1. Ertalabgi qiziqarli ma'lumot\n---\n"
        "2. Quiz (Viktorina) savoli\n---\n"
        "3. Quiz variantlari (vergul bilan: Variant1, Variant2, Variant3, Variant4)\n---\n"
        "4. To'g'ri javob raqami (0 dan 3 gacha, masalan: 0 birinchi variant uchun)\n---\n"
        "5. Abetdagi (13:00) IT fakt\n---\n"
        "6. Kechki (22:00) so'rovnoma savoli\n---\n"
        "7. So'rovnoma variantlari (vergul bilan)"
    )

@dp.message(F.text & ~F.command())
async def handle_admin_text(message: Message):
    if message.from_user.id != ADMIN_ID or admin_states.get(ADMIN_ID) != "waiting_for_template":
        return
    
    parts = message.text.split("---")
    if len(parts) < 7:
        await message.answer("❌ Xatolik! 7 ta qismni `---` bilan ajratib to'liq yuboring. Qaytadan urinib ko'ring.")
        return
    
    try:
        morning_fact = parts[0].strip()
        quiz_question = parts[1].strip()
        quiz_options = parts[2].strip() # vergul bilan
        quiz_correct = int(parts[3].strip())
        lunch_fact = parts[4].strip()
        evening_poll_q = parts[5].strip()
        evening_poll_opts = parts[6].strip() # vergul bilan
        
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        # Eskisini o'chiramiz va yangisini yozamiz (Faqat 1 ta shablon turadi)
        cursor.execute("DELETE FROM daily_template")
        cursor.execute("""
            INSERT INTO daily_template (id, morning_fact, quiz_question, quiz_options, quiz_correct_index, lunch_fact, evening_poll_question, evening_poll_options)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (morning_fact, quiz_question, quiz_options, quiz_correct, lunch_fact, evening_poll_q, evening_poll_opts))
        conn.commit()
        conn.close()
        
        admin_states.pop(ADMIN_ID, None)
        await message.answer("✅ **Yangi shablon muvaffaqiyatli saqlandi!** Eskisi o'chirib yuborildi. Endi belgilangan vaqtlarda shu shablon ishlaydi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}\nFormatni tekshirib qaytadan yuboring.")

# --- AVTO-POSTLAR (09:00, 13:00, 22:00) ---
async def send_morning_post():
    """Soat 09:00 da ertalabgi ma'lumot va Quiz yuborish"""
    try:
        conn = sqlite3.connect("bot_base.db")
        cursor = conn.cursor()
        cursor.execute("SELECT morning_fact, quiz_question, quiz_options, quiz_correct_index FROM daily_template WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return
        
        fact, q_text, opts_str, correct_idx = row
        options = [o.strip() for o in opts_str.split(",")]
        
        # 1. Ertalabgi ma'lumot
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=f"🌅 <b>Ertalabgi IT Ma'lumot:</b>\n\n{fact}")
        
        # 2. Quiz (Viktorina) savoli
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
        print(f"Ertalabgi postni yuborishda xatolik: {e}")

async def send_lunch_post():
    """Soat 13:00 da abetdagi IT faktni yuborish"""
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
        print("Kunduzgi fakt kanalga yuborildi!")
    except Exception as e:
        print(f"Kunduzgi postda xatolik: {e}")

async def send_evening_poll():
    """Soat 22:00 da kechki qiziqarli so'rovnomani yuborish"""
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
        print("Kechki so'rovnoma kanalga yuborildi!")
    except Exception as e:
        print(f"Kechki so'rovnomada xatolik: {e}")

# --- MENYU BUYRUQLARI ---
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="hisobim", description="Hisobdagi pulni ko'rish"),
        BotCommand(command="help", description="Yordam olish"),
        BotCommand(command="ogohlantirish", description="Pul yechib olish shartlari"),
        BotCommand(command="admin", description="Admin paneli")
    ]
    await bot.set_my_commands(commands)

# --- KANALGA A'ZO BO'LGANINI TEKSHIRISH ---
async def check_user_channel(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        print(f"Tekshirish xatoligi: {e}")
    return False

# --- /START KOMANDASI ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Yo'q"
    args = message.text.split()
    
    if user_id == ADMIN_ID:
        await message.answer(
            f"👑 <b>Assalomu alaykum, Xojayin (Admin)!</b>\n\n"
            f"Siz botning boshqaruv panelidasiz.\n"
            f"Shablonlarni o'zgartirish uchun /admin buyrug'ini bosing."
        )
        return

    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referrer_id = None
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (ref_id,))
                if cursor.fetchone():
                    referrer_id = ref_id
        
        cursor.execute("INSERT INTO users (user_id, referrer_id, balance, first_name, username) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, referrer_id, STARTING_BALANCE, first_name, username))
        conn.commit()
        
        if referrer_id:
            cursor.execute("UPDATE users SET invited_count = invited_count + 1 WHERE user_id = ?", (referrer_id,))
            cursor.execute("SELECT invited_count, balance FROM users WHERE user_id = ?", (referrer_id,))
            ref_data = cursor.fetchone()
            inv_count = ref_data[0]
            ref_balance = ref_data[1]
            
            if inv_count % REQUIRED_INVITES == 0:
                ref_balance += INVITE_REWARD
                cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (ref_balance, referrer_id))
            conn.commit()
            
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 Tabriklaymiz! Sizning havolangiz orqali yangi do'st qo'shildi!\n"
                    f"👥 Jami taklif qilinganlar: <b>{inv_count} ta</b>\n"
                    f"💰 Joriy balansingiz: <b>{ref_balance} so'm</b>"
                )
            except:
                pass
    conn.close()

    is_subscribed = await check_user_channel(user_id)
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer(
            "⚠️ <b>Diqqat!</b> Botdan foydalanish va sovg'alarga ega bo'lish uchun avval kanalimizga a'zo bo'lishingiz kerak.",
            reply_markup=keyboard
        )
    else:
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        await message.answer(
            f"🎉 <b>Tabriklaymiz!</b> Siz <b>3000 so'm</b> pul yutib oldingiz!\n\n"
            f"📢 Agar siz kanalga mana bu link orqali <b>{REQUIRED_INVITES} ta</b> do'stingizni qo'shsangiz, yana <b>{INVITE_REWARD} so'm</b> yutib olasiz!\n\n"
            f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>"
        )

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_user_channel(user_id)
    if is_subscribed:
        await callback.message.delete()
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        await callback.message.answer(
            f"✅ Kanalga obuna tasdiqlandi!\n\n"
            f"🎉 <b>Tabriklaymiz!</b> Siz <b>3000 so'm</b> pul yutib oldingiz!\n\n"
            f"📢 Agar siz kanalga mana bu link orqali <b>{REQUIRED_INVITES} ta</b> do'stingizni qo'shsangiz, yana <b>{INVITE_REWARD} so'm</b> yutib olasiz!\n\n"
            f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>"
        )
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

@dp.message(Command("hisobim"))
async def cmd_my_account(message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("👑 Siz Adminsiz!")
        return
    if not await check_user_channel(user_id):
        return
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, invited_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else STARTING_BALANCE
    invited = row[1] if row else 0
    
    keyboard = None
    if balance >= MIN_WITHDRAW:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Pul yechib olish", callback_data="withdraw_money")]
        ])
    await message.answer(f"💳 <b>Hisobingiz:</b>\n\n💰 Balans: <b>{balance} so'm</b>\n👥 Do'stlar: <b>{invited} ta</b>", reply_markup=keyboard)

@dp.callback_query(F.data == "withdraw_money")
async def callback_withdraw(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Yo'q"
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < MIN_WITHDRAW:
        conn.close()
        await callback.answer("❌ Balansingiz yetarli emas!", show_alert=True)
        return
    
    balance = row[0]
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"✅ So'rov yuborildi! Yechilgan summa: <b>{balance} so'm</b>")
    await bot.send_message(ADMIN_ID, f"🚨 <b>Pul yechish so'rovi!</b>\n👤 {user_name} ({username})\n🆔 <code>{user_id}</code>\n💰 <b>{balance} so'm</b>")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(f"ℹ️ Do'stlaringizni taklif qiling (Har {REQUIRED_INVITES} ta do'st uchun +{INVITE_REWARD} so'm). Minimum yechish: {MIN_WITHDRAW} so'm.")

@dp.message(Command("ogohlantirish"))
async def cmd_warning(message: Message):
    await message.answer(f"⚠️ Pul yechish uchun kamida <b>{MIN_WITHDRAW} so'm</b> bo'lishi kerak!")

# --- RENDER WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- SCHEDULER (ANIQ SOATLARDA ISHLASH) ---
async def main():
    await start_web_server()

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent") # O'zbekiston vaqti bo'yicha
    
    # 09:00 da ertalabgi fakt va quiz
    scheduler.add_job(send_morning_post, "cron", hour=9, minute=0)
    # 13:00 da abetdagi fakt
    scheduler.add_job(send_lunch_post, "cron", hour=13, minute=0)
    # 22:00 da kechki so'rovnoma
    scheduler.add_job(send_evening_poll, "cron", hour=22, minute=0)
    
    scheduler.start()

    await set_bot_commands(bot)
    print("Bot shablon boshqaruvi va vaqtli postlar bilan ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())