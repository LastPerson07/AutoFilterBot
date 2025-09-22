#!/usr/bin/env python3
"""
AutoFilter Bot Startup Script
Simple script to start the bot with proper error handling
"""

import os
import sys
import asyncio
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_requirements():
    """Check if all required packages are installed"""
    required_packages = [
        'pyrogram',
        'motor',
        'pymongo',
        'psutil'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Check if configuration is properly set"""
    required_vars = [
        'API_ID',
        'API_HASH', 
        'BOT_TOKEN',
        'MONGO_URI',
        'OWNER_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) and var not in globals():
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing configuration variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Set environment variables or edit bot.py directly")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting AutoFilter Bot...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check configuration
    if not check_config():
        sys.exit(1)
    
    print("✅ All checks passed!")
    print("🤖 Starting bot...")
    print("=" * 50)
    
    try:
        # Import and run the bot
        from bot import main as bot_main
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
