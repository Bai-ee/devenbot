"""
Metrics module for Grok Trading Bot
Handles on-chain metrics fetching and trend analysis
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import time
import math

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsError(Exception):
    """Custom exception for metrics errors"""
    pass

class OnChainMetrics:
    def __init__(self):
        self.gmgn_api_key = None  # GMGN doesn't require API key
        self.gmgn_base_url = os.getenv('GMGN_BASE_URL', 'https://gmgn.ai/defi/router/v1/sol')
        self.rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # Thresholds
        self.min_liquidity_threshold = float(os.getenv('MIN_LIQUIDITY_THRESHOLD', '50000'))
        self.metrics_update_interval = int(os.getenv('METRICS_UPDATE_INTERVAL', '30'))
        self.trend_analysis_period = int(os.getenv('TREND_ANALYSIS_PERIOD', '24'))
        
        # Logs
        self.metrics_log_file = 'logs/metrics.log'
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
    
    def _log_metrics(self, metrics_data: Dict[str, Any]):
        """Log metrics data to file"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'metrics_data': metrics_data
            }
            
            with open(self.metrics_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
    
    async def _make_api_request(self, url: str, headers: Optional[Dict] = None, 
                               params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'data': data,
                            'status_code': response.status
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': error_text,
                            'status_code': response.status
                        }
        except Exception as e:
            logger.error(f"API request error: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': 0
            }
    
    async def get_token_metrics_gmgn(self, token_address: str) -> Dict[str, Any]:
        """Get token metrics from GMGN API"""
        try:
            url = f"{self.gmgn_base_url}/tokens/{token_address}/metrics"
            headers = {
                'Authorization': f'Bearer {self.gmgn_api_key}',
                'Content-Type': 'application/json'
            } if self.gmgn_api_key else None
            
            result = await self._make_api_request(url, headers)
            
            if result['success']:
                data = result['data']
                return {
                    'success': True,
                    'metrics': {
                        'market_cap': data.get('market_cap', 0),
                        'liquidity': data.get('liquidity', 0),
                        'holder_count': data.get('holder_count', 0),
                        'volume_24h': data.get('volume_24h', 0),
                        'price': data.get('price', 0),
                        'price_change_24h': data.get('price_change_24h', 0),
                        'created_at': data.get('created_at'),
                        'verified': data.get('verified', False)
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            logger.error(f"Error fetching GMGN metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_token_metrics_etherscan(self, token_address: str, 
                                         etherscan_api_key: Optional[str] = None) -> Dict[str, Any]:
        """Get token metrics from Etherscan (backup/complement to GMGN)"""
        try:
            if not etherscan_api_key:
                etherscan_api_key = os.getenv('ETHERSCAN_API_KEY')
            
            if not etherscan_api_key:
                return {
                    'success': False,
                    'error': 'Etherscan API key not provided'
                }
            
            # Get token info
            url = "https://api.etherscan.io/api"
            params = {
                'module': 'token',
                'action': 'tokeninfo',
                'contractaddress': token_address,
                'apikey': etherscan_api_key
            }
            
            result = await self._make_api_request(url, params=params)
            
            if result['success'] and result['data']['status'] == '1':
                token_info = result['data']['result'][0] if result['data']['result'] else {}
                
                return {
                    'success': True,
                    'metrics': {
                        'name': token_info.get('tokenName'),
                        'symbol': token_info.get('symbol'),
                        'decimals': int(token_info.get('divisor', '18')),
                        'total_supply': token_info.get('totalSupply', '0')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch from Etherscan')
                }
                
        except Exception as e:
            logger.error(f"Error fetching Etherscan metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_contract_age(self, created_at: Optional[str]) -> Dict[str, Any]:
        """Calculate contract age and score"""
        try:
            if not created_at:
                return {
                    'age_hours': 0,
                    'age_days': 0,
                    'age_score': 0,
                    'age_category': 'unknown'
                }
            
            # Parse creation time
            if isinstance(created_at, str):
                try:
                    creation_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    # Try parsing Unix timestamp
                    creation_time = datetime.fromtimestamp(float(created_at))
            else:
                creation_time = datetime.fromtimestamp(float(created_at))
            
            current_time = datetime.now(creation_time.tzinfo) if creation_time.tzinfo else datetime.now()
            age_delta = current_time - creation_time
            
            age_hours = age_delta.total_seconds() / 3600
            age_days = age_hours / 24
            
            # Score based on age (0-100, higher is better for established tokens)
            if age_hours < 1:
                age_score = 10  # Very new, high risk
                age_category = 'very_new'
            elif age_hours < 24:
                age_score = 25  # New, still risky
                age_category = 'new'
            elif age_days < 7:
                age_score = 50  # Week old, moderate risk
                age_category = 'young'
            elif age_days < 30:
                age_score = 75  # Month old, lower risk
                age_category = 'established'
            else:
                age_score = 90  # Mature contract
                age_category = 'mature'
            
            return {
                'age_hours': round(age_hours, 2),
                'age_days': round(age_days, 2),
                'age_score': age_score,
                'age_category': age_category
            }
            
        except Exception as e:
            logger.error(f"Error calculating contract age: {e}")
            return {
                'age_hours': 0,
                'age_days': 0,
                'age_score': 0,
                'age_category': 'error'
            }
    
    def analyze_trend(self, price: float, price_change_24h: float, 
                     volume_24h: float, market_cap: float) -> Dict[str, Any]:
        """Analyze price trend and classify token"""
        try:
            # Price trend analysis
            if price_change_24h > 10:
                price_trend = 'rising_strong'
                price_score = 80
            elif price_change_24h > 3:
                price_trend = 'rising'
                price_score = 60
            elif price_change_24h > -3:
                price_trend = 'flat'
                price_score = 40
            elif price_change_24h > -10:
                price_trend = 'falling'
                price_score = 20
            else:
                price_trend = 'falling_strong'
                price_score = 10
            
            # Volume analysis (relative to market cap)
            volume_ratio = volume_24h / max(market_cap, 1) if market_cap > 0 else 0
            
            if volume_ratio > 0.5:
                volume_trend = 'very_high'
                volume_score = 90
            elif volume_ratio > 0.2:
                volume_trend = 'high'
                volume_score = 70
            elif volume_ratio > 0.05:
                volume_trend = 'moderate'
                volume_score = 50
            elif volume_ratio > 0.01:
                volume_trend = 'low'
                volume_score = 30
            else:
                volume_trend = 'very_low'
                volume_score = 10
            
            # Combined trend classification
            combined_score = (price_score * 0.6) + (volume_score * 0.4)
            
            if combined_score >= 70:
                overall_trend = 'rising'
            elif combined_score >= 40:
                overall_trend = 'flat'
            else:
                overall_trend = 'falling'
            
            return {
                'price_trend': price_trend,
                'price_score': price_score,
                'volume_trend': volume_trend,
                'volume_score': volume_score,
                'volume_ratio': round(volume_ratio, 4),
                'combined_score': round(combined_score, 2),
                'overall_trend': overall_trend,
                'recommendation': 'buy' if combined_score >= 60 else 'hold' if combined_score >= 35 else 'avoid'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return {
                'price_trend': 'unknown',
                'price_score': 0,
                'volume_trend': 'unknown',
                'volume_score': 0,
                'volume_ratio': 0,
                'combined_score': 0,
                'overall_trend': 'unknown',
                'recommendation': 'avoid'
            }
    
    def calculate_risk_score(self, metrics: Dict[str, Any], age_data: Dict[str, Any], 
                           trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall risk score for the token"""
        try:
            # Liquidity score (0-100, higher is better)
            liquidity = metrics.get('liquidity', 0)
            if liquidity >= self.min_liquidity_threshold * 10:
                liquidity_score = 90
            elif liquidity >= self.min_liquidity_threshold * 5:
                liquidity_score = 70
            elif liquidity >= self.min_liquidity_threshold:
                liquidity_score = 50
            elif liquidity >= self.min_liquidity_threshold * 0.5:
                liquidity_score = 30
            else:
                liquidity_score = 10
            
            # Holder count score
            holder_count = metrics.get('holder_count', 0)
            if holder_count >= 10000:
                holder_score = 90
            elif holder_count >= 1000:
                holder_score = 70
            elif holder_count >= 100:
                holder_score = 50
            elif holder_count >= 10:
                holder_score = 30
            else:
                holder_score = 10
            
            # Market cap score
            market_cap = metrics.get('market_cap', 0)
            if market_cap >= 100000000:  # 100M+
                mcap_score = 90
            elif market_cap >= 10000000:  # 10M+
                mcap_score = 70
            elif market_cap >= 1000000:   # 1M+
                mcap_score = 50
            elif market_cap >= 100000:    # 100K+
                mcap_score = 30
            else:
                mcap_score = 10
            
            # Combine all scores
            age_score = age_data.get('age_score', 0)
            trend_score = trend_data.get('combined_score', 0)
            
            # Weighted average
            overall_score = (
                liquidity_score * 0.25 +
                holder_score * 0.20 +
                mcap_score * 0.20 +
                age_score * 0.15 +
                trend_score * 0.20
            )
            
            # Risk categories
            if overall_score >= 75:
                risk_category = 'low'
                risk_level = 1
            elif overall_score >= 50:
                risk_category = 'medium'
                risk_level = 2
            elif overall_score >= 25:
                risk_category = 'high'
                risk_level = 3
            else:
                risk_category = 'very_high'
                risk_level = 4
            
            return {
                'liquidity_score': round(liquidity_score, 2),
                'holder_score': round(holder_score, 2),
                'mcap_score': round(mcap_score, 2),
                'age_score': age_score,
                'trend_score': trend_score,
                'overall_score': round(overall_score, 2),
                'risk_category': risk_category,
                'risk_level': risk_level,
                'meets_threshold': liquidity >= self.min_liquidity_threshold
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return {
                'liquidity_score': 0,
                'holder_score': 0,
                'mcap_score': 0,
                'age_score': 0,
                'trend_score': 0,
                'overall_score': 0,
                'risk_category': 'very_high',
                'risk_level': 4,
                'meets_threshold': False
            }
    
    async def get_comprehensive_analysis(self, token_address: str) -> Dict[str, Any]:
        """Get comprehensive token analysis"""
        try:
            logger.info(f"Analyzing token: {token_address}")
            
            # Fetch metrics from GMGN
            gmgn_result = await self.get_token_metrics_gmgn(token_address)
            
            if not gmgn_result['success']:
                logger.error(f"Failed to get GMGN metrics: {gmgn_result['error']}")
                return {
                    'success': False,
                    'error': gmgn_result['error']
                }
            
            metrics = gmgn_result['metrics']
            
            # Calculate contract age
            age_data = self.calculate_contract_age(metrics.get('created_at'))
            
            # Analyze trends
            trend_data = self.analyze_trend(
                price=metrics.get('price', 0),
                price_change_24h=metrics.get('price_change_24h', 0),
                volume_24h=metrics.get('volume_24h', 0),
                market_cap=metrics.get('market_cap', 0)
            )
            
            # Calculate risk score
            risk_data = self.calculate_risk_score(metrics, age_data, trend_data)
            
            # Compile comprehensive analysis
            analysis = {
                'token_address': token_address,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'age_analysis': age_data,
                'trend_analysis': trend_data,
                'risk_analysis': risk_data,
                'trading_recommendation': self._generate_trading_recommendation(risk_data, trend_data)
            }
            
            # Log the analysis
            self._log_metrics(analysis)
            
            logger.info(f"Analysis complete for {token_address}: "
                       f"Risk: {risk_data['risk_category']}, "
                       f"Trend: {trend_data['overall_trend']}, "
                       f"Score: {risk_data['overall_score']}")
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_trading_recommendation(self, risk_data: Dict[str, Any], 
                                       trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading recommendation based on analysis"""
        try:
            risk_score = risk_data.get('overall_score', 0)
            trend_recommendation = trend_data.get('recommendation', 'avoid')
            overall_trend = trend_data.get('overall_trend', 'unknown')
            
            # Decision matrix
            if risk_score >= 60 and trend_recommendation == 'buy' and overall_trend == 'rising':
                action = 'strong_buy'
                confidence = 'high'
                position_size = 'normal'
            elif risk_score >= 45 and trend_recommendation in ['buy', 'hold'] and overall_trend in ['rising', 'flat']:
                action = 'buy'
                confidence = 'medium'
                position_size = 'small'
            elif risk_score >= 30 and overall_trend == 'flat':
                action = 'hold'
                confidence = 'low'
                position_size = 'minimal'
            else:
                action = 'avoid'
                confidence = 'high'
                position_size = 'none'
            
            return {
                'action': action,
                'confidence': confidence,
                'position_size': position_size,
                'reasoning': f"Risk score: {risk_score}, Trend: {overall_trend}, "
                           f"Trend rec: {trend_recommendation}"
            }
            
        except Exception as e:
            logger.error(f"Error generating trading recommendation: {e}")
            return {
                'action': 'avoid',
                'confidence': 'high',
                'position_size': 'none',
                'reasoning': f"Error in analysis: {str(e)}"
            }

# Test functions
async def test_token_analysis():
    """Test token analysis with a known Solana token"""
    metrics = OnChainMetrics()
    
    # Test with a known Solana token (e.g., BONK)
    test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    
    print(f"Analyzing token: {test_token}")
    result = await metrics.get_comprehensive_analysis(test_token)
    
    if result['success']:
        analysis = result['analysis']
        print(f"\nAnalysis Results:")
        print(f"- Risk Category: {analysis['risk_analysis']['risk_category']}")
        print(f"- Overall Score: {analysis['risk_analysis']['overall_score']}")
        print(f"- Trend: {analysis['trend_analysis']['overall_trend']}")
        print(f"- Recommendation: {analysis['trading_recommendation']['action']}")
        print(f"- Age: {analysis['age_analysis']['age_category']} "
              f"({analysis['age_analysis']['age_days']} days)")
    else:
        print(f"Analysis failed: {result['error']}")

if __name__ == "__main__":
    print("Testing Metrics Module...")
    asyncio.run(test_token_analysis()) 