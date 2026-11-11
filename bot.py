import asyncio
import logging
import sqlite3
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web  # <--- UptimeRobot va Render uchun qo'shildi

TOKEN = "9297297005:AAH6kj7a_pToJoQktbOI1zTfCkjJMpLQQcs"
CHANNEL_USERNAME = "@shoxrux_code"      # Kanal username'ingiz
ADMIN_ID = 7439126820                   # O'zingizning Telegram ID'ingiz
STARTING_BALANCE = 3000                 # Boshlang'ich summa (3 ming)
REQUIRED_INVITES = 10                   # 10 ta do'st kerak
INVITE_REWARD = 3000                    # 10 ta do'st uchun beriladigan summa
MIN_WITHDRAW = 20000                    # Pul yechish uchun minimal summa

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
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
    for col, col_type in [("reactions_count", "INTEGER DEFAULT 0"), 
                           ("invited_count", "INTEGER DEFAULT 0"), 
                           ("first_name", "TEXT"),
                           ("username", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except:
            pass
            
    conn.commit()
    conn.close()

db_start()

# --- 3 KUNLIK KONTENT REJASI (Faktlar, Matnli bilimlar va So'rovnomalar) ---

# 1-KUN ELEMENTLARI
DAY_1_FACTS_AND_TIPS = [
    "🧠 <b>IT Fakti #1:</b> Dunyodagi ilk dasturlash tili va birinchi kompilyator ayol olima Grace Hopper tomonidan 1950-yillarda ishlab chiqilgan.",
    "🧠 <b>IT Fakti #2:</b> Dastlabki sichqoncha (mishq) yog'ochdan yasalgan bo'lib, uning ostida ikkita temir g'ildirak bo'lgan.",
    "📚 <b>Foydali bilim #1:</b> Kod yozishda toza arxitektura (Clean Code) tamoyillariga amal qilish — kelajakdagi xatolarni 50% ga kamaytiradi.",
    "📚 <b>Foydali bilim #2:</b> Algoritmlarni tushunish har qanday dasturlash tilini o'rganishni 3 barobar tezlashtiradi."
]

DAY_1_POLLS = [
    {"question": "Sizningcha, kelajakda qaysi dasturlash tili eng ommabop bo'ladi?", "options": ["Python", "JavaScript", "C++ / C#", "Go / Rust"]},
    {"question": "Kuniga o'rtacha necha soat kompyuter yoki telefon qarshisida o'tqazasiz?", "options": ["2-4 soat", "5-7 soat", "8-10 soat", "10 soatdan ko'p"]}
]

# 2-KUN ELEMENTLARI
DAY_2_FACTS_AND_TIPS = [
    "🧠 <b>IT Fakti #1:</b> Python dasturlash tili ilon sharafiga emas, balki muallifning sevimli 'Monty Python's Flying Circus' nomli komediya shousi nomidan kelib chiqqan.",
    "🧠 <b>IT Fakti #2:</b> Google qidiruv tizimining dastlabki nomi 'BackRub' bo'lgan.",
    "📚 <b>Foydali bilim #1:</b> Xatolardan (Bug) qo'rqmang. Har bir topilgan xatolik — bu sizning tajribangizni oshiruvchi yangi darsdir.",
    "📚 <b>Foydali bilim #2:</b> Git va GitHub bilan ishlashni o'rganish istalgan dasturchi uchun birinchi raqamli majburiyatdir."
]

DAY_2_POLLS = [
    {"question": "IT sohasida ishlashni boshlash uchun eng asosiy qadam nima?", "options": ["Kuchli ingliz tili", "Amaliy loyihalar", "Nazandiy bilim", "Mentor yordami"]},
    {"question": "Sizga qaysi yo'nalish ko'proq yoqadi?", "options": ["Front-end", "Back-end", "Mobil ilovalar", "Sun'iy intellekt (AI)"]}
]

# 3-KUN ELEMENTLARI
DAY_3_FACTS_AND_TIPS = [
    "🧠 <b>IT Fakti #1:</b> Qidiruv tizimlarida har kuni millionlab so'rovlar qayta ishlanadi va ularning aksariyati sun'iy intellekt orqali tahlil qilinadi.",
    "🧠 <b>IT Fakti #2:</b> Ilk veb-sayt hali ham ishlaydi va uni Tim Berners-Lee 1991 yilda yaratgan.",
    "📚 <b>Foydali bilim #1:</b> Har kuni kamida 30 daqiqa yangi texnologiyalarni o'qib o'rganish mutaxassislikka tezroq chiqishga yordam beradi.",
    "📚 <b>Foydali bilim #2:</b> Kodni optimallashtirish vaqtni tejaydi va dastur ish faoliyatini keskin yaxshilaydi."
]

DAY_3_POLLS = [
    {"question": "Sun'iy intellekt (AI) kelajakda dasturchilarning o'rnini to'laqonli egallay oladimi?", "options": ["Ha, albatta", "Yo'q, faqat yordamchi bo'ladi", "Bilmadim", "Fikr bildirishga qiynalaman"]},
    {"question": "Siz qaysi operatsion tizimdan foydalanasiz?", "options": ["Windows", "macOS", "Linux", "Mobil qurilma"]}
]


async def send_auto_post():
    """Kanalga 3 kunlik reja asosida xavfsiz va xatolarsiz fakt/savol va so'rovnomalarni yuborish"""
    try:
        day_index = datetime.now().day % 3
        
        if day_index == 1:
            facts = DAY_1_FACTS_AND_TIPS
            polls = DAY_1_POLLS
        elif day_index == 2:
            facts = DAY_2_FACTS_AND_TIPS
            polls = DAY_2_POLLS
        else:
            facts = DAY_3_FACTS_AND_TIPS
            polls = DAY_3_POLLS
            
        choice_type = random.choice(["fact", "poll"])
        
        if choice_type == "fact":
            text = random.choice(facts)
            await bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
            print("Kanalga IT fakt/bilim yuborildi!")
        else:
            poll_data = random.choice(polls)
            await bot.send_poll(
                chat_id=CHANNEL_USERNAME,
                question=poll_data["question"],
                options=poll_data["options"],
                is_anonymous=False
            )
            print("Kanalga interaktiv so'rovnoma (Poll) yuborildi!")
            
    except Exception as e:
        print(f"Avto-post yuborishda xatolik: {e}")

# --- MENYU BUYRUQLARINI O'RNATISH ---
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="hisobim", description="Hisobdagi pulni ko'rish"),
        BotCommand(command="help", description="Yordam olish"),
        BotCommand(command="ogohlantirish", description="Pul yechib olish shartlari"),
        BotCommand(command="admin", description="Admin paneli (Faqat admin uchun)")
    ]
    await bot.set_my_commands(commands)

