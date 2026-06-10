#!/usr/bin/env python3
"""
Telegram Bot Group Admin Tracker & Remote Administrator
A premium, highly-robust solution to track all groups where your bot is an administrator,
and allow the bot owner to manage those groups remotely via private messages.

Features:
1. Real-time tracking of promotion/demotion/membership updates via @bot.my_chat_member_handler.
2. Auto-discovery fallback: Auto-registers pre-existing groups when a message is sent.
3. Thread-safe SQLite persistence layer.
4. Beautiful, secure, admin-only HTML-formatted group list with Inline Keyboard menus.
5. Remote Administration: Get invite links, remote kick, and remote promote from private chats.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
import telebot
from telebot import types

# ---------------------------------------------------------
# 1. SETUP LOGGING
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("GroupTracker")

# ---------------------------------------------------------
# 2. CONFIGURATION
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Replace 0 with your actual Telegram User ID (e.g., 12345678)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "groups_tracker.db")

if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or ADMIN_ID == 0:
    logger.warning("⚠️ Please configure your BOT_TOKEN and ADMIN_ID at the top of the script or set them as environment variables!")

# ---------------------------------------------------------
# 3. DATABASE PERSISTENCE LAYER (SQLite)
# ---------------------------------------------------------
def get_db_connection():
    """Returns a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracked_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT NOT NULL,
                chat_username TEXT,
                chat_type TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("sqlite3: Database initialized successfully.")

def save_or_update_chat(chat_id, title, username, chat_type, is_admin):
    """Inserts or updates a group record in the database."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO tracked_chats (chat_id, chat_title, chat_username, chat_type, is_admin, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                chat_title = excluded.chat_title,
                chat_username = excluded.chat_username,
                chat_type = excluded.chat_type,
                is_admin = excluded.is_admin,
                updated_at = excluded.updated_at
        """, (chat_id, title, username, chat_type, int(is_admin), now_str))
        conn.commit()
    status_label = "ADMIN" if is_admin else "MEMBER"
    logger.info(f"DB Update: Saved chat '{title}' ({chat_id}) as {status_label}")

def remove_chat(chat_id):
    """Removes a chat from the database (e.g. when kicked or bot leaves)."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM tracked_chats WHERE chat_id = ?", (chat_id,))
        conn.commit()
    logger.info(f"DB Update: Removed chat ID {chat_id} from database.")

def is_chat_tracked(chat_id):
    """Checks if a chat is already in our tracker database."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT 1 FROM tracked_chats WHERE chat_id = ?", (chat_id,)).fetchone()
        return row is not None

def get_admin_chats():
    """Retrieves all tracked chats where the bot is an admin."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT chat_id, chat_title, chat_username, chat_type, updated_at FROM tracked_chats WHERE is_admin = 1 ORDER BY chat_title ASC"
        )
        return [dict(row) for row in cursor.fetchall()]

def get_chat_by_id(chat_id):
    """Retrieves a single chat by its ID."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM tracked_chats WHERE chat_id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None

# ---------------------------------------------------------
# 4. INITIALIZE TELEGRAM BOT
# ---------------------------------------------------------
init_db()

# Bypass any environment-level proxy that might be broken/misconfigured
telebot.apihelper.proxy = {}

if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or ":" not in BOT_TOKEN:
    logger.critical("❌ Invalid or missing BOT_TOKEN! Please configure your BOT_TOKEN at the top of the script or set it as an environment variable (e.g., BOT_TOKEN=123456:ABC-def...).")
    sys.exit(1)

if ADMIN_ID == 0:
    logger.critical("❌ Invalid or missing ADMIN_ID! Please configure your ADMIN_ID at the top of the script or set it as an environment variable (e.g., ADMIN_ID=123456789).")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Verify connectivity before launching the polling thread
try:
    me = bot.get_me()
    logger.info(f"✅ Connection successful! Authenticated as: @{me.username} ({me.first_name})")
except Exception as e:
    logger.critical(f"❌ Connection failed: {e}")
    logger.critical("Could not reach Telegram API. Verify that your server has direct internet access to api.telegram.org.")


# ---------------------------------------------------------
# 5. UI LAYOUT HELPERS (INLINE KEYBOARDS)
# ---------------------------------------------------------
def make_groups_list_keyboard(admin_chats):
    """Generates the main list inline keyboard."""
    markup = types.InlineKeyboardMarkup()
    for chat in admin_chats:
        emoji = "👥" if chat['chat_type'] in ['group', 'supergroup'] else "📢"
        btn = types.InlineKeyboardButton(
            text=f"{emoji} {chat['chat_title']}",
            callback_data=f"manage:{chat['chat_id']}"
        )
        markup.add(btn)
    return markup

