from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from userbot import bot, get_dashboard_markup, is_authorized_manager
import userbot

# Save the original get_dashboard_markup function
original_get_dashboard_markup = get_dashboard_markup

def new_get_dashboard_markup():
    markup = original_get_dashboard_markup()
    # Add the "📬 Group Mailer" button to the dashboard
    markup.add(InlineKeyboardButton("📬 Group Mailer", callback_data="group_mailer_main"))
    return markup

# Monkeypatch the dashboard markup function in testuserbot_v3
testuserbot_v3.get_dashboard_markup = new_get_dashboard_markup

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
        
        # Row 1: Select Userbot, Import, Export Group (Horizontally aligned)
        markup.row(
            InlineKeyboardButton("👤 Select Userbot", callback_data="gm_select_userbot"),
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
