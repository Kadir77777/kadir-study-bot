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
intents.members = True  # used by usercount

# --- Timezone & reminder channel ---
TZ = zoneinfo.ZoneInfo("America/New_York")
REMINDER_CHANNEL_ID: Optional[int] = None  # set via !setreminderhere

# --- Data folders ---
os.makedirs("data", exist_ok=True)
os.makedirs(FLASHCARDS_DIR, exist_ok=True)

# --- DB setup ---
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

def init_db():
    try:
        # Assignments
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL
            )
        """)
        # Study sessions (pomodoro)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                started_at TEXT NOT NULL
            )
        """)
        # Quiz results (optional)
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
        # Reminders (from File B, integrated)
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

# --- Bot initialization ---
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
bot.remove_command("help")  # allow custom help command

# --- Admin notifications ---
async def notify_admin(text: str):
    if not ADMIN_USER_ID:
        return
    try:
        user = await bot.fetch_user(ADMIN_USER_ID)
        if user:
            await user.send(text)
    except Exception as e:
        log.warning(f"Admin notify failed: {e}")

# --- Quotes helpers (non-blocking retry/backoff) ---
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
                log.warning(f"ZenQuotes error (try {i+1}/{QUOTE_MAX_TRIES}): {e}")
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
    except Exception as fe:
        log.error(f"Local quotes fallback failed: {fe}")
    return None

# --- Daily reminder loop (from File B, integrated) ---
@tasks.loop(time=dt.time(hour=9, minute=0, tzinfo=TZ))
async def reminder_loop():
    global REMINDER_CHANNEL_ID
    if REMINDER_CHANNEL_ID is None:
        return

    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if not channel:
        log.warning("Reminder loop: channel not found.")
        return

    try:
        cur.execute("SELECT user_id, message FROM reminders")
        reminders = cur.fetchall()
    except Exception as e:
        log.error(f"Reminder loop DB error: {e}")
        return

    if not reminders:
        return

    for user_id, message in reminders:
        try:
            await channel.send(f"<@{user_id}> reminder: {message}")
        except Exception as e:
            log.warning(f"Failed to send reminder to {user_id}: {e}")

# --- Lifecycle & error handling ---
@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{COMMAND_PREFIX}help"
        )
    )
    # Start the reminder loop if not running
    if not reminder_loop.is_running():
        log.info("Starting daily reminder loop")
        reminder_loop.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing parameter: `{error.param.name}`. Try `{COMMAND_PREFIX}help {ctx.command.name}`.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Bad argument. Please check your input format.")
        return
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"🤖 Unknown command. Try `{COMMAND_PREFIX}help`.")
        log.warning(f"Unknown command by {ctx.author}: {ctx.message.content}")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🔒 You do not have permission to use this command.")
        return

    log.exception(f"Unhandled error in command {getattr(ctx, 'command', None)}: {error}")
    await ctx.send("❌ Something went wrong on my end. The team has been notified.")
    await notify_admin(f"Error in {ctx.command} by {ctx.author}: {error}")

@bot.before_invoke
async def log_before(ctx):
    log.info(f"Invoking {ctx.command} by {ctx.author} in #{ctx.channel} (guild: {ctx.guild})")

@bot.event
async def on_command_completion(ctx):
    log.info(f"Completed {ctx.command} for {ctx.author} in #{ctx.channel}")

# --- Core commands ---

@bot.command(name="help", help="Show commands and usage examples.")
async def help_cmd(ctx):
    await ctx.send(
        "**Commands & Usage:**\n"
        f"{COMMAND_PREFIX}quote — Get a random quote\n"
        f"{COMMAND_PREFIX}due add <title> <YYYY-MM-DD>\n"
        f"{COMMAND_PREFIX}due list | {COMMAND_PREFIX}due next | {COMMAND_PREFIX}due delete <id>\n"
        f"{COMMAND_PREFIX}pomodoro <minutes>  |  {COMMAND_PREFIX}stop\n"
        f"{COMMAND_PREFIX}progress — Show study stats\n"
        f"{COMMAND_PREFIX}quiz <topic> — Flashcard quiz (e.g., default)\n"
        f"{COMMAND_PREFIX}setreminderhere — Set this channel for daily reminders\n"
        f"{COMMAND_PREFIX}remind <message> — Save a daily reminder\n"
        f"{COMMAND_PREFIX}listreminders — List your reminders\n"
        f"{COMMAND_PREFIX}deletereminder <exact text> — Delete a reminder\n"
        f"{COMMAND_PREFIX}admin — Admin-only command\n"
        f"{COMMAND_PREFIX}ping  |  {COMMAND_PREFIX}usercount\n"
    )

@bot.command(name="helpme", help="Alias for help.")
async def helpme(ctx):
    await help_cmd(ctx)

@bot.command(name="ping", help="Health check. Replies with Pong and latency.")
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: `{latency_ms} ms`")

