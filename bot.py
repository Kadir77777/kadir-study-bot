import os
import json
import random
import logging
import asyncio
import sqlite3
from typing import Optional
from datetime import datetime
import datetime as dt
import zoneinfo

import requests
import discord
from discord.ext import commands, tasks
from pathlib import Path

from config import (
    DISCORD_TOKEN, COMMAND_PREFIX,
    ADMIN_USER_ID,
    ZENQUOTES_URL, QUOTE_MAX_TRIES, QUOTE_BACKOFF_SECONDS, QUOTE_TIMEOUT_SECONDS,
    LOG_FILE, DB_PATH, FLASHCARDS_DIR, LOCAL_QUOTES_FILE
)

# --- Sanity checks ---
print("TOKEN FROM ENV:", DISCORD_TOKEN)
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Add it to your .env file.")

# --- Logging setup ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")]
)
log = logging.getLogger("study-buddy-bot")

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# --- Timezone & reminder channel ---
TZ = zoneinfo.ZoneInfo("America/New_York")
REMINDER_CHANNEL_ID: Optional[int] = None

# --- Data folders ---
os.makedirs("data", exist_ok=True)
os.makedirs(FLASHCARDS_DIR, exist_ok=True)

# --- DB setup ---
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

def init_db():
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                started_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                correct INTEGER NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)

        conn.commit()
        log.info("Database initialized")

    except Exception as e:
        log.error(f"DB init error: {e}")

init_db()

# --- Bot Init ---
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
bot.remove_command("help")

# --- Admin Notifications ---
async def notify_admin(text: str):
    if not ADMIN_USER_ID:
        return
    try:
        user = await bot.fetch_user(ADMIN_USER_ID)
        if user:
            await user.send(text)
    except Exception as e:
        log.warning(f"Admin notify failed: {e}")

# --- ZenQuotes Fetch ---
async def fetch_zenquote_async() -> Optional[dict]:
    async def _do_request():
        for i in range(QUOTE_MAX_TRIES):
            try:
                r = requests.get(ZENQUOTES_URL, timeout=QUOTE_TIMEOUT_SECONDS)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and data:
                    return {"content": data[0].get("q"), "author": data[0].get("a")}
            except requests.exceptions.RequestException as e:
                log.warning(f"ZenQuotes error (try {i+1}): {e}")
                await asyncio.sleep(QUOTE_BACKOFF_SECONDS)
        return None
    return await _do_request()

def fetch_local_quote() -> Optional[dict]:
    tr
