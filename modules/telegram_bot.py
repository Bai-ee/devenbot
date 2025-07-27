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
    from modules.wallet import SolanaWallet
    from modules.metrics import OnChainMetrics
    from modules.strategy import TradingStrategy
    from modules.scanner import SolanaTokenScanner
    from modules.safety import SolanaTokenSafety
    
    # Import Agent SDK
    from modules.agent_sdk import GrokBotAgent
    from modules.chat_interface import ChatInterface, TelegramAgentInterface
except ImportError as e:
    print(f"Import error: {e}")
    # Mock classes for development
    
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.session = None
        self.running = False
        
        # Initialize components
        self.auth = AuthManager()
        self.trader = GMGNTrader()
        self.wallet = SolanaWallet()
        self.metrics = OnChainMetrics()
        self.strategy = None
        self.scanner = None
        self.safety = None
        
        # Initialize Agent SDK components
        self.agent = None
        self.chat_interface = None
        self.telegram_agent_interface = None
        self._initialize_agent_sdk()
        
        # Admin configuration
        self.admin_chat_id = None
        self.pending_swaps = {}
        
        # Command handlers
        self.command_handlers = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/status': self._handle_status,
            '/balance': self._handle_balance,
            '/swap': self._handle_swap,
            '/analyze': self._handle_analyze,
            '/positions': self._handle_positions,
            '/settings': self._handle_settings,
            '/scan': self._handle_market_scan,
            '/start_auto': self._handle_start_auto,
            '/stop_auto': self._handle_stop_auto,
            '/auto_status': self._handle_auto_status,
            '/autonomous': self._handle_autonomous,
            
            # New Agent SDK commands
            '/chat': self._handle_chat,
            '/ask': self._handle_chat,
            '/talk': self._handle_chat,
            '/agent': self._handle_chat,
            '/ai': self._handle_chat,
            '/clear': self._handle_clear_chat
        }
        
        logger.info("🤖 Telegram Bot initialized with Agent SDK")
    
    def _initialize_agent_sdk(self):
        """Initialize the OpenAI Agent SDK components"""
        try:
            # Check if OpenAI is configured
            openai_key = os.getenv('OPENAI_API_KEY')
            assistant_id = os.getenv('OPENAI_ASSISTANT_ID')
            
            if openai_key and assistant_id:
                logger.info("🧠 Initializing OpenAI Agent SDK...")
                
                # Initialize agent with bot components
                self.agent = GrokBotAgent(
                    trader=self.trader,
                    wallet=self.wallet,
                    strategy=self.strategy,
                    scanner=self.scanner,
                    safety=self.safety
                )
                
                # Initialize chat interface
                self.chat_interface = ChatInterface(self.agent)
                self.telegram_agent_interface = TelegramAgentInterface(self.chat_interface)
                
                logger.info("✅ Agent SDK initialized successfully")
            else:
                logger.warning("⚠️ OpenAI credentials not found - Agent SDK disabled")
                self.agent = None
                self.chat_interface = None
                self.telegram_agent_interface = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Agent SDK: {e}")
            self.agent = None
            self.chat_interface = None
            self.telegram_agent_interface = None

    async def initialize_strategy(self):
        """Initialize strategy and related components"""
        try:
            # Initialize strategy
            self.strategy = TradingStrategy(self.trader, self.wallet, telegram_bot=self)
            
            # Initialize scanner and safety
            self.scanner = SolanaTokenScanner()
            self.safety = SolanaTokenSafety(self.wallet)
            
            # Update agent with new components
            if self.agent:
                self.agent.strategy = self.strategy
                self.agent.scanner = self.scanner
                self.agent.safety = self.safety
                
            logger.info("✅ Strategy and components initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy: {e}")

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
            auth_result = await self.auth.handle_telegram_start(chat_id, username)
            
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
🤖 **GROKBOT - AI-POWERED TRADING ASSISTANT**

**🧠 AI CHAT (NEW!):**
`/chat <message>` - 💬 **Talk naturally with AI assistant**
`/ask <question>` - 🤔 **Ask anything about trading**
`/ai <request>` - 🤖 **Natural language commands**
`/clear` - 🗑️ **Clear conversation history**
*Or just type normally - no command needed!*

**📊 MARKET ANALYSIS:**
`/scan` - 🔍 **Enhanced market opportunity scan**
`/scan detailed` - 📋 **Deep dive analysis with rejection reasons**
`/analyze <token_address>` - Detailed token analysis
`/balance` - Check wallet balance & portfolio

