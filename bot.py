import asyncio
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
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

MEDIA_GROUP_WAIT_SECONDS = 2.5
pending_media_groups = {}
pending_media_group_tasks = {}


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


def get_message_text(message) -> str:
    return message.text or message.caption or ""


def has_supported_media(message) -> bool:
    return bool(message.photo or message.video or message.audio or message.document)


def build_input_media(message, caption=None):
    if message.photo:
        return InputMediaPhoto(
            media=message.photo[-1].file_id,
            caption=caption or None,
        )

    if message.video:
        return InputMediaVideo(
            media=message.video.file_id,
            caption=caption or None,
        )

    if message.audio:
        return InputMediaAudio(
            media=message.audio.file_id,
            caption=caption or None,
        )

    if message.document:
        return InputMediaDocument(
            media=message.document.file_id,
            caption=caption or None,
        )

    return None


async def send_single_post(context: ContextTypes.DEFAULT_TYPE, message, translated: str):
    caption = translated or None

    if message.photo:
        return await context.bot.send_photo(
            chat_id=EN_CHANNEL_ID,
            photo=message.photo[-1].file_id,
            caption=caption,
        )

    if message.video:
        return await context.bot.send_video(
            chat_id=EN_CHANNEL_ID,
            video=message.video.file_id,
            caption=caption,
        )

    if message.audio:
        return await context.bot.send_audio(
            chat_id=EN_CHANNEL_ID,
            audio=message.audio.file_id,
            caption=caption,
        )

    if message.document:
        return await context.bot.send_document(
            chat_id=EN_CHANNEL_ID,
            document=message.document.file_id,
            caption=caption,
        )

    if translated:
        return await context.bot.send_message(
            chat_id=EN_CHANNEL_ID,
            text=translated,
        )

    return None


async def flush_media_group(context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    await asyncio.sleep(MEDIA_GROUP_WAIT_SECONDS)

    messages = pending_media_groups.pop(media_group_id, [])
    pending_media_group_tasks.pop(media_group_id, None)

    if not messages:
        return

    messages.sort(key=lambda item: item.message_id)

    text = next((get_message_text(item) for item in messages if get_message_text(item)), "")
    translated = translate(text) if text else ""

    media = []
    ru_ids = []

    for index, item in enumerate(messages):
        if get_en_id(item.message_id):
            continue

        input_media = build_input_media(
            item,
            caption=translated if index == 0 else None,
        )

        if input_media:
            media.append(input_media)
            ru_ids.append(item.message_id)

    if not media:
        return

    if len(media) == 1:
        for index, item in enumerate(messages):
            if get_en_id(item.message_id):
                continue

            sent = await send_single_post(
                context,
                item,
                translated if index == 0 else "",
            )

            if sent:
                save_mapping(item.message_id, sent.message_id)
                print("CREATED:", item.message_id, "->", sent.message_id)

            return

    try:
        sent_messages = await context.bot.send_media_group(
            chat_id=EN_CHANNEL_ID,
            media=media,
        )
    except Exception as exc:
        print("MEDIA_GROUP_FALLBACK:", media_group_id, exc)
        sent_messages = []

        for index, item in enumerate(messages):
            if get_en_id(item.message_id):
                continue

            sent = await send_single_post(
                context,
                item,
                translated if index == 0 else "",
            )

            if sent:
                sent_messages.append(sent)

    for ru_id, sent in zip(ru_ids, sent_messages):
        save_mapping(ru_id, sent.message_id)
        print("CREATED:", ru_id, "->", sent.message_id)


#processing new posts and updated posts
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    is_new = update.channel_post is not None
    is_edit = update.edited_channel_post is not None

    message = update.channel_post or update.edited_channel_post

    if not message:
        return

    if message.chat.id != RU_CHANNEL_ID:
        return

    text = get_message_text(message)
    translated = translate(text) if text else ""

    ru_id = message.message_id
    en_id = get_en_id(ru_id)

    # -------------------
    # NEW POST
    # -------------------
    if is_new:

        # защита от дубля (очень важно)
        if en_id:
            return

        if message.media_group_id and has_supported_media(message):
            media_group_id = str(message.media_group_id)
            pending_media_groups.setdefault(media_group_id, []).append(message)

            if media_group_id not in pending_media_group_tasks:
                pending_media_group_tasks[media_group_id] = asyncio.create_task(
                    flush_media_group(context, media_group_id)
                )

            return

        if not translated and not has_supported_media(message):
            return

        sent = await send_single_post(context, message, translated)

        if sent:
            save_mapping(ru_id, sent.message_id)
            print("CREATED:", ru_id, "->", sent.message_id)

    # -------------------
    # EDIT POST
    # -------------------
    elif is_edit:

        if not en_id:
            return

        if not translated:
            return

        if has_supported_media(message):
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
