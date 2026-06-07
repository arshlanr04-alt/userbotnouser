# 🤖 Advanced Forward Bot

A Telegram bot with a customizable `/start` message — photo, welcome text, and quoted block — all configurable by admins via chat commands.

## ✨ Features

- **Customizable Start Message** — Photo + welcome text + quoted description
- **Admin Panel** — Set photo, welcome message, and quote via commands
- **PostgreSQL Storage** — Settings persist across restarts
- **Inline Buttons** — Home, Help, About, Settings, Status, How to Use
- **User Mention** — Automatically greets users by name with a clickable mention

## 📁 Project Structure

```
telegram-userbot/
├── bot.py              # Main entry point
├── config.py           # Environment config loader
├── database.py         # PostgreSQL handler
├── requirements.txt    # Python dependencies
├── .env.example        # Template for environment variables
└── plugins/
    ├── __init__.py
    ├── start.py        # /start command handler
    └── admin.py        # Admin customization commands
```

## 🚀 Setup

### 1. Prerequisites
- Python 3.10+
- PostgreSQL running locally or remotely

### 2. Create the database
```sql
CREATE DATABASE userbot;
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the bot
```bash
python bot.py
```

## 🔧 Admin Commands

| Command | Description |
|---------|-------------|
| `/setphoto` | Send a photo to set as the start image |
| `/setwelcome` | Set the welcome message text (use `{mention}` for user name) |
| `/setquote` | Set the text inside the quote block |
| `/clearphoto` | Remove the start photo (text-only mode) |
| `/preview` | Preview the current start message |
| `/cancel` | Cancel the current operation |

## 💡 Message Format Variables

In the welcome message, you can use:
- `{mention}` — Replaced with a clickable mention of the user's name

## 📝 Example

**Welcome Message:**
```
✨ HI {mention} WELCOME TO OUR BOT 👋
```

**Quote Message:**
```
🍥 I'M AN ADVANCED FORWARD BOT WITH SPECIAL FEATURES

⚡ CLICK THE BUTTONS BELOW TO EXPLORE MORE
```
