import sys
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# Find the active running bot module from sys.modules to prevent circular imports/double execution
main_module = None
for name in ['__main__', 'userbot', 'testuserbot_v3']:
    mod = sys.modules.get(name)
    if mod and hasattr(mod, 'get_dashboard_markup'):
        main_module = mod
        break

if main_module is None:
    # Fallback to standard import if not loaded as a script main
    try:
        import userbot as main_module
    except ImportError:
        import testuserbot_v3 as main_module

bot = main_module.bot
get_dashboard_markup = main_module.get_dashboard_markup
is_authorized_manager = main_module.is_authorized_manager

# Save the original get_dashboard_markup function
original_get_dashboard_markup = get_dashboard_markup

def new_get_dashboard_markup():
    markup = original_get_dashboard_markup()
    # Add the "📬 Group Mailer" button to the dashboard
    markup.add(InlineKeyboardButton("📬 Group Mailer", callback_data="group_mailer_main"))
    return markup

# Monkeypatch the dashboard markup function in the correct main module instance
main_module.get_dashboard_markup = new_get_dashboard_markup

# Register callback query handler
@bot.callback_query_handler(func=lambda call: call.data == "group_mailer_main" or call.data.startswith("gm_"))
def handle_group_mailer_callbacks(call):
    uid = call.from_user.id
    if not is_authorized_manager(uid):
        return

    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if data == "group_mailer_main":
        markup = InlineKeyboardMarkup()
        
        markup.row(
            InlineKeyboardButton("👤 Select Userbot", callback_data="gm_select_userbot"),
        )
        
        # Row 1: Select Userbot, Import, Export Group (Horizontally aligned)
        markup.row(
            InlineKeyboardButton("📥 Import", callback_data="gm_import"),
            InlineKeyboardButton("📤 Export Group", callback_data="gm_export")
        )
        
        # Row 2: Select Msg, Groups (Horizontally aligned)
        markup.row(
            InlineKeyboardButton("💬 Select Msg", callback_data="gm_select_msg"),
            InlineKeyboardButton("👥 Groups", callback_data="gm_select_groups")
        )
        
        # Row 3: Start Operation (Vertically aligned)
        markup.row(
            InlineKeyboardButton("🚀 Start Operation", callback_data="gm_start_op")
        )
        
        # Row 4: Back to Dashboard
        markup.row(
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dash_main")
        )

        text = (
            "📬 *GROUP MAILER CONSOLE*\n\n"
            "Welcome to the Group Mailer extension!\n"
            "Use the options below to configure your userbot, import/export groups, select your message, and initiate the broadcast operation."
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    elif data.startswith("gm_"):
        bot.answer_callback_query(call.id, "Placeholder: Feature coming soon!")
