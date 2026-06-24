import sys
import os
import json
import asyncio
import logging
import random
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Find the active running bot module from sys.modules
main_module = None
for name in ['__main__', 'userbot', 'testuserbot_v3']:
    mod = sys.modules.get(name)
    if mod and hasattr(mod, 'get_dashboard_markup'):
        main_module = mod
        break

if main_module is None:
    try:
        import userbot as main_module
    except ImportError:
        import testuserbot_v3 as main_module

bot = main_module.bot
get_dashboard_markup = main_module.get_dashboard_markup
is_authorized_manager = main_module.is_authorized_manager
set_setting = main_module.set_setting
get_setting = main_module.get_setting
admin_states = main_module.admin_states
userbot_fleet_manager = main_module.userbot_fleet_manager
loop = main_module.loop

# Media folder configuration
MEDIA_DIR = "mailer_media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# In-memory cache for userbot groups to avoid constant API polling
# format: { userbot_id: [ {"id": int, "title": str, "username": str}, ... ] }
userbot_groups_cache = {}

def get_mailer_status():
    selected_ub = get_setting("gm_selected_userbot")
    selected_groups = json.loads(get_setting("gm_selected_group_ids") or "[]")
    msg_data = json.loads(get_setting("gm_message") or "{}")
    
    ub_status = "🔴 None"
    if selected_ub:
        client = userbot_fleet_manager.get_client(int(selected_ub))
        if client and client.is_connected():
            ub_status = f"🟢 Connected (ID: {selected_ub})"
        else:
            ub_status = f"🟡 Offline (ID: {selected_ub})"
            
    msg_status = "🔴 None"
    if msg_data:
        msg_status = f"🟢 Configured ({msg_data.get('type').upper()})"
        
    return (
        f"👤 *Selected Userbot:* {ub_status}\n"
        f"👥 *Groups Selected:* `{len(selected_groups)}` groups marked\n"
        f"💬 *Mailer Message:* {msg_status}"
    )

# Save the original get_dashboard_markup function
original_get_dashboard_markup = get_dashboard_markup

def new_get_dashboard_markup():
    markup = original_get_dashboard_markup()
    markup.add(InlineKeyboardButton("📬 Group Mailer", callback_data="group_mailer_main"))
    return markup

# Monkeypatch the dashboard markup function
main_module.get_dashboard_markup = new_get_dashboard_markup

# Dynamic fetching dialogs function
async def fetch_dialogs_async(client, ub_id):
    groups = []
    async for dialog in client.iter_dialogs(limit=200):
        if dialog.is_group or dialog.is_channel:
            groups.append({
                "id": dialog.id,
                "title": dialog.name,
                "username": dialog.entity.username if hasattr(dialog.entity, 'username') and dialog.entity.username else None
            })
    userbot_groups_cache[ub_id] = groups

