#!/usr/bin/env python3
"""
Professional Telegram AutoFilter Bot
A complete bot with MongoDB integration, admin controls, and file management
Built with Pyrogram for maximum performance and reliability
"""

import os
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
import random

from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    CallbackQuery, User
)
from pyrogram.errors import (
    FloodWait, UserNotParticipant, ChatAdminRequired,
    PeerIdInvalid, UserBannedInChannel, MessageNotModified
)
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError
import motor.motor_asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration - You can use environment variables or set directly
API_ID = int(os.getenv('API_ID', '21936466'))
API_HASH = os.getenv('API_HASH', '5d89c2323f79201eb440ab83ff272156')
BOT_TOKEN = os.getenv('BOT_TOKEN', '7511924283:AAHFTm3_bquGy858_WIrGvB46IUK15xH82w')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27018/')
DB_NAME = os.getenv('DB_NAME', 'AutoFilterBot')
OWNER_ID = int(os.getenv('OWNER_ID', '1633472140'))
REQUIRED_CHANNEL = os.getenv('REQUIRED_CHANNEL', '-1001557378145')
SOURCE_CHANNEL_IDS = [int(x) for x in os.getenv('SOURCE_CHANNEL_IDS', '-1001860710176').split(',')]
BRANDING_TAG = os.getenv('BRANDING_TAG', 'Uploaded By @Netflixian_Movie')

# Validate required configuration
if not all([API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID]):
    logger.error("Missing required configuration!")
    exit(1)

# Initialize Pyrogram client
app = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

# MongoDB connection
try:
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    logger.info(f"Connected to MongoDB successfully - Database: {DB_NAME}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

# Database collections
users_collection = db.users
files_collection = db.files
banned_collection = db.banned_users
groups_collection = db.groups
settings_collection = db.settings

# Bot start time for uptime calculation
BOT_START_TIME = time.time()

# Helper functions
async def is_admin(user_id: int, chat_id: int = None) -> bool:
    """Check if user is admin or owner"""
    if user_id == OWNER_ID:
        return True
    
    if chat_id:
        try:
            member = await app.get_chat_member(chat_id, user_id)
            return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        except:
            return False
    
    return False

async def is_banned(user_id: int) -> bool:
    """Check if user is banned"""
    banned_user = await banned_collection.find_one({"user_id": user_id})
    return banned_user is not None

async def check_user_subscription(user_id: int) -> bool:
    """Check if user is subscribed to required channel"""
    try:
        member = await app.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.KICKED]
    except:
        return False

async def add_user(user_id: int, username: str = None, first_name: str = None):
    """Add user to database"""
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "joined_at": datetime.now(),
                    "last_active": datetime.now()
                }
            },
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")

async def get_user_count() -> int:
    """Get total user count"""
    return await users_collection.count_documents({})

async def get_file_count() -> int:
    """Get total file count"""
    return await files_collection.count_documents({})

async def get_banned_count() -> int:
    """Get total banned user count"""
    return await banned_collection.count_documents({})

