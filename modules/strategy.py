"""
🤖 Enhanced Trading Strategy Module - Auto Scalp & Snipe
Advanced autonomous trading with token discovery, safety checks, and scalping strategies
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import aiohttp
import json
from dataclasses import dataclass

# Import our new modules
try:
    from .scanner import Token, SolanaTokenScanner
    from .safety import SolanaTokenSafety, SafetyResult
except ImportError:
    # Fallback for testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from scanner import Token, SolanaTokenScanner
    from safety import SolanaTokenSafety, SafetyResult

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradePosition:
    """Active trading position"""
    token: Token
    entry_price: float
    entry_time: datetime
    amount_usd: float
    take_profit: float
    stop_loss: float
    position_type: str  # 'scalp' or 'swing'
    transaction_id: Optional[str] = None

class TradingStrategy:
    def __init__(self, wallet, trader, telegram_bot):
        self.wallet = wallet
        self.trader = trader
        self.telegram_bot = telegram_bot
        self.is_running = False
        self.last_scan = None
        
        # Enhanced strategy parameters
        self.min_profit_threshold = 0.02  # 2% minimum profit
        self.max_trade_size_usd = 5.0     # Max $5 per trade
        self.scan_interval = 90           # Scan every 90 seconds (optimized for new tokens)
        self.daily_trade_limit = 15       # Increased to 15 trades per day
        self.trades_today = 0
        self.last_reset = datetime.now().date()
        
        # Scalping parameters
        self.scalp_take_profit = 0.30     # 30% take profit for scalps
        self.scalp_stop_loss = 0.10       # 10% stop loss for scalps
        self.min_pump_threshold = 0.25    # 25% minimum pump to enter
        self.max_age_minutes = 60         # Only trade tokens < 1 hour old
        self.min_liquidity_usd = 5000     # Minimum $5k liquidity
        
        # Position tracking
        self.active_positions: List[TradePosition] = []
        self.scanner: Optional[SolanaTokenScanner] = None
        self.safety: Optional[SolanaTokenSafety] = None
        
        # Trading pairs to monitor
        self.trading_pairs = [
            {'from': 'USDC', 'to': 'SOL', 'from_addr': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'to_addr': 'So11111111111111111111111111111111111111112'},
            {'from': 'SOL', 'to': 'USDC', 'from_addr': 'So11111111111111111111111111111111111111112', 'to_addr': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
        ]
        
        # Popular Solana tokens to scan
        self.popular_tokens = {
            'WIF': '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr',  # dogwifhat
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',   # Bonk
            'POPCAT': '6n7HuEbFUYJxSjvKsAFrGjjhz4WjLU4Vm6wJ17KhLhKn', # Popcat
            'WEN': '9VNRRgBVd9Fqf2fEAhrDVJCdgpXbZHBUFPgNvjQbKF1b',     # Wen
            'BOME': '3K6rftdAaQYMPunrtNRHgnK2UAtjm2JwyT2oCiTDoubl',    # Book of Meme
            'PEPE': '2iKQgpqKU4C2ek4BSCNpEBKgAT1qqBFGGcjKpxBW8nYa',    # Pepe (SOL)
            'MEW': '4HqRNOFrFjQJJQvELwj6RQeVJfX9Hs6o9uWGJdgQY1nY',     # Cat in a dogs world
            'MYRO': '9nEqaUcb16sQ3Tn1psbzWqD71n9Q1KfVt4qgWG3ZqnGD',   # Myro
        }
        
        logger.info("🤖 Trading Strategy initialized")
        logger.info(f"📊 Min profit: {self.min_profit_threshold*100}%")
        logger.info(f"💰 Max trade: ${self.max_trade_size_usd}")
        logger.info(f"⏰ Scan interval: {self.scan_interval}s")

    async def start_automated_trading(self):
        """Start the automated trading loop"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 Starting automated trading...")
        
        # Notify user
        await self.telegram_bot.send_message(
            self.telegram_bot.admin_chat_id, 
            "🤖 **AUTOMATED TRADING STARTED**\n\n"
            f"📊 Scanning every {self.scan_interval}s for opportunities\n"
            f"💰 Max trade size: ${self.max_trade_size_usd}\n"
            f"📈 Min profit: {self.min_profit_threshold*100}%\n"
            f"🔢 Daily limit: {self.daily_trade_limit} trades\n\n"
            "Use `/stop_auto` to stop automated trading"
        )
        
        while self.is_running:
            try:
                await self._scan_and_trade()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def stop_automated_trading(self):
        """Stop the automated trading loop"""
        self.is_running = False
        logger.info("⏹️ Automated trading stopped")
        
        await self.telegram_bot.send_message(
            self.telegram_bot.admin_chat_id,
            "⏹️ **AUTOMATED TRADING STOPPED**\n\n"
            f"📊 Trades executed today: {self.trades_today}"
        )

    async def _scan_and_trade(self):
        """Scan for opportunities and execute profitable trades"""
        # Reset daily counter
        if datetime.now().date() > self.last_reset:
            self.trades_today = 0
            self.last_reset = datetime.now().date()
            
        # Check daily limit
        if self.trades_today >= self.daily_trade_limit:
            return
            
        logger.info(f"🔍 Scanning for opportunities... ({self.trades_today}/{self.daily_trade_limit} trades today)")
        
        # Get current balances
        balances = await self.wallet.get_all_balances()
        if not balances['success']:
            return
            
        current_balances = balances['balances']
        
        # Scan each trading pair
        for pair in self.trading_pairs:
            try:
                opportunity = await self._check_arbitrage_opportunity(pair, current_balances)
                if opportunity:
                    await self._execute_opportunity(opportunity)
                    self.trades_today += 1
                    break  # Only one trade per scan
            except Exception as e:
                logger.error(f"Error checking pair {pair['from']}->{pair['to']}: {e}")

    async def _check_arbitrage_opportunity(self, pair: Dict, balances: Dict) -> Dict[str, Any]:
        """Check if there's a profitable arbitrage opportunity"""
        from_token = pair['from']
        to_token = pair['to']
        
        # Check if we have enough balance
        available_balance = balances.get(from_token, 0)
        if available_balance < 1.0:  # Need at least 1 token
            return None
            
        # Calculate trade size (smaller of available balance or max trade size)
        if from_token == 'USDC':
            trade_size = min(available_balance, self.max_trade_size_usd)
            trade_amount = trade_size * 1000000  # Convert to units
        else:  # SOL
            sol_price = await self.telegram_bot._get_sol_price()
            max_sol = self.max_trade_size_usd / sol_price
            trade_size = min(available_balance, max_sol)
            trade_amount = int(trade_size * 1000000000)  # Convert to lamports
            
        # Get swap route
        route_result = await self.trader.get_swap_route(
            token_in_address=pair['from_addr'],
            token_out_address=pair['to_addr'],
            in_amount=str(trade_amount),
            from_address=self.wallet.get_address()
        )
        
        if not route_result.get('success'):
            return None
            
        quote = route_result.get('quote', {})
        price_impact = float(quote.get('priceImpactPct', 0))
        
        # Calculate expected profit (simple strategy - look for low price impact)
        if price_impact < self.min_profit_threshold:
            # This is a profitable opportunity
            out_amount = float(quote.get('outAmount', 0))
            
            # Calculate output in readable format
            if to_token == 'SOL':
                readable_output = out_amount / 1000000000
            else:  # USDC
                readable_output = out_amount / 1000000
                
            return {
                'pair': pair,
                'trade_size': trade_size,
                'expected_output': readable_output,
                'price_impact': price_impact,
                'profit_potential': self.min_profit_threshold - price_impact,
                'route_result': route_result
            }
            
        return None

    async def _execute_opportunity(self, opportunity: Dict):
        """Execute a profitable trading opportunity"""
        pair = opportunity['pair']
        
        logger.info(f"💰 EXECUTING OPPORTUNITY: {opportunity['trade_size']} {pair['from']} -> {opportunity['expected_output']:.6f} {pair['to']}")
        
        # Notify user about the trade
        await self.telegram_bot.send_message(
            self.telegram_bot.admin_chat_id,
            f"🎯 **OPPORTUNITY FOUND!**\n\n"
            f"💱 Trade: {opportunity['trade_size']} {pair['from']} → {opportunity['expected_output']:.6f} {pair['to']}\n"
            f"📊 Price Impact: {opportunity['price_impact']:.2f}%\n"
            f"💰 Profit Potential: {opportunity['profit_potential']:.2f}%\n\n"
            f"⚡ Executing automatically..."
        )
        
        # Execute the trade
        raw_tx = opportunity['route_result'].get('raw_tx', {})
        if isinstance(raw_tx, dict):
            raw_tx = raw_tx.get('swapTransaction', raw_tx)
            
        result = await self.wallet.execute_swap(raw_tx)
        
        if result['success']:
            await self.telegram_bot.send_message(
                self.telegram_bot.admin_chat_id,
                f"✅ **TRADE EXECUTED SUCCESSFULLY!**\n\n"
                f"🔗 Transaction: {result['explorer_url']}\n"
                f"📊 Trade #{self.trades_today} today\n\n"
                f"💰 Check your updated balance with /balance"
            )
        else:
            await self.telegram_bot.send_message(
                self.telegram_bot.admin_chat_id,
                f"❌ **TRADE FAILED**\n\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )

    async def scan_market_opportunities(self) -> Dict[str, Any]:
        """
        Comprehensive one-shot market scan for trading opportunities
        Returns detailed analysis of what's worth trading and why
        """
        logger.info("🔍 Starting comprehensive market scan...")
        
        scan_results = {
            'scan_time': datetime.now().isoformat(),
            'opportunities': [],
            'rejected_tokens': [],
            'market_summary': {},
            'recommendations': []
        }
        
        # Get current wallet balances
        balances = await self.wallet.get_all_balances()
        if not balances['success']:
            scan_results['error'] = "Failed to get wallet balances"
            return scan_results
            
        current_balances = balances['balances']
        usdc_balance = current_balances.get('USDC', 0)
        sol_balance = current_balances.get('SOL', 0)
        
        # Get SOL price for calculations
        sol_price = await self.telegram_bot._get_sol_price()
        scan_results['market_summary']['sol_price'] = sol_price
        scan_results['market_summary']['usdc_balance'] = usdc_balance
        scan_results['market_summary']['sol_balance'] = sol_balance
        
        # If we don't have enough balance to trade, explain why
        total_balance_usd = usdc_balance + (sol_balance * sol_price)
        if total_balance_usd < 1.0:
            scan_results['recommendations'].append({
                'type': 'insufficient_balance',
                'message': f"Insufficient balance for trading. Total: ${total_balance_usd:.2f}, need at least $1.00",
                'action': 'Add more USDC or SOL to your wallet'
            })
            return scan_results
            
        # Scan each popular token
        for token_symbol, token_address in self.popular_tokens.items():
            try:
                token_analysis = await self._analyze_token_opportunity(
                    token_symbol, token_address, usdc_balance, sol_balance, sol_price
                )
                
                if token_analysis['is_opportunity']:
                    scan_results['opportunities'].append(token_analysis)
                else:
                    scan_results['rejected_tokens'].append(token_analysis)
                    
            except Exception as e:
                logger.error(f"Failed to analyze {token_symbol}: {e}")
                scan_results['rejected_tokens'].append({
                    'token': token_symbol,
                    'error': str(e),
                    'reason': 'Analysis failed'
                })
                
        # Sort opportunities by profit potential
        scan_results['opportunities'].sort(key=lambda x: x.get('profit_score', 0), reverse=True)
        
        # Generate final recommendations
        if scan_results['opportunities']:
            best_opportunity = scan_results['opportunities'][0]
            scan_results['recommendations'].append({
                'type': 'buy_recommendation',
                'token': best_opportunity['token'],
                'message': f"Best opportunity: {best_opportunity['token']} - {best_opportunity['reason']}",
                'action': f"Consider: /swap {best_opportunity['suggested_amount']} USDC {best_opportunity['token']}"
            })
        else:
            # Explain why nothing is worth trading
            top_rejection_reasons = {}
            for rejected in scan_results['rejected_tokens']:
                reason = rejected.get('rejection_reason', 'Unknown')
                top_rejection_reasons[reason] = top_rejection_reasons.get(reason, 0) + 1
                
            most_common_reason = max(top_rejection_reasons.items(), key=lambda x: x[1])[0] if top_rejection_reasons else "No clear pattern"
            
            scan_results['recommendations'].append({
                'type': 'no_opportunities',
                'message': f"No profitable opportunities found. Most common issue: {most_common_reason}",
                'action': 'Wait for better market conditions or lower risk tolerance'
            })
            
        return scan_results

    async def _analyze_token_opportunity(self, token_symbol: str, token_address: str, usdc_balance: float, sol_balance: float, sol_price: float) -> Dict[str, Any]:
        """Analyze a specific token for trading opportunity with detailed feedback"""
        
        analysis = {
            'token': token_symbol,
            'address': token_address,
            'is_opportunity': False,
            'profit_score': 0,
            'reason': '',
            'rejection_reason': '',
            'detailed_feedback': '',
            'market_data': {},
            'metrics': {},
            'suggested_amount': 0,
            'price_movement': 'unknown',
            'risk_level': 'unknown'
        }
        
        try:
            # First, get real-time market data from DexScreener
            await self._fetch_market_data(analysis, token_address, token_symbol)
            
            # Test a small USDC->Token swap to get pricing info
            test_amount = min(2.0, usdc_balance * 0.5)  # Test with $2 or 50% of balance
            if test_amount < 1.0:
                analysis['rejection_reason'] = 'Insufficient balance for meaningful test'
                analysis['reason'] = f'Need at least $1 USDC for testing, have ${usdc_balance:.2f}'
                analysis['detailed_feedback'] = f"""
🔴 **{token_symbol} - INSUFFICIENT BALANCE**

💰 **Your Balance Issue:**
• Current USDC: ${usdc_balance:.2f}
• Minimum needed: $1.00 for testing
• Recommendation: Add more USDC to test opportunities

📊 **Market Context:**
• {analysis['market_data'].get('price_trend', 'Unable to fetch price data')}
• This token might have potential but can't analyze properly
                """
                return analysis
                
            # Get swap route from USDC to token (with enhanced error handling)
            route_result = await self.trader.get_swap_route(
                token_in_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                token_out_address=token_address,
                in_amount=str(int(test_amount * 1000000)),  # Convert to USDC units
                from_address=self.wallet.get_address(),
                slippage=1.0
            )
            
            if not route_result.get('success'):
                analysis['rejection_reason'] = 'No swap route available'
                analysis['reason'] = f'GMGN API could not find a route for {token_symbol}'
                
                # Enhanced feedback for swap route failures
                route_error = route_result.get('error', 'Unknown routing error')
                analysis['detailed_feedback'] = f"""
⚠️ **{token_symbol} - NO SWAP ROUTE AVAILABLE**

🔄 **Routing Issue:**
• GMGN API Error: {route_error}
• This usually means: Low liquidity, delisted, or routing problems
• The token exists but can't be traded efficiently right now

📊 **Market Analysis:**
{analysis['market_data'].get('detailed_analysis', '• Unable to fetch current market data')}

💡 **What This Means:**
• Token might be too illiquid for safe trading
• Could be experiencing technical issues
• May have been delisted from major DEXs
• Wait for better liquidity or try a different token

🎯 **Alternative Action:**
Try manual swap with very small amount to test: `/swap 0.5 USDC {token_symbol}`
                """
                return analysis
                
            quote = route_result.get('quote', {})
            price_impact = float(quote.get('priceImpactPct', 100))
            
            # Enhanced price impact analysis
            analysis['metrics']['price_impact'] = price_impact
            analysis['metrics']['estimated_tokens'] = float(quote.get('outAmount', 0))
            
            if price_impact > 10.0:
                analysis['rejection_reason'] = 'High price impact'
                analysis['reason'] = f'Price impact too high: {price_impact:.2f}% (max: 10%)'
                analysis['risk_level'] = 'very_high'
                analysis['detailed_feedback'] = f"""
🔴 **{token_symbol} - HIGH PRICE IMPACT RISK**

⚠️ **Price Impact Analysis:**
• Your ${test_amount:.2f} trade would cause {price_impact:.2f}% price impact
• This is VERY HIGH (safe level: <3%)
• Indicates low liquidity or large trade size

📊 **Market Context:**
{analysis['market_data'].get('detailed_analysis', '• Price movement data unavailable')}

💡 **Why This Matters:**
• You'd buy at artificially high prices
• Could be hard to sell without big losses
• Token may be low-volume or manipulated

🎯 **Better Strategy:**
• Wait for higher liquidity
• Try smaller amount like $0.50
• Look for tokens with <3% impact
• Consider popular tokens instead
                """
                return analysis
                
            if price_impact > 5.0:
                analysis['rejection_reason'] = 'Moderate price impact'
                analysis['reason'] = f'Price impact concerning: {price_impact:.2f}% (prefer <5%)'
                analysis['risk_level'] = 'high'
                analysis['detailed_feedback'] = f"""
🟡 **{token_symbol} - MODERATE PRICE IMPACT**

⚠️ **Price Impact Analysis:**
• Your ${test_amount:.2f} trade would cause {price_impact:.2f}% price impact
• This is HIGHER than ideal (prefer <3%)
• Tradeable but not optimal

📊 **Market Context:**
{analysis['market_data'].get('detailed_analysis', '• Price movement data unavailable')}

💡 **Risk Assessment:**
• Acceptable for small trades
• Watch out for slippage on larger amounts
• Could indicate moderate liquidity

🎯 **If You Trade:**
• Keep position size very small
• Use higher slippage tolerance (2-3%)
• Monitor closely for exit opportunities
                """
            
            # Check if there's a reverse route (liquidity test)
            reverse_route = await self.trader.get_swap_route(
                token_in_address=token_address,
                token_out_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                in_amount=quote.get('outAmount', '1000'),  # Use output from first swap
                from_address=self.wallet.get_address(),
                slippage=1.0
            )
            
            reverse_price_impact = 100.0
            if reverse_route.get('success'):
                reverse_quote = reverse_route.get('quote', {})
                reverse_price_impact = float(reverse_quote.get('priceImpactPct', 100))
                
            analysis['metrics']['reverse_price_impact'] = reverse_price_impact
            analysis['metrics']['round_trip_efficiency'] = self._calculate_round_trip_efficiency(test_amount, reverse_quote.get('outAmount', '0'))
            
            if reverse_price_impact > 15.0:
                analysis['rejection_reason'] = 'Poor exit liquidity'
                analysis['reason'] = f'Difficult to sell back: {reverse_price_impact:.2f}% impact'
                analysis['risk_level'] = 'very_high'
                analysis['detailed_feedback'] = f"""
🔴 **{token_symbol} - POOR EXIT LIQUIDITY**

🚪 **Exit Analysis:**
• Selling would cause {reverse_price_impact:.2f}% price impact
• This is VERY HIGH (danger zone: >10%)
• Could get stuck in the position

📊 **Market Context:**
{analysis['market_data'].get('detailed_analysis', '• Price movement data unavailable')}

💡 **Why This Is Dangerous:**
• Easy to buy, hard to sell
• Could be a "honeypot" or low-liquidity trap
• Risk of significant losses on exit

🎯 **Recommendation:**
• AVOID this token for now
• Look for tokens with <10% exit impact
• Wait for better liquidity conditions
• Consider more established tokens
                """
                return analysis
                
            # Calculate profit potential and trading costs
            total_slippage = price_impact + reverse_price_impact
            analysis['metrics']['total_trading_cost'] = total_slippage
            
            if total_slippage > 8.0:
                analysis['rejection_reason'] = 'High round-trip cost'
                analysis['reason'] = f'Total trading cost: {total_slippage:.2f}% (too high for profit)'
                analysis['risk_level'] = 'high'
                analysis['detailed_feedback'] = f"""
🟡 **{token_symbol} - HIGH TRADING COSTS**

💸 **Cost Analysis:**
• Buy Impact: {price_impact:.2f}%
• Sell Impact: {reverse_price_impact:.2f}%
• Total Cost: {total_slippage:.2f}%
• Need >{total_slippage:.2f}% price move just to break even

📊 **Market Context:**
{analysis['market_data'].get('detailed_analysis', '• Price movement data unavailable')}

💡 **Profitability Challenge:**
• High trading costs eat into profits
• Token needs significant movement to be profitable
• Better opportunities likely exist

🎯 **Strategy:**
• Wait for better market conditions
• Look for tokens with <5% total cost
• Consider tokens with recent momentum
                """
                return analysis
                
            # This token passes basic tests - it's an opportunity!
            analysis['is_opportunity'] = True
            analysis['profit_score'] = 10.0 - total_slippage  # Higher score = better opportunity
            analysis['suggested_amount'] = min(self.max_trade_size_usd, usdc_balance * 0.2)  # Suggest 20% of balance or max trade size
            analysis['risk_level'] = 'low' if total_slippage < 3.0 else 'moderate'
            
            # Generate positive reasoning with detailed feedback
            reasons = []
            if price_impact < 2.0:
                reasons.append(f"Excellent liquidity ({price_impact:.2f}% impact)")
            elif price_impact < 5.0:
                reasons.append(f"Good liquidity ({price_impact:.2f}% impact)")
            
            if reverse_price_impact < 5.0:
                reasons.append(f"Easy exit ({reverse_price_impact:.2f}% impact)")
            elif reverse_price_impact < 10.0:
                reasons.append(f"Reasonable exit ({reverse_price_impact:.2f}% impact)")
            
            if total_slippage < 3.0:
                reasons.append(f"Low trading costs ({total_slippage:.2f}%)")
            elif total_slippage < 5.0:
                reasons.append(f"Acceptable costs ({total_slippage:.2f}%)")
                
            analysis['reason'] = "OPPORTUNITY: " + ", ".join(reasons)
            analysis['detailed_feedback'] = f"""
🟢 **{token_symbol} - TRADING OPPORTUNITY FOUND!**

✅ **Opportunity Analysis:**
• Buy Impact: {price_impact:.2f}% (Excellent: <2%)
• Sell Impact: {reverse_price_impact:.2f}% (Good: <10%)
• Total Cost: {total_slippage:.2f}% (Low: <5%)
• Profit Score: {analysis['profit_score']:.1f}/10

📊 **Market Context:**
{analysis['market_data'].get('detailed_analysis', '• Price movement data unavailable')}

💡 **Why This Works:**
• Good liquidity for entry and exit
• Low trading costs allow for profit
• Established token with decent volume

🎯 **Suggested Action:**
`/swap {analysis['suggested_amount']:.1f} USDC {token_symbol}`

⚠️ **Risk Management:**
• Start with suggested amount
• Set stop loss at -10%
• Take profits at +15-20%
• Monitor closely after entry
            """
            
        except Exception as e:
            analysis['rejection_reason'] = 'Analysis error'
            analysis['reason'] = f'Technical error: {str(e)}'
            analysis['detailed_feedback'] = f"""
🔴 **{token_symbol} - ANALYSIS ERROR**

❌ **Technical Issue:**
• Error: {str(e)}
• Unable to complete full analysis
• This could be temporary

🔄 **Possible Causes:**
• API rate limiting
• Network connectivity issues
• Token data unavailable
• Temporary service disruption

🎯 **Next Steps:**
• Try scanning again in a few minutes
• Check if token address is correct
• Consider manual testing with small amount
            """
            
        return analysis

    def _calculate_round_trip_efficiency(self, initial_usdc: float, final_usdc_str: str) -> float:
        """Calculate how much USDC you'd get back from a round-trip trade"""
        try:
            final_usdc = float(final_usdc_str) / 1000000  # Convert from USDC units
            return (final_usdc / initial_usdc) if initial_usdc > 0 else 0
        except:
            return 0

    async def _fetch_market_data(self, analysis: dict, token_address: str, token_symbol: str):
        """Fetch real-time market data from DexScreener"""
        try:
            if not hasattr(self, '_market_session'):
                self._market_session = aiohttp.ClientSession()
            
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            async with self._market_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        # Get the most liquid pair
                        best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))
                        
                        price_usd = float(best_pair.get('priceUsd', 0) or 0)
                        price_change_5m = float(best_pair.get('priceChange', {}).get('m5', 0) or 0)
                        price_change_1h = float(best_pair.get('priceChange', {}).get('h1', 0) or 0)
                        price_change_24h = float(best_pair.get('priceChange', {}).get('h24', 0) or 0)
                        volume_24h = float(best_pair.get('volume', {}).get('h24', 0) or 0)
                        liquidity_usd = float(best_pair.get('liquidity', {}).get('usd', 0) or 0)
                        
                        analysis['market_data'] = {
                            'price_usd': price_usd,
                            'price_change_5m': price_change_5m,
                            'price_change_1h': price_change_1h,
                            'price_change_24h': price_change_24h,
                            'volume_24h': volume_24h,
                            'liquidity_usd': liquidity_usd,
                            'dex': best_pair.get('dexId', 'unknown')
                        }
                        
                        # Determine price movement trend
                        if price_change_1h > 5:
                            analysis['price_movement'] = 'pumping'
                        elif price_change_1h < -5:
                            analysis['price_movement'] = 'dumping'
                        elif abs(price_change_1h) < 1:
                            analysis['price_movement'] = 'flat'
                        else:
                            analysis['price_movement'] = 'stable'
                        
                        # Create detailed analysis text
                        movement_emoji = {
                            'pumping': '🚀',
                            'dumping': '📉',
                            'flat': '😴',
                            'stable': '📊'
                        }
                        
                        analysis['market_data']['detailed_analysis'] = f"""• Price: ${price_usd:.6f}
• 5m: {price_change_5m:+.1f}% | 1h: {price_change_1h:+.1f}% | 24h: {price_change_24h:+.1f}%
• 24h Volume: ${volume_24h:,.0f}
• Liquidity: ${liquidity_usd:,.0f}
• Status: {movement_emoji.get(analysis['price_movement'], '❓')} {analysis['price_movement'].title()}"""
                        
                        analysis['market_data']['price_trend'] = f"Currently {analysis['price_movement']} ({price_change_1h:+.1f}% 1h)"
                        
                    else:
                        analysis['market_data']['price_trend'] = "No active trading pairs found"
                        analysis['market_data']['detailed_analysis'] = "• No market data available from DexScreener"
                        
        except Exception as e:
            analysis['market_data']['price_trend'] = f"Market data fetch failed: {str(e)}"
            analysis['market_data']['detailed_analysis'] = f"• Unable to fetch market data: {str(e)}"

    async def evaluate_and_trade(self, token: Token) -> None:
        """
        🎯 Enhanced evaluate and trade logic for scalping and sniping
        
        Args:
            token: Token discovered by scanner
        """
        try:
            logger.info(f"🔍 Evaluating {token.symbol} for scalp/snipe opportunity...")
            
            # Quick filters before detailed analysis
            if token.age_minutes > self.max_age_minutes:
                logger.info(f"❌ {token.symbol} too old: {token.age_minutes}m > {self.max_age_minutes}m")
                return
                
            if token.liquidity_usd < self.min_liquidity_usd:
                logger.info(f"❌ {token.symbol} low liquidity: ${token.liquidity_usd:,.0f} < ${self.min_liquidity_usd:,.0f}")
                return
            
            # Check if we already have a position in this token
            for position in self.active_positions:
                if position.token.address == token.address:
                    logger.info(f"⏩ Already have position in {token.symbol}")
                    return
            
            # Safety check
            if self.safety:
                safety_result = await self.safety.is_token_safe(token)
                if not safety_result.is_safe:
                    logger.info(f"🚫 {token.symbol} failed safety check: {safety_result.risk_factors}")
                    return
                    
                logger.info(f"✅ {token.symbol} passed safety check (confidence: {safety_result.confidence_score:.2f})")
            
            # Determine trading strategy
            if token.price_change_5m >= self.min_pump_threshold * 100:  # Convert to percentage
                await self._execute_scalp_trade(token, safety_result)
            elif token.volume_5m_usd > 25000 and token.age_minutes < 30:
                await self._execute_snipe_trade(token, safety_result)
            else:
                logger.info(f"📊 {token.symbol} doesn't meet trading criteria")
                logger.info(f"   5m change: {token.price_change_5m:.1f}% (need >{self.min_pump_threshold*100:.0f}%)")
                logger.info(f"   Volume: ${token.volume_5m_usd:,.0f} (need >$25k for snipe)")
                
        except Exception as e:
            logger.error(f"❌ Error evaluating {token.symbol}: {e}")
    
    async def _execute_scalp_trade(self, token: Token, safety_result: SafetyResult) -> None:
        """
        ⚡ Execute scalping trade for pumping token
        
        Args:
            token: Token to scalp
            safety_result: Safety analysis result
        """
        try:
            logger.info(f"⚡ SCALP OPPORTUNITY: {token.symbol} (+{token.price_change_5m:.1f}%)")
            
            # Calculate position size based on confidence
            confidence_multiplier = min(safety_result.confidence_score * 1.5, 1.0)
            position_size_usd = self.max_trade_size_usd * confidence_multiplier
            
            # Execute buy order
            buy_result = await self._execute_buy_order(token, position_size_usd, 'scalp')
            
            if buy_result['success']:
                logger.info(f"✅ Scalp entry successful: {token.symbol} @ ${position_size_usd:.2f}")
                
                # Add position to tracking
                position = TradePosition(
                    token=token,
                    entry_price=token.price_usd,
                    entry_time=datetime.utcnow(),
                    amount_usd=position_size_usd,
                    take_profit=token.price_usd * (1 + self.scalp_take_profit),
                    stop_loss=token.price_usd * (1 - self.scalp_stop_loss),
                    position_type='scalp',
                    transaction_id=buy_result.get('transaction_id')
                )
                
                self.active_positions.append(position)
                self.trades_today += 1
                
                # Notify via Telegram
                await self._notify_trade_entry(position)
                
            else:
                logger.error(f"❌ Scalp entry failed for {token.symbol}: {buy_result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Scalp execution error for {token.symbol}: {e}")
    
    async def _execute_snipe_trade(self, token: Token, safety_result: SafetyResult) -> None:
        """
        🎯 Execute snipe trade for high volume early token
        
        Args:
            token: Token to snipe
            safety_result: Safety analysis result
        """
        try:
            logger.info(f"🎯 SNIPE OPPORTUNITY: {token.symbol} (${token.volume_5m_usd:,.0f} volume)")
            
            # More conservative sizing for snipes
            confidence_multiplier = safety_result.confidence_score * 0.8
            position_size_usd = self.max_trade_size_usd * confidence_multiplier
            
            # Execute buy order
            buy_result = await self._execute_buy_order(token, position_size_usd, 'snipe')
            
            if buy_result['success']:
                logger.info(f"✅ Snipe entry successful: {token.symbol} @ ${position_size_usd:.2f}")
                
                # More aggressive targets for snipes
                position = TradePosition(
                    token=token,
                    entry_price=token.price_usd,
                    entry_time=datetime.utcnow(),
                    amount_usd=position_size_usd,
                    take_profit=token.price_usd * 1.50,  # 50% target
                    stop_loss=token.price_usd * 0.85,   # 15% stop loss
                    position_type='snipe',
                    transaction_id=buy_result.get('transaction_id')
                )
                
                self.active_positions.append(position)
                self.trades_today += 1
                
                # Notify via Telegram
                await self._notify_trade_entry(position)
                
            else:
                logger.error(f"❌ Snipe entry failed for {token.symbol}: {buy_result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Snipe execution error for {token.symbol}: {e}")
    
    async def _execute_buy_order(self, token: Token, amount_usd: float, trade_type: str) -> Dict[str, Any]:
        """
        💰 Execute buy order using GMGN
        
        Args:
            token: Token to buy
            amount_usd: USD amount to spend
            trade_type: 'scalp' or 'snipe'
            
        Returns:
            Trade execution result
        """
        try:
            # Get swap route
            route = await self.trader.get_swap_route(
                token_in_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                token_out_address=token.address,
                in_amount=amount_usd,
                from_address=self.wallet.get_address(),
                slippage=2.0  # 2% slippage for fast execution
            )
            
            if not route.get('success'):
                return {'success': False, 'error': route.get('error', 'Route failed')}
            
            # Execute the swap
            result = await self.wallet.execute_swap(route)
            
            if result.get('success'):
                return {
                    'success': True,
                    'transaction_id': result.get('signature'),
                    'amount_usd': amount_usd,
                    'trade_type': trade_type
                }
            else:
                return {'success': False, 'error': result.get('error', 'Execution failed')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _notify_trade_entry(self, position: TradePosition) -> None:
        """
        📱 Send Telegram notification for trade entry
        
        Args:
            position: Trade position entered
        """
        try:
            message = f"""
🚀 **{position.position_type.upper()} ENTRY**

💎 **{position.token.symbol}** ({position.token.name})
📍 Address: `{position.token.address}`
💰 Position: ${position.amount_usd:.2f}
📈 Entry: ${position.entry_price:.8f}
🎯 Target: ${position.take_profit:.8f} (+{((position.take_profit/position.entry_price)-1)*100:.1f}%)
🛑 Stop: ${position.stop_loss:.8f} ({((position.stop_loss/position.entry_price)-1)*100:.1f}%)

📊 **Token Metrics:**
⏰ Age: {position.token.age_minutes}m
💧 Liquidity: ${position.token.liquidity_usd:,.0f}
📈 5m Change: {position.token.price_change_5m:+.1f}%
📊 Volume: ${position.token.volume_5m_usd:,.0f}

🔗 [View on Solscan](https://solscan.io/token/{position.token.address})
"""
            
            if self.telegram_bot and hasattr(self.telegram_bot, 'admin_chat_id'):
                await self.telegram_bot.send_message(
                    self.telegram_bot.admin_chat_id,
                    message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to send trade notification: {e}")
    
    async def monitor_positions(self) -> None:
        """
        👀 Monitor active positions and execute stop losses / take profits
        """
        try:
            if not self.active_positions:
                return
                
            logger.info(f"👀 Monitoring {len(self.active_positions)} active positions...")
            
            positions_to_close = []
            
            for position in self.active_positions:
                try:
                    # Get current price (simplified - in reality you'd get from multiple sources)
                    current_price = await self._get_current_token_price(position.token.address)
                    
                    if current_price is None:
                        logger.warning(f"⚠️ Could not get price for {position.token.symbol}")
                        continue
                    
                    # Calculate PnL
                    pnl_pct = ((current_price / position.entry_price) - 1) * 100
                    
                    # Check exit conditions
                    should_exit = False
                    exit_reason = ""
                    
                    if current_price >= position.take_profit:
                        should_exit = True
                        exit_reason = f"Take profit hit: {pnl_pct:+.1f}%"
                    elif current_price <= position.stop_loss:
                        should_exit = True
                        exit_reason = f"Stop loss hit: {pnl_pct:+.1f}%"
                    elif (datetime.utcnow() - position.entry_time).total_seconds() > 3600:  # 1 hour max hold
                        should_exit = True
                        exit_reason = f"Time exit (1h): {pnl_pct:+.1f}%"
                    
                    if should_exit:
                        # Execute exit
                        exit_result = await self._execute_exit_order(position, current_price)
                        
                        if exit_result['success']:
                            logger.info(f"✅ {exit_reason} - {position.token.symbol} closed")
                            positions_to_close.append(position)
                            
                            # Notify exit
                            await self._notify_trade_exit(position, current_price, exit_reason, pnl_pct)
                        else:
                            logger.error(f"❌ Failed to close {position.token.symbol}: {exit_result.get('error')}")
                    else:
                        logger.info(f"📊 {position.token.symbol}: {pnl_pct:+.1f}% (${current_price:.8f})")
                        
                except Exception as e:
                    logger.error(f"❌ Error monitoring position {position.token.symbol}: {e}")
            
            # Remove closed positions
            for position in positions_to_close:
                self.active_positions.remove(position)
                
        except Exception as e:
            logger.error(f"❌ Position monitoring error: {e}")
    
    async def _get_current_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price from DexScreener"""
        try:
            if not hasattr(self, '_price_session'):
                self._price_session = aiohttp.ClientSession()
            
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            
            async with self._price_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    if pairs:
                        # Get the most liquid pair
                        best_pair = max(pairs, key=lambda p: float(p.get('liquidity', {}).get('usd', 0) or 0))
                        return float(best_pair.get('priceUsd', 0) or 0)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Price fetch error for {token_address}: {e}")
            return None
    
    async def _execute_exit_order(self, position: TradePosition, current_price: float) -> Dict[str, Any]:
        """Execute exit order for position"""
        try:
            # Calculate token amount to sell (simplified - in reality track exact amounts)
            token_amount = position.amount_usd / position.entry_price
            
            # Get exit route
            route = await self.trader.get_swap_route(
                token_in_address=position.token.address,
                token_out_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                in_amount=token_amount,
                from_address=self.wallet.get_address(),
                slippage=3.0  # Higher slippage for fast exit
            )
            
            if not route.get('success'):
                return {'success': False, 'error': route.get('error')}
            
            # Execute the swap
            result = await self.wallet.execute_swap(route)
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _notify_trade_exit(self, position: TradePosition, exit_price: float, reason: str, pnl_pct: float) -> None:
        """Send exit notification"""
        try:
            profit_emoji = "🟢" if pnl_pct > 0 else "🔴"
            
            message = f"""
{profit_emoji} **{position.position_type.upper()} EXIT**

💎 **{position.token.symbol}** 
🚪 Exit: ${exit_price:.8f}
📊 PnL: {pnl_pct:+.1f}%
💰 ${position.amount_usd:.2f} → ${position.amount_usd * (1 + pnl_pct/100):.2f}

📋 **Reason:** {reason}
⏰ Hold time: {(datetime.utcnow() - position.entry_time).total_seconds()/60:.0f}m
"""
            
            if self.telegram_bot and hasattr(self.telegram_bot, 'admin_chat_id'):
                await self.telegram_bot.send_message(
                    self.telegram_bot.admin_chat_id,
                    message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to send exit notification: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        return {
            'is_running': self.is_running,
            'trades_today': self.trades_today,
            'daily_limit': self.daily_trade_limit,
            'min_profit': self.min_profit_threshold,
            'max_trade_size': self.max_trade_size_usd,
            'scan_interval': self.scan_interval,
            'last_scan': self.last_scan,
            'active_positions': len(self.active_positions),
            'scalp_params': {
                'take_profit': f"{self.scalp_take_profit*100:.0f}%",
                'stop_loss': f"{self.scalp_stop_loss*100:.0f}%",
                'min_pump': f"{self.min_pump_threshold*100:.0f}%"
            }
        } 