# Helper to render the interactive groups page
def show_groups_page(chat_id, message_id, ub_id, page=0):
    groups = userbot_groups_cache.get(ub_id, [])
    selected_ids = set(json.loads(get_setting("gm_selected_group_ids") or "[]"))
    
    if not groups:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="group_mailer_main"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="👥 *Groups:* Userbot is not in any groups or channels yet.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    page_size = 8
    total_pages = (len(groups) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_groups = groups[start_idx:end_idx]
    
    markup = InlineKeyboardMarkup()
    for g in page_groups:
        is_selected = g["id"] in selected_ids
        checkbox = "✅" if is_selected else "⬜"
        title = g["title"][:25]
        markup.add(InlineKeyboardButton(f"{checkbox} {title}", callback_data=f"gm_tgl_{g['id']}_{page}"))
        
    # Navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"gm_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"Page {page+1}/{total_pages}", callback_data="gm_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"gm_page_{page+1}"))
    markup.row(*nav_row)
    
    # Bulk actions row
    markup.row(
        InlineKeyboardButton("Select All", callback_data=f"gm_all_sel_{page}"),
        InlineKeyboardButton("Clear All", callback_data=f"gm_all_clr_{page}")
    )
    
    markup.add(InlineKeyboardButton("🔙 Back to Mailer Console", callback_data="group_mailer_main"))
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"👥 *SELECT TARGET GROUPS* (Selected: `{len(selected_ids)}`)\nToggle the checkboxes below to select targets for the broadcast:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# Register callback query handler
@bot.callback_query_handler(func=lambda call: call.data == "group_mailer_main" or call.data.startswith("gm_"))
def handle_group_mailer_callbacks(call):
    uid = call.from_user.id
    if not is_authorized_manager(uid):
        return

    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    selected_ub = get_setting("gm_selected_userbot")

    if data == "group_mailer_main":
        markup = InlineKeyboardMarkup()
        
        # Row 1: Select Userbot, Select Msg
        markup.row(
            InlineKeyboardButton("👤 Select Userbot", callback_data="gm_select_userbot"),
            InlineKeyboardButton("💬 Select Msg", callback_data="gm_select_msg")
        )
        
        # Row 2: Groups Selector
        markup.row(
            InlineKeyboardButton("👥 Groups", callback_data="gm_groups_list")
        )
        
        # Row 3: Start Operation
        markup.row(
            InlineKeyboardButton("🚀 Start Operation", callback_data="gm_start_op")
        )
        
        # Row 4: Back to Dashboard
        markup.row(
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dash_main")
        )

        status_text = get_mailer_status()
        text = (
            "📬 *GROUP MAILER CONSOLE*\n\n"
            f"{status_text}\n\n"
            "Use the options below to configure and execute your broadcast operation."
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data == "gm_select_userbot":
        clients = userbot_fleet_manager.get_all_clients()
        connected_clients = [c for c in clients if c.is_connected()]
        
        if not connected_clients:
            bot.answer_callback_query(call.id, "❌ No active connected userbots found!")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for client in connected_clients:
            first_name = client._me.first_name if hasattr(client, '_me') and client._me else "Userbot"
            username = f"@{client._me.username}" if hasattr(client, '_me') and client._me and client._me.username else ""
            markup.add(InlineKeyboardButton(f"👤 {first_name} {username}", callback_data=f"gm_set_ub_{client._me.id}"))
        
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="group_mailer_main"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="👤 *Select Userbot to use for broadcast:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("gm_set_ub_"):
        ub_id = data.split("_")[-1]
        set_setting("gm_selected_userbot", ub_id)
        # Clear selected groups when userbot is changed
        set_setting("gm_selected_group_ids", "[]")
        if ub_id in userbot_groups_cache:
            del userbot_groups_cache[ub_id]
            
        bot.answer_callback_query(call.id, "✅ Userbot selected! Target groups reset.")
        
        # Refresh console
        handle_group_mailer_callbacks(type('MockCall', (object,), {'from_user': call.from_user, 'data': 'group_mailer_main', 'message': call.message, 'id': call.id})())

    elif data == "gm_groups_list":
        if not selected_ub:
            bot.answer_callback_query(call.id, "⚠️ Please select a Userbot first!", show_alert=True)
            return

        client = userbot_fleet_manager.get_client(int(selected_ub))
        if not client or not client.is_connected():
            bot.answer_callback_query(call.id, "❌ Selected userbot is offline or disconnected!", show_alert=True)
            return

        bot.answer_callback_query(call.id, "⏳ Loading groups...")
        if selected_ub in userbot_groups_cache:
            show_groups_page(chat_id, message_id, selected_ub, page=0)
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="⏳ *Fetching groups list from userbot. Please wait...*",
                parse_mode="Markdown"
            )
            def on_fetch_done(fut):
                show_groups_page(chat_id, message_id, selected_ub, page=0)
            
            future = asyncio.run_coroutine_threadsafe(fetch_dialogs_async(client, selected_ub), loop)
            future.add_done_callback(on_fetch_done)

    elif data.startswith("gm_page_"):
        page = int(data.split("_")[-1])
        show_groups_page(chat_id, message_id, selected_ub, page)
        bot.answer_callback_query(call.id)

    elif data.startswith("gm_tgl_"):
        parts = data.split("_")
        g_id = int(parts[2])
        page = int(parts[3])
        
        selected_ids = json.loads(get_setting("gm_selected_group_ids") or "[]")
        if g_id in selected_ids:
            selected_ids.remove(g_id)
        else:
            selected_ids.append(g_id)
            
        set_setting("gm_selected_group_ids", json.dumps(selected_ids))
        show_groups_page(chat_id, message_id, selected_ub, page)
        bot.answer_callback_query(call.id)

    elif data.startswith("gm_all_sel_"):
        page = int(data.split("_")[-1])
        groups = userbot_groups_cache.get(selected_ub, [])
        selected_ids = set(json.loads(get_setting("gm_selected_group_ids") or "[]"))
        
        for g in groups:
            selected_ids.add(g["id"])
            
        set_setting("gm_selected_group_ids", json.dumps(list(selected_ids)))
        show_groups_page(chat_id, message_id, selected_ub, page)
        bot.answer_callback_query(call.id, "✅ Selected all groups!")

    elif data.startswith("gm_all_clr_"):
        page = int(data.split("_")[-1])
        set_setting("gm_selected_group_ids", "[]")
        show_groups_page(chat_id, message_id, selected_ub, page)
        bot.answer_callback_query(call.id, "🗑 Cleared all selections!")

    elif data == "gm_select_msg":
        admin_states[uid] = "awaiting_gm_message"
        bot.send_message(
            chat_id,
            "💬 *SET MAILER MESSAGE*\n\n"
            "Please send or forward the message you want to broadcast (can be text, photo, video, or document with captions)."
        )
        bot.answer_callback_query(call.id)

    elif data == "gm_start_op":
        selected_groups = json.loads(get_setting("gm_selected_group_ids") or "[]")
        msg_data = json.loads(get_setting("gm_message") or "{}")

        if not selected_ub:
            bot.answer_callback_query(call.id, "❌ Please select a Userbot first!", show_alert=True)
            return
        if not selected_groups:
            bot.answer_callback_query(call.id, "❌ Please select target groups first!", show_alert=True)
            return
        if not msg_data:
            bot.answer_callback_query(call.id, "❌ Please set the mailer message first!", show_alert=True)
            return

        client = userbot_fleet_manager.get_client(int(selected_ub))
        if not client or not client.is_connected():
            bot.answer_callback_query(call.id, "❌ Selected userbot is offline or disconnected!", show_alert=True)
            return

        bot.answer_callback_query(call.id, "🚀 Starting operation...")
        # Dispatch the task safely to the main event loop thread
        asyncio.run_coroutine_threadsafe(
            run_broadcast(client, selected_groups, msg_data, chat_id),
            loop
        )

# Intercept message state inputs for Group Mailer
@bot.message_handler(func=lambda m: is_authorized_manager(m.from_user.id) and admin_states.get(m.from_user.id) == "awaiting_gm_message")
def handle_mailer_states(message):
    uid = message.from_user.id
    chat_id = message.chat.id

    msg_type = "text"
    file_id = None
    caption = message.caption or ""
    local_path = None

    if message.photo:
        msg_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        msg_type = "video"
        file_id = message.video.file_id
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id

    if file_id:
        try:
            msg_status = bot.reply_to(message, "⏳ Downloading media locally...")
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            ext = file_info.file_path.split(".")[-1]
            local_path = os.path.join(MEDIA_DIR, f"mailer_media_{uid}.{ext}")
            
            with open(local_path, "wb") as f:
                f.write(downloaded_file)
            bot.delete_message(chat_id, msg_status.message_id)
        except Exception as e:
            bot.reply_to(message, f"❌ Media download failed: {e}")
            return

    msg_data = {
        "type": msg_type,
        "text": message.text or "",
        "caption": caption,
        "local_path": local_path
    }
    
    set_setting("gm_message", json.dumps(msg_data))
    admin_states[uid] = None
    bot.reply_to(message, f"✅ *Mailer Message Saved!* (Type: `{msg_type.upper()}`)", parse_mode="Markdown")

# Asynchronous broadcast implementation
async def run_broadcast(client, group_ids, msg_data, chat_id):
    success = 0
    failed = 0
    progress_msg = bot.send_message(chat_id, "⏳ *Mailer progress:* `0%`", parse_mode="Markdown")

    for idx, group_id in enumerate(group_ids):
        try:
            msg_type = msg_data.get("type")
            if msg_type == "text":
                await client.send_message(group_id, msg_data["text"])
            elif msg_type in ["photo", "video", "document"]:
                await client.send_file(group_id, msg_data["local_path"], caption=msg_data.get("caption", ""))
                
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Group Mailer error sending to {group_id}: {e}")

        # Update progress every 5 groups
        if (idx + 1) % 5 == 0 or (idx + 1) == len(group_ids):
            pct = int(((idx + 1) / len(group_ids)) * 100)
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=f"⏳ *Mailer progress:* `{pct}%` (Success: `{success}`, Failed: `{failed}`)",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        # Random delay between 5 to 10 seconds to avoid flooding limits
        delay = random.randint(5, 10)
        await asyncio.sleep(delay)

    bot.send_message(
        chat_id,
        f"✅ *Group Mailer Completed!*\n\n🟢 Success: `{success}`\n🔴 Failed: `{failed}`",
        parse_mode="Markdown"
    )