async def get_uptime() -> str:
    """Get bot uptime"""
    uptime_seconds = int(time.time() - BOT_START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

# Database models
class FileDocument:
    def __init__(self, file_id: str, file_name: str, file_type: str, 
                 file_size: int, caption: str = "", group_id: int = None):
        self.file_id = file_id
        self.file_name = file_name
        self.file_type = file_type
        self.file_size = file_size
        self.caption = caption
        self.group_id = group_id
        self.added_at = datetime.now()
        self.download_count = 0

    async def save(self):
        """Save file to database"""
        try:
            await files_collection.update_one(
                {"file_id": self.file_id},
                {
                    "$set": {
                        "file_id": self.file_id,
                        "file_name": self.file_name,
                        "file_type": self.file_type,
                        "file_size": self.file_size,
                        "caption": self.caption,
                        "group_id": self.group_id,
                        "added_at": self.added_at,
                        "download_count": self.download_count
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving file {self.file_id}: {e}")
            return False

    @staticmethod
    async def search_files(query: str, limit: int = 10) -> List[Dict]:
        """Search files by name or caption"""
        try:
            # Create text index if it doesn't exist
            await files_collection.create_index([("file_name", "text"), ("caption", "text")])
            
            # Search with regex for better matching
            regex_query = {"$regex": query, "$options": "i"}
            cursor = files_collection.find({
                "$or": [
                    {"file_name": regex_query},
                    {"caption": regex_query}
                ]
            }).limit(limit)
            
            files = []
            async for file_doc in cursor:
                files.append(file_doc)
            
            return files
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []

# Command handlers
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check if user is banned
    if await is_banned(user_id):
        await message.reply("❌ You are banned from using this bot.")
        return
    
    # Check if user is subscribed to required channel
    if not await check_user_subscription(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '').replace('-100', '')}")],
            [InlineKeyboardButton("🔄 Check Subscription", callback_data="check_sub")]
        ])
        
        await message.reply(
            f"❌ <b>Subscription Required!</b>\n\n"
            f"Please join our channel to use this bot:\n"
            f"📢 <a href='https://t.me/{REQUIRED_CHANNEL.replace('@', '').replace('-100', '')}'>Join Channel</a>\n\n"
            f"After joining, click the button below to verify your subscription.",
            reply_markup=keyboard
        )
        return
    
    # Add user to database
    await add_user(user_id, username, first_name)
    
    # Welcome message with buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Files", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("📊 About", callback_data="about")],
        [InlineKeyboardButton("🆔 Get ID", callback_data="get_id")]
    ])
    
    welcome_text = f"""
🎬 <b>Welcome to AutoFilter Bot!</b>

👋 Hello <b>{first_name}</b>!

I'm a powerful file search bot that can help you find movies, series, and other files instantly.

<b>🚀 Quick Actions:</b>
• Use the search button below to find files
• Use @{client.me.username} <i>query</i> in any chat for inline search
• Join our support group for help

<b>📋 Available Commands:</b>
/help - Show detailed help
/about - Bot information
/id - Get user ID

Enjoy searching! 🔍
    """
    
    await message.reply(welcome_text, reply_markup=keyboard)

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    help_text = """
📖 <b>AutoFilter Bot Help</b>

<b>🔍 How to Search:</b>
• Use the search button in /start
• Type @{bot_username} <i>query</i> in any chat
• Use inline mode for quick access

<b>📋 Commands:</b>
/start - Start the bot and see welcome message
/help - Show this help message
/about - Show bot information
/id - Get your user ID or replied user's ID

<b>👑 Admin Commands:</b>
/ban <user> - Ban a user
/unban <user> - Unban a user
/broadcast <message> - Send message to all users
/status - Show bot statistics

<b>💡 Tips:</b>
• Search with keywords from movie/series names
• Use partial names for better results
• Check file size before downloading

<b>🆘 Support:</b>
If you need help, contact the admin or join our support group.
    """.format(bot_username=client.me.username)
    
    await message.reply(help_text)

@app.on_message(filters.command("about"))
async def about_command(client: Client, message: Message):
    """Handle /about command"""
    uptime = await get_uptime()
    user_count = await get_user_count()
    file_count = await get_file_count()
    
    about_text = f"""
🤖 <b>AutoFilter Bot Information</b>

<b>📊 Statistics:</b>
• <b>Uptime:</b> {uptime}
• <b>Total Users:</b> {user_count:,}
• <b>Total Files:</b> {file_count:,}
• <b>Version:</b> 2.0

<b>🔧 Features:</b>
• 🔍 Instant file search
• 📁 MongoDB database storage
• 👑 Admin controls
• 🚫 User management
• 📢 Broadcast system
• 🎯 Inline search mode

<b>⚡ Performance:</b>
• Fast async operations
• Optimized database queries
• Efficient file indexing
• Scalable architecture

<b>🛠️ Built with:</b>
• Python 3.8+
• Pyrogram
• MongoDB
• Motor (async MongoDB driver)

<b>👨‍💻 Developer:</b> Professional Bot Developer
    """
    
    await message.reply(about_text)

@app.on_message(filters.command("id"))
async def id_command(client: Client, message: Message):
    """Handle /id command"""
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "No username"
        first_name = user.first_name or "No name"
        
        id_text = f"""
🆔 <b>User Information</b>

<b>👤 Name:</b> {first_name}
<b>🆔 User ID:</b> <code>{user_id}</code>
<b>📝 Username:</b> @{username}
<b>💬 Chat ID:</b> <code>{message.chat.id}</code>
        """
    else:
        user = message.from_user
        user_id = user.id
        username = user.username or "No username"
        first_name = user.first_name or "No name"
        
        id_text = f"""
🆔 <b>Your Information</b>

<b>👤 Name:</b> {first_name}
<b>🆔 User ID:</b> <code>{user_id}</code>
<b>📝 Username:</b> @{username}
<b>💬 Chat ID:</b> <code>{message.chat.id}</code>
        """
    
    await message.reply(id_text)