def make_group_control_keyboard(chat_id):
    """Generates the group control panel inline keyboard."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_invite = types.InlineKeyboardButton("🔗 Invite Link", callback_data=f"invite:{chat_id}")
    btn_promote = types.InlineKeyboardButton("👑 Promote", callback_data=f"h_promote:{chat_id}")
    btn_kick = types.InlineKeyboardButton("🚫 Kick Member", callback_data=f"h_kick:{chat_id}")
    btn_back = types.InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_list")
    
    markup.add(btn_invite)
    markup.add(btn_promote, btn_kick)
    markup.add(btn_back)
    return markup

def make_back_to_group_keyboard(chat_id):
    """Generates a simple 'Back to group panel' inline keyboard."""
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Back to Menu", callback_data=f"manage:{chat_id}")
    markup.add(btn_back)
    return markup

# ---------------------------------------------------------
# 6. COMMAND HANDLERS
# ---------------------------------------------------------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Welcome and status check handler."""
    user_id = message.from_user.id
    is_user_admin = (user_id == ADMIN_ID)
    
    welcome_text = (
        "🤖 <b>Welcome to Group Admin Tracker & Control Center!</b>\n\n"
        "This bot tracks groups and channels where it is an Administrator, "
        "allowing the Bot Owner to manage them remotely from this private chat.\n\n"
    )
    
    if is_user_admin:
        welcome_text += (
            "👑 <b>Admin Controls:</b>\n"
            "• Use /mygroups to view interactive control panels for all groups.\n"
            "• Promote members to admins using: <code>/promote &lt;group_id&gt; &lt;user_id&gt;</code>\n"
            "• Kick members using: <code>/kick &lt;group_id&gt; &lt;user_id&gt;</code>\n"
            "• Add this bot to any group as an admin to register it instantly!"
        )
    else:
        welcome_text += (
            "👥 <b>For Users:</b>\n"
            "Add this bot to your group and promote it to Admin to let it assist you."
        )
        
    bot.reply_to(message, welcome_text, parse_mode="HTML")


@bot.message_handler(commands=['addgroup'])
def manually_add_group(message):
    """Admin-only command to manually track a group by ID."""
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> Restricted to the Bot Owner.", parse_mode="HTML")
        return
        
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ <b>Usage:</b> <code>/addgroup &lt;group_id&gt;</code>\n\n<i>Note: Group IDs usually start with -100 (e.g. -1001234567890).</i>", parse_mode="HTML")
        return
        
    try:
        chat_id = int(args[1])
        
        # Fetch group details from Telegram API
        chat = bot.get_chat(chat_id)
        
        # Check bot's status in this group
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        is_admin = bot_member.status in ['administrator', 'creator']
        
        save_or_update_chat(
            chat_id=chat_id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            is_admin=is_admin
        )
        
        status_label = "an <b>Administrator</b>" if is_admin else "a <b>Regular Member</b>"
        bot.reply_to(
            message, 
            f"✅ <b>Successfully Linked Group!</b>\n\n"
            f"• <b>Title:</b> {chat.title}\n"
            f"• <b>ID:</b> <code>{chat_id}</code>\n"
            f"• <b>Status:</b> {status_label}",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.reply_to(
            message, 
            f"❌ <b>Failed to link group:</b>\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Make sure the ID is correct and the bot is already a member of that group!</i>",
            parse_mode="HTML"
        )


@bot.message_handler(commands=['mygroups'])
def list_groups(message):
    """Admin-only command to list all groups using the premium interactive panel."""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> This command is restricted to the Bot Owner.", parse_mode="HTML")
        return
        
    admin_chats = get_admin_chats()
    
    if not admin_chats:
        no_groups_text = (
            "📋 <b>Bot Admin Groups</b>\n"
            "───────────────────\n"
            "<i>No groups or channels have been registered yet.</i>\n\n"
            "💡 <b>How to start:</b>\n"
            "1. Add the bot to a group or channel.\n"
            "2. Promote it to <b>Administrator</b>.\n"
            "3. Use /mygroups here to see it list!"
        )
        bot.send_message(message.chat.id, no_groups_text, parse_mode="HTML")
        return
        
    response = (
        "📋 <b>Group Management Panel ({count})</b>\n"
        "───────────────────\n"
        "Select an active group below to open its remote management dashboard:"
    ).format(count=len(admin_chats))
    
    markup = make_groups_list_keyboard(admin_chats)
    bot.send_message(message.chat.id, response, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=['kick'])
def remote_kick(message):
    """Remote kick command: /kick <chat_id> <user_id>"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> Restricted to the Bot Owner.", parse_mode="HTML")
        return
        
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ <b>Usage:</b> <code>/kick &lt;group_id&gt; &lt;user_id&gt;</code>", parse_mode="HTML")
        return
        
    try:
        chat_id = int(args[1])
        user_id = int(args[2])
        
        # Ban the user
        bot.ban_chat_member(chat_id, user_id)
        # Immediately unban so they can rejoin if invited later (Standard Kick)
        bot.unban_chat_member(chat_id, user_id)
        
        bot.reply_to(message, f"✅ Successfully kicked user <code>{user_id}</code> from group <code>{chat_id}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error performing kick:</b>\n<code>{str(e)}</code>", parse_mode="HTML")


@bot.message_handler(commands=['promote'])
def remote_promote(message):
    """Remote promote command: /promote <chat_id> <user_id>"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ <b>Access Denied:</b> Restricted to the Bot Owner.", parse_mode="HTML")
        return
        
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ <b>Usage:</b> <code>/promote &lt;group_id&gt; &lt;user_id&gt;</code>", parse_mode="HTML")
        return
        
    try:
        chat_id = int(args[1])
        user_id = int(args[2])
        
        bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=True,
            can_change_info=True,
            can_post_messages=True, # For channels
            can_edit_messages=True, # For channels
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_manage_topics=True,
            can_promote_members=True
        )
        bot.reply_to(message, f"👑 Successfully promoted user <code>{user_id}</code> to Administrator in group <code>{chat_id}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error performing promotion:</b>\n<code>{str(e)}</code>", parse_mode="HTML")


