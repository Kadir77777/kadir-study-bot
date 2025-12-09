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
    try:
        with open(LOCAL_QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes = json.load(f)
        if quotes:
            q = random.choice(quotes)
            return {"content": q, "author": "Local"}
    except Exception:
        return None

# --- Daily Reminder Loop ---
@tasks.loop(time=dt.time(hour=9, minute=0, tzinfo=TZ))
async def reminder_loop():
    global REMINDER_CHANNEL_ID
    if REMINDER_CHANNEL_ID is None:
        return
    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if not channel:
        return

    cur.execute("SELECT user_id, message FROM reminders")
    reminders = cur.fetchall()

    for user_id, message in reminders:
        await channel.send(f"<@{user_id}> reminder: {message}")

# --- Lifecycle ---
@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{COMMAND_PREFIX}help"))

    if not reminder_loop.is_running():
        reminder_loop.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"🤖 Unknown command. Try `{COMMAND_PREFIX}help`.")
        return
    await ctx.send("❌ Error occurred.")
    await notify_admin(f"Error: {error}")

# ------------------ COMMANDS ----------------------

# --- HELP ---
@bot.command(name="help")
async def help_cmd(ctx):
    await ctx.send(
        "**Commands & Usage:**\n"
        f"{COMMAND_PREFIX}quote\n"
        f"{COMMAND_PREFIX}due add <title> <YYYY-MM-DD>\n"
        f"{COMMAND_PREFIX}pomodoro <minutes> | stop\n"
        f"{COMMAND_PREFIX}progress\n"
        f"{COMMAND_PREFIX}leaderboard ← NEW FEATURE\n"
        f"{COMMAND_PREFIX}quiz <topic>\n"
        f"{COMMAND_PREFIX}setreminderhere | remind | listreminders | deletereminder\n"
        f"{COMMAND_PREFIX}ping | usercount\n"
    )

# --- Ping ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency*1000)} ms")

# --- Quote ---
@bot.command()
async def quote(ctx):
    q = await fetch_zenquote_async()
    if not q:
        q = fetch_local_quote()
    if not q:
        return await ctx.send("Error fetching quote.")
    await ctx.send(f"{q['content']} — *{q['author']}*")

# --- User Count ---
@bot.command()
async def usercount(ctx):
    await ctx.send(f"Members: {ctx.guild.member_count}")

# --- Admin ---
@bot.command()
@commands.has_permissions(administrator=True)
async def admin(ctx):
    await ctx.send("Admin command executed.")

# --- DUE COMMAND ---
@bot.command()
async def due(ctx, sub=None, *args):
    uid = str(ctx.author.id)

    if sub == "add":
        title = " ".join(args[:-1])
        date = args[-1]
        cur.execute("INSERT INTO assignments (user_id, title, due_date) VALUES (?, ?, ?)", (uid, title, date))
        conn.commit()
        return await ctx.send(f"Added: {title} due {date}")

    cur.execute("SELECT id, title, due_date FROM assignments WHERE user_id=?", (uid,))
    rows = cur.fetchall()
    msg = "\n".join([f"{r[0]} — {r[1]} ({r[2]})" for r in rows])
    await ctx.send("Your assignments:\n" + msg)

# --- Pomodoro ---
active_timers = {}

@bot.command()
async def pomodoro(ctx, minutes: int = 25):
    uid = ctx.author.id
    await ctx.send(f"Pomodoro started for {minutes} minutes!")

    async def timer():
        await asyncio.sleep(minutes*60)
        cur.execute("INSERT INTO study_sessions (user_id, minutes, started_at) VALUES (?, ?, datetime('now'))", (str(uid), minutes))
        conn.commit()
        await ctx.send(f"{ctx.author.mention} Time's up!")

    active_timers[uid] = asyncio.create_task(timer())

@bot.command()
async def stop(ctx):
    uid = ctx.author.id
    task = active_timers.get(uid)
    if task:
        task.cancel()
        await ctx.send("Timer stopped.")

# --- Progress ---
@bot.command()
async def progress(ctx):
    uid = str(ctx.author.id)
    cur.execute("SELECT COUNT(*), SUM(minutes) FROM study_sessions WHERE user_id=?", (uid,))
    count, total = cur.fetchone()
    total = total or 0
    await ctx.send(f"Sessions: {count}, Total minutes: {total}")

# ---------------------------------------------------
# NEW FEATURE FOR MODULE 10 — LEADERBOARD
# ---------------------------------------------------

@bot.command(name="leaderboard", help="Show top study times leaderboard.")
async def leaderboard(ctx):
    try:
        cur.execute("""
            SELECT user_id, SUM(minutes) AS total_minutes
            FROM study_sessions
            GROUP BY user_id
            ORDER BY total_minutes DESC
            LIMIT 10
        """)
        rows = cur.fetchall()

        if not rows:
            return await ctx.send("📊 No study data yet — start a pomodoro session using `!pomodoro <minutes>`.")        

        lines = []
        rank = 1
        for uid, minutes in rows:
            user = await bot.fetch_user(int(uid))
            name = user.name if user else f"User {uid}"
            lines.append(f"**#{rank}** — {name}: `{minutes}` minutes")
            rank += 1

        await ctx.send("🏆 **Study Leaderboard**\n" + "\n".join(lines))

    except Exception as e:
        log.error(f"Leaderboard error: {e}")
        await ctx.send("❌ Couldn't load leaderboard.")

# --- Quiz ---
@bot.command()
async def quiz(ctx, topic="default"):
    qfile = os.path.join(FLASHCARDS_DIR, f"{topic}.json")
    try:
        with open(qfile, "r") as f:
            questions = json.load(f)
    except:
        return await ctx.send("No quiz found.")

    random.shuffle(questions)
    score = 0
    for q in questions[:5]:
        await ctx.send(q["question"])
        msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author, timeout=20)
        if msg.content.lower() == q["answer"].lower():
            score += 1
            await ctx.send("Correct!")
        else:
            await ctx.send(f"Wrong — {q['answer']}")
    await ctx.send(f"Score: {score}/5")

# --- Reminder Commands ---
@bot.command()
async def setreminderhere(ctx):
    global REMINDER_CHANNEL_ID
    REMINDER_CHANNEL_ID = ctx.channel.id
    await ctx.send("Daily reminders will be sent here.")

@bot.command()
async def remind(ctx, *, message):
    cur.execute("INSERT INTO reminders (user_id, message) VALUES (?, ?)", (str(ctx.author.id), message))
    conn.commit()
    await ctx.send("Reminder saved!")

@bot.command()
async def listreminders(ctx):
    cur.execute("SELECT message FROM reminders WHERE user_id=?", (str(ctx.author.id),))
    rows = cur.fetchall()
    if not rows:
        return await ctx.send("You have no reminders.")
    await ctx.send("\n".join([f"- {r[0]}" for r in rows]))

@bot.command()
async def deletereminder(ctx, *, message):
    cur.execute("DELETE FROM reminders WHERE user_id=? AND message=?", (str(ctx.author.id), message))
    conn.commit()
    await ctx.send("Reminder deleted (if it existed).")

# --- Run Bot ---
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