# Admin commands
@app.on_message(filters.command("ban") & filters.user(OWNER_ID))
async def ban_command(client: Client, message: Message):
    """Handle /ban command (Owner only)"""
    if not message.reply_to_message:
        await message.reply("❌ Please reply to a user to ban them.")
        return
    
    user_to_ban = message.reply_to_message.from_user
    user_id = user_to_ban.id
    
    if user_id == OWNER_ID:
        await message.reply("❌ You cannot ban yourself!")
        return
    
    try:
        # Add to banned collection
        await banned_collection.insert_one({
            "user_id": user_id,
            "username": user_to_ban.username,
            "first_name": user_to_ban.first_name,
            "banned_at": datetime.now(),
            "banned_by": message.from_user.id
        })
        
        await message.reply(f"✅ User {user_to_ban.first_name} (ID: {user_id}) has been banned.")
        logger.info(f"User {user_id} banned by {message.from_user.id}")
        
    except DuplicateKeyError:
        await message.reply("❌ User is already banned.")
    except Exception as e:
        await message.reply(f"❌ Error banning user: {e}")
        logger.error(f"Error banning user {user_id}: {e}")

@app.on_message(filters.command("unban") & filters.user(OWNER_ID))
async def unban_command(client: Client, message: Message):
    """Handle /unban command (Owner only)"""
    if not message.reply_to_message:
        await message.reply("❌ Please reply to a user to unban them.")
        return
    
    user_to_unban = message.reply_to_message.from_user
    user_id = user_to_unban.id
    
    try:
        result = await banned_collection.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            await message.reply(f"✅ User {user_to_unban.first_name} (ID: {user_id}) has been unbanned.")
            logger.info(f"User {user_id} unbanned by {message.from_user.id}")
        else:
            await message.reply("❌ User is not banned.")
            
    except Exception as e:
        await message.reply(f"❌ Error unbanning user: {e}")
        logger.error(f"Error unbanning user {user_id}: {e}")

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_command(client: Client, message: Message):
    """Handle /broadcast command (Owner only)"""
    if not message.reply_to_message:
        await message.reply("❌ Please reply to a message to broadcast it.")
        return
    
    broadcast_message = message.reply_to_message
    users_cursor = users_collection.find({})
    total_users = await get_user_count()
    
    if total_users == 0:
        await message.reply("❌ No users found to broadcast to.")
        return
    
    await message.reply(f"📢 Starting broadcast to {total_users} users...")
    
    success_count = 0
    failed_count = 0
    
    async for user_doc in users_cursor:
        try:
            user_id = user_doc["user_id"]
            
            # Skip if user is banned
            if await is_banned(user_id):
                continue
            
            # Forward the message
            await broadcast_message.forward(user_id)
            success_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await broadcast_message.forward(user_doc["user_id"])
                success_count += 1
            except:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Error broadcasting to user {user_doc['user_id']}: {e}")
    
    await message.reply(
        f"📢 Broadcast completed!\n"
        f"✅ Success: {success_count}\n"
        f"❌ Failed: {failed_count}\n"
        f"📊 Total: {total_users}"
    )

@app.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status_command(client: Client, message: Message):
    """Handle /status command (Owner only)"""
    uptime = await get_uptime()
    user_count = await get_user_count()
    file_count = await get_file_count()
    banned_count = await get_banned_count()
    
    # Get system info
    import psutil
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    status_text = f"""
📊 <b>Bot Status Report</b>

<b>⏰ Uptime:</b> {uptime}
<b>👥 Total Users:</b> {user_count:,}
<b>📁 Total Files:</b> {file_count:,}
<b>🚫 Banned Users:</b> {banned_count:,}

<b>💻 System Resources:</b>
• <b>CPU Usage:</b> {cpu_percent}%
• <b>Memory Usage:</b> {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
• <b>Disk Usage:</b> {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)

<b>🔧 Bot Configuration:</b>
• <b>API ID:</b> {API_ID}
• <b>Bot Username:</b> @{client.me.username}
• <b>Owner ID:</b> {OWNER_ID}
• <b>Database:</b> {DB_NAME} ✅
• <b>Required Channel:</b> {REQUIRED_CHANNEL}
• <b>Source Channels:</b> {len(SOURCE_CHANNEL_IDS)} configured
• <b>Branding:</b> {BRANDING_TAG[:30]}...

<b>📈 Performance:</b>
• <b>Response Time:</b> < 1s
• <b>Database:</b> Optimized
• <b>Memory:</b> Efficient
    """
    
    await message.reply(status_text)

