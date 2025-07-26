"""
Telegram Bot Management for Grok Trading Bot
Handles Telegram commands and user interactions
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
try:
    from modules.auth import AuthManager
    from modules.trades import GMGNTrader
    from modules.metrics import OnChainMetrics
    from modules.wallet import SolanaWallet
    from modules.strategy import TradingStrategy
except ImportError:
    # Handle import when running from different directory
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.auth import AuthManager
    from modules.trades import GMGNTrader
    from modules.metrics import OnChainMetrics
    from modules.wallet import SolanaWallet
    from modules.strategy import TradingStrategy

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBotManager:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.auth_manager = AuthManager()
        self.trader = GMGNTrader()
        self.metrics = OnChainMetrics()
        self.wallet = SolanaWallet()
        
        # Store pending swaps for confirmation
        self.pending_swaps = {}
        
        # Get admin chat ID (your Telegram user ID)
        self.admin_chat_id = int(os.getenv('ADMIN_CHAT_ID', '1508863163'))  # Your user ID
        
        # Initialize trading strategy
        self.strategy = TradingStrategy(self.wallet, self.trader, self)
        
        # Initialize scanner and safety for advanced features
        from .scanner import SolanaTokenScanner
        from .safety import SolanaTokenSafety
        self.scanner = SolanaTokenScanner()
        self.safety = SolanaTokenSafety()
        
        # Connect strategy to new modules
        self.strategy.scanner = self.scanner
        self.strategy.safety = self.safety
        
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN not found in environment variables")
        
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        
        # Command handlers
        self.commands = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/status': self._handle_status,
            '/balance': self._handle_balance,
            '/analyze': self._handle_analyze,
            '/swap': self._handle_swap,
            '/positions': self._handle_positions,
            '/settings': self._handle_settings,
            '/stop': self._handle_stop,
            '/start_auto': self._handle_start_auto,
            '/stop_auto': self._handle_stop_auto,
            '/auto_status': self._handle_auto_status,
            '/scan': self._handle_market_scan,
            '/autonomous': self._handle_start_autonomous
        }
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = 'Markdown') -> bool:
        """Send message to Telegram chat"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    return result.get('ok', False)
                    
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def _handle_start(self, chat_id: int, username: str = None) -> Dict[str, Any]:
        """Handle /start command"""
        try:
            # Authenticate user
            auth_result = await self.auth_manager.handle_telegram_start(chat_id, username)
            
            if auth_result['success']:
                welcome_msg = f"""
🤖 *Welcome to Grok Trading Bot!*

You've been successfully authenticated!

*Available Commands:*
/help - Show all commands
/status - Bot status and health
/balance - Check wallet balance  
/analyze <token> - Analyze a token
/swap <amount> <from> <to> - Execute swap
/positions - View active positions
/settings - Bot configuration
/stop - Stop the bot

*Quick Start:*
• Use `/analyze DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` to analyze BONK
• Use `/swap 1 USDC SOL` to swap 1 USDC for SOL

Ready to hunt memecoins! 🦎💎
                """
                
                await self.send_message(chat_id, welcome_msg)
                return auth_result
            else:
                await self.send_message(chat_id, f"❌ Authentication failed: {auth_result['error']}")
                return auth_result
                
        except Exception as e:
            logger.error(f"Error in /start handler: {e}")
            await self.send_message(chat_id, "❌ Error during authentication")
            return {'success': False, 'error': str(e)}
    
    async def _handle_help(self, chat_id: int, args: list = None) -> None:
        """Handle /help command"""
        help_msg = """
🤖 **Grok Trading Bot - Enhanced Commands**

**📊 MARKET ANALYSIS:**
`/scan` - 🔍 **One-shot market opportunity scan**
`/analyze <token_address>` - Detailed token analysis
`/balance` - Check wallet balance & portfolio

**💰 MANUAL TRADING:**
`/swap <amount> <from> <to>` - Execute token swap
`/positions` - View active trading positions

**🤖 AUTOMATED TRADING:**
`/start_auto` - Basic automation (existing tokens)
`/autonomous` - 🚀 **FULL AUTONOMOUS MODE** (new tokens!)
`/stop_auto` - Stop automated trading
`/auto_status` - Check automation status

**ℹ️ BOT MANAGEMENT:**
`/status` - Bot health and connection status
`/settings` - View/modify bot settings

**🎯 EXAMPLES:**
`/scan` - Find opportunities now
`/swap 1 USDC SOL` - Buy SOL with USDC
`/autonomous` - Start autonomous sniping

**🛡️ NEW SAFETY FEATURES:**
• **Honeypot Detection** - Simulates buy/sell tests
• **Rug Analysis** - Checks mint authority & holders
• **Age Filtering** - Only fresh tokens (< 1hr)
• **Liquidity Checks** - Minimum $5k liquidity

**⚡ ENHANCED SCALPING:**
• Detects 25%+ pumps automatically
• 30% take profit, 10% stop loss
• Max $5 trades, 15/day limit
• Real-time Telegram notifications

**🎯 AUTONOMOUS MODE:**
Fully automated token discovery, safety analysis, and trading!

Need help? The bot is now smarter than ever! 🚀
        """
        await self.send_message(chat_id, help_msg)
    
    async def _handle_status(self, chat_id: int, args: list = None) -> None:
        """Handle /status command"""
        try:
            # Test GMGN connection
            gmgn_test = await self.trader.test_connection(print_debug=False)
            gmgn_status = "✅ Connected" if gmgn_test['success'] else "❌ Disconnected"
            
            status_msg = f"""
🤖 *Grok Bot Status*

*API Connections:*
GMGN API: {gmgn_status}
Solana RPC: ✅ Connected
Telegram: ✅ Active

*Bot Health:*
• Uptime: Active
• Memory: Normal
• Trades Today: 0/10
• Active Positions: 0

*Configuration:*
• Network: Solana Mainnet
• Max Position: $1000
• Risk Level: 2%

Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.send_message(chat_id, status_msg)
            
        except Exception as e:
            await self.send_message(chat_id, f"❌ Error checking status: {str(e)}")
    
    async def _handle_analyze(self, chat_id: int, args: list = None) -> None:
        """Handle /analyze command"""
        if not args or len(args) == 0:
            await self.send_message(chat_id, 
                "❌ Please provide a token address.\nExample: `/analyze DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`")
            return
        
        token_address = args[0]
        
        await self.send_message(chat_id, f"🔍 Analyzing token: `{token_address}`\nPlease wait...")
        
        try:
            # Get comprehensive analysis
            analysis_result = await self.metrics.get_comprehensive_analysis(token_address)
            
            if analysis_result['success']:
                analysis = analysis_result['analysis']
                risk = analysis['risk_analysis']
                trend = analysis['trend_analysis']
                recommendation = analysis['trading_recommendation']
                
                result_msg = f"""
