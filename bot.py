import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN
from database import db
from plugins.start import register_start_handler
from plugins.admin import register_admin_handler


print("""
╔══════════════════════════════════════════════╗
║      🤖 ADVANCED FORWARD BOT                ║
║      ─────────────────────────               ║
║      Powered by Pyrogram + PostgreSQL        ║
╚══════════════════════════════════════════════╝
""")

# ─── Initialize Pyrogram Client ──────────────────────────────────
app = Client(
    name="userbot",
    api_id=9163661678,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ─── Register Handlers ──────────────────────────────────────────
register_start_handler(app)
register_admin_handler(app)


async def main():
    """Main entry point — connect DB and start the bot."""
    # Connect to PostgreSQL
    await db.connect()

    # Start the bot
    print("🚀 Bot is starting...")
    await app.start()

    user = await app.get_me()
    print(f"✅ Bot started as @{user.username} ({user.first_name})")
    print(f"📡 Listening for messages...")
    print(f"─────────────────────────────────────")
    print(f"Admin Commands:")
    print(f"  /setphoto    — Set start photo")
    print(f"  /setwelcome  — Set welcome message")
    print(f"  /setquote    — Set quote message")
    print(f"  /clearphoto  — Remove start photo")
    print(f"  /preview     — Preview start message")
    print(f"─────────────────────────────────────")

    # Keep the bot running
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔴 Bot stopped.")