# --- KANALGA A'ZO BO'LGANINI TEKSHIRISH (ADMIN UCHUN OCHIQ) ---
async def check_user_channel(user_id: int) -> bool:
    # Agar foydalanuvchi Admin bo'lsa, tekshirib o'tirmasdan True qaytaradi!
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
            f"Foydalanuvchilar ro'yxati va statistikani ko'rish uchun /admin buyrug'ini bosing."
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

# --- OBUNANI TEKSHIRISH (CALLBACK) ---
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

# --- /HISOBIM KOMANDASI ---
@dp.message(Command("hisobim"))
async def cmd_my_account(message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("👑 Siz Adminsiz! Sizda balans mavjud emas.")
        return

    # Oddiy foydalanuvchilar uchun kanal obunasini tekshirish
    if not await check_user_channel(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer("⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'lishingiz kerak.", reply_markup=keyboard)
        return

    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, invited_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else STARTING_BALANCE
    invited = row[1] if row else 0
    
    text = (
        f"💳 <b>Sizning hisobingiz:</b>\n\n"
        f"💰 Balansingiz: <b>{balance} so'm</b>\n"
        f"👥 Taklif qilingan do'stlar: <b>{invited} ta</b>"
    )
    
    keyboard = None
    if balance >= MIN_WITHDRAW:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Pul yechib olish", callback_data="withdraw_money")]
        ])
    
    await message.answer(text, reply_markup=keyboard)