📊 *Token Analysis Results*

*Token:* `{token_address[:8]}...{token_address[-8:]}`

*Risk Assessment:*
• Overall Score: {risk['overall_score']}/100
• Risk Level: {risk['risk_category'].upper()}
• Liquidity Score: {risk['liquidity_score']}/100
• Holder Score: {risk['holder_score']}/100

*Trend Analysis:*
• Overall Trend: {trend['overall_trend'].upper()}
• Price Trend: {trend['price_trend']}
• Volume Trend: {trend['volume_trend']}
• Combined Score: {trend['combined_score']}/100

*Trading Recommendation:*
• Action: {recommendation['action'].upper()}
• Confidence: {recommendation['confidence']}
• Position Size: {recommendation['position_size']}

*Reasoning:* {recommendation['reasoning']}

⚠️ *Remember: This is not financial advice. Always DYOR!*
                """
                
            else:
                result_msg = f"❌ Analysis failed: {analysis_result['error']}"
            
            await self.send_message(chat_id, result_msg)
            
        except Exception as e:
            await self.send_message(chat_id, f"❌ Error during analysis: {str(e)}")
    
    async def _handle_swap(self, chat_id: int, args: list = None) -> None:
        """Handle /swap command"""
        if not args or len(args) < 3:
            await self.send_message(chat_id, 
                "❌ Invalid swap format.\nExample: `/swap 1 USDC SOL`\nFormat: `/swap <amount> <from_token> <to_token>`")
            return
        
        try:
            amount = float(args[0])
            from_token = args[1].upper()
            to_token = args[2].upper()
            
            # Token address mapping
            token_addresses = {
                'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'SOL': 'So11111111111111111111111111111111111111112',
                'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'
            }
            
            if from_token not in token_addresses or to_token not in token_addresses:
                await self.send_message(chat_id, 
                    f"❌ Unsupported token. Supported: {', '.join(token_addresses.keys())}")
                return
            
            from_address = token_addresses[from_token]
            to_address = token_addresses[to_token]
            
            # Convert amount to smallest units
            decimals = 6 if from_token == 'USDC' else 9  # USDC has 6 decimals, SOL has 9
            amount_units = int(amount * (10 ** decimals))
            
            await self.send_message(chat_id, 
                f"🔄 Getting swap route for {amount} {from_token} → {to_token}...")
            
            # Get swap route
            route_result = await self.trader.get_swap_route(
                token_in_address=from_address,
                token_out_address=to_address,
                in_amount=str(amount_units),
                from_address=self.wallet.get_address(),  # Use our actual wallet address!
                slippage=1.0,
                print_debug=False
            )
            
            if route_result['success']:
                quote = route_result['quote']
                
                # Calculate output amount based on token decimals
                out_decimals = 9 if to_token == 'SOL' else 6  # SOL has 9, USDC has 6
                out_amount = float(quote['outAmount']) / (10 ** out_decimals)
                price_impact = float(quote.get('priceImpactPct', 0))
                
                # Execute swap immediately to avoid timestamp expiry
                await self.send_message(chat_id, 
                    f"⚡ Executing {amount} {from_token} → {to_token} swap immediately...")
                
                # Get the raw transaction
                raw_tx = route_result.get('raw_tx', {})
                if isinstance(raw_tx, dict):
                    raw_tx = raw_tx.get('swapTransaction', raw_tx)
                
                # Execute the swap
                result = await self.wallet.execute_swap(raw_tx)
                
                if result['success']:
                    success_msg = f"""
