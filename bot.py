import logging
import aiohttp
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import sqlite3
import datetime
import zoneinfo
import asyncio

#Declare variables and such
TZ = zoneinfo.ZoneInfo("America/New_York")

# Configure logging to console and file
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv(dotenv_path=".env", override=True)
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    logging.info(f'Bot is online as {bot.user}')
    print(f'Bot is online as {bot.user}')
    if not reminder_loop.is_running():
        logging.info(f'Starting Reminder loop')
        reminder_loop.start()


@bot.command(name='ping')
async def ping(ctx):
    logging.info("Ping command triggered")
    await ctx.send('Pong!')

@bot.command(name='quote')
async def quote(ctx):
    logging.info("Quote command triggered")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://zenquotes.io/api/random') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.send(f'"{data[0]["q"]}" � {data[0]["a"]}')
                else:
                    await ctx.send(f'Failed to fetch quote. Status: {resp.status}')
    except Exception as e:
        logging.error(f'Quote command error: {e}')
        await ctx.send('Could not fetch quote. Here is one: "Keep going, you are doing great!"')

@bot.command(name='helpme')
async def helpme(ctx):
    logging.info("Help command triggered")
    help_text = (
        "Available commands:\n"
        "!ping - Check bot status\n"
        "!quote - Get a random quote\n"
        "!remind <message> - Save a reminder\n"
        "!listreminders - List your reminders\n"
        "!admin - Admin-only command\n"
    )
    await ctx.send(help_text)

os.makedirs('data', exist_ok=True)
conn = sqlite3.connect('data/bot.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    message TEXT
                )''')
conn.commit()

#reminder functions
@bot.command(name='setreminderhere')
async def setreminderhere(ctx):
    logging.info("SetReminderHere command triggered")
    global REMINDER_CHANNEL_ID
    REMINDER_CHANNEL_ID = ctx.message.channel.id
    await ctx.send('Daily reminders will now be sent here.')

@bot.command(name='remind')
async def remind(ctx, *, message: str):
    logging.info("Remind command triggered")
    try:
        cursor.execute('INSERT INTO reminders (user_id, message) VALUES (?, ?)', (str(ctx.author.id), message))
        conn.commit()
        await ctx.send(f'Reminder saved: {message}')
    except Exception as e:
        logging.error(f'Remind command error: {e}')
        await ctx.send('Failed to save reminder.')

@bot.command(name='listreminders')
async def listreminders(ctx):
    logging.info("ListReminders command triggered")
    cursor.execute('SELECT message FROM reminders WHERE user_id = ?', (str(ctx.author.id),))
    reminders = cursor.fetchall()
    if reminders:
        reminder_list = '\n'.join([r[0] for r in reminders])
        await ctx.send(f'Your reminders:\n{reminder_list}')
    else:
        await ctx.send('You have no reminders.')


@bot.command(name='deletereminder', aliases=['DR'])
async def deletereminders(ctx, *, reminder: str):
    user_id = ctx.author.id
    conn = sqlite3.connect('data/bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reminders WHERE user_id = ? AND message = ?')
    changes = cursor.rowcount()
    conn.commit()
    await ctx.send('Reminders deleted.')
    conn.close()
    if changes == 0:
        await ctx.send(f'No reminder named {reminder} found on your account')
    else:
        await ctx.send(f'Reminder {reminder} deleted')

    #daily remind loop
@tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=TZ))
async def reminder_loop():
    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if not channel:
        return

    conn = sqlite3.connect('data/bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, message FROM reminders')
    reminders = cursor.fetchall()
    if not reminders:
        return
    for user_id, message in reminders:
        await channel.send(f'<@{user_id}> reminder: {message}')

#admin Functions
@admin.error
async def admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('You do not have permission to use this command.')

@bot.command(name='admin')
@commands.has_permissions(administrator=True)
async def admin(ctx):
    logging.info("Admin command triggered")
    await ctx.send('Admin command executed.')


# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)
