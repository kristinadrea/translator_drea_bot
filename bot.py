import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("BOT_TOKEN")
RU_CHANNEL_ID = int(os.getenv("RU_CHANNEL_ID", "0"))
EN_CHANNEL_ID = int(os.getenv("EN_CHANNEL_ID", "0"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_FILE = DATA_DIR / "messages.db"

if not TOKEN:
    raise RuntimeError("Add BOT_TOKEN to .env")

if not RU_CHANNEL_ID:
    raise RuntimeError("Add RU_CHANNEL_ID to .env")

if not EN_CHANNEL_ID:
    raise RuntimeError("Add EN_CHANNEL_ID to .env")

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS message_map (
    ru_id INTEGER PRIMARY KEY,
    en_id INTEGER
)
""")

conn.commit()

def save_mapping(ru_id, en_id):
    cursor.execute(
        "INSERT OR REPLACE INTO message_map (ru_id, en_id) VALUES (?, ?)",
        (ru_id, en_id)
    )
    conn.commit()


def get_en_id(ru_id):
    cursor.execute(
        "SELECT en_id FROM message_map WHERE ru_id = ?",
        (ru_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def translate(text: str) -> str:
    return GoogleTranslator(source='ru', target='en').translate(text)

#processing new posts and updated posts
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    is_new = update.channel_post is not None
    is_edit = update.edited_channel_post is not None

    message = update.channel_post or update.edited_channel_post

    if not message:
        return

    if message.chat.id != RU_CHANNEL_ID:
        return

    text = message.text or message.caption or ""
    if not text:
        return

    translated = translate(text)

    ru_id = message.message_id
    en_id = get_en_id(ru_id)

    # -------------------
    # NEW POST
    # -------------------
    if is_new:

        # защита от дубля (очень важно)
        if en_id:
            return

        if message.photo:
            sent = await context.bot.send_photo(
                chat_id=EN_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=translated
            )
        else:
            sent = await context.bot.send_message(
                chat_id=EN_CHANNEL_ID,
                text=translated
            )

        save_mapping(ru_id, sent.message_id)
        print("CREATED:", ru_id, "->", sent.message_id)

    # -------------------
    # EDIT POST
    # -------------------
    elif is_edit:

        if not en_id:
            return

        if message.photo:
            await context.bot.edit_message_caption(
                chat_id=EN_CHANNEL_ID,
                message_id=en_id,
                caption=translated
            )
        else:
            await context.bot.edit_message_text(
                chat_id=EN_CHANNEL_ID,
                message_id=en_id,
                text=translated
            )

        print("UPDATED:", ru_id, "->", en_id)


app = Application.builder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, handler))

print("Bot is running...")
app.run_polling()