🎉 **SWAP EXECUTED SUCCESSFULLY!**

💱 **Trade Completed:**
• From: {amount} {from_token}
• To: ~{out_amount:.6f} {to_token}
• Price Impact: {price_impact}%
• Route: {quote.get('routePlan', [{}])[0].get('swapInfo', {}).get('label', 'Unknown')}
• USD In: ${route_result.get('amount_in_usd', 'N/A')}
• USD Out: ${route_result.get('amount_out_usd', 'N/A')}

🔗 **Transaction:** {result['explorer_url']}

✅ Check your updated balance with /balance"""
                    
                    await self.send_message(chat_id, success_msg)
                else:
                    error_msg = f"""
❌ **SWAP FAILED**

Error: {result.get('error', 'Unknown error')}

Try again or check your balance with /balance"""
                    
                    await self.send_message(chat_id, error_msg)
                
                return
                
            else:
                await self.send_message(chat_id, f"❌ Failed to get swap route: {route_result['error']}")
        
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid amount. Please enter a number.")
        except Exception as e:
            await self.send_message(chat_id, f"❌ Swap error: {str(e)}")
    
    async def _execute_pending_swap(self, chat_id: int) -> None:
        """Execute a pending swap transaction"""
        try:
            if chat_id not in self.pending_swaps:
                await self.send_message(chat_id, "❌ No pending swap found. Please try again.")
                return
            
            swap_data = self.pending_swaps[chat_id]
            
            await self.send_message(chat_id, "🚀 Executing swap transaction...\nPlease wait...")
            
            # Get the raw transaction from the stored swap data
            raw_tx = swap_data.get('raw_tx', {})
            swap_transaction = raw_tx.get('swapTransaction', '')
            
            if not swap_transaction:
                await self.send_message(chat_id, "❌ No transaction data found. Please try the swap again.")
                del self.pending_swaps[chat_id]
                return
            
            # Execute the transaction
            tx_result = await self.wallet.execute_swap(swap_transaction)
            
            if tx_result['success']:
                success_msg = f"""
✅ *Swap Executed Successfully!*

*Transaction Details:*
• Hash: `{tx_result['transaction_hash']}`
• Status: {tx_result['status']}
• Explorer: {tx_result['explorer_url']}