@bot.message_handler(commands=['syncgroup'])
def manual_sync_group(message):
    """Allows manual synchronization of the current group's admin status."""
    chat = message.chat
    if chat.type in ['private']:
        bot.reply_to(message, "❌ This command must be run inside a Group or Channel.")
        return
        
    try:
        bot_self = bot.get_chat_member(chat.id, bot.get_me().id)
        is_admin = bot_self.status in ['administrator', 'creator']
        save_or_update_chat(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            is_admin=is_admin
        )
        status_text = "an <b>Administrator</b>" if is_admin else "a <b>Regular Member</b>"
        bot.reply_to(message, f"✅ Sync complete! Tracked as {status_text}.", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        bot.reply_to(message, f"❌ Failed to sync chat: {e}")

# ---------------------------------------------------------
# 7. CALLBACK QUERY HANDLERS (INLINE BUTTON ROUTER)
# ---------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_menu_callbacks(call):
    """Handles transitions inside the inline management dashboards."""
    user_id = call.from_user.id
    
    # 1. Security Check
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Access Denied: Admin Only", show_alert=True)
        return
        
    data = call.data
    
    # --- Back to Main Group List ---
    if data == "back_to_list":
        admin_chats = get_admin_chats()
        if not admin_chats:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="<i>No active admin groups are registered.</i>",
                parse_mode="HTML"
            )
            return
            
        markup = make_groups_list_keyboard(admin_chats)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📋 <b>Group Management Panel ({len(admin_chats)})</b>\n───────────────────\nSelect an active group below to open its remote management dashboard:",
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        
    # --- View Group Control Dashboard ---
    elif data.startswith("manage:"):
        chat_id = int(data.split(":")[1])
        chat = get_chat_by_id(chat_id)
        
        if not chat:
            bot.answer_callback_query(call.id, "❌ Error: Group not found in DB", show_alert=True)
            return
            
        emoji = "👥" if chat['chat_type'] in ['group', 'supergroup'] else "📢"
        group_title = f"<a href='t.me/{chat['chat_username']}'>{chat['chat_title']}</a>" if chat['chat_username'] else f"<b>{chat['chat_title']}</b> (Private)"
        
        menu_text = (
            f"⚙️ <b>Dashboard:</b> {emoji} {group_title}\n"
            f"───────────────────\n"
            f"• <b>Group ID:</b> <code>{chat['chat_id']}</code>\n"
            f"• <b>Type:</b> <code>{chat['chat_type'].capitalize()}</code>\n"
            f"• <b>Last Active Sync:</b> <code>{chat['updated_at']}</code>\n\n"
            f"Select an administrative command below to execute remotely:"
        )
        
        markup = make_group_control_keyboard(chat_id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=menu_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    # --- Generate Invite Link ---
    elif data.startswith("invite:"):
        chat_id = int(data.split(":")[1])
        bot.answer_callback_query(call.id, "⏳ Generating Link...")
        
        try:
            # Create a premium invite link that is single-use and has a 24 hour expiry
            invite = bot.create_chat_invite_link(
                chat_id=chat_id,
                expire_date=int(datetime.now().timestamp() + 86400),
                member_limit=1
            )
            
            success_text = (
                f"🔗 <b>Invite Link Generated Successfully!</b>\n\n"
                f"📎 <b>Link:</b> {invite.invite_link}\n\n"
                f"<i>⚠️ This is a secure, single-use link expiring in 24 hours.</i>"
            )
            
            markup = make_back_to_group_keyboard(chat_id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=success_text,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            error_text = f"❌ <b>Failed to generate invite link:</b>\n<code>{str(e)}</code>"
            markup = make_back_to_group_keyboard(chat_id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=error_text,
                parse_mode="HTML",
                reply_markup=markup
            )

    # --- Remote Promote Guide ---
    elif data.startswith("h_promote:"):
        chat_id = int(data.split(":")[1])
        promote_text = (
            f"👑 <b>Remote Promotion Helper</b>\n"
            f"───────────────────\n"
            f"To promote a user to administrator in this group (with full rights, including the ability to add other administrators), copy and send the following command in this chat:\n\n"
            f"<code>/promote {chat_id} USER_ID</code>\n\n"
            f"<i>💡 Replace <code>USER_ID</code> with the numerical Telegram User ID of the member you want to promote.</i>"
        )
        markup = make_back_to_group_keyboard(chat_id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=promote_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    # --- Remote Kick Guide ---
    elif data.startswith("h_kick:"):
        chat_id = int(data.split(":")[1])
        kick_text = (
            f"🚫 <b>Remote Kick Helper</b>\n"
            f"───────────────────\n"
            f"To ban and kick a user from this group, copy and send the following command in this chat:\n\n"
            f"<code>/kick {chat_id} USER_ID</code>\n\n"
            f"<i>💡 Replace <code>USER_ID</code> with the numerical Telegram User ID of the member you want to kick.</i>"
        )
        markup = make_back_to_group_keyboard(chat_id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=kick_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

# ---------------------------------------------------------
# 8. SYSTEM STATUS & AUTO-DISCOVERY HANDLERS
# ---------------------------------------------------------
@bot.my_chat_member_handler()
def handle_chat_member_updates(event: types.ChatMemberUpdated):
    """
    Listens to changes in the bot's membership status.
    Triggered when bot is added, promoted, demoted, or kicked.
    """
    chat = event.chat
    new_status = event.new_chat_member.status
    
    logger.info(f"Status update received for chat '{chat.title}' ({chat.id}): {new_status}")
    
    if new_status in ['administrator', 'creator']:
        save_or_update_chat(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            is_admin=True
        )
    elif new_status in ['member', 'restricted']:
        save_or_update_chat(
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
            chat_type=chat.type,
            is_admin=False
        )
    elif new_status in ['left', 'kicked']:
        remove_chat(chat.id)


@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def auto_discover_groups(message):
    """
    Auto-discovery Fallback:
    Finds and syncs pre-existing groups where the bot is active.
    """
    chat = message.chat
    if not is_chat_tracked(chat.id):
        logger.info(f"🔍 Auto-discovery: Found message in untracked chat '{chat.title}' ({chat.id}). Syncing...")
        try:
            bot_self = bot.get_chat_member(chat.id, bot.get_me().id)
            is_admin = bot_self.status in ['administrator', 'creator']
            save_or_update_chat(
                chat_id=chat.id,
                title=chat.title,
                username=chat.username,
                chat_type=chat.type,
                is_admin=is_admin
            )
        except Exception as e:
            logger.error(f"Failed to auto-discover status for chat {chat.id}: {e}")

# ---------------------------------------------------------
# 9. RUN THE BOT
# ---------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Group Tracker Bot with Remote Admin Console...")
    try:
        # We explicitly request both message and my_chat_member updates to guarantee we receive status change events
        bot.infinity_polling(allowed_updates=['message', 'my_chat_member', 'callback_query'])
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly.")
        sys.exit(0)
