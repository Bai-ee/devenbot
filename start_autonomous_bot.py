#!/usr/bin/env python3
"""
🚀 Autonomous GrokBot Launcher
Starts the fully autonomous Solana memecoin trading bot with token discovery, 
safety analysis, and automated trading.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the modules directory to Python path
current_dir = Path(__file__).parent
modules_dir = current_dir / "modules"
sys.path.insert(0, str(modules_dir))

from modules.main_loop import start_autonomous_bot

def setup_logging():
    """Setup comprehensive logging for autonomous operation"""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / 'autonomous_bot.log'),
            logging.FileHandler(logs_dir / 'trades.log')  # Separate file for trades
        ]
    )
    
    # Set specific log levels
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def check_environment():
    """Check that all required environment variables are set"""
    required_vars = [
        'SOLANA_PRIVATE_KEY',
        'SOLANA_RPC_URL', 
        'TELEGRAM_TOKEN',
        'ADMIN_CHAT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n📝 Create a .env file with these variables or set them in your shell.")
        return False
    
    return True

def print_banner():
    """Print startup banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                     🚀 GROKBOT AUTONOMOUS                     ║
    ║               Solana Memecoin Trading Bot                     ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║                                                               ║
    ║  🔍 Token Discovery     🛡️ Safety Analysis                   ║
    ║  ⚡ Auto Scalping       🎯 Position Management                ║
    ║  📱 Telegram Alerts     💰 Profit Optimization               ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    
    🤖 AUTONOMOUS MODE FEATURES:
    • Scans DexScreener every 90 seconds for new tokens
    • Comprehensive safety checks (honeypot, rug detection)
    • Automatic scalping of 25%+ pumps
    • Smart position management with stop losses
    • Real-time Telegram notifications
    • Maximum 15 trades per day, $5 per trade
    
    ⚠️  WARNING: This bot trades with real money!
    🛡️ Safety features enabled, but DYOR always applies.
    
    """)

async def main():
    """Main entry point"""
    print_banner()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except ImportError:
        print("📝 python-dotenv not installed, using system environment")
    
    # Check environment
    if not check_environment():
        return
    
    # Setup logging
    setup_logging()
    
    # Get configuration from environment
    wallet_address = os.getenv('SOLANA_PRIVATE_KEY', 'Not set')[:8] + "..." if os.getenv('SOLANA_PRIVATE_KEY') else 'Not set'
    admin_chat_id = os.getenv('ADMIN_CHAT_ID', 'Not set')
    
    print(f"💼 Wallet: {wallet_address}")
    print(f"📱 Admin Chat ID: {admin_chat_id}")
    print(f"🌐 RPC: {os.getenv('SOLANA_RPC_URL', 'Default')}")
    print("")
    
    # Final confirmation
    print("🚨 FINAL WARNING: Starting autonomous trading bot!")
    print("   • The bot will trade automatically")
    print("   • Real money will be used")
    print("   • Positions will be managed without your input")
    print("")
    
    try:
        response = input("Type 'START' to begin autonomous trading: ").strip().upper()
        if response != 'START':
            print("❌ Autonomous mode cancelled")
            return
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return
    
    print("\n🚀 Starting autonomous bot...")
    print("   Press Ctrl+C to stop gracefully")
    print("   Check Telegram for live updates")
    print("")
    
    # Start the autonomous bot
    try:
        await start_autonomous_bot()
    except KeyboardInterrupt:
        print("\n🛑 Autonomous bot stopped by user")
    except Exception as e:
        print(f"\n❌ Autonomous bot crashed: {e}")
        logging.exception("Fatal error in autonomous bot")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 