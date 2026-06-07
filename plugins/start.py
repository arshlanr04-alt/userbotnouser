from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from config import ADMIN_IDS
from database import db


def get_start_buttons() -> InlineKeyboardMarkup:
    """Generate the start message inline keyboard buttons."""
    buttons = InlineKeyboardMarkup(
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
    return buttons


def build_start_text(user, welcome_msg: str, quote_msg: str) -> str:
    """
    Build the full start message with user mention and blockquote.

    Uses Telegram's HTML blockquote for the quoted section:
      <blockquote>...</blockquote>
    """
    # Build the user mention
    first_name = user.first_name or "User"
    mention = f'<a href="tg://user?id={user.id}">{first_name}</a>'

    # Replace {mention} placeholder in the welcome message
    formatted_welcome = welcome_msg.replace("{mention}", mention)

    # Build the full message with blockquote
    if quote_msg:
        full_text = f"{formatted_welcome}\n\n<blockquote>{quote_msg}</blockquote>"
    else:
        full_text = formatted_welcome

    return full_text


def register_start_handler(app: Client):
    """Register the /start command handler."""

    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client: Client, message: Message):
        """Handle the /start command — send customizable welcome message."""
        user = message.from_user
        settings = await db.get_start_settings()

        photo_file_id = settings.get("photo_file_id", "")
        welcome_msg = settings.get(
            "welcome_message", "✨ HI {mention} WELCOME TO OUR BOT 👋"
        )
        quote_msg = settings.get(
            "quote_message",
            "🍥 I'M AN ADVANCED FORWARD BOT WITH SPECIAL FEATURES\n\n"
            "⚡ CLICK THE BUTTONS BELOW TO EXPLORE MORE",
        )

        text = build_start_text(user, welcome_msg, quote_msg)
        buttons = get_start_buttons()

        if photo_file_id:
            # Send photo with caption
            await message.reply_photo(
                photo=photo_file_id,
                caption=text,
                reply_markup=buttons,
                parse_mode="html",
            )
        else:
            # Send text-only if no photo is set
            await message.reply_text(
                text=text,
                reply_markup=buttons,
                parse_mode="html",
                disable_web_page_preview=True,
            )

    # ─── Callback handler for buttons (placeholder) ──────────────

    @app.on_callback_query()
    async def handle_callbacks(client, callback_query):
        """Handle inline button presses — placeholder responses."""
        data = callback_query.data

        responses = {
            "home": "🏠 **You're already home!**\n\nUse the buttons to navigate.",
            "help": "📚 **Help Menu**\n\nThis bot helps you forward messages with special features.\n\nUse /start to see the main menu.",
            "about": "ℹ️ **About**\n\nAn advanced forward bot built with ❤️\nPowered by Pyrogram.",
            "settings": "⚙️ **Settings**\n\nSettings panel coming soon!",
            "status": "📊 **Status**\n\n✅ Bot is running\n📡 Connection: Stable",
            "how_to_use": "🔗 **How to Use**\n\n1️⃣ Add me to a group or use in private\n2️⃣ Use the menu buttons to navigate\n3️⃣ Explore the features!",
        }

        answer_text = responses.get(data, "❓ Unknown action.")
        await callback_query.answer(answer_text, show_alert=True)