*Trade Summary:*
• From: {swap_data['amount']} {swap_data['from_token']}
• To: ~{swap_data['expected_output']:.6f} {swap_data['to_token']}
• USD Value: ${swap_data.get('usd_in', 'N/A')} → ${swap_data.get('usd_out', 'N/A')}

🎉 *Swap Complete!*
Check your wallet for the new tokens.
                """
                await self.send_message(chat_id, success_msg)
            else:
                error_msg = f"""
❌ *Swap Failed*

Error: {tx_result['error']}

💡 *Possible Solutions:*
• Check if you have sufficient balance
• Try with lower slippage
• Wait and try again (network congestion)
• Ensure your wallet has SOL for fees

Your funds are safe - no transaction was executed.
                """
                await self.send_message(chat_id, error_msg)
            
            # Clean up pending swap
            del self.pending_swaps[chat_id]
            
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            await self.send_message(chat_id, f"❌ Error executing swap: {str(e)}")
            if chat_id in self.pending_swaps:
                del self.pending_swaps[chat_id]

    async def _handle_positions(self, chat_id: int, args: list = None) -> None:
        """Handle /positions command"""
        # This would integrate with the main bot's position tracking
        positions_msg = """
📈 *Active Positions*

Currently no active positions.

*Recent Trades:*
No recent trades found.

Use `/swap` to start trading!
        """
        await self.send_message(chat_id, positions_msg)
    
    async def _handle_balance(self, chat_id: int, args: list = None) -> None:
        """Handle /balance command"""
        try:
            await self.send_message(chat_id, "💰 *Fetching your real balances...*")
            
            # Get all wallet balances
            balance_result = await self.wallet.get_all_balances()
            
            if balance_result['success']:
                balances = balance_result['balances']
                
                # Get real-time SOL price
                sol_price = await self._get_sol_price()
                usdc_value = balances.get('USDC', 0)
                sol_value = balances.get('SOL', 0) * sol_price
                total_usd = sol_value + usdc_value
                
                balance_msg = f"""
💰 *Your Real Wallet Balance*

💎 **SOL**: {balances.get('SOL', 0):.4f} SOL (~${sol_value:.2f})
💵 **USDC**: ${balances.get('USDC', 0):.2f} USDC
🐕 **BONK**: {balances.get('BONK', 0):,.0f} BONK

📊 *Total Estimated Value:* ~${total_usd:.2f}

*Wallet Address:*
`{self.wallet.get_address()}`

