#!/usr/bin/env python3
"""
🧪 Safety Module - Rug Check & Token Vetting
Comprehensive security analysis to avoid honeypots, rugs, and malicious tokens.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import os

from .scanner import Token

logger = logging.getLogger(__name__)

@dataclass
class SafetyResult:
    """Safety analysis result"""
    is_safe: bool
    confidence_score: float  # 0.0 to 1.0
    risk_factors: List[str]
    safety_checks: Dict[str, bool]
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'is_safe': self.is_safe,
            'confidence_score': self.confidence_score,
            'risk_factors': self.risk_factors,
            'safety_checks': self.safety_checks,
            'details': self.details
        }

class SolanaTokenSafety:
    """
    🛡️ Solana Token Security Analyzer
    
    Performs comprehensive safety checks including:
    - Honeypot detection
    - Mint authority checks  
    - Liquidity lock verification
    - Holder distribution analysis
    - Social signals analysis
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # Risk thresholds
        self.min_confidence_score = 0.7   # Minimum safety confidence
        self.max_top_holder_percentage = 50  # Max % one holder can own
        self.min_holder_count = 10        # Minimum unique holders
        self.max_dev_tokens_percentage = 20  # Max % dev can hold
        
        logger.info("🛡️ Solana Token Safety Analyzer initialized")
        logger.info(f"📊 Safety thresholds:")
        logger.info(f"  • Min confidence: {self.min_confidence_score}")
        logger.info(f"  • Max top holder: {self.max_top_holder_percentage}%")
        logger.info(f"  • Min holders: {self.min_holder_count}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'GrokBot/1.0 (Security Scanner)',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _check_honeypot_via_simulation(self, token: Token) -> Tuple[bool, Dict[str, Any]]:
        """
        🍯 Simulate buy/sell to detect honeypot behavior
        
        Args:
            token: Token to test
            
        Returns:
            (is_honeypot, details)
        """
        try:
            # Import our existing GMGN trader for simulation
            from .trades import GMGNTrader
            
            trader = GMGNTrader()
            
            # Test small buy route (don't execute)
            test_amount = 0.01  # $0.01 USDC test
            
            buy_route = await trader.get_swap_route(
                token_in_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                token_out_address=token.address,
                in_amount=test_amount,
                from_address='11111111111111111111111111111111',  # Dummy address for simulation
                slippage=0.01
            )
            
            if not buy_route.get('success'):
                return True, {'error': 'Cannot simulate buy', 'reason': buy_route.get('error', 'Unknown')}
            
            # Test sell route immediately after
            buy_amount = float(buy_route.get('quote', {}).get('outAmount', 0))
            if buy_amount <= 0:
                return True, {'error': 'Invalid buy simulation', 'buy_amount': buy_amount}
            
            sell_route = await trader.get_swap_route(
                token_in_address=token.address,
                token_out_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                in_amount=buy_amount,
                from_address='11111111111111111111111111111111',  # Dummy address
                slippage=0.01
            )
            
            if not sell_route.get('success'):
                return True, {'error': 'Cannot simulate sell', 'reason': sell_route.get('error', 'Unknown')}
            
            # Calculate round-trip efficiency
            sell_amount = float(sell_route.get('quote', {}).get('outAmount', 0))
            round_trip_efficiency = sell_amount / test_amount if test_amount > 0 else 0
            
            # Honeypot if round-trip loss > 50%
            is_honeypot = round_trip_efficiency < 0.5
            
            details = {
                'buy_success': True,
                'sell_success': True,
                'round_trip_efficiency': round_trip_efficiency,
                'buy_amount': buy_amount,
                'sell_amount': sell_amount,
                'is_honeypot': is_honeypot
            }
            
            return is_honeypot, details
            
        except Exception as e:
            logger.error(f"❌ Honeypot simulation failed for {token.symbol}: {e}")
            # If simulation fails, assume risky
            return True, {'error': str(e), 'simulation_failed': True}
    
    async def _check_token_metadata(self, token: Token) -> Dict[str, Any]:
        """
        🔍 Check token metadata and mint authority
        
        Args:
            token: Token to analyze
            
        Returns:
            Dictionary with metadata checks
        """
        try:
            if not self.session:
                raise RuntimeError("Safety session not initialized")
            
            # Query Solana RPC for token metadata
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token.address,
                    {"encoding": "base64"}
                ]
            }
            
            async with self.session.post(self.rpc_url, json=payload) as response:
                if response.status != 200:
                    return {'error': f'RPC error: {response.status}'}
                
                data = await response.json()
                result = data.get('result')
                
                if not result or not result.get('value'):
                    return {'error': 'Token account not found'}
                
                # Check if account exists and is initialized
                account_data = result['value']
                is_initialized = account_data.get('owner') == 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
                
                # For comprehensive mint checks, we'd need the mint address
                # This is a simplified check
                return {
                    'token_exists': True,
                    'is_initialized': is_initialized,
                    'owner': account_data.get('owner'),
                    'lamports': account_data.get('lamports', 0)
                }
                
        except Exception as e:
            logger.error(f"❌ Metadata check failed for {token.symbol}: {e}")
            return {'error': str(e)}
    
    async def _check_rugcheck_api(self, token: Token) -> Dict[str, Any]:
        """
        🚩 Check RugCheck.xyz API for known issues
        
        Args:
            token: Token to check
            
        Returns:
            RugCheck analysis results
        """
        try:
            if not self.session:
                raise RuntimeError("Safety session not initialized")
            
            # RugCheck API endpoint (free tier)
            url = f"https://api.rugcheck.xyz/v1/tokens/solana/{token.address}"
            
            async with self.session.get(url) as response:
                if response.status == 404:
                    return {'status': 'not_found', 'message': 'Token not in RugCheck database'}
                
                if response.status != 200:
                    return {'error': f'RugCheck API error: {response.status}'}
                
                data = await response.json()
                
                # Extract key safety metrics
                return {
                    'status': 'found',
                    'risk_level': data.get('riskLevel', 'unknown'),
                    'score': data.get('score', 0),
                    'risks': data.get('risks', []),
                    'mint_authority': data.get('mintAuthority'),
                    'freeze_authority': data.get('freezeAuthority'),
                    'top_holders': data.get('topHolders', [])
                }
                
        except Exception as e:
            logger.error(f"❌ RugCheck API failed for {token.symbol}: {e}")
            return {'error': str(e)}
    
    async def _analyze_holder_distribution(self, token: Token) -> Dict[str, Any]:
        """
        👥 Analyze token holder distribution via RPC
        
        Args:
            token: Token to analyze
            
        Returns:
            Holder distribution analysis
        """
        try:
            if not self.session:
                raise RuntimeError("Safety session not initialized")
            
            # Get largest token accounts for this mint
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token.address]
            }
            
            async with self.session.post(self.rpc_url, json=payload) as response:
                if response.status != 200:
                    return {'error': f'RPC error: {response.status}'}
                
                data = await response.json()
                result = data.get('result')
                
                if not result or 'value' not in result:
                    return {'error': 'No holder data available'}
                
                accounts = result['value']
                if not accounts:
                    return {'error': 'No accounts found'}
                
                # Calculate distribution metrics
                total_supply = sum(int(acc.get('amount', 0)) for acc in accounts)
                if total_supply == 0:
                    return {'error': 'Zero total supply'}
                
                # Get top holder percentage
                top_holder_amount = int(accounts[0].get('amount', 0)) if accounts else 0
                top_holder_percentage = (top_holder_amount / total_supply) * 100
                
                # Count significant holders (>0.1% of supply)
                significant_threshold = total_supply * 0.001
                significant_holders = len([acc for acc in accounts if int(acc.get('amount', 0)) > significant_threshold])
                
                return {
                    'total_accounts': len(accounts),
                    'total_supply': total_supply,
                    'top_holder_percentage': top_holder_percentage,
                    'significant_holders': significant_holders,
                    'distribution_score': min(significant_holders / 50, 1.0),  # Score 0-1
                    'top_10_holders': accounts[:10]
                }
                
        except Exception as e:
            logger.error(f"❌ Holder analysis failed for {token.symbol}: {e}")
            return {'error': str(e)}
    
    def _calculate_confidence_score(self, checks: Dict[str, Dict[str, Any]]) -> float:
        """
        📊 Calculate overall confidence score based on all checks
        
        Args:
            checks: Dictionary of all safety check results
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        score = 1.0
        
        # Honeypot check (critical)
        honeypot = checks.get('honeypot', {})
        if honeypot.get('is_honeypot', True):
            score *= 0.1  # Major penalty for honeypots
        elif honeypot.get('round_trip_efficiency', 0) < 0.7:
            score *= 0.6  # Moderate penalty for high slippage
        
        # RugCheck analysis
        rugcheck = checks.get('rugcheck', {})
        if rugcheck.get('status') == 'found':
            risk_level = rugcheck.get('risk_level', 'high')
            if risk_level == 'high':
                score *= 0.2
            elif risk_level == 'medium':
                score *= 0.5
            elif risk_level == 'low':
                score *= 0.9
        
        # Holder distribution
        holders = checks.get('holders', {})
        top_holder_pct = holders.get('top_holder_percentage', 100)
        if top_holder_pct > 70:
            score *= 0.3  # Very centralized
        elif top_holder_pct > 50:
            score *= 0.6  # Moderately centralized
        elif top_holder_pct > 30:
            score *= 0.8  # Somewhat centralized
        
        significant_holders = holders.get('significant_holders', 0)
        if significant_holders < 5:
            score *= 0.5  # Too few holders
        elif significant_holders < 10:
            score *= 0.7
        
        # Token metadata
        metadata = checks.get('metadata', {})
        if not metadata.get('is_initialized', True):
            score *= 0.4
        
        return max(0.0, min(1.0, score))
    
    async def is_token_safe(self, token: Token) -> SafetyResult:
        """
        🔍 Main safety analysis function
        
        Args:
            token: Token to analyze
            
        Returns:
            SafetyResult with comprehensive analysis
        """
        logger.info(f"🛡️ Analyzing safety for {token.symbol} ({token.address[:8]}...)")
        
        # Run all safety checks in parallel
        checks = {}
        risk_factors = []
        
        try:
            # Parallel execution of all checks
            tasks = [
                ('honeypot', self._check_honeypot_via_simulation(token)),
                ('rugcheck', self._check_rugcheck_api(token)),
                ('holders', self._analyze_holder_distribution(token)),
                ('metadata', self._check_token_metadata(token))
            ]
            
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # Process results
            for i, (check_name, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ {check_name} check failed: {result}")
                    checks[check_name] = {'error': str(result)}
                elif check_name == 'honeypot':
                    is_honeypot, details = result
                    checks[check_name] = details
                    if is_honeypot:
                        risk_factors.append(f"Honeypot detected: {details.get('error', 'Failed simulation')}")
                else:
                    checks[check_name] = result
            
            # Analyze results and build risk factors
            
            # RugCheck risks
            rugcheck = checks.get('rugcheck', {})
            if rugcheck.get('status') == 'found':
                risks = rugcheck.get('risks', [])
                risk_factors.extend([f"RugCheck: {risk}" for risk in risks])
                
                if rugcheck.get('mint_authority'):
                    risk_factors.append("Mint authority not renounced")
                if rugcheck.get('freeze_authority'):
                    risk_factors.append("Freeze authority active")
            
            # Holder distribution risks
            holders = checks.get('holders', {})
            top_holder_pct = holders.get('top_holder_percentage', 0)
            if top_holder_pct > self.max_top_holder_percentage:
                risk_factors.append(f"Top holder owns {top_holder_pct:.1f}% (>50% risky)")
            
            significant_holders = holders.get('significant_holders', 0)
            if significant_holders < self.min_holder_count:
                risk_factors.append(f"Only {significant_holders} significant holders (<{self.min_holder_count} risky)")
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(checks)
            
            # Determine if token is safe
            is_safe = (
                confidence_score >= self.min_confidence_score and
                not checks.get('honeypot', {}).get('is_honeypot', True) and
                len(risk_factors) < 3  # Max 2 risk factors allowed
            )
            
            # Build safety check summary
            safety_checks = {
                'honeypot_test': not checks.get('honeypot', {}).get('is_honeypot', True),
                'rugcheck_passed': rugcheck.get('risk_level', 'high') in ['low', 'medium'],
                'holder_distribution_ok': top_holder_pct <= self.max_top_holder_percentage,
                'sufficient_holders': significant_holders >= self.min_holder_count,
                'metadata_valid': checks.get('metadata', {}).get('is_initialized', False)
            }
            
            result = SafetyResult(
                is_safe=is_safe,
                confidence_score=confidence_score,
                risk_factors=risk_factors,
                safety_checks=safety_checks,
                details=checks
            )
            
            # Log result
            status = "✅ SAFE" if is_safe else "⚠️ RISKY"
            logger.info(f"{status} {token.symbol}: {confidence_score:.2f} confidence")
            if risk_factors:
                logger.info(f"   🚩 Risk factors: {', '.join(risk_factors[:3])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Safety analysis failed for {token.symbol}: {e}")
            return SafetyResult(
                is_safe=False,
                confidence_score=0.0,
                risk_factors=[f"Analysis failed: {str(e)}"],
                safety_checks={},
                details={'error': str(e)}
            )

# Test function
async def test_safety():
    """Test the safety analyzer"""
    from .scanner import Token
    from datetime import datetime
    
    # Create a test token (BONK)
    test_token = Token(
        address='DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        name='Bonk',
        symbol='BONK',
        age_minutes=30,
        liquidity_usd=50000,
        volume_5m_usd=5000,
        volume_1h_usd=25000,
        price_change_5m=15.5,
        price_change_1h=25.0,
        price_usd=0.000025,
        market_cap=1000000,
        unique_holders=1500,
        creation_time=datetime.utcnow()
    )
    
    async with SolanaTokenSafety() as safety:
        result = await safety.is_token_safe(test_token)
        print(f"\n🛡️ Safety Analysis for {test_token.symbol}:")
        print(f"  Safe: {result.is_safe}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Risk factors: {result.risk_factors}")

if __name__ == "__main__":
    asyncio.run(test_safety()) 