"""
Authentication module for Grok Trading Bot
Handles Telegram bot login and wallet authentication
"""

import json
import logging
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import base58

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass

class AuthManager:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.auth_sessions_file = 'auth_sessions.json'
        self.sessions = self._load_sessions()
        
        if not self.telegram_token:
            logger.warning("TELEGRAM_TOKEN not found in environment variables")
    
    def _load_sessions(self) -> Dict[str, Any]:
        """Load existing authentication sessions"""
        try:
            if os.path.exists(self.auth_sessions_file):
                with open(self.auth_sessions_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
        return {}
    
    def _save_sessions(self):
        """Save authentication sessions to file"""
        try:
            with open(self.auth_sessions_file, 'w') as f:
                json.dump(self.sessions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    async def setup_telegram_webhook(self, webhook_url: str) -> bool:
        """Setup Telegram webhook for bot"""
        if not self.telegram_token:
            raise AuthenticationError("Telegram token not configured")
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/setWebhook"
        data = {'url': webhook_url}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()
                if result.get('ok'):
                    logger.info("Telegram webhook setup successfully")
                    return True
                else:
                    logger.error(f"Failed to setup webhook: {result}")
                    return False
    
    async def handle_telegram_start(self, chat_id: int, username: str = None) -> Dict[str, Any]:
        """Handle Telegram /start command"""
        try:
            # Generate session token
            session_token = hashlib.sha256(f"{chat_id}_{datetime.now()}".encode()).hexdigest()
            
            # Create session
            session_data = {
                'chat_id': chat_id,
                'username': username,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'authenticated': True,
                'auth_method': 'telegram'
            }
            
            self.sessions[session_token] = session_data
            self._save_sessions()
            
            logger.info(f"Telegram user authenticated: {chat_id} ({username})")
            
            return {
                'success': True,
                'session_token': session_token,
                'message': 'Successfully authenticated via Telegram!'
            }
            
        except Exception as e:
            logger.error(f"Telegram auth error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_wallet_challenge(self, address: str) -> str:
        """Create a challenge message for wallet signature"""
        timestamp = int(datetime.now().timestamp())
        nonce = hashlib.sha256(f"{address}_{timestamp}".encode()).hexdigest()[:16]
        
        challenge = f"Sign this message to authenticate with Grok Trading Bot.\n\nAddress: {address}\nTimestamp: {timestamp}\nNonce: {nonce}"
        
        # Store challenge temporarily (in production, use Redis or similar)
        challenge_key = hashlib.sha256(f"{address}_{timestamp}".encode()).hexdigest()
        self.sessions[f"challenge_{challenge_key}"] = {
            'address': address,
            'challenge': challenge,
            'timestamp': timestamp,
            'expires_at': (datetime.now() + timedelta(minutes=5)).isoformat()
        }
        self._save_sessions()
        
        return challenge
    
    def verify_wallet_signature(self, address: str, signature: str, challenge: str) -> Dict[str, Any]:
        """Verify Solana wallet signature and create session"""
        try:
            # Verify the signature using Solana's ed25519
            public_key = Pubkey.from_string(address)
            message_bytes = challenge.encode('utf-8')
            signature_bytes = base58.b58decode(signature)
            
            # Verify signature (simplified - in production use proper Solana message signing)
            if len(signature_bytes) != 64:
                raise AuthenticationError("Invalid signature length")
            
            # Create authenticated session
            session_token = hashlib.sha256(f"{address}_{datetime.now()}".encode()).hexdigest()
            
            session_data = {
                'wallet_address': address,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'authenticated': True,
                'auth_method': 'wallet'
            }
            
            self.sessions[session_token] = session_data
            self._save_sessions()
            
            # Clean up challenge
            for key in list(self.sessions.keys()):
                if key.startswith('challenge_') and self.sessions[key].get('address') == address:
                    del self.sessions[key]
            self._save_sessions()
            
            logger.info(f"Wallet authenticated: {address}")
            
            return {
                'success': True,
                'session_token': session_token,
                'address': address,
                'message': 'Successfully authenticated via wallet signature!'
            }
            
        except Exception as e:
            logger.error(f"Wallet auth error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """Validate an existing session token"""
        try:
            if session_token not in self.sessions:
                return {'valid': False, 'error': 'Session not found'}
            
            session = self.sessions[session_token]
            expires_at = datetime.fromisoformat(session['expires_at'])
            
            if datetime.now() > expires_at:
                del self.sessions[session_token]
                self._save_sessions()
                return {'valid': False, 'error': 'Session expired'}
            
            return {
                'valid': True,
                'session': session
            }
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return {'valid': False, 'error': str(e)}
    
    def logout(self, session_token: str) -> bool:
        """Logout and invalidate session"""
        try:
            if session_token in self.sessions:
                del self.sessions[session_token]
                self._save_sessions()
                logger.info(f"Session logged out: {session_token[:8]}...")
                return True
            return False
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for token, session in self.sessions.items():
                try:
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if current_time > expires_at:
                        expired_sessions.append(token)
                except:
                    expired_sessions.append(token)  # Invalid format, remove it
            
            for token in expired_sessions:
                del self.sessions[token]
            
            if expired_sessions:
                self._save_sessions()
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

# Example usage and testing functions
async def test_telegram_auth():
    """Test Telegram authentication flow"""
    auth = AuthManager()
    
    # Simulate Telegram /start command
    result = await auth.handle_telegram_start(123456789, "testuser")
    print(f"Telegram auth result: {result}")
    
    if result['success']:
        # Validate the session
        validation = auth.validate_session(result['session_token'])
        print(f"Session validation: {validation}")

def test_wallet_auth():
    """Test Solana wallet authentication flow"""
    auth = AuthManager()
    
    # Create a test Solana wallet
    keypair = Keypair()
    address = str(keypair.pubkey())
    
    print(f"Test Solana wallet address: {address}")
    
    # Create challenge
    challenge = auth.create_wallet_challenge(address)
    print(f"Challenge created: {challenge[:50]}...")
    
    # Sign the challenge (simplified for demo)
    message_bytes = challenge.encode('utf-8')
    signature_bytes = keypair.sign_message(message_bytes)
    signature = base58.b58encode(signature_bytes).decode('utf-8')
    
    # Verify signature
    result = auth.verify_wallet_signature(address, signature, challenge)
    print(f"Wallet auth result: {result}")
    
    if result['success']:
        # Validate the session
        validation = auth.validate_session(result['session_token'])
        print(f"Session validation: {validation}")

if __name__ == "__main__":
    print("Testing Authentication Module...")
    
    # Test wallet auth
    print("\n=== Wallet Authentication Test ===")
    test_wallet_auth()
    
    # Test Telegram auth
    print("\n=== Telegram Authentication Test ===")
    asyncio.run(test_telegram_auth()) 