# --- PUL YECHIB OLISH ---
@dp.callback_query(F.data == "withdraw_money")
async def callback_withdraw(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Kiritilmagan"
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or row[0] < MIN_WITHDRAW:
        conn.close()
        await callback.answer("❌ Kechirasiz, balansingiz yetarli emas!", show_alert=True)
        return
    
    balance = row[0]
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"✅ <b>Pul yechib olish uchun so'rov yuborildi!</b>\n\n"
        f"💰 Yechilgan summa: <b>{balance} so'm</b>\n"
        f"Admin tez orada siz bilan bog'lanadi."
    )
    
    try:
        admin_text = (
            f"🚨 <b>Yangi pul yechish so'rovi!</b>\n\n"
            f"👤 Foydalanuvchi: <b>{user_name}</b>\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💰 Summa: <b>{balance} so'm</b>"
        )
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print(f"Adminga xabar yuborishda xatolik: {e}")

# --- /HELP KOMANDASI ---
@dp.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != ADMIN_ID and not await check_user_channel(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer("⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'lishingiz kerak.", reply_markup=keyboard)
        return

    text = (
        "ℹ️ <b>Yordam bo'limi:</b>\n\n"
        f"• Shaxsiy havolangiz orqali do'stlaringizni taklif qiling (Har {REQUIRED_INVITES} ta do'st uchun +{INVITE_REWARD} so'm qo'shiladi).\n"
        f"• Pul yechish uchun hisobingizda kamida {MIN_WITHDRAW} so'm bo'lishi kerak."
    )
    await message.answer(text)

# --- /OGOHLANTIRISH KOMANDASI ---
@dp.message(Command("ogohlantirish"))
async def cmd_warning(message: Message):
    if message.from_user.id != ADMIN_ID and not await check_user_channel(message.from_user.id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
        ])
        await message.answer("⚠️ Botdan foydalanish uchun avval kanalimizga a'zo bo'lishingiz kerak.", reply_markup=keyboard)
        return

    text = (
        f"⚠️ <b>Ogohlantirish!</b>\n\n"
        f"Hisobingizdan pul yechib olish uchun hisobingizda kamida <b>{MIN_WITHDRAW} so'm</b> bo'lishi kerak!"
    )
    await message.answer(text)

# --- /ADMIN PANEL KOMANDASI ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Kechirasiz, bu buyruq faqat admin uchun!")
        return
    
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id != ?", (ADMIN_ID,))
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT first_name, username, user_id, invited_count, balance FROM users WHERE user_id != ? ORDER BY invited_count DESC", (ADMIN_ID,))
    users_list = cursor.fetchall()
    
    conn.close()
    
    users_text = ""
    for idx, user in enumerate(users_list, 1):
        name = user[0] or "Noma'lum"
        uname = user[1] or "Yo'q"
        uid = user[2]
        inv = user[3]
        bal = user[4]
        users_text += f"{idx}. <b>{name}</b> ({uname})\n   🆔 ID: <code>{uid}</code> | 👥 {inv} ta odam | 💰 {bal} so'm\n\n"
    
    if not users_text:
        users_text = "Hozircha botdan foydalanayotgan oddiy foydalanuvchilar yo'q."

    admin_panel_text = (
        f"👑 <b>Admin Panel - Foydalanuvchilar ro'yxati</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{users_text}"
    )
    
    if len(admin_panel_text) > 4000:
        admin_panel_text = admin_panel_text[:4000] + "\n\n... (ro'yxat juda uzun)"

    await message.answer(admin_panel_text)

# --- RENDER WEB SERVICE UCHUN HTTP SERVER ---
async def handle(request):
    return web.Response(text="Bot is running and alive!")

app = web.Application()
app.router.add_get("/", handle)

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# --- BOT ISHGA TUSHGANDagi AMALLAR ---
async def main():
    await start_web_server()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_auto_post, "interval", hours=3)
    scheduler.start()

    await set_bot_commands(bot)
    print("Bot 3 kunlik reja, haqiqiy so'rovnomalar va faktlar bilan ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())