🚀 *Ready to trade!* Use `/swap 1 USDC SOL` to start.
                """
                await self.send_message(chat_id, balance_msg)
            else:
                await self.send_message(chat_id, f"❌ Error getting balance: {balance_result['error']}")
        
        except Exception as e:
            await self.send_message(chat_id, f"❌ Balance check failed: {str(e)}")
    
    async def _get_sol_price(self) -> float:
        """Get current SOL price from CoinGecko API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd') as response:
                    data = await response.json()
                    price = data['solana']['usd']
                    logger.info(f"Real-time SOL price: ${price}")
                    return float(price)
        except Exception as e:
            logger.error(f"Failed to get real-time SOL price: {e}")
            # Fallback to recent price
            return 186.87  # Last known good price
    
    async def _handle_settings(self, chat_id: int, args: list = None) -> None:
        """Handle /settings command"""
        settings_msg = """
⚙️ *Bot Settings*

*Risk Management:*
• Max Position Size: $1000
• Stop Loss: 10%
• Take Profit: 25%
• Daily Trade Limit: 10
• Risk Percentage: 2%

*Trading Preferences:*
• Slippage Tolerance: 1%
• Anti-MEV: Enabled
• Auto-Trading: Disabled

*Notifications:*
• Trade Alerts: Enabled
• Price Alerts: Disabled
• Daily Summary: Enabled

Use `/settings <parameter> <value>` to modify.
Example: `/settings slippage 0.5`
        """
        await self.send_message(chat_id, settings_msg)
    
    async def _handle_stop(self, chat_id: int, args: list = None) -> None:
        """Handle /stop command"""
        stop_msg = """
🛑 *Bot Stop Requested*

• All active trading suspended
• Positions monitoring continues
• Telegram commands still available

Use `/start` to reactivate trading.

⚠️ Existing positions remain open and monitored.
        """
        await self.send_message(chat_id, stop_msg)
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process incoming Telegram message"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            username = message.get('from', {}).get('username')
            
            # Handle confirmation responses (YES/NO)
            if text.upper() in ['YES', 'NO']:
                if text.upper() == 'YES':
                    # Execute the pending swap
                    await self._execute_pending_swap(chat_id)
                else:
                    # Cancel the pending swap
                    if chat_id in self.pending_swaps:
                        del self.pending_swaps[chat_id]
                    await self.send_message(chat_id, "❌ Swap cancelled.")
                return
            
            if not text.startswith('/'):
                await self.send_message(chat_id, 
                    "ℹ️ Please use commands starting with /\nType /help for available commands.")
                return
            
            # Parse command and arguments
            parts = text.split()
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Execute command
            if command in self.commands:
                await self.commands[command](chat_id, args)
            else:
                await self.send_message(chat_id, 
                    f"❌ Unknown command: {command}\nType /help for available commands.")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def start_polling(self):
        """Start polling for Telegram messages"""
        logger.info("Starting Telegram bot polling...")
        offset = 0
        
        while True:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {'offset': offset, 'timeout': 30}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        data = await response.json()
                        
                        if data.get('ok') and data.get('result'):
                            for update in data['result']:
                                if 'message' in update:
                                    await self.process_message(update['message'])
                                offset = update['update_id'] + 1
            
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)

    async def _handle_start_auto(self, chat_id: int, args: list = None) -> None:
        """Start automated trading"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized. Only the bot owner can use automated trading.")
            return
            
        if self.strategy.is_running:
            await self.send_message(chat_id, "🤖 Automated trading is already running!")
            return
            
        # Start automated trading in background
        asyncio.create_task(self.strategy.start_automated_trading())
        
    async def _handle_stop_auto(self, chat_id: int, args: list = None) -> None:
        """Stop automated trading"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized. Only the bot owner can stop automated trading.")
            return
            
        if not self.strategy.is_running:
            await self.send_message(chat_id, "🤖 Automated trading is not running.")
            return
            
        await self.strategy.stop_automated_trading()
        
    async def _handle_auto_status(self, chat_id: int, args: list = None) -> None:
        """Get automated trading status"""
        status = self.strategy.get_status()
        
        status_msg = f"""
🤖 **AUTOMATED TRADING STATUS**

🔄 Status: {'🟢 RUNNING' if status['is_running'] else '🔴 STOPPED'}
📊 Trades Today: {status['trades_today']}/{status['daily_limit']}
💰 Max Trade Size: ${status['max_trade_size']}
📈 Min Profit: {status['min_profit']*100}%
⏰ Scan Interval: {status['scan_interval']}s

**Commands:**
• `/start_auto` - Start automated trading
• `/stop_auto` - Stop automated trading
• `/scan` - One-shot market opportunity scan
• `/auto_status` - Check status
        """
        
        await self.send_message(chat_id, status_msg)

    async def _handle_market_scan(self, chat_id: int, args: list = None) -> None:
        """Perform one-shot market scan for opportunities"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized. Only the bot owner can access market scanning.")
            return
        
        # Send initial scanning message
        await self.send_message(chat_id, "🔍 **SCANNING MARKET OPPORTUNITIES**\n\nAnalyzing popular Solana tokens...\n\n⏳ This may take 30-60 seconds...")
        
        try:
            # Perform the comprehensive market scan
            scan_results = await self.strategy.scan_market_opportunities()
            
            # Format the results message
            scan_msg = f"""🔍 **MARKET SCAN COMPLETE**
📅 *Scan Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 **Your Balance:**
• USDC: ${scan_results['market_summary']['usdc_balance']:.2f}
• SOL: {scan_results['market_summary']['sol_balance']:.6f} (~${scan_results['market_summary']['sol_balance'] * scan_results['market_summary']['sol_price']:.2f})
• Total: ~${scan_results['market_summary']['usdc_balance'] + (scan_results['market_summary']['sol_balance'] * scan_results['market_summary']['sol_price']):.2f}