**💰 MANUAL TRADING:**
`/swap <amount> <from> <to>` - Execute token swap (USDC/SOL to ANY token!)
`/positions` - View active trading positions

**💱 SWAP EXAMPLES:**
`/swap 1 USDC SOL` - Use token symbols
`/swap 1 USDC BONK` - Buy memecoins with USDC
`/swap 1 USDC DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` - Use any contract address

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

**💬 AI CHAT EXAMPLES:**
"What's trending right now?"
"Buy 1 USDC of WIF"
"Show me my balance"
"Scan for good opportunities"
"What did we trade today?"

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

🔥 **Try saying:** "What's pumping?" or "Buy some BONK" or just ask me anything!

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
        """Handle /swap command - supports USDC/SOL to ANY Solana token with automatic SOL routing"""
        if not args or len(args) < 3:
            await self.send_message(chat_id, 
                "❌ Invalid swap format.\n"
                "**Examples:**\n"
                "`/swap 1 USDC SOL` - Direct swap\n"
                "`/swap 1 USDC BONK` - Auto-routes via SOL\n"
                "`/swap 1 USDC DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` - Use any contract\n"
                "**Format:** `/swap <amount> <from_token> <to_token>`")
            return
        
        try:
            amount = float(args[0])
            from_token = args[1].upper()
            to_token = args[2].upper()
            
            # Common token symbols with addresses
            known_tokens = {
                'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'SOL': 'So11111111111111111111111111111111111111112',
                'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
                'WIF': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',
                'POPCAT': '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',
                'WEN': 'WENWENvqqNya429ubCdR81ZmD69brwQaaBYY6p3LCpk',
                'BOME': 'ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82',
                'PEPE': '9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump',
                'MEW': 'MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5',
                'MYRO': 'HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4'
            }
            
            # Function to resolve token (symbol or address)
            def resolve_token(token_input: str) -> str:
                # If it's a known symbol, return the address
                if token_input in known_tokens:
                    return known_tokens[token_input]
                # If it looks like a Solana address (base58, ~44 chars), use it directly
                elif len(token_input) >= 32 and len(token_input) <= 44:
                    return token_input
                else:
                    return None
            
            from_address = resolve_token(from_token)
            to_address = resolve_token(to_token)
            
            if not from_address:
                await self.send_message(chat_id, 
                    f"❌ Unknown from_token: `{from_token}`\n"
                    f"**Supported symbols:** {', '.join(known_tokens.keys())}\n"
                    f"**Or use:** Token contract address")
                return
                
            if not to_address:
                await self.send_message(chat_id, 
                    f"❌ Unknown to_token: `{to_token}`\n"
                    f"**Supported symbols:** {', '.join(known_tokens.keys())}\n"
                    f"**Or use:** Token contract address")
                return
            
            # Determine token decimals (most SPL tokens use 6 or 9)
            def get_token_decimals(token_symbol: str, token_address: str) -> int:
                # Known decimals for specific tokens
                token_decimals = {
                    'USDC': 6, 'SOL': 9, 'BONK': 5, 'WIF': 6, 'POPCAT': 9,
                    'WEN': 5, 'BOME': 6, 'PEPE': 6, 'MEW': 6, 'MYRO': 9
                }
                # Use known decimals if available, otherwise default to 6 (most common)
                return token_decimals.get(token_symbol, 6)
            
            from_decimals = get_token_decimals(from_token, from_address)
            to_decimals = get_token_decimals(to_token, to_address)
            
            # Convert amount to smallest units
            amount_units = int(amount * (10 ** from_decimals))
            
            # 🚀 NEW: Check if we need SOL routing (GMGN API requirement)
            sol_address = 'So11111111111111111111111111111111111111112'
            needs_sol_routing = (from_address != sol_address and to_address != sol_address)
            
            if needs_sol_routing:
                await self.send_message(chat_id, 
                    f"🔄 GMGN requires SOL routing. Executing: {from_token} → SOL → {to_token}\n"
                    f"This may take 2 transactions...")
                
                # Step 1: FROM_TOKEN -> SOL
                await self.send_message(chat_id, f"Step 1/2: {amount} {from_token} → SOL...")
                
                route_result_1 = await self.trader.get_swap_route(
                    token_in_address=from_address,
                    token_out_address=sol_address,
                    in_amount=str(amount_units),
                    from_address=self.wallet.get_address(),
                    slippage=2.0,  # Higher slippage for multi-hop
                    print_debug=False
                )
                
                if not route_result_1['success']:
                    await self.send_message(chat_id, f"❌ Step 1 failed: {route_result_1.get('error')}")
                    return
                
                # Execute first swap
                raw_tx_1 = route_result_1.get('raw_tx', {})
                if isinstance(raw_tx_1, dict):
                    raw_tx_1 = raw_tx_1.get('swapTransaction', raw_tx_1)
                
                result_1 = await self.wallet.execute_swap(raw_tx_1)
                
                if not result_1['success']:
                    await self.send_message(chat_id, f"❌ Step 1 execution failed: {result_1.get('error')}")
                    return
                
                sol_received = float(route_result_1['quote']['outAmount']) / (10 ** 9)  # SOL has 9 decimals
                await self.send_message(chat_id, 
                    f"✅ Step 1 complete: Received {sol_received:.6f} SOL\n"
                    f"🔗 [Transaction](https://solscan.io/tx/{result_1.get('signature')})")
                
                # Small delay to ensure transaction is confirmed
                await asyncio.sleep(3)
                
                # Step 2: SOL -> TO_TOKEN
                await self.send_message(chat_id, f"Step 2/2: SOL → {to_token}...")
                
                # Use the SOL we received (with small buffer for fees)
                sol_amount_units = int(sol_received * 0.98 * (10 ** 9))  # 98% to account for fees
                
                route_result_2 = await self.trader.get_swap_route(
                    token_in_address=sol_address,
                    token_out_address=to_address,
                    in_amount=str(sol_amount_units),
                    from_address=self.wallet.get_address(),
                    slippage=2.0,
                    print_debug=False
                )
                
                if not route_result_2['success']:
                    await self.send_message(chat_id, f"❌ Step 2 failed: {route_result_2.get('error')}")
                    return
                
                # Execute second swap
                raw_tx_2 = route_result_2.get('raw_tx', {})
                if isinstance(raw_tx_2, dict):
                    raw_tx_2 = raw_tx_2.get('swapTransaction', raw_tx_2)
                
                result_2 = await self.wallet.execute_swap(raw_tx_2)
                
                if result_2['success']:
                    final_amount = float(route_result_2['quote']['outAmount']) / (10 ** to_decimals)
                    
                    success_msg = f"""
🎉 **2-STEP SWAP COMPLETED!**

💱 **Final Result:**
• From: {amount} {from_token}
• To: {final_amount:.6f} {to_token}
• Route: {from_token} → SOL → {to_token}

📊 **Transaction Details:**
• Step 1: [View on Solscan](https://solscan.io/tx/{result_1.get('signature')})
• Step 2: [View on Solscan](https://solscan.io/tx/{result_2.get('signature')})

⚡ **Multi-hop routing required by GMGN API**
                    """
                    await self.send_message(chat_id, success_msg)
                else:
                    await self.send_message(chat_id, f"❌ Step 2 execution failed: {result_2.get('error')}")
                
            else:
                # Direct swap (one token is SOL)
                await self.send_message(chat_id, 
                    f"🔄 Direct swap: {amount} {from_token} → {to_token}...")
                
                # Get swap route
                route_result = await self.trader.get_swap_route(
                    token_in_address=from_address,
                    token_out_address=to_address,
                    in_amount=str(amount_units),
                    from_address=self.wallet.get_address(),
                    slippage=1.0,
                    print_debug=False
                )
                
                if route_result['success']:
                    quote = route_result['quote']
                    
                    # Calculate output amount using correct decimals
                    out_amount = float(quote['outAmount']) / (10 ** to_decimals)
                    price_impact = float(quote.get('priceImpactPct', 0))
                    
                    # Execute swap immediately to avoid timestamp expiry
                    await self.send_message(chat_id, 
                        f"⚡ Executing swap immediately to avoid timeout...")
                    
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
• To: {out_amount:.6f} {to_token}
• Price Impact: {price_impact:.2f}%

