# Translator Drea Telegram Bot

Telegram bot that watches the Russian channel, translates posts to English, and mirrors them to the English channel. It stores source-to-translation message IDs in SQLite so edited Russian posts can update their English versions.

## Local Setup

1. Copy `.env.example` to `.env`.
2. Fill in:

```text
BOT_TOKEN=your_bot_token
RU_CHANNEL_ID=-100...
EN_CHANNEL_ID=-100...
DATA_DIR=data
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run:

```bash
python bot.py
```

## Files

- `bot.py` is the bot entry point.
- `data/messages.db` stores message mapping state and is ignored by Git.
- `.env` stores secrets and is ignored by Git.
- `.env.example` is safe to commit.

Do not commit `.env`, `data/*.db`, or `secrets/*`.
