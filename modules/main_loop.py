#!/usr/bin/env python3
"""
🧠 Main Loop Module - Autonomous Trading Orchestrator
Coordinates scanner, safety, and strategy modules in an async loop for fully autonomous trading.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os
import signal
import sys

# Import our modules
try:
    from .scanner import SolanaTokenScanner, Token
    from .safety import SolanaTokenSafety
    from .strategy import TradingStrategy
    from .wallet import SolanaWallet
    from .trades import GMGNTrader
    from .telegram_bot import TelegramBot
except ImportError:
    # Fallback for testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scanner import SolanaTokenScanner, Token
    from safety import SolanaTokenSafety
    from strategy import TradingStrategy
    from wallet import SolanaWallet
    from trades import GMGNTrader
    from telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class GrokBotMainLoop:
    """
    🚀 Autonomous Grok Trading Bot Main Loop
    
    Orchestrates:
    - Token scanning and discovery
    - Safety analysis and rug checking  
    - Strategy evaluation and execution
    - Position monitoring and management
    - Telegram notifications and control
    """
    
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self.loop_count = 0
        self.start_time = None
        
        # Core components
        self.wallet: Optional[SolanaWallet] = None
        self.trader: Optional[GMGNTrader] = None
        self.scanner: Optional[SolanaTokenScanner] = None
        self.safety: Optional[SolanaTokenSafety] = None
        self.strategy: Optional[TradingStrategy] = None
        self.telegram_bot: Optional[TelegramBot] = None
        
        # Configuration
        self.scan_interval = 90  # 90 seconds between scans
        self.max_daily_trades = 15
        self.max_active_positions = 5
        
        # Statistics
        self.stats = {
            'total_scans': 0,
            'tokens_found': 0,
            'tokens_analyzed': 0,
            'safe_tokens': 0,
            'trades_executed': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl_usd': 0.0
        }
        
        logger.info("🧠 GrokBot Main Loop initialized")
        logger.info(f"📊 Config: {self.scan_interval}s intervals, max {self.max_daily_trades} trades/day")
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.should_stop = True
    
    async def initialize(self) -> bool:
        """
        🚀 Initialize all components
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("🔧 Initializing GrokBot components...")
            
            # Initialize wallet
            self.wallet = SolanaWallet()
            logger.info(f"💼 Wallet initialized: {self.wallet.get_address()}")
            
            # Initialize trader
            self.trader = GMGNTrader()
            
            # Test trader connection
            connection_test = await self.trader.test_connection()
            if not connection_test:
                logger.error("❌ GMGN trader connection failed")
                return False
            logger.info("✅ GMGN trader connected")
            
            # Initialize scanner
            self.scanner = SolanaTokenScanner()
            logger.info("🔍 Token scanner initialized")
            
            # Initialize safety analyzer
            self.safety = SolanaTokenSafety()
            logger.info("🛡️ Safety analyzer initialized")
            
            # Initialize strategy
            self.strategy = TradingStrategy(self.wallet, self.trader, self.telegram_bot)
            
            # Connect strategy to scanner and safety
            self.strategy.scanner = self.scanner
            self.strategy.safety = self.safety
            
            logger.info("🤖 Trading strategy initialized")
            
            # Initialize Telegram bot (optional)
            telegram_token = os.getenv('TELEGRAM_TOKEN')
            if telegram_token:
                try:
                    self.telegram_bot = TelegramBot()
                    self.strategy.telegram_bot = self.telegram_bot  # Update reference
                    logger.info("📱 Telegram bot initialized")
                except Exception as e:
                    logger.warning(f"⚠️ Telegram bot initialization failed: {e}")
                    self.telegram_bot = None
            else:
                logger.info("📱 Telegram bot not configured (optional)")
            
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def run_main_loop(self) -> None:
        """
        🔄 Main autonomous trading loop
        
        This is the core loop that:
        1. Scans for new tokens
        2. Analyzes safety
        3. Executes trades based on strategy
        4. Monitors positions
        5. Reports status
        """
        
        if not await self.initialize():
            logger.error("❌ Failed to initialize, cannot start main loop")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        logger.info("🚀 Starting autonomous trading loop...")
        await self._send_startup_notification()
        
        try:
            while not self.should_stop:
                loop_start = datetime.utcnow()
                self.loop_count += 1
                
                logger.info(f"🔄 Loop #{self.loop_count} starting...")
                
                try:
                    # Reset daily trades if new day
                    if self.strategy and self.strategy.last_reset != datetime.now().date():
                        self.strategy.trades_today = 0
                        self.strategy.last_reset = datetime.now().date()
                        logger.info("📅 Daily trade count reset")
                    
                    # Skip trading if daily limit reached
                    if self.strategy and self.strategy.trades_today >= self.max_daily_trades:
                        logger.info(f"🚫 Daily trade limit reached ({self.strategy.trades_today}/{self.max_daily_trades})")
                        await self._monitor_positions_only()
                        await self._sleep_until_next_scan(loop_start)
                        continue
                    
                    # Skip trading if too many active positions
                    active_positions = len(self.strategy.active_positions) if self.strategy else 0
                    if active_positions >= self.max_active_positions:
                        logger.info(f"🚫 Max active positions reached ({active_positions}/{self.max_active_positions})")
                        await self._monitor_positions_only()
                        await self._sleep_until_next_scan(loop_start)
                        continue
                    
                    # Execute main trading logic
                    await self._execute_trading_cycle()
                    
                    # Monitor existing positions
                    if self.strategy:
                        await self.strategy.monitor_positions()
                    
                    # Update statistics
                    await self._update_statistics()
                    
                    # Send periodic status update
                    if self.loop_count % 10 == 0:  # Every 10 loops (~15 minutes)
                        await self._send_status_update()
                    
                except Exception as e:
                    logger.error(f"❌ Error in main loop iteration {self.loop_count}: {e}")
                    self.stats['failed_trades'] += 1
                
                # Sleep until next scan
                await self._sleep_until_next_scan(loop_start)
                
        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received")
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}")
        finally:
            await self._shutdown()
    
    async def _execute_trading_cycle(self) -> None:
        """
        🎯 Execute one complete trading cycle
        
        Steps:
        1. Scan for new tokens
        2. Filter candidates
        3. Analyze safety
        4. Execute trades
        """
        try:
            logger.info("🔍 Starting trading cycle...")
            
            # Step 1: Scan for new tokens
            new_tokens = []
            if self.scanner:
                async with self.scanner:
                    new_tokens = await self.scanner.get_candidate_tokens()
            
            self.stats['tokens_found'] += len(new_tokens)
            
            if not new_tokens:
                logger.info("📭 No candidate tokens found this cycle")
                return
            
            logger.info(f"🎯 Found {len(new_tokens)} candidate tokens")
            
            # Step 2: Analyze each token
            safe_tokens = []
            
            if self.safety:
                async with self.safety:
                    for token in new_tokens:
                        try:
                            self.stats['tokens_analyzed'] += 1
                            
                            # Safety analysis
                            safety_result = await self.safety.is_token_safe(token)
                            
                            if safety_result.is_safe:
                                safe_tokens.append((token, safety_result))
                                self.stats['safe_tokens'] += 1
                                logger.info(f"✅ {token.symbol} passed safety checks")
                            else:
                                logger.info(f"⚠️ {token.symbol} failed safety: {safety_result.risk_factors[:2]}")
                                
                        except Exception as e:
                            logger.error(f"❌ Error analyzing {token.symbol}: {e}")
            else:
                # If no safety module, treat all as safe (not recommended for production)
                safe_tokens = [(token, None) for token in new_tokens]
            
            logger.info(f"🛡️ {len(safe_tokens)}/{len(new_tokens)} tokens passed safety checks")
            
            # Step 3: Execute trades on safe tokens
            if self.strategy:
                for token, safety_result in safe_tokens:
                    try:
                        # Set safety result for strategy to use
                        if hasattr(self.strategy, '_current_safety_result'):
                            self.strategy._current_safety_result = safety_result
                        
                        await self.strategy.evaluate_and_trade(token)
                        
                        # Small delay between trades to avoid rate limits
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ Error trading {token.symbol}: {e}")
                        self.stats['failed_trades'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error in trading cycle: {e}")
    
    async def _monitor_positions_only(self) -> None:
        """Monitor positions without scanning for new tokens"""
        try:
            if self.strategy:
                await self.strategy.monitor_positions()
                logger.info(f"👀 Monitored {len(self.strategy.active_positions)} positions")
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")
    
    async def _update_statistics(self) -> None:
        """Update trading statistics"""
        try:
            self.stats['total_scans'] = self.loop_count
            
            if self.strategy:
                self.stats['trades_executed'] = self.strategy.trades_today
                
                # Calculate successful trades (simplified)
                total_positions = len(self.strategy.active_positions)
                self.stats['successful_trades'] = max(0, self.stats['trades_executed'] - self.stats['failed_trades'])
                
        except Exception as e:
            logger.error(f"❌ Error updating statistics: {e}")
    
    async def _send_startup_notification(self) -> None:
        """Send startup notification via Telegram"""
        try:
            if not self.telegram_bot:
                return
            
            message = f"""
🚀 **GROKBOT STARTED**

🕐 **Started:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
💼 **Wallet:** `{self.wallet.get_address()[:8]}...`
⚙️ **Config:**
  • Scan interval: {self.scan_interval}s
  • Max daily trades: {self.max_daily_trades}
  • Max positions: {self.max_active_positions}

🤖 **Bot is now hunting for opportunities!**
            """
            
            if hasattr(self.telegram_bot, 'admin_chat_id'):
                await self.telegram_bot.send_message(
                    self.telegram_bot.admin_chat_id,
                    message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to send startup notification: {e}")
    
    async def _send_status_update(self) -> None:
        """Send periodic status update"""
        try:
            if not self.telegram_bot:
                return
            
            runtime = datetime.utcnow() - self.start_time if self.start_time else timedelta(0)
            active_positions = len(self.strategy.active_positions) if self.strategy else 0
            
            message = f"""
📊 **GROKBOT STATUS UPDATE**

⏰ **Runtime:** {runtime.total_seconds()/3600:.1f}h ({self.loop_count} cycles)
📈 **Today's Stats:**
  • Scans: {self.stats['total_scans']}
  • Tokens found: {self.stats['tokens_found']}
  • Safe tokens: {self.stats['safe_tokens']}
  • Trades executed: {self.stats['trades_executed']}/{self.max_daily_trades}
  • Active positions: {active_positions}/{self.max_active_positions}

🎯 **Next scan in ~{self.scan_interval}s**
            """
            
            if hasattr(self.telegram_bot, 'admin_chat_id'):
                await self.telegram_bot.send_message(
                    self.telegram_bot.admin_chat_id,
                    message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to send status update: {e}")
    
    async def _sleep_until_next_scan(self, loop_start: datetime) -> None:
        """Sleep until the next scan should begin"""
        try:
            elapsed = (datetime.utcnow() - loop_start).total_seconds()
            sleep_time = max(0, self.scan_interval - elapsed)
            
            if sleep_time > 0:
                logger.info(f"😴 Sleeping for {sleep_time:.1f}s until next scan...")
                await asyncio.sleep(sleep_time)
            else:
                logger.warning(f"⚠️ Cycle took {elapsed:.1f}s (longer than {self.scan_interval}s interval)")
                
        except Exception as e:
            logger.error(f"❌ Error in sleep calculation: {e}")
            await asyncio.sleep(self.scan_interval)  # Fallback
    
    async def _shutdown(self) -> None:
        """Gracefully shutdown all components"""
        logger.info("🛑 Initiating graceful shutdown...")
        
        self.is_running = False
        
        try:
            # Close any open positions (optional - you might want to keep them)
            if self.strategy and hasattr(self.strategy, '_price_session'):
                await self.strategy._price_session.close()
            
            # Send shutdown notification
            if self.telegram_bot:
                try:
                    runtime = datetime.utcnow() - self.start_time if self.start_time else timedelta(0)
                    message = f"""
🛑 **GROKBOT SHUTDOWN**

⏰ **Runtime:** {runtime.total_seconds()/3600:.1f}h
📊 **Final Stats:**
  • Total scans: {self.stats['total_scans']}
  • Tokens analyzed: {self.stats['tokens_analyzed']}
  • Trades executed: {self.stats['trades_executed']}
  • Active positions: {len(self.strategy.active_positions) if self.strategy else 0}

💤 **Bot is now offline.**
                    """
                    
                    if hasattr(self.telegram_bot, 'admin_chat_id'):
                        await self.telegram_bot.send_message(
                            self.telegram_bot.admin_chat_id,
                            message,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"❌ Failed to send shutdown notification: {e}")
            
            logger.info("✅ Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        runtime = datetime.utcnow() - self.start_time if self.start_time else timedelta(0)
        
        return {
            'is_running': self.is_running,
            'loop_count': self.loop_count,
            'runtime_hours': runtime.total_seconds() / 3600,
            'stats': self.stats,
            'config': {
                'scan_interval': self.scan_interval,
                'max_daily_trades': self.max_daily_trades,
                'max_active_positions': self.max_active_positions
            },
            'active_positions': len(self.strategy.active_positions) if self.strategy else 0,
            'components': {
                'wallet': self.wallet is not None,
                'trader': self.trader is not None,
                'scanner': self.scanner is not None,
                'safety': self.safety is not None,
                'strategy': self.strategy is not None,
                'telegram': self.telegram_bot is not None
            }
        }

# Main execution function
async def start_autonomous_bot():
    """
    🎯 Start the autonomous GrokBot
    
    This is the main entry point for running the bot autonomously.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('grokbot_autonomous.log')
        ]
    )
    
    logger.info("🚀 Starting Autonomous GrokBot...")
    
    # Create and run the main loop
    bot = GrokBotMainLoop()
    await bot.run_main_loop()

# CLI entry point
if __name__ == "__main__":
    try:
        asyncio.run(start_autonomous_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1) 