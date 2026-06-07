from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    ForceReply,
)
from config import ADMIN_IDS
from database import db


# ─── State tracking for multi-step admin commands ────────────────
# Stores which admin is in what customization state
admin_states = {}

STATES = {
    "WAITING_PHOTO": "waiting_photo",
    "WAITING_WELCOME_MSG": "waiting_welcome_msg",
    "WAITING_QUOTE_MSG": "waiting_quote_msg",
}


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin."""
    return user_id in ADMIN_IDS


def register_admin_handler(app: Client):
    """Register admin customization commands."""

    # ─── /setphoto — Set the start message photo ─────────────────

    @app.on_message(filters.command("setphoto") & filters.private)
    async def set_photo_cmd(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return await message.reply_text("❌ You are not authorized to use this command.")

        admin_states[message.from_user.id] = STATES["WAITING_PHOTO"]
        await message.reply_text(
            "📸 **Send me the photo** you want to set as the start image.\n\n"
            "Send /cancel to cancel.",
            reply_markup=ForceReply(selective=True),
        )

    # ─── /setwelcome — Set the welcome message text ──────────────

    @app.on_message(filters.command("setwelcome") & filters.private)
    async def set_welcome_cmd(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return await message.reply_text("❌ You are not authorized to use this command.")

        # Check if the message itself contains the text
        if len(message.command) > 1:
            # Inline usage: /setwelcome ✨ HI {mention} WELCOME TO OUR BOT 👋
            new_msg = message.text.split(None, 1)[1]
            await db.set_welcome_message(new_msg)
            await message.reply_text(
                f"✅ **Welcome message updated!**\n\n"
                f"New message:\n{new_msg}\n\n"
                f"💡 Use `{{mention}}` to insert the user's name.",
                parse_mode="html",
            )
        else:
            admin_states[message.from_user.id] = STATES["WAITING_WELCOME_MSG"]
            await message.reply_text(
                "✏️ **Send me the new welcome message.**\n\n"
                "Use `{mention}` where you want the user's name.\n"
                "Example: `✨ HI {mention} WELCOME TO OUR BOT 👋`\n\n"
                "Send /cancel to cancel.",
                reply_markup=ForceReply(selective=True),
            )

    # ─── /setquote — Set the quoted message text ─────────────────

    @app.on_message(filters.command("setquote") & filters.private)
    async def set_quote_cmd(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return await message.reply_text("❌ You are not authorized to use this command.")

        if len(message.command) > 1:
            new_quote = message.text.split(None, 1)[1]
            await db.set_quote_message(new_quote)
            await message.reply_text(
                f"✅ **Quote message updated!**\n\n"
                f"New quote:\n<blockquote>{new_quote}</blockquote>",
                parse_mode="html",
            )
        else:
            admin_states[message.from_user.id] = STATES["WAITING_QUOTE_MSG"]
            await message.reply_text(
                "💬 **Send me the new quote message.**\n\n"
                "This will appear inside the quote block (「  」) in the start message.\n\n"
                "Send /cancel to cancel.",
                reply_markup=ForceReply(selective=True),
            )

    # ─── /clearphoto — Remove the start photo ────────────────────

    @app.on_message(filters.command("clearphoto") & filters.private)
    async def clear_photo_cmd(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return await message.reply_text("❌ You are not authorized to use this command.")

        await db.clear_start_photo()
        await message.reply_text("✅ **Start photo cleared!** The start message will now be text-only.")

    # ─── /preview — Preview the current start message ────────────

    @app.on_message(filters.command("preview") & filters.private)
    async def preview_cmd(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            return await message.reply_text("❌ You are not authorized to use this command.")

        from plugins.start import build_start_text, get_start_buttons

        settings = await db.get_start_settings()
        text = build_start_text(
            message.from_user,
            settings.get("welcome_message", ""),
            settings.get("quote_message", ""),
        )
        buttons = get_start_buttons()
        photo = settings.get("photo_file_id", "")

        if photo:
            await message.reply_photo(
                photo=photo,
                caption=f"👁️ **PREVIEW:**\n\n{text}",
                reply_markup=buttons,
                parse_mode="html",
            )
        else:
            await message.reply_text(
                text=f"👁️ **PREVIEW:**\n\n{text}",
                reply_markup=buttons,
                parse_mode="html",
            )

    # ─── /cancel — Cancel current admin operation ────────────────

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in admin_states:
            del admin_states[user_id]
            await message.reply_text("❌ **Cancelled.** No changes were made.")
        else:
            await message.reply_text("🤷 Nothing to cancel.")

    # ─── State handler — Process admin inputs ────────────────────

    @app.on_message(filters.private & ~filters.command(["start", "setphoto", "setwelcome", "setquote", "clearphoto", "preview", "cancel"]))
    async def handle_admin_state(client: Client, message: Message):
        """Handle follow-up messages when admin is in a customization state."""
        user_id = message.from_user.id

        if user_id not in admin_states:
            return  # Not in any state, ignore

        if not is_admin(user_id):
            return

        state = admin_states[user_id]

        # ── Handle photo upload ──────────────────────────────────
        if state == STATES["WAITING_PHOTO"]:
            if message.photo:
                file_id = message.photo.file_id
                await db.set_start_photo(file_id)
                del admin_states[user_id]
                await message.reply_text(
                    "✅ **Start photo updated!**\n\n"
                    "Use /preview to see the result."
                )
            else:
                await message.reply_text("❌ Please send a **photo**, not text. Try again or /cancel.")
            return

        # ── Handle welcome message text ──────────────────────────
        if state == STATES["WAITING_WELCOME_MSG"]:
            if message.text:
                await db.set_welcome_message(message.text)
                del admin_states[user_id]
                await message.reply_text(
                    f"✅ **Welcome message updated!**\n\n"
                    f"New message:\n{message.text}\n\n"
                    f"Use /preview to see the result."
                )
            else:
                await message.reply_text("❌ Please send a **text message**. Try again or /cancel.")
            return

        # ── Handle quote message text ────────────────────────────
        if state == STATES["WAITING_QUOTE_MSG"]:
            if message.text:
                await db.set_quote_message(message.text)
                del admin_states[user_id]
                await message.reply_text(
                    f"✅ **Quote message updated!**\n\n"
                    f"New quote:\n<blockquote>{message.text}</blockquote>\n\n"
                    f"Use /preview to see the result.",
                    parse_mode="html",
                )
            else:
                await message.reply_text("❌ Please send a **text message**. Try again or /cancel.")
            return