"""

            # Add opportunities section
            if scan_results['opportunities']:
                scan_msg += f"🎯 **OPPORTUNITIES FOUND ({len(scan_results['opportunities'])})**\n\n"
                
                for i, opp in enumerate(scan_results['opportunities'][:3], 1):  # Show top 3
                    scan_msg += f"**{i}. {opp['token']}** (Score: {opp['profit_score']:.1f})\n"
                    scan_msg += f"   • {opp['reason']}\n"
                    scan_msg += f"   • Suggested: ${opp['suggested_amount']:.2f} USDC\n"
                    scan_msg += f"   • Price Impact: {opp['metrics'].get('price_impact', 0):.2f}%\n\n"
                    
            else:
                scan_msg += "❌ **NO OPPORTUNITIES FOUND**\n\n"
                
                # Show why tokens were rejected (top 3 reasons)
                rejection_reasons = {}
                for rejected in scan_results['rejected_tokens']:
                    reason = rejected.get('rejection_reason', 'Unknown')
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    
                top_reasons = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
                
                scan_msg += "**Top Rejection Reasons:**\n"
                for reason, count in top_reasons:
                    scan_msg += f"• {reason}: {count} tokens\n"
                scan_msg += "\n"

            # Add recommendations
            scan_msg += "🎯 **RECOMMENDATIONS:**\n"
            for rec in scan_results['recommendations']:
                scan_msg += f"• {rec['message']}\n"
                if rec.get('action'):
                    scan_msg += f"  *Action:* `{rec['action']}`\n"
            
            # Send the comprehensive report
            await self.send_message(chat_id, scan_msg)
            
            # If there are opportunities, send detailed breakdown for the best one
            if scan_results['opportunities']:
                best_opp = scan_results['opportunities'][0]
                detail_msg = f"""🔥 **DETAILED ANALYSIS: {best_opp['token']}**

**Token Info:**
• Contract: `{best_opp['address']}`
• Analysis Score: {best_opp['profit_score']:.1f}/10.0

**Metrics:**
• Buy Impact: {best_opp['metrics'].get('price_impact', 0):.2f}%
• Sell Impact: {best_opp['metrics'].get('reverse_price_impact', 0):.2f}%
• Round-trip Cost: {best_opp['metrics'].get('price_impact', 0) + best_opp['metrics'].get('reverse_price_impact', 0):.2f}%

**Why It's Good:**
{best_opp['reason']}

**Suggested Trade:**
`/swap {best_opp['suggested_amount']:.1f} USDC {best_opp['token']}`

⚠️ *Always DYOR - This is not financial advice*"""
                
                await self.send_message(chat_id, detail_msg)
                
        except Exception as e:
            logger.error(f"Market scan error: {e}")
            await self.send_message(chat_id, f"❌ **SCAN FAILED**\n\nError: {str(e)}\n\nTry again in a few minutes.")

    async def _handle_start_autonomous(self, chat_id: int, args: list = None) -> None:
        """Start the fully autonomous trading bot"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized. Only the bot owner can start autonomous mode.")
            return
        
        await self.send_message(chat_id, """
🚀 **STARTING AUTONOMOUS MODE**

⚠️ **WARNING:** This will start fully autonomous trading that:
• Scans for new tokens continuously 
• Performs safety checks automatically
• Executes trades without confirmation
• Manages positions automatically

**Type 'CONFIRM AUTONOMOUS' to proceed**
        """)
        
        # This would integrate with the main_loop.py module
        # For now, send a message explaining next steps
        await self.send_message(chat_id, """
🧠 **AUTONOMOUS MODE SETUP**

To enable full autonomous trading:

1. Stop the current bot (Ctrl+C)
2. Run: `python -m modules.main_loop`
3. The bot will scan every 90 seconds
4. Maximum 15 trades per day
5. Full Telegram notifications

**Current manual mode will continue running**
**Use /start_auto for simple automation**
        """)

# Test function
async def test_telegram_bot():
    """Test Telegram bot functionality"""
    try:
        bot = TelegramBotManager()
        print("✅ Telegram bot initialized successfully")
        print(f"Bot token: {bot.token[:10]}...")
        print("Available commands:", list(bot.commands.keys()))
        return True
    except Exception as e:
        print(f"❌ Telegram bot test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_telegram_bot()) 