@bot.command(name="quote", help="Get a random inspirational quote (ZenQuotes, fallback to local file).")
async def quote(ctx):
    q = await fetch_zenquote_async()
    if not q:
        q = fetch_local_quote()
    if not q or not q.get("content"):
        await ctx.send("⚠️ I couldn't fetch a quote right now. Please try again later.")
        return
    author = q.get("author") or "Unknown"
    await ctx.send(f"💬 {q['content']} — *{author}*")

@bot.command(name="usercount", help="Shows member count in this server.")
@commands.guild_only()
async def usercount(ctx):
    guild = ctx.guild
    await ctx.send(f"👥 Members in **{guild.name}**: `{guild.member_count}`")

# ----- Admin (permissions) -----
@bot.command(name="admin", help="Admin-only action.")
@commands.has_permissions(administrator=True)
async def admin(ctx):
    await ctx.send("🔐 Admin command executed.")

@admin.error
async def admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🔒 You do not have permission to use this command.")

# ----- Assignment Tracker (!due) -----
@bot.command(name="due", help="Assignment tracker. Use: !due add <title> <YYYY-MM-DD> | !due list | !due next | !due delete <id>")
async def due(ctx, subcommand: Optional[str] = None, *args):
    uid = str(ctx.author.id)
    try:
        if subcommand is None or subcommand.lower() == "list":
            cur.execute("SELECT id, title, due_date FROM assignments WHERE user_id = ? ORDER BY due_date", (uid,))
            rows = cur.fetchall()
            if not rows:
                return await ctx.send("📚 You have no assignments saved. Use `!due add <title> <YYYY-MM-DD>`.")
            today = datetime.now().date()
            lines = []
            for rid, title, ds in rows:
                when = ds
                try:
                    d = datetime.strptime(ds, "%Y-%m-%d").date()
                    delta = (d - today).days
                    when = f"{ds} ({'today' if delta == 0 else f'in {delta} days' if delta > 0 else f'{abs(delta)} days ago'})"
                except Exception:
                    pass
                lines.append(f"`{rid}` — **{title}** due **{when}**")
            return await ctx.send("📚 **Your Assignments:**\n" + "\n".join(lines))

        if subcommand.lower() == "add":
            if len(args) < 2:
                return await ctx.send("Usage: `!due add <title> <YYYY-MM-DD>`")
            due_date = args[-1]
            title = " ".join(args[:-1])
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                return await ctx.send("Date must be in `YYYY-MM-DD` format.")
            cur.execute("INSERT INTO assignments (user_id, title, due_date) VALUES (?, ?, ?)", (uid, title, due_date))
            conn.commit()
            return await ctx.send(f"📌 Saved: **{title}** due on **{due_date}**.")

        if subcommand.lower() == "next":
            cur.execute("SELECT title, due_date FROM assignments WHERE user_id = ? ORDER BY due_date LIMIT 1", (uid,))
            row = cur.fetchone()
            if not row:
                return await ctx.send("No assignments found. Use `!due add ...`")
            title, ds = row
            try:
                d = datetime.strptime(ds, "%Y-%m-%d").date()
                days = (d - datetime.now().date()).days
                suffix = "today" if days == 0 else f"in {days} days" if days > 0 else f'{abs(days)} days ago'
            except Exception:
                suffix = ds
            return await ctx.send(f"⏰ Next: **{title}** due **{ds}** ({suffix}).")

        if subcommand.lower() == "delete":
            if len(args) != 1:
                return await ctx.send("Usage: `!due delete <id>`")
            rid = int(args[0])
            cur.execute("DELETE FROM assignments WHERE id = ? AND user_id = ?", (rid, uid))
            conn.commit()
            if cur.rowcount and cur.rowcount > 0:
                return await ctx.send(f"🗑️ Deleted assignment `{rid}`.")
            return await ctx.send("No such assignment for you.")
        # Fallback
        await ctx.send("Unknown subcommand. Try: `add`, `list`, `next`, or `delete`.")
    except Exception as e:
        log.error(f"Due command error: {e}")
        await ctx.send("Couldn't process your assignment command.")
        await notify_admin(f"Due error for {ctx.author}: {e}")

# ----- Study Timer (!pomodoro) + !stop -----
active_timers: dict[int, asyncio.Task] = {}

@bot.command(name="pomodoro", help="Start a focused study timer. Usage: !pomodoro <minutes> (default 25)")
async def pomodoro(ctx, minutes: int = 25):
    if minutes <= 0 or minutes > 180:
        return await ctx.send("Please choose between 1 and 180 minutes.")
    uid = ctx.author.id
    if uid in active_timers and not active_timers[uid].done():
        return await ctx.send("You already have a running timer. Use `!stop` to cancel it.")

    await ctx.send(f"⏱️ Pomodoro started for **{minutes}** minutes. Stay focused!")

    async def run_timer():
        try:
            start_iso = datetime.utcnow().isoformat()
            await asyncio.sleep(minutes * 60)
            try:
                cur.execute(
                    "INSERT INTO study_sessions (user_id, minutes, started_at) VALUES (?, ?, ?)",
                    (str(uid), minutes, start_iso)
                )
                conn.commit()
            except Exception as e:
                log.error(f"Pomodoro DB error: {e}")
            await ctx.send(f"✅ Time's up, {ctx.author.mention}! Great job focusing for **{minutes}** minutes.")
        except asyncio.CancelledError:
            await ctx.send("⛔ Pomodoro canceled.")
        except Exception as e:
            log.exception(f"Pomodoro error: {e}")
            await ctx.send("Something went wrong with the timer.")
            await notify_admin(f"Pomodoro error for {ctx.author}: {e}")

    task = asyncio.create_task(run_timer())
    active_timers[uid] = task

