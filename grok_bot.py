#!/usr/bin/env python3
"""
Grok Trading Bot - Main Entry Point
Automated memecoin trading bot with GMGN API integration

Usage:
    python grok_bot.py --test              # Run test mode
    python grok_bot.py --dry-run           # Simulate trades without execution
    python grok_bot.py --monitor <token>   # Monitor specific token
    python grok_bot.py --daemon            # Run as background daemon
"""

import os
import sys
import json
import asyncio
import argparse
import logging
import signal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our modules
try:
    from modules.auth import AuthManager
    from modules.trades import GMGNTrader
    from modules.metrics import OnChainMetrics
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required dependencies are installed and modules are in the correct location.")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grok_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GrokBot:
    def __init__(self):
        """Initialize the Grok Trading Bot"""
        self.auth_manager = AuthManager()
        self.trader = GMGNTrader()
        self.metrics = OnChainMetrics()
        
        # Bot configuration
        self.max_daily_trades = int(os.getenv('MAX_DAILY_TRADES', '10'))
        self.stop_loss_percentage = float(os.getenv('STOP_LOSS_PERCENTAGE', '10.0'))
        self.take_profit_percentage = float(os.getenv('TAKE_PROFIT_PERCENTAGE', '25.0'))
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', '2.0'))
        
        # Runtime state
        self.daily_trade_count = 0
        self.active_positions = {}
        self.last_reset_date = datetime.now().date()
        self.running = False
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        logger.info("Grok Trading Bot initialized")
    
    def _reset_daily_counters(self):
        """Reset daily trade counters if new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = current_date
            logger.info("Daily trade counters reset")
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate bot configuration and API connections"""
        results = {
            'auth': {'status': 'checking'},
            'trading': {'status': 'checking'},
            'metrics': {'status': 'checking'},
            'environment': {'status': 'checking'}
        }
        
        # Check environment variables
        required_vars = [
            'GMGN_API_KEY', 'TELEGRAM_TOKEN', 'PRIVATE_KEY', 'RPC_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            results['environment'] = {
                'status': 'failed',
                'error': f"Missing environment variables: {', '.join(missing_vars)}"
            }
        else:
            results['environment'] = {'status': 'passed'}
        
        # Test GMGN API connection
        try:
            connection_test = await self.trader.test_connection()
            if connection_test['success']:
                results['trading'] = {'status': 'passed'}
            else:
                results['trading'] = {
                    'status': 'failed',
                    'error': connection_test.get('error', 'Connection failed')
                }
        except Exception as e:
            results['trading'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # Test auth system
        try:
            # Test session cleanup (basic functionality test)
            self.auth_manager.cleanup_expired_sessions()
            results['auth'] = {'status': 'passed'}
        except Exception as e:
            results['auth'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # Test metrics system
        try:
            # Test with a known token
            test_token = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
            metrics_test = await self.metrics.get_comprehensive_analysis(test_token)
            if metrics_test['success']:
                results['metrics'] = {'status': 'passed'}
            else:
                results['metrics'] = {
                    'status': 'warning',
                    'error': 'Metrics API may be unavailable'
                }
        except Exception as e:
            results['metrics'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return results
    
    async def analyze_and_trade(self, token_address: str, dry_run: bool = False) -> Dict[str, Any]:
        """Analyze a token and execute trade if criteria are met"""
        try:
            self._reset_daily_counters()
            
            # Check daily trade limit
            if self.daily_trade_count >= self.max_daily_trades:
                return {
                    'success': False,
                    'error': f'Daily trade limit reached ({self.max_daily_trades})'
                }
            
            logger.info(f"Analyzing token: {token_address}")
            
            # Get comprehensive analysis
            analysis_result = await self.metrics.get_comprehensive_analysis(token_address)
            
            if not analysis_result['success']:
                return {
                    'success': False,
                    'error': f"Analysis failed: {analysis_result['error']}"
                }
            
            analysis = analysis_result['analysis']
            recommendation = analysis['trading_recommendation']
            risk_analysis = analysis['risk_analysis']
            
            logger.info(f"Analysis complete - Action: {recommendation['action']}, "
                       f"Risk: {risk_analysis['risk_category']}, "
                       f"Score: {risk_analysis['overall_score']}")
            
            # Check if we should trade
            if recommendation['action'] in ['strong_buy', 'buy']:
                
                # Calculate position size based on risk
                base_amount = 0.1  # Base amount in ETH
                risk_multiplier = {
                    'minimal': 0.25,
                    'small': 0.5,
                    'normal': 1.0,
                    'none': 0
                }.get(recommendation['position_size'], 0.5)
                
                trade_amount = base_amount * risk_multiplier
                
                if trade_amount > 0:
                    if dry_run:
                        logger.info(f"DRY RUN: Would buy {trade_amount} ETH worth of {token_address}")
                        return {
                            'success': True,
                            'action': 'dry_run_buy',
                            'amount': trade_amount,
                            'analysis': analysis,
                            'message': f"Dry run: Buy signal for {token_address}"
                        }
                    else:
                        # Execute actual trade
                        trade_result = await self.trader.place_market_order(
                            token_address=token_address,
                            side='buy',
                            amount=trade_amount,
                            print_debug=True
                        )
                        
                        if trade_result['success']:
                            self.daily_trade_count += 1
                            
                            # Store position for monitoring
                            self.active_positions[token_address] = {
                                'entry_time': datetime.now().isoformat(),
                                'entry_amount': trade_amount,
                                'entry_price': analysis['metrics']['price'],
                                'stop_loss': analysis['metrics']['price'] * (1 - self.stop_loss_percentage / 100),
                                'take_profit': analysis['metrics']['price'] * (1 + self.take_profit_percentage / 100),
                                'order_id': trade_result.get('order_id')
                            }
                            
                            logger.info(f"Trade executed: Bought {trade_amount} ETH worth of {token_address}")
                            
                            return {
                                'success': True,
                                'action': 'buy_executed',
                                'amount': trade_amount,
                                'order_id': trade_result.get('order_id'),
                                'analysis': analysis
                            }
                        else:
                            return {
                                'success': False,
                                'error': f"Trade execution failed: {trade_result['error']}"
                            }
            
            return {
                'success': True,
                'action': 'no_trade',
                'reason': f"Recommendation: {recommendation['action']}",
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_and_trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def monitor_positions(self) -> Dict[str, Any]:
        """Monitor active positions for stop loss/take profit"""
        try:
            if not self.active_positions:
                return {'positions_monitored': 0, 'actions_taken': 0}
            
            actions_taken = 0
            
            for token_address, position in list(self.active_positions.items()):
                try:
                    # Get current metrics
                    analysis_result = await self.metrics.get_comprehensive_analysis(token_address)
                    
                    if not analysis_result['success']:
                        logger.warning(f"Failed to get current metrics for {token_address}")
                        continue
                    
                    current_price = analysis_result['analysis']['metrics']['price']
                    stop_loss = position['stop_loss']
                    take_profit = position['take_profit']
                    
                    should_sell = False
                    sell_reason = ""
                    
                    # Check stop loss
                    if current_price <= stop_loss:
                        should_sell = True
                        sell_reason = f"Stop loss triggered at {current_price}"
                    
                    # Check take profit
                    elif current_price >= take_profit:
                        should_sell = True
                        sell_reason = f"Take profit triggered at {current_price}"
                    
                    if should_sell:
                        # Execute sell order
                        sell_result = await self.trader.place_market_order(
                            token_address=token_address,
                            side='sell',
                            amount=position['entry_amount'],
                            print_debug=True
                        )
                        
                        if sell_result['success']:
                            logger.info(f"Position closed: {sell_reason}")
                            del self.active_positions[token_address]
                            actions_taken += 1
                        else:
                            logger.error(f"Failed to close position: {sell_result['error']}")
                
                except Exception as e:
                    logger.error(f"Error monitoring position {token_address}: {e}")
            
            return {
                'positions_monitored': len(self.active_positions),
                'actions_taken': actions_taken
            }
            
        except Exception as e:
            logger.error(f"Error in monitor_positions: {e}")
            return {'error': str(e)}
    
    async def run_daemon(self, scan_interval: int = 300):
        """Run bot as daemon, scanning for opportunities"""
        logger.info(f"Starting Grok Bot daemon mode (scan interval: {scan_interval}s)")
        self.running = True
        
        # List of tokens to monitor (you can expand this)
        watchlist = [
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH (example)
            # Add more tokens to monitor
        ]
        
        try:
            while self.running:
                logger.info("Starting scan cycle...")
                
                # Monitor existing positions
                position_result = await self.monitor_positions()
                logger.info(f"Position monitoring: {position_result}")
                
                # Scan watchlist for new opportunities
                for token_address in watchlist:
                    if not self.running:
                        break
                    
                    try:
                        result = await self.analyze_and_trade(token_address, dry_run=False)
                        if result['success'] and result['action'] in ['buy_executed']:
                            logger.info(f"New position opened: {token_address}")
                    
                    except Exception as e:
                        logger.error(f"Error scanning {token_address}: {e}")
                
                # Wait for next scan
                logger.info(f"Scan complete. Waiting {scan_interval}s for next cycle...")
                await asyncio.sleep(scan_interval)
        
        except Exception as e:
            logger.error(f"Daemon error: {e}")
        
        finally:
            logger.info("Daemon mode stopped")
    
    def stop_daemon(self):
        """Stop the daemon"""
        self.running = False
        logger.info("Stopping daemon...")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Grok Trading Bot')
    parser.add_argument('--test', action='store_true', help='Run system tests')
    parser.add_argument('--dry-run', action='store_true', help='Simulate trades without execution')
    parser.add_argument('--monitor', type=str, help='Monitor specific token address')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--scan-interval', type=int, default=300, help='Daemon scan interval in seconds')
    
    args = parser.parse_args()
    
    # Initialize bot
    bot = GrokBot()
    
    try:
        if args.test:
            print("🤖 Running Grok Trading Bot Tests...")
            print("=" * 50)
            
            # Validate configuration
            print("\n📋 Validating Configuration...")
            validation_results = await bot.validate_configuration()
            
            for component, result in validation_results.items():
                status = result['status']
                if status == 'passed':
                    print(f"✅ {component.capitalize()}: OK")
                elif status == 'warning':
                    print(f"⚠️  {component.capitalize()}: Warning - {result.get('error', 'Unknown issue')}")
                else:
                    print(f"❌ {component.capitalize()}: Failed - {result.get('error', 'Unknown error')}")
            
            # Test with a sample token
            print("\n🔍 Testing Token Analysis...")
            test_token = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
            analysis_result = await bot.analyze_and_trade(test_token, dry_run=True)
            
            if analysis_result['success']:
                print(f"✅ Token analysis successful")
                print(f"   Action: {analysis_result.get('action', 'N/A')}")
                if 'analysis' in analysis_result:
                    risk = analysis_result['analysis']['risk_analysis']
                    print(f"   Risk Score: {risk['overall_score']}")
                    print(f"   Risk Category: {risk['risk_category']}")
            else:
                print(f"❌ Token analysis failed: {analysis_result['error']}")
            
            print("\n🎯 Test Summary:")
            print("All core systems tested. Check logs for detailed information.")
        
        elif args.monitor:
            print(f"🔍 Monitoring token: {args.monitor}")
            result = await bot.analyze_and_trade(args.monitor, dry_run=args.dry_run)
            print(f"Result: {json.dumps(result, indent=2)}")
        
        elif args.daemon:
            print("🤖 Starting Grok Bot in daemon mode...")
            
            # Setup signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                print("\n🛑 Received shutdown signal")
                bot.stop_daemon()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            await bot.run_daemon(args.scan_interval)
        
        else:
            print("🤖 Grok Trading Bot")
            print("Use --help to see available options")
            print("\nQuick start:")
            print("  python grok_bot.py --test     # Run tests")
            print("  python grok_bot.py --daemon   # Start trading")
    
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 