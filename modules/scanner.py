#!/usr/bin/env python3
"""
🔎 Scanner Module - Token Discovery & Filtering
Fetches fresh Solana token listings and filters potential scalp opportunities.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Token:
    """Token data structure for trading analysis"""
    address: str
    name: str
    symbol: str
    age_minutes: int
    liquidity_usd: float
    volume_5m_usd: float
    volume_1h_usd: float
    price_change_5m: float
    price_change_1h: float
    price_usd: float
    market_cap: float
    unique_holders: int
    creation_time: datetime
    dex: str = "Raydium"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'address': self.address,
            'name': self.name,
            'symbol': self.symbol,
            'age_minutes': self.age_minutes,
            'liquidity_usd': self.liquidity_usd,
            'volume_5m_usd': self.volume_5m_usd,
            'volume_1h_usd': self.volume_1h_usd,
            'price_change_5m': self.price_change_5m,
            'price_change_1h': self.price_change_1h,
            'price_usd': self.price_usd,
            'market_cap': self.market_cap,
            'unique_holders': self.unique_holders,
            'dex': self.dex
        }

class SolanaTokenScanner:
    """
    🔍 Solana Token Discovery Engine
    
    Monitors DexScreener for new Solana tokens and filters
    based on scalping criteria.
    """
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Filtering criteria for scalp opportunities
        self.min_age_minutes = 2          # At least 2 minutes old (avoid instant rugs)
        self.max_age_minutes = 60         # No older than 1 hour (fresh opportunities)
        self.min_liquidity_usd = 3000     # Minimum liquidity threshold
        self.min_volume_5m_usd = 2000     # Minimum 5-minute volume
        self.min_price_change_5m = 15     # Minimum 5m price pump (15%)
        self.max_price_change_5m = 200    # Max pump to avoid obvious PnDs (200%)
        
        logger.info("🔍 Solana Token Scanner initialized")
        logger.info(f"📊 Filtering criteria:")
        logger.info(f"  • Age: {self.min_age_minutes}-{self.max_age_minutes} minutes")
        logger.info(f"  • Min Liquidity: ${self.min_liquidity_usd:,}")
        logger.info(f"  • Min Volume (5m): ${self.min_volume_5m_usd:,}")
        logger.info(f"  • Price Change (5m): {self.min_price_change_5m}%-{self.max_price_change_5m}%")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'GrokBot/1.0 (Solana Trading Bot)',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_trending_solana_tokens(self) -> List[Dict[str, Any]]:
        """
        Fetch trending Solana tokens from DexScreener
        
        Returns:
            List of raw token data from DexScreener API
        """
        try:
            if not self.session:
                raise RuntimeError("Scanner session not initialized. Use async context manager.")
            
            # Get trending tokens on Solana
            url = f"{self.base_url}/dex/tokens/trending"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"❌ DexScreener API error: {response.status}")
                    return []
                
                data = await response.json()
                
                # Filter for Solana tokens only
                solana_tokens = []
                for token_data in data.get('pairs', []):
                    if token_data.get('chainId') == 'solana':
                        solana_tokens.append(token_data)
                
                logger.info(f"📡 Fetched {len(solana_tokens)} trending Solana tokens")
                return solana_tokens
                
        except Exception as e:
            logger.error(f"❌ Error fetching trending tokens: {e}")
            return []
    
    async def get_new_solana_pairs(self) -> List[Dict[str, Any]]:
        """
        Fetch newest Solana trading pairs from DexScreener
        
        Returns:
            List of new token pairs on Solana
        """
        try:
            if not self.session:
                raise RuntimeError("Scanner session not initialized. Use async context manager.")
            
            # Get new pairs on Solana
            url = f"{self.base_url}/dex/pairs/solana"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"❌ DexScreener pairs API error: {response.status}")
                    return []
                
                data = await response.json()
                pairs = data.get('pairs', [])
                
                # Sort by creation time (newest first)
                now = datetime.utcnow()
                fresh_pairs = []
                
                for pair in pairs:
                    created_at = pair.get('pairCreatedAt')
                    if created_at:
                        try:
                            creation_time = datetime.fromtimestamp(created_at / 1000)
                            age_minutes = (now - creation_time).total_seconds() / 60
                            
                            # Only include pairs created in the last 2 hours
                            if age_minutes <= 120:
                                pair['age_minutes'] = age_minutes
                                fresh_pairs.append(pair)
                        except:
                            continue
                
                # Sort by age (newest first)
                fresh_pairs.sort(key=lambda x: x.get('age_minutes', 999))
                
                logger.info(f"🆕 Found {len(fresh_pairs)} fresh Solana pairs (< 2 hours old)")
                return fresh_pairs
                
        except Exception as e:
            logger.error(f"❌ Error fetching new pairs: {e}")
            return []
    
    def _parse_token_data(self, pair_data: Dict[str, Any]) -> Optional[Token]:
        """
        Parse raw DexScreener pair data into Token object
        
        Args:
            pair_data: Raw pair data from DexScreener
            
        Returns:
            Token object or None if parsing fails
        """
        try:
            # Extract base token info (the new token, not SOL/USDC)
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            
            # Determine which is the meme token (not SOL/USDC)
            known_quote_tokens = {'So11111111111111111111111111111111111111112', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
            
            if quote_token.get('address') in known_quote_tokens:
                token_info = base_token
            elif base_token.get('address') in known_quote_tokens:
                token_info = quote_token
            else:
                # If neither is a known quote, use base token
                token_info = base_token
            
            if not token_info.get('address'):
                return None
            
            # Calculate age
            created_at = pair_data.get('pairCreatedAt', 0)
            if created_at:
                creation_time = datetime.fromtimestamp(created_at / 1000)
                age_minutes = (datetime.utcnow() - creation_time).total_seconds() / 60
            else:
                age_minutes = 999  # Unknown age
            
            # Extract metrics
            price_change_5m = float(pair_data.get('priceChange', {}).get('m5', 0) or 0)
            price_change_1h = float(pair_data.get('priceChange', {}).get('h1', 0) or 0)
            volume_5m = float(pair_data.get('volume', {}).get('m5', 0) or 0)
            volume_1h = float(pair_data.get('volume', {}).get('h1', 0) or 0)
            liquidity = float(pair_data.get('liquidity', {}).get('usd', 0) or 0)
            price_usd = float(pair_data.get('priceUsd', 0) or 0)
            market_cap = float(pair_data.get('marketCap', 0) or 0)
            
            # Create Token object
            token = Token(
                address=token_info['address'],
                name=token_info.get('name', 'Unknown'),
                symbol=token_info.get('symbol', 'UNKNOWN'),
                age_minutes=int(age_minutes),
                liquidity_usd=liquidity,
                volume_5m_usd=volume_5m,
                volume_1h_usd=volume_1h,
                price_change_5m=price_change_5m,
                price_change_1h=price_change_1h,
                price_usd=price_usd,
                market_cap=market_cap,
                unique_holders=0,  # DexScreener doesn't provide this
                creation_time=creation_time if created_at else datetime.utcnow(),
                dex=pair_data.get('dexId', 'unknown').title()
            )
            
            return token
            
        except Exception as e:
            logger.error(f"❌ Error parsing token data: {e}")
            return None
    
    def _is_scalp_candidate(self, token: Token) -> bool:
        """
        Apply filtering criteria to determine if token is a scalp candidate
        
        Args:
            token: Token object to evaluate
            
        Returns:
            True if token meets scalping criteria
        """
        # Age filter (avoid brand new and old tokens)
        if not (self.min_age_minutes <= token.age_minutes <= self.max_age_minutes):
            return False
        
        # Liquidity filter
        if token.liquidity_usd < self.min_liquidity_usd:
            return False
        
        # Volume filter
        if token.volume_5m_usd < self.min_volume_5m_usd:
            return False
        
        # Price movement filter (avoid stagnant and obvious PnDs)
        if not (self.min_price_change_5m <= token.price_change_5m <= self.max_price_change_5m):
            return False
        
        # Exclude if price is too low (dust tokens)
        if token.price_usd <= 0.000001:
            return False
        
        # Exclude if no market cap data
        if token.market_cap <= 0:
            return False
        
        return True
    
    async def get_candidate_tokens(self) -> List[Token]:
        """
        🎯 Main function: Get filtered list of scalp candidate tokens
        
        Returns:
            List of Token objects that meet scalping criteria
        """
        logger.info("🔍 Starting candidate token scan...")
        
        # Fetch data from multiple sources
        trending_data = await self.get_trending_solana_tokens()
        new_pairs_data = await self.get_new_solana_pairs()
        
        # Combine and deduplicate
        all_pairs = trending_data + new_pairs_data
        seen_addresses = set()
        unique_pairs = []
        
        for pair in all_pairs:
            base_addr = pair.get('baseToken', {}).get('address')
            quote_addr = pair.get('quoteToken', {}).get('address')
            
            # Create unique key
            pair_key = f"{base_addr}_{quote_addr}"
            if pair_key not in seen_addresses:
                seen_addresses.add(pair_key)
                unique_pairs.append(pair)
        
        logger.info(f"📊 Processing {len(unique_pairs)} unique pairs...")
        
        # Parse and filter tokens
        candidate_tokens = []
        for pair_data in unique_pairs:
            token = self._parse_token_data(pair_data)
            if token and self._is_scalp_candidate(token):
                candidate_tokens.append(token)
                logger.info(f"✅ Candidate found: {token.symbol} ({token.address[:8]}...)")
                logger.info(f"   📈 Age: {token.age_minutes}m, Liquidity: ${token.liquidity_usd:,.0f}")
                logger.info(f"   🚀 5m Change: {token.price_change_5m:+.1f}%, Volume: ${token.volume_5m_usd:,.0f}")
        
        logger.info(f"🎯 Found {len(candidate_tokens)} scalp candidates")
        return candidate_tokens

# Async function for easy testing
async def test_scanner():
    """Test the scanner functionality"""
    async with SolanaTokenScanner() as scanner:
        candidates = await scanner.get_candidate_tokens()
        
        print(f"\n🎯 Found {len(candidates)} candidates:")
        for token in candidates[:5]:  # Show top 5
            print(f"  {token.symbol}: {token.price_change_5m:+.1f}% (${token.liquidity_usd:,.0f} liq)")

if __name__ == "__main__":
    # Test the scanner
    asyncio.run(test_scanner()) 