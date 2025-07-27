#!/usr/bin/env python3
"""
Start the Grok Trading Bot Telegram interface
This script will start the bot and listen for Telegram commands
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.telegram_bot import TelegramBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Start the Telegram bot"""
    
    # Check if Telegram token is configured
    if not os.getenv('TELEGRAM_TOKEN'):
        print("❌ TELEGRAM_TOKEN not found in .env file")
        print("Please add your Telegram bot token to the .env file")
        return
    
    try:
        print("🤖 Starting Grok Trading Bot Telegram Interface...")
        print("=" * 60)
        print(f"Bot Token: {os.getenv('TELEGRAM_TOKEN')[:20]}...")
        print("Available Commands:")
        print("  /start - Authenticate and get welcome message")
        print("  /help - Show all commands")
        print("  /status - Check bot health")
        print("  /analyze <token> - Analyze token")
        print("  /swap <amount> <from> <to> - Execute swap")
        print("  /balance - Check wallet balance")
        print("  /positions - View positions")
        print("  /settings - Bot settings") 
        print("=" * 60)
        
        # Initialize and start the bot
        bot = TelegramBot()
        await bot.initialize_strategy()
        print(f"✅ Bot initialized successfully")
        print(f"🔗 Bot URL: https://t.me/ebrenillabDegen_Bot")
        print("\n🚀 Bot is now listening for commands...")
        print("💬 Go to Telegram and send /start to your bot!")
        print("\n⏹️  Press Ctrl+C to stop the bot")
        
        # Start polling for messages
        await bot.start_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        logger.error(f"Bot startup error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 