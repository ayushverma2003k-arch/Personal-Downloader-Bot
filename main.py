import os
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# 🔐 TOKEN (Railway ENV)
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing in environment variables")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# 👑 OWNER ID (CHANGE THIS)
OWNER_ID = 8044682416

# 💎 SYSTEM STORAGE
premium_users = set()

# ================= DATABASE =================
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    downloads INTEGER DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    music_count INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= DB FUNCTIONS =================
def add_user(user_id):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def log_video(user_id):
    cur.execute("""
        UPDATE users 
        SET downloads = downloads + 1,
            video_count = video_count + 1
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()

def log_music(user_id):
    cur.execute("""
        UPDATE users 
        SET downloads = downloads + 1,
            music_count = music_count + 1
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):

    add_user(msg.from_user.id)

    text = f"""
👋 Welcome to Ultra Downloader Bot 🚀

⚡ How it works:
1️⃣ Send any video/music link
2️⃣ Choose type 🎥 or 🎵
3️⃣ Select quality
4️⃣ Get file instantly

🔥 Features:
• 🎥 Video (360p - 1080p)
• 🎵 Music (128k - 320k)
• ⚡ Fast download
• 📊 Usage tracking

👤 Your ID: {msg.from_user.id}
"""

    await msg.answer(text)

# ================= LINK HANDLER =================
@dp.message_handler(lambda m: "http" in m.text)
async def link(msg: types.Message):

    kb = InlineKeyboardMarkup(row_width=1)

    kb.add(
        InlineKeyboardButton("🎥 Video", callback_data=f"v|{msg.text}"),
        InlineKeyboardButton("🎵 Music", callback_data=f"m|{msg.text}")
    )

    await msg.answer("🎯 Choose type:", reply_markup=kb)

# ================= CALLBACK =================
@dp.callback_query_handler(lambda c: True)
async def cb(call: types.CallbackQuery):

    data = call.data.split("|")
    mode = data[0]
    url = data[1]
    uid = call.from_user.id

    is_premium = uid in premium_users or uid == OWNER_ID

    kb = InlineKeyboardMarkup(row_width=1)

    if mode == "v":

        qualities = ["mp4 360p", "mp4 480p"]

        if is_premium:
            qualities += ["mp4 720p", "mp4 1080p"]

        for q in qualities:
            kb.add(InlineKeyboardButton(q, callback_data=f"d|v|{q}|{url}"))

        await bot.send_message(uid, "🎥 Select Video Quality:", reply_markup=kb)

    else:

        qualities = ["mp3 128k"]

        if is_premium:
            qualities += ["mp3 256k", "mp3 320k"]

        for q in qualities:
            kb.add(InlineKeyboardButton(q, callback_data=f"d|m|{q}|{url}"))

        await bot.send_message(uid, "🎵 Select Music Quality:", reply_markup=kb)

# ================= DOWNLOAD =================
@dp.callback_query_handler(lambda c: c.data.startswith("d"))
async def download(call: types.CallbackQuery):

    _, mode, quality, url = call.data.split("|")
    uid = call.from_user.id

    await bot.send_message(uid, "⚡ Downloading... Please wait 🔥")

    try:

        # 🎥 VIDEO
        if mode == "v":

            if quality == "mp4 360p":
                fmt = "best[height<=360]"
            elif quality == "mp4 480p":
                fmt = "best[height<=480]"
            elif quality == "mp4 720p":
                fmt = "best[height<=720]"
            else:
                fmt = "best"

            ydl_opts = {
                "format": fmt,
                "outtmpl": "video.mp4",
            }

            file = "video.mp4"

            log_video(uid)

        # 🎵 MUSIC
        else:

            bitrate = quality.split()[1].replace("k", "")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "music.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }],
            }

            file = "music.mp3"

            log_music(uid)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await bot.send_document(uid, open(file, "rb"))

    except Exception as e:
        await bot.send_message(uid, f"❌ Error: {str(e)}")

# ================= OWNER COMMANDS =================
@dp.message_handler(commands=['add'])
async def add(msg: types.Message):

    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner")

    user_id = int(msg.get_args())
    premium_users.add(user_id)

    await msg.reply("💎 Premium added")

@dp.message_handler(commands=['remove'])
async def remove(msg: types.Message):

    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner")

    user_id = int(msg.get_args())
    premium_users.discard(user_id)

    await msg.reply("❌ Removed premium")

# ================= STATS =================
@dp.message_handler(commands=['stats'])
async def stats(msg: types.Message):

    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ Only owner")

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT SUM(downloads), SUM(video_count), SUM(music_count) FROM users")
    data = cur.fetchone()

    await msg.reply(f"""
📊 BOT STATS

👥 Users: {users}
📥 Downloads: {data[0] or 0}
🎥 Videos: {data[1] or 0}
🎵 Music: {data[2] or 0}
""")

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
