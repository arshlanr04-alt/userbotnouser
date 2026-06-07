import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ─── Read credentials from environment variables ──────────────
# API_ID = int(os.environ.get("API_ID", 0))
# API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# app = Client(
#     name="userbot",
#     api_id=API_ID,
#     api_hash=API_HASH,
#     bot_token=BOT_TOKEN,
# )

# ─── Start Photo (file_id — admin can change later) ───────────
START_PHOTO = ""  # leave empty for now, set file_id after first upload

# ─── Start Message & Quote ────────────────────────────────────
START_MESSAGE = "✨ <b>HI {mention} WELCOME TO OUR BOT</b> 👋"

START_QUOTE = (
    "🍥 <b>I'M AN ADVANCED FORWARD BOT "
    "WITH SPECIAL FEATURES</b>\n\n"
    "⚡ <b>CLICK THE BUTTONS BELOW TO "
    "EXPLORE MORE</b>"
)

# ─── Inline Buttons Layout (matching the screenshot) ──────────
START_BUTTONS = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🏠 Home", callback_data="home"),
        ],
        [
            InlineKeyboardButton("📚 Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("📊 Status", callback_data="status"),
        ],
        [
            InlineKeyboardButton("🔗 How to Use", callback_data="how_to_use"),
        ],
    ]
)


# ─── /start Command ──────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user = message.from_user
    first_name = user.first_name or "User"
    mention = f'<a href="tg://user?id={user.id}">{first_name}</a>'

    # Build the full message: welcome + quoted block
    text = START_MESSAGE.replace("{mention}", mention)
    text += f"\n\n<blockquote>{START_QUOTE}</blockquote>"

    if START_PHOTO:
        await message.reply_photo(
            photo=START_PHOTO,
            caption=text,
            reply_markup=START_BUTTONS,
            parse_mode="html",
        )
    else:
        await message.reply_text(
            text=text,
            reply_markup=START_BUTTONS,
            parse_mode="html",
            disable_web_page_preview=True,
        )


# ─── Button Clicks (placeholder) ─────────────────────────────
@app.on_callback_query()
async def button_handler(client, callback_query):
    await callback_query.answer("🔜 Coming soon!", show_alert=True)


# ─── Run ──────────────────────────────────────────────────────
print("🤖 Bot starting...")
app.run()