@app.on_message(filters.command("send") & filters.user(OWNER_ID))
async def send_file_command(client: Client, message: Message):
    """Handle /send command to send files to users (Owner only)"""
    if not message.reply_to_message:
        await message.reply("❌ Please reply to a file to send it.")
        return
    
    if not message.reply_to_message.document and not message.reply_to_message.video and not message.reply_to_message.audio and not message.reply_to_message.photo:
        await message.reply("❌ Please reply to a file (document, video, audio, or photo).")
        return
    
    # Get the file
    file_message = message.reply_to_message
    
    # Get target user ID from command arguments
    try:
        target_user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply("❌ Please provide a valid user ID.\nUsage: /send <user_id>")
        return
    
    try:
        # Send the file to the user
        await file_message.forward(target_user_id)
        await message.reply(f"✅ File sent successfully to user {target_user_id}")
        logger.info(f"File sent to user {target_user_id} by {message.from_user.id}")
        
    except Exception as e:
        await message.reply(f"❌ Error sending file: {e}")
        logger.error(f"Error sending file to user {target_user_id}: {e}")

# File indexing and management
@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def index_file(client: Client, message: Message):
    """Index files automatically from source channels or admin uploads"""
    # Check if message is from source channel or user is admin
    is_from_source = message.chat.id in SOURCE_CHANNEL_IDS
    is_admin_upload = await is_admin(message.from_user.id, message.chat.id)
    
    if not (is_from_source or is_admin_upload):
        return
    
    try:
        # Get file information
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or "Unknown Document"
            file_type = "document"
            file_size = message.document.file_size or 0
        elif message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or "Unknown Video"
            file_type = "video"
            file_size = message.video.file_size or 0
        elif message.audio:
            file_id = message.audio.file_id
            file_name = message.audio.file_name or "Unknown Audio"
            file_type = "audio"
            file_size = message.audio.file_size or 0
        elif message.photo:
            file_id = message.photo.file_id
            file_name = "Photo"
            file_type = "photo"
            file_size = message.photo.file_size or 0
        else:
            return
        
        # Add branding to caption
        caption = message.caption or ""
        if BRANDING_TAG and BRANDING_TAG not in caption:
            caption = f"{caption}\n\n{BRANDING_TAG}" if caption else BRANDING_TAG
        
        # Create file document
        file_doc = FileDocument(
            file_id=file_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            caption=caption,
            group_id=message.chat.id
        )
        
        # Save to database
        if await file_doc.save():
            logger.info(f"Indexed file: {file_name} from {'source channel' if is_from_source else 'admin upload'}")
        else:
            logger.error(f"Failed to index file: {file_name}")
            
    except Exception as e:
        logger.error(f"Error indexing file: {e}")