@bot.command(name="stop", help="Cancel your current pomodoro timer.")
async def stop(ctx):
    uid = ctx.author.id
    task = active_timers.get(uid)
    if task and not task.done():
        task.cancel()
        await ctx.send("Timer canceled.")
    else:
        await ctx.send("You don't have a running timer.")

# ----- Progress Check (!progress) -----
@bot.command(name="progress", help="Show your study statistics.")
async def progress(ctx):
    uid = str(ctx.author.id)
    try:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(minutes),0) FROM study_sessions WHERE user_id = ?", (uid,))
        count, total_minutes = cur.fetchone()
        if not count or count == 0:
            await ctx.send("You haven't logged any study sessions yet! Try `!pomodoro <minutes>`.")
        else:
            await ctx.send(f"📈 You have completed `{count}` sessions, studying for `{total_minutes}` minutes!")
    except Exception as e:
        log.error(f"Progress command error: {e}")
        await ctx.send("Couldn't fetch your progress. Please try again later.")
        await notify_admin(f"Progress error for {ctx.author}: {e}")

# ----- Quiz Feature (!quiz) -----
@bot.command(name="quiz", help="Start a quick quiz. Usage: !quiz <topic>")
async def quiz(ctx, topic: str = "default"):
    q_file = os.path.join(FLASHCARDS_DIR, f"{topic}.json")
    try:
        with open(q_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except Exception as e:
        log.error(f"Quiz file load failed: {e}")
        await ctx.send(f"❌ No quiz found for `{topic}`.")
        return

    random.shuffle(questions)
    score = 0
    total = min(5, len(questions))
    for i in range(total):
        q = questions[i]
        await ctx.send(f"Q{i+1}: {q['question']}")
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=20)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up!")
            continue
        if msg.content.strip().lower() == q['answer'].strip().lower():
            score += 1
            await ctx.send("✅ Correct!")
        else:
            await ctx.send(f"❌ Wrong. Answer: {q['answer']}")
    await ctx.send(f"Quiz complete! Your Score: {score}/{total}")

# reminder functions - ZM
@bot.command(name="setreminderhere")
async def setreminderhere(ctx):
    global REMINDER_CHANNEL_ID
    REMINDER_CHANNEL_ID = ctx.channel.id
    log.info(f"Reminder channel set to {REMINDER_CHANNEL_ID} by {ctx.author}")
    await ctx.send("Daily reminders will now be sent in this channel.")

@bot.command(name="remind")
async def remind(ctx, *, message: str):
    try:
        cur.execute(
            "INSERT INTO reminders (user_id, message) VALUES (?, ?)",
            (str(ctx.author.id), message)
        )
        conn.commit()
        await ctx.send(f"Reminder saved: {message}")
    except Exception as e:
        log.error(f"Remind command error: {e}")
        await ctx.send("Failed to save your reminder.")
        await notify_admin(f"Remind error for {ctx.author}: {e}")

@bot.command(name="listreminders")
async def listreminders(ctx):
    try:
        cur.execute("SELECT message FROM reminders WHERE user_id = ?", (str(ctx.author.id),))
        reminders = cur.fetchall()
        if reminders:
            reminder_list = "\n".join([f"- {r[0]}" for r in reminders])
            await ctx.send(f"Your reminders:\n{reminder_list}")
        else:
            await ctx.send("You have no reminders.")
    except Exception as e:
        log.error(f"ListReminders command error: {e}")
        await ctx.send("Failed to fetch your reminders.")
        await notify_admin(f"ListReminders error for {ctx.author}: {e}")

@bot.command(name="deletereminder", aliases=["dr"])
async def deletereminder(ctx, *, reminder: str):
    try:
        cur.execute(
            "DELETE FROM reminders WHERE user_id = ? AND message = ?",
            (str(ctx.author.id), reminder)
        )
        deleted = cur.rowcount
        conn.commit()
        if deleted == 0:
            await ctx.send(f"No reminder named `{reminder}` found on your account.")
        else:
            await ctx.send(f"Deleted `{deleted}` reminder(s) named `{reminder}`.")
    except Exception as e:
        log.error(f"DeleteReminder command error: {e}")
        await ctx.send("Failed to delete reminder(s).")
        await notify_admin(f"DeleteReminder error for {ctx.author}: {e}")

# --- Run the bot ---
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