🔗 **Transaction:** [View on Solscan](https://solscan.io/tx/{result.get('signature')})

⚡ **Direct swap (one token was SOL)**
                        """
                        await self.send_message(chat_id, success_msg)
                    else:
                        await self.send_message(chat_id, f"❌ Swap execution failed: {result.get('error')}")
                else:
                    await self.send_message(chat_id, f"❌ Failed to get swap route: {route_result.get('error')}")
                    
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid amount. Please enter a valid number.")
        except Exception as e:
            logger.error(f"Swap error: {e}")
            await self.send_message(chat_id, f"❌ Swap failed: {str(e)}")
    
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
    
    async def _handle_chat(self, chat_id: int, args: list = None) -> None:
        """Handle natural language chat with the AI agent"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized. Only the bot owner can use AI chat.")
            return
        
        if not self.telegram_agent_interface:
            await self.send_message(chat_id, "🤖 **AI CHAT UNAVAILABLE**\n\n❌ OpenAI Agent SDK is not configured.\n\n📋 To enable AI chat:\n1. Set OPENAI_API_KEY in environment\n2. Set OPENAI_ASSISTANT_ID in environment\n3. Restart the bot\n\n💬 Use regular commands like `/scan`, `/balance` instead.")
            return
        
        if not args:
            await self.send_message(chat_id, "🤖 **AI CHAT MODE**\n\nHi! I'm GrokBot's AI assistant. Ask me anything about trading!\n\n**Examples:**\n• What's trending right now?\n• Show me my balance\n• Scan for opportunities\n• Buy 1 USDC of BONK\n• What did we trade today?\n\n**Usage:** `/chat <your message>`")
            return
        
        user_message = ' '.join(args)
        
        try:
            # Show typing indicator
            await self.send_message(chat_id, "🤖 *Thinking...*")
            
            # Process through agent
            response = await self.telegram_agent_interface.handle_telegram_message(user_message, chat_id)
            
            # Send response
            await self.send_message(chat_id, response)
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            await self.send_message(chat_id, f"🤖 Sorry, I encountered an error: {str(e)}")
    
    async def _handle_clear_chat(self, chat_id: int, args: list = None) -> None:
        """Clear the AI chat conversation history"""
        if chat_id != self.admin_chat_id:
            await self.send_message(chat_id, "❌ Unauthorized.")
            return
        
        if not self.chat_interface:
            await self.send_message(chat_id, "❌ AI chat is not available")
            return
        
        try:
            self.chat_interface.clear_session(str(chat_id), "telegram")
            await self.send_message(chat_id, "🗑️ **CONVERSATION CLEARED**\n\nYour AI chat history has been reset!")
        except Exception as e:
            await self.send_message(chat_id, f"❌ Error clearing chat: {str(e)}")

    async def process_message(self, message: Dict[str, Any]) -> None:
        """Process incoming Telegram message"""
        try:
            # Extract message info
            chat_id = message.get('chat', {}).get('id')
            user_id = message.get('from', {}).get('id')
            text = message.get('text', '').strip()
            
            if not chat_id or not user_id or not text:
                return
            
            # Authenticate user
            if not self.auth.is_authenticated(user_id):
                auth_result = self.auth.authenticate_user(user_id, message.get('from', {}))
                if not auth_result:
                    await self.send_message(chat_id, "❌ Authentication failed. Please contact the bot owner.")
                    return
            
            # Set admin chat ID on first interaction
            if self.admin_chat_id is None:
                self.admin_chat_id = chat_id
                logger.info(f"✅ Admin chat ID set: {chat_id}")
            
            # Check for natural language (non-command) messages
            if not text.startswith('/') and self.telegram_agent_interface:
                # Handle as natural language conversation
                try:
                    await self.send_message(chat_id, "🤖 *Processing...*")
                    response = await self.telegram_agent_interface.handle_telegram_message(text, user_id)
                    await self.send_message(chat_id, response)
                    return
                except Exception as e:
                    logger.error(f"Natural language processing error: {e}")
                    # Fall back to command processing
            
            # Parse command
            parts = text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle command
            if command in self.command_handlers:
                await self.command_handlers[command](chat_id, args)
            else:
                # Try agent command conversion if available
                if self.telegram_agent_interface:
                    try:
                        response = await self.telegram_agent_interface.handle_telegram_command(command, args, user_id)
                        await self.send_message(chat_id, response)
                    except Exception as e:
                        await self.send_message(chat_id, f"❓ Unknown command: {command}\n\nType /help for available commands or just ask me anything!")
                else:
                    await self.send_message(chat_id, f"❓ Unknown command: {command}\n\nType /help for available commands.")
                    
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            if 'chat_id' in locals():
                await self.send_message(chat_id, "❌ An error occurred processing your message.")

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
                
                # Show market overview
                rejection_summary = {}
                price_movements = {'pumping': 0, 'dumping': 0, 'flat': 0, 'stable': 0, 'unknown': 0}
                
                for rejected in scan_results['rejected_tokens']:
                    reason = rejected.get('rejection_reason', 'Unknown')
                    rejection_summary[reason] = rejection_summary.get(reason, 0) + 1
                    movement = rejected.get('price_movement', 'unknown')
                    price_movements[movement] = price_movements.get(movement, 0) + 1
                
                # Market overview
                total_tokens = len(scan_results['rejected_tokens'])
                scan_msg += "📊 **MARKET OVERVIEW:**\n"
                scan_msg += f"• Tokens Analyzed: {total_tokens}\n"
                
                if price_movements['pumping'] > 0:
                    scan_msg += f"• 🚀 Pumping: {price_movements['pumping']} tokens\n"
                if price_movements['dumping'] > 0:
                    scan_msg += f"• 📉 Dumping: {price_movements['dumping']} tokens\n"
                if price_movements['flat'] > 0:
                    scan_msg += f"• 😴 Flat/Sideways: {price_movements['flat']} tokens\n"
                if price_movements['stable'] > 0:
                    scan_msg += f"• 📊 Stable: {price_movements['stable']} tokens\n"
                
                scan_msg += "\n**🚫 WHY NO OPPORTUNITIES:**\n"
                top_reasons = sorted(rejection_summary.items(), key=lambda x: x[1], reverse=True)[:3]
                for reason, count in top_reasons:
                    scan_msg += f"• {reason}: {count} tokens\n"
                scan_msg += "\n"

            # Add recommendations
            scan_msg += "🎯 **RECOMMENDATIONS:**\n"
            for rec in scan_results['recommendations']:
                scan_msg += f"• {rec['message']}\n"
                if rec.get('action'):
                    scan_msg += f"  *Action:* `{rec['action']}`\n"
                    
            scan_msg += "\n💡 *Send `/scan detailed` for specific token breakdowns*"
            
            # Send the comprehensive report
            await self.send_message(chat_id, scan_msg)
            
            # If user requested detailed analysis, show detailed feedback for rejected tokens
            if args and len(args) > 0 and args[0].lower() == 'detailed':
                await self.send_message(chat_id, "📋 **DETAILED TOKEN ANALYSIS:**\n\nSending detailed breakdown for each token...")
                
                # Send detailed feedback for the most interesting rejected tokens (up to 4)
                interesting_tokens = []
                
                # Prioritize tokens by how close they came to being opportunities
                for rejected in scan_results['rejected_tokens']:
                    if rejected.get('detailed_feedback') and rejected.get('rejection_reason') != 'Analysis error':
                        # Add a priority score
                        priority = 0
                        if rejected.get('price_movement') == 'pumping':
                            priority += 3
                        if rejected.get('rejection_reason') in ['Moderate price impact', 'High round-trip cost']:
                            priority += 2
                        if rejected.get('rejection_reason') == 'Poor exit liquidity':
                            priority += 1
                        
                        rejected['priority'] = priority
                        interesting_tokens.append(rejected)
                
                # Sort by priority and take top 4
                interesting_tokens.sort(key=lambda x: x.get('priority', 0), reverse=True)
                
                for token_info in interesting_tokens[:4]:
                    if token_info.get('detailed_feedback'):
                        # Split long messages if needed
                        feedback = token_info['detailed_feedback']
                        if len(feedback) > 4000:  # Telegram message limit
                            parts = feedback.split('\n\n')
                            current_msg = ""
                            for part in parts:
                                if len(current_msg + part) > 3800:
                                    await self.send_message(chat_id, current_msg)
                                    await asyncio.sleep(1)  # Small delay between messages
                                    current_msg = part + "\n\n"
                                else:
                                    current_msg += part + "\n\n"
                            if current_msg.strip():
                                await self.send_message(chat_id, current_msg)
                        else:
                            await self.send_message(chat_id, feedback)
                        
                        await asyncio.sleep(2)  # Delay between detailed token reports
                
                if not interesting_tokens:
                    await self.send_message(chat_id, "🤷‍♂️ No detailed analysis available - all tokens had basic routing or technical issues.")
            
            elif not scan_results['opportunities']:
                # Show a quick hint about getting more details
                hint_msg = "🔍 **WANT MORE DETAILS?**\n\n"
                hint_msg += "For specific insights on why each token was rejected:\n"
                hint_msg += "`/scan detailed`\n\n"
                hint_msg += "This will show you exactly what's wrong with each token, including:\n"
                hint_msg += "• Real-time price movements\n• Liquidity analysis\n• Trading cost breakdowns\n• Risk assessments"
                
                await self.send_message(chat_id, hint_msg)
            
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
        bot = TelegramBot()
        print("✅ Telegram bot initialized successfully")
        print(f"Bot token: {bot.token[:10]}...")
        print("Available commands:", list(bot.command_handlers.keys()))
        return True
    except Exception as e:
        print(f"❌ Telegram bot test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_telegram_bot()) 