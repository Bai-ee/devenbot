"""
Trading module for Grok Trading Bot
Handles GMGN API integration and order placement
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingError(Exception):
    """Custom exception for trading errors"""
    pass

class GMGNTrader:
    def __init__(self):
        self.api_key = None  # GMGN doesn't require API key
        self.base_url = os.getenv('GMGN_BASE_URL', 'https://gmgn.ai/defi/router/v1/sol')
        self.private_key = os.getenv('SOLANA_PRIVATE_KEY')
        self.rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # Trading parameters
        self.default_slippage = float(os.getenv('DEFAULT_SLIPPAGE', '0.01'))
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '1000'))
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', '2.0'))
        
        # Logs
        self.trade_log_file = 'logs/trades.log'
        
        logger.info("GMGN API configured (no API key required)")
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
    
    def _log_trade(self, trade_data: Dict[str, Any]):
        """Log trade data to file"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'trade_data': trade_data
            }
            
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    async def _make_api_request(self, endpoint: str, method: str = 'GET', 
                               data: Optional[Dict] = None, 
                               print_debug: bool = False) -> Dict[str, Any]:
        """Make authenticated API request to GMGN"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'GrokBot/1.0'
            }
            
            if print_debug:
                logger.info(f"Making {method} request to: {url}")
                logger.info(f"Headers: {headers}")
                logger.info(f"Data: {data}")
            
            async with aiohttp.ClientSession() as session:
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers, params=data) as response:
                        result = await response.json()
                        
                        if print_debug:
                            logger.info(f"Response status: {response.status}")
                            logger.info(f"Response: {result}")
                        
                        return {
                            'status_code': response.status,
                            'data': result,
                            'success': response.status == 200
                        }
                
                elif method.upper() == 'POST':
                    async with session.post(url, headers=headers, json=data) as response:
                        result = await response.json()
                        
                        if print_debug:
                            logger.info(f"Response status: {response.status}")
                            logger.info(f"Response: {result}")
                        
                        return {
                            'status_code': response.status,
                            'data': result,
                            'success': response.status == 200
                        }
        
        except Exception as e:
            logger.error(f"API request error: {e}")
            return {
                'status_code': 500,
                'data': {'error': str(e)},
                'success': False
            }
    
    async def test_connection(self, print_debug: bool = True) -> Dict[str, Any]:
        """Test GMGN API connection with a simple swap route query"""
        try:
            # Test with a simple USDC to SOL query
            test_params = {
                'token_in_address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'token_out_address': 'So11111111111111111111111111111111111111112',   # SOL
                'in_amount': '1000000',  # 1 USDC (6 decimals)
                'from_address': 'So11111111111111111111111111111111111111112',  # Dummy address
                'slippage': '1',
                'swap_mode': 'ExactIn',
                'fee': '0.0025',  # 0.25% fee
                'is_anti_mev': 'true'
            }
            
            result = await self._make_api_request('tx/get_swap_route', 'GET', test_params, print_debug=print_debug)
            
            if result['success']:
                logger.info("GMGN API connection successful")
                return {
                    'success': True,
                    'message': 'API connection successful',
                    'data': result['data']
                }
            else:
                logger.error(f"GMGN API connection failed: {result['data']}")
                return {
                    'success': False,
                    'error': f"Connection failed: {result['data']}",
                    'status_code': result['status_code']
                }
                
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_swap_route(self, token_in_address: str, token_out_address: str, 
                            in_amount: str, from_address: str, slippage: float = 1.0,
                            swap_mode: str = 'ExactIn', fee: float = 0.0025, is_anti_mev: bool = True,
                            print_debug: bool = False) -> Dict[str, Any]:
        """
        Get swap route from GMGN API
        
        Args:
            token_in_address: Input token mint address
            token_out_address: Output token mint address  
            in_amount: Amount to swap (in smallest units)
            from_address: User's wallet address
            slippage: Slippage tolerance (default 1.0%)
            swap_mode: 'ExactIn' or 'ExactOut'
            is_anti_mev: Enable anti-MEV protection
            print_debug: Print debug information
        """
        try:
            params = {
                'token_in_address': token_in_address,
                'token_out_address': token_out_address,
                'in_amount': str(in_amount),
                'from_address': from_address,
                'slippage': str(slippage),
                'swap_mode': swap_mode,
                'fee': str(fee),
                'is_anti_mev': str(is_anti_mev).lower()
            }
            
            result = await self._make_api_request('tx/get_swap_route', 'GET', params, print_debug)
            
            if result['success']:
                response_data = result['data']
                if response_data.get('code') == 0:  # GMGN success code
                    data = response_data.get('data', {})
                    return {
                        'success': True,
                        'quote': data.get('quote', {}),
                        'raw_tx': data.get('raw_tx', {}),
                        'route_plan': data.get('quote', {}).get('routePlan', []),
                        'price_impact': data.get('quote', {}).get('priceImpactPct', 0),
                        'amount_in_usd': data.get('amount_in_usd', '0'),
                        'amount_out_usd': data.get('amount_out_usd', '0'),
                        'message': 'Swap route retrieved successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('msg', 'Unknown GMGN error')
                    }
            else:
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error getting swap route: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_token_info(self, token_address: str, print_debug: bool = False) -> Dict[str, Any]:
        """Get token information from GMGN"""
        try:
            endpoint = f"tokens/{token_address}"
            result = await self._make_api_request(endpoint, print_debug=print_debug)
            
            if result['success']:
                return {
                    'success': True,
                    'token_info': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def place_market_order(self, token_address: str, side: str, amount: float, 
                                slippage: Optional[float] = None, 
                                print_debug: bool = False) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            token_address: Address of the token to trade
            side: 'buy' or 'sell'
            amount: Amount in base currency (ETH/SOL)
            slippage: Slippage tolerance (optional)
            print_debug: Whether to print debug info
        """
        try:
            if not self.private_key:
                raise TradingError("Private key not configured")
            
            slippage = slippage or self.default_slippage
            
            # Validate inputs
            if side not in ['buy', 'sell']:
                raise TradingError("Side must be 'buy' or 'sell'")
            
            if amount <= 0:
                raise TradingError("Amount must be positive")
            
            if amount > self.max_position_size:
                raise TradingError(f"Amount exceeds max position size: {self.max_position_size}")
            
            # Prepare order data
            order_data = {
                'token_address': token_address,
                'side': side,
                'amount': str(amount),
                'type': 'market',
                'slippage': str(slippage),
                'timestamp': int(time.time())
            }
            
            # Make the API call
            result = await self._make_api_request('orders', 'POST', order_data, print_debug)
            
            # Log the trade
            trade_log = {
                'type': 'market_order',
                'order_data': order_data,
                'result': result,
                'success': result['success']
            }
            self._log_trade(trade_log)
            
            if result['success']:
                logger.info(f"Market order placed successfully: {side} {amount} of {token_address}")
                return {
                    'success': True,
                    'order_id': result['data'].get('order_id'),
                    'transaction_hash': result['data'].get('transaction_hash'),
                    'message': f"Market {side} order placed successfully"
                }
            else:
                logger.error(f"Market order failed: {result['data']}")
                return {
                    'success': False,
                    'error': result['data']
                }
        
        except Exception as e:
            logger.error(f"Market order error: {e}")
            trade_log = {
                'type': 'market_order',
                'error': str(e),
                'success': False
            }
            self._log_trade(trade_log)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def place_limit_order(self, token_address: str, side: str, amount: float, 
                               price: float, print_debug: bool = False) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            token_address: Address of the token to trade
            side: 'buy' or 'sell'
            amount: Amount in base currency (ETH/SOL)
            price: Limit price
            print_debug: Whether to print debug info
        """
        try:
            if not self.private_key:
                raise TradingError("Private key not configured")
            
            # Validate inputs
            if side not in ['buy', 'sell']:
                raise TradingError("Side must be 'buy' or 'sell'")
            
            if amount <= 0:
                raise TradingError("Amount must be positive")
            
            if price <= 0:
                raise TradingError("Price must be positive")
            
            if amount > self.max_position_size:
                raise TradingError(f"Amount exceeds max position size: {self.max_position_size}")
            
            # Prepare order data
            order_data = {
                'token_address': token_address,
                'side': side,
                'amount': str(amount),
                'price': str(price),
                'type': 'limit',
                'timestamp': int(time.time())
            }
            
            # Make the API call
            result = await self._make_api_request('orders', 'POST', order_data, print_debug)
            
            # Log the trade
            trade_log = {
                'type': 'limit_order',
                'order_data': order_data,
                'result': result,
                'success': result['success']
            }
            self._log_trade(trade_log)
            
            if result['success']:
                logger.info(f"Limit order placed successfully: {side} {amount} of {token_address} at {price}")
                return {
                    'success': True,
                    'order_id': result['data'].get('order_id'),
                    'message': f"Limit {side} order placed successfully"
                }
            else:
                logger.error(f"Limit order failed: {result['data']}")
                return {
                    'success': False,
                    'error': result['data']
                }
        
        except Exception as e:
            logger.error(f"Limit order error: {e}")
            trade_log = {
                'type': 'limit_order',
                'error': str(e),
                'success': False
            }
            self._log_trade(trade_log)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_order_status(self, order_id: str, print_debug: bool = False) -> Dict[str, Any]:
        """Get order status"""
        try:
            endpoint = f"orders/{order_id}"
            result = await self._make_api_request(endpoint, print_debug=print_debug)
            
            if result['success']:
                return {
                    'success': True,
                    'order': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cancel_order(self, order_id: str, print_debug: bool = False) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            endpoint = f"orders/{order_id}/cancel"
            result = await self._make_api_request(endpoint, 'POST', print_debug=print_debug)
            
            # Log the cancellation
            trade_log = {
                'type': 'cancel_order',
                'order_id': order_id,
                'result': result,
                'success': result['success']
            }
            self._log_trade(trade_log)
            
            if result['success']:
                logger.info(f"Order cancelled successfully: {order_id}")
                return {
                    'success': True,
                    'message': 'Order cancelled successfully'
                }
            else:
                logger.error(f"Order cancellation failed: {result['data']}")
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_trade_history(self, limit: int = 50, print_debug: bool = False) -> Dict[str, Any]:
        """Get trade history"""
        try:
            params = {'limit': limit}
            result = await self._make_api_request('trades', params=params, print_debug=print_debug)
            
            if result['success']:
                return {
                    'success': True,
                    'trades': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_portfolio_balances(self, print_debug: bool = False) -> Dict[str, Any]:
        """Get portfolio balances"""
        try:
            result = await self._make_api_request('portfolio/balances', print_debug=print_debug)
            
            if result['success']:
                return {
                    'success': True,
                    'balances': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result['data']
                }
                
        except Exception as e:
            logger.error(f"Error getting portfolio balances: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Test functions
async def test_gmgn_connection():
    """Test GMGN API connection"""
    trader = GMGNTrader()
    
    print("Testing GMGN API connection...")
    result = await trader.test_connection()
    print(f"Connection test result: {result}")
    
    return result['success']

async def test_mock_trade():
    """Test mock trade functionality"""
    trader = GMGNTrader()
    
    # Mock token address (replace with actual test token)
    test_token = "0x1234567890123456789012345678901234567890"
    
    print("\nTesting mock market buy order...")
    buy_result = await trader.place_market_order(
        token_address=test_token,
        side='buy',
        amount=0.1,
        print_debug=True
    )
    print(f"Mock buy result: {buy_result}")
    
    print("\nTesting mock limit sell order...")
    sell_result = await trader.place_limit_order(
        token_address=test_token,
        side='sell',
        amount=0.1,
        price=100.0,
        print_debug=True
    )
    print(f"Mock sell result: {sell_result}")

if __name__ == "__main__":
    print("Testing Trading Module...")
    
    # Test connection
    print("\n=== Connection Test ===")
    asyncio.run(test_gmgn_connection())
    
    # Test mock trades
    print("\n=== Mock Trade Test ===")
    asyncio.run(test_mock_trade()) 