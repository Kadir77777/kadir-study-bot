import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

ZENQUOTES_URL = "https://zenquotes.io/api/random"
QUOTE_MAX_TRIES = int(os.getenv("QUOTE_MAX_TRIES", "2"))
QUOTE_BACKOFF_SECONDS = float(os.getenv("QUOTE_BACKOFF_SECONDS", "1.0"))
QUOTE_TIMEOUT_SECONDS = float(os.getenv("QUOTE_TIMEOUT_SECONDS", "10.0"))

LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
FLASHCARDS_DIR = os.getenv("FLASHCARDS_DIR", "data/flashcards")
LOCAL_QUOTES_FILE = os.getenv("LOCAL_QUOTES_FILE", "data/quotes.json")
