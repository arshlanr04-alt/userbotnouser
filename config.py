import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# PostgreSQL Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/userbot")

# Admin user IDs (comma-separated in .env)
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Default start message settings
DEFAULT_START_PHOTO = ""  # URL or file_id
DEFAULT_START_MESSAGE = "✨ HI {mention} WELCOME TO OUR BOT 👋"
DEFAULT_START_QUOTE = "🍥 I'M AN ADVANCED FORWARD BOT WITH SPECIAL FEATURES\n\n⚡ CLICK THE BUTTONS BELOW TO EXPLORE MORE"