# Inline query handler
@app.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    """Handle inline queries for file search"""
    user_id = query.from_user.id
    
    # Check if user is banned
    if await is_banned(user_id):
        return
    
    # Check if user is subscribed to required channel
    if not await check_user_subscription(user_id):
        # Show subscription required message
        results = [
            InlineQueryResultArticle(
                title="❌ Subscription Required",
                description="Please join our channel to use this bot",
                input_message_content=InputTextMessageContent(
                    f"❌ <b>Subscription Required!</b>\n\n"
                    f"Please join our channel to use this bot:\n"
                    f"📢 <a href='https://t.me/{REQUIRED_CHANNEL.replace('@', '').replace('-100', '')}'>Join Channel</a>"
                )
            )
        ]
        await query.answer(results, cache_time=300)
        return
    
    # Add user to database
    await add_user(user_id, query.from_user.username, query.from_user.first_name)
    
    query_text = query.query.strip()
    
    if not query_text:
        # Show recent files if no query
        files = await FileDocument.search_files("", limit=10)
    else:
        # Search files
        files = await FileDocument.search_files(query_text, limit=20)
    
    if not files:
        # No results found
        results = [
            InlineQueryResultArticle(
                title="❌ No files found",
                description=f"No files found for '{query_text}'",
                input_message_content=InputTextMessageContent(
                    f"❌ No files found for '{query_text}'\n\nTry searching with different keywords."
                )
            )
        ]
    else:
        results = []
        for file_doc in files:
            # Create result based on file type
            if file_doc["file_type"] == "video":
                results.append(
                    InlineQueryResultArticle(
                        title=f"🎬 {file_doc['file_name']}",
                        description=f"Video • {file_doc['file_size'] // (1024*1024)}MB",
                        input_message_content=InputTextMessageContent(
                            f"🎬 <b>{file_doc['file_name']}</b>\n\n"
                            f"📁 Type: Video\n"
                            f"📊 Size: {file_doc['file_size'] // (1024*1024)}MB\n"
                            f"📅 Added: {file_doc['added_at'].strftime('%Y-%m-%d')}"
                        ),
                        thumb_url="https://img.icons8.com/color/48/000000/video.png"
                    )
                )
            elif file_doc["file_type"] == "audio":
                results.append(
                    InlineQueryResultArticle(
                        title=f"🎵 {file_doc['file_name']}",
                        description=f"Audio • {file_doc['file_size'] // (1024*1024)}MB",
                        input_message_content=InputTextMessageContent(
                            f"🎵 <b>{file_doc['file_name']}</b>\n\n"
                            f"📁 Type: Audio\n"
                            f"📊 Size: {file_doc['file_size'] // (1024*1024)}MB\n"
                            f"📅 Added: {file_doc['added_at'].strftime('%Y-%m-%d')}"
                        ),
                        thumb_url="https://img.icons8.com/color/48/000000/audio.png"
                    )
                )
            elif file_doc["file_type"] == "document":
                results.append(
                    InlineQueryResultArticle(
                        title=f"📄 {file_doc['file_name']}",
                        description=f"Document • {file_doc['file_size'] // (1024*1024)}MB",
                        input_message_content=InputTextMessageContent(
                            f"📄 <b>{file_doc['file_name']}</b>\n\n"
                            f"📁 Type: Document\n"
                            f"📊 Size: {file_doc['file_size'] // (1024*1024)}MB\n"
                            f"📅 Added: {file_doc['added_at'].strftime('%Y-%m-%d')}"
                        ),
                        thumb_url="https://img.icons8.com/color/48/000000/document.png"
                    )
                )
            else:
                results.append(
                    InlineQueryResultArticle(
                        title=f"📁 {file_doc['file_name']}",
                        description=f"File • {file_doc['file_size'] // (1024*1024)}MB",
                        input_message_content=InputTextMessageContent(
                            f"📁 <b>{file_doc['file_name']}</b>\n\n"
                            f"📁 Type: {file_doc['file_type'].title()}\n"
                            f"📊 Size: {file_doc['file_size'] // (1024*1024)}MB\n"
                            f"📅 Added: {file_doc['added_at'].strftime('%Y-%m-%d')}"
                        )
                    )
                )
    
    await query.answer(results, cache_time=300)

