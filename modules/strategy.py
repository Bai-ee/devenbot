"""
Automated Trading Strategy Module
Scans for opportunities and executes trades automatically
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random
import aiohttp
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self, wallet, trader, telegram_bot):
        self.wallet = wallet
        self.trader = trader
        self.telegram_bot = telegram_bot
        self.is_running = False
        self.last_scan = None
        
        # Strategy parameters
        self.min_profit_threshold = 0.02  # 2% minimum profit
        self.max_trade_size_usd = 5.0     # Max $5 per trade
        self.scan_interval = 30           # Scan every 30 seconds
        self.daily_trade_limit = 10       # Max 10 trades per day
        self.trades_today = 0
        self.last_reset = datetime.now().date()
        
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
        """Analyze a specific token for trading opportunity"""
        
        analysis = {
            'token': token_symbol,
            'address': token_address,
            'is_opportunity': False,
            'profit_score': 0,
            'reason': '',
            'rejection_reason': '',
            'metrics': {},
            'suggested_amount': 0
        }
        
        try:
            # Test a small USDC->Token swap to get pricing info
            test_amount = min(2.0, usdc_balance * 0.5)  # Test with $2 or 50% of balance
            if test_amount < 1.0:
                analysis['rejection_reason'] = 'Insufficient balance for meaningful test'
                analysis['reason'] = f'Need at least $1 USDC for testing, have ${usdc_balance:.2f}'
                return analysis
                
            # Get swap route from USDC to token
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
                return analysis
                
            quote = route_result.get('quote', {})
            price_impact = float(quote.get('priceImpactPct', 100))
            
            # Analyze price impact
            analysis['metrics']['price_impact'] = price_impact
            
            if price_impact > 10.0:
                analysis['rejection_reason'] = 'High price impact'
                analysis['reason'] = f'Price impact too high: {price_impact:.2f}% (max: 10%)'
                return analysis
                
            if price_impact > 5.0:
                analysis['rejection_reason'] = 'Moderate price impact'
                analysis['reason'] = f'Price impact concerning: {price_impact:.2f}% (prefer <5%)'
                return analysis
                
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
            
            if reverse_price_impact > 15.0:
                analysis['rejection_reason'] = 'Poor exit liquidity'
                analysis['reason'] = f'Difficult to sell back: {reverse_price_impact:.2f}% impact'
                return analysis
                
            # Calculate profit potential (this is simplified - in reality you'd want more complex analysis)
            total_slippage = price_impact + reverse_price_impact
            if total_slippage > 8.0:
                analysis['rejection_reason'] = 'High round-trip cost'
                analysis['reason'] = f'Total trading cost: {total_slippage:.2f}% (too high for profit)'
                return analysis
                
            # This token passes basic tests - it's an opportunity!
            analysis['is_opportunity'] = True
            analysis['profit_score'] = 10.0 - total_slippage  # Higher score = better opportunity
            analysis['suggested_amount'] = min(self.max_trade_size_usd, usdc_balance * 0.2)  # Suggest 20% of balance or max trade size
            
            # Generate positive reasoning
            reasons = []
            if price_impact < 2.0:
                reasons.append(f"Low price impact ({price_impact:.2f}%)")
            if reverse_price_impact < 10.0:
                reasons.append(f"Good exit liquidity ({reverse_price_impact:.2f}%)")
            if total_slippage < 5.0:
                reasons.append(f"Low trading costs ({total_slippage:.2f}%)")
                
            analysis['reason'] = "Good opportunity: " + ", ".join(reasons)
            
        except Exception as e:
            analysis['rejection_reason'] = 'Analysis error'
            analysis['reason'] = f'Technical error: {str(e)}'
            
        return analysis

    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        return {
            'is_running': self.is_running,
            'trades_today': self.trades_today,
            'daily_limit': self.daily_trade_limit,
            'min_profit': self.min_profit_threshold,
            'max_trade_size': self.max_trade_size_usd,
            'scan_interval': self.scan_interval,
            'last_scan': self.last_scan
        } 