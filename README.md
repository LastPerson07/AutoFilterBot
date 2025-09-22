# 🎬 AutoFilter Telegram Bot

A professional, production-ready Telegram bot built with Python and Pyrogram that provides instant file search capabilities with MongoDB integration.

## ✨ Features

### 🔍 Core Functionality

- **AutoFilter System**: Automatically indexes movies, series, and files from source channels
- **MongoDB Storage**: Efficient database storage with metadata
- **Instant Search**: Lightning-fast file search via inline queries
- **Multiple Filter Types**: Global, Group, and PM filters

### 👑 Admin Controls

- **User Management**: Ban/unban users with database persistence
- **Broadcast System**: Send messages to all users
- **Status Monitoring**: Real-time bot statistics and system info
- **File Indexing**: Automatic file indexing from admin uploads

### 🎯 User Experience

- **Inline Search**: Search files directly from any chat using `@YourBot query`
- **Interactive Buttons**: User-friendly navigation with inline keyboards
- **Welcome Messages**: Customizable welcome messages for new group members
- **Help System**: Comprehensive help and about commands

### 🚀 Technical Excellence

- **Single File Architecture**: Everything in one `bot.py` file
- **Async Performance**: Optimized for high-performance operations
- **Error Handling**: Comprehensive error handling and logging
- **Scalable Design**: Handles 10,000+ member groups efficiently

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB database (local or cloud)
- Telegram Bot Token
- Telegram API credentials

### Quick Setup

1. **Clone or download the bot files**

   ```bash
   # Download bot.py and requirements.txt
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   # Copy the example config
   cp config.env.example .env

   # Edit .env with your credentials
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here
   BOT_TOKEN=your_bot_token_here
   MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/database_name
   OWNER_ID=your_telegram_user_id_here
   ```

4. **Run the bot**

   ```bash
   # Option 1: Direct run
   python bot.py

   # Option 2: Using startup script (recommended)
   python start.py
   ```

## 📋 Environment Variables

| Variable             | Description                            | Required | Default Value  |
| -------------------- | -------------------------------------- | -------- | -------------- |
| `API_ID`             | Telegram API ID from my.telegram.org   | ✅       | 21936466       |
| `API_HASH`           | Telegram API Hash from my.telegram.org | ✅       | 5d89c2123f...  |
| `BOT_TOKEN`          | Bot token from @BotFather              | ✅       | 7552224283...  |
| `MONGO_URI`          | MongoDB connection string              | ✅       | mongodb://...  |
| `DB_NAME`            | MongoDB database name                  | ✅       | AutoFilterBot  |
| `OWNER_ID`           | Your Telegram user ID                  | ✅       | 1634752140     |
| `REQUIRED_CHANNEL`   | Channel ID users must join             | ✅       | -1001557378254 |
| `SOURCE_CHANNEL_IDS` | Source channel IDs for auto-indexing   | ✅       | -1045260710176 |
| `BRANDING_TAG`       | Branding tag for uploaded files        | ✅       | Uploaded By... |

## 🎮 Commands

### User Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show detailed help information
- `/about` - Display bot information and statistics
- `/id` - Get your user ID or replied user's ID

### Admin Commands (Owner Only)

- `/ban <user>` - Ban a user (reply to user)
- `/unban <user>` - Unban a user (reply to user)
- `/broadcast <message>` - Send message to all users (reply to message)
- `/status` - Show bot statistics and system info
- `/send <user_id>` - Send a file to a specific user (reply to file)

### Inline Search

- Use `@YourBot query` in any chat to search files
- Supports partial matching and keywords
- Shows file details including size and type

## 🗄️ Database Schema

### Collections

- **users**: User information and activity tracking
- **files**: File metadata and indexing information
- **banned_users**: Banned user records
- **groups**: Group information and settings
- **settings**: Bot configuration settings

## 🚀 Deployment

### Heroku

1. Create a new Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy using Git or Heroku CLI

### Railway

1. Connect your GitHub repository
2. Set environment variables
3. Deploy automatically

### VPS/Dedicated Server

1. Install Python 3.8+ and pip
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables
4. Run: `python bot.py`

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
```

## 📊 Performance Features

- **Async Operations**: Non-blocking I/O for better performance
- **Database Optimization**: Indexed queries for fast searches
- **Memory Efficient**: Optimized memory usage
- **Rate Limiting**: Built-in flood wait handling
- **Error Recovery**: Graceful error handling and recovery

## 🔒 Security Features

- **User Banning**: Persistent user ban system
- **Admin Verification**: Owner-only admin commands
- **Input Validation**: Safe input handling
- **Error Logging**: Comprehensive error tracking

## 📈 Monitoring

The bot includes built-in monitoring with:

- Real-time uptime tracking
- User and file statistics
- System resource monitoring
- Error logging and tracking

## 🤝 Support

For support and questions:

1. Check the `/help` command in the bot
2. Review the logs for error details
3. Ensure all environment variables are set correctly
4. Verify MongoDB connection

## 📝 License

This project is open source and available under the MIT License.

## 🎯 Production Ready

This bot is designed for production use with:

- ✅ Comprehensive error handling
- ✅ Database optimization
- ✅ Security measures
- ✅ Performance monitoring
- ✅ Scalable architecture
- ✅ Easy deployment

---

**Built with ❤️ using Python, Pyrogram, and MongoDB**