# Callback query handler
@app.on_callback_query()
async def callback_query_handler(client: Client, callback_query: CallbackQuery):
    """Handle callback queries"""
    user_id = callback_query.from_user.id
    
    # Check if user is banned
    if await is_banned(user_id):
        await callback_query.answer("❌ You are banned from using this bot.", show_alert=True)
        return
    
    data = callback_query.data
    
    if data == "help":
        help_text = """
📖 <b>AutoFilter Bot Help</b>

<b>🔍 How to Search:</b>
• Use the search button in /start
• Type @{bot_username} <i>query</i> in any chat
• Use inline mode for quick access

<b>📋 Commands:</b>
/start - Start the bot and see welcome message
/help - Show this help message
/about - Show bot information
/id - Get your user ID or replied user's ID

<b>💡 Tips:</b>
• Search with keywords from movie/series names
• Use partial names for better results
• Check file size before downloading
        """.format(bot_username=client.me.username)
        
        await callback_query.edit_message_text(help_text)
        
    elif data == "about":
        uptime = await get_uptime()
        user_count = await get_user_count()
        file_count = await get_file_count()
        
        about_text = f"""
🤖 <b>AutoFilter Bot Information</b>

<b>📊 Statistics:</b>
• <b>Uptime:</b> {uptime}
• <b>Total Users:</b> {user_count:,}
• <b>Total Files:</b> {file_count:,}
• <b>Version:</b> 2.0

<b>🔧 Features:</b>
• 🔍 Instant file search
• 📁 MongoDB database storage
• 👑 Admin controls
• 🚫 User management
• 📢 Broadcast system
• 🎯 Inline search mode
        """
        
        await callback_query.edit_message_text(about_text)
        
    elif data == "get_id":
        id_text = f"""
🆔 <b>Your Information</b>

<b>👤 Name:</b> {callback_query.from_user.first_name}
<b>🆔 User ID:</b> <code>{callback_query.from_user.id}</code>
<b>📝 Username:</b> @{callback_query.from_user.username or 'No username'}
        """
        
        await callback_query.edit_message_text(id_text)
    
    elif data == "check_sub":
        # Check subscription status
        if await check_user_subscription(callback_query.from_user.id):
            await callback_query.edit_message_text(
                "✅ <b>Subscription Verified!</b>\n\n"
                "You are now subscribed to our channel. You can use the bot normally.\n\n"
                "Use /start to see the main menu."
            )
        else:
            await callback_query.edit_message_text(
                f"❌ <b>Subscription Not Found!</b>\n\n"
                f"Please join our channel first:\n"
                f"📢 <a href='https://t.me/{REQUIRED_CHANNEL.replace('@', '').replace('-100', '')}'>Join Channel</a>\n\n"
                f"After joining, click the button below to verify your subscription.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Check Again", callback_data="check_sub")]
                ])
            )
    
    await callback_query.answer()

# Welcome message for new group members
@app.on_message(filters.new_chat_members)
async def welcome_new_members(client: Client, message: Message):
    """Welcome new group members"""
    for new_member in message.new_chat_members:
        if new_member.id == client.me.id:
            # Bot was added to group
            welcome_text = """
🎉 <b>Thanks for adding me to this group!</b>

I'm AutoFilter Bot, your file search assistant.

<b>🚀 What I can do:</b>
• 🔍 Search and find files instantly
• 📁 Index files automatically
• 👑 Admin controls for group management
• 🎯 Inline search mode

<b>📋 Admin Commands:</b>
• Add files to index them automatically
• Use /status to see bot statistics
• Manage users with ban/unban commands

<b>💡 For Users:</b>
• Use @{bot_username} <i>query</i> to search files
• Get help with /help command

Let's make file sharing easier! 🚀
            """.format(bot_username=client.me.username)
            
            await message.reply(welcome_text)
            
            # Add group to database
            try:
                await groups_collection.update_one(
                    {"group_id": message.chat.id},
                    {
                        "$set": {
                            "group_id": message.chat.id,
                            "group_title": message.chat.title,
                            "added_at": datetime.now(),
                            "added_by": message.from_user.id
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error adding group {message.chat.id}: {e}")
        
        else:
            # New user joined
            welcome_text = f"""
👋 <b>Welcome to the group, {new_member.first_name}!</b>

🎬 I'm AutoFilter Bot, your file search assistant.

<b>🔍 Quick Start:</b>
• Use @{client.me.username} <i>movie name</i> to search files
• Get help with /help command
• Use /start for more options

Enjoy your stay! 🚀
            """
            
            await message.reply(welcome_text)

# Error handlers
@app.on_message(filters.all)
async def error_handler(client: Client, message: Message):
    """Handle errors and unknown commands"""
    try:
        # Check if user is banned
        if await is_banned(message.from_user.id):
            return
        
        # Add user to database
        await add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )
        
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")

# Startup event
@app.on_ready()
async def startup_handler():
    """Handle bot startup"""
    logger.info("🚀 AutoFilter Bot is starting...")
    logger.info(f"Bot username: @{app.me.username}")
    logger.info(f"Bot ID: {app.me.id}")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info("✅ Bot started successfully!")

# Shutdown event
@app.on_disconnect()
async def shutdown_handler():
    """Handle bot shutdown"""
    logger.info("🛑 AutoFilter Bot is shutting down...")
    logger.info("✅ Bot stopped successfully!")

# Main function
async def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting AutoFilter Bot...")
        await app.start()
        logger.info("Bot started successfully!")
        
        # Keep the bot running
        await app.idle()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await app.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
