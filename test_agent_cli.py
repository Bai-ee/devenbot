"""
🧪 Test CLI for GrokBot Agent SDK
Tests the agent functionality with mock responses when OpenAI is not available
"""

import os
import asyncio
import logging
from modules.agent_sdk import GrokBotAgent
from modules.chat_interface import ChatInterface, CLIInterface
from modules.trades import GMGNTrader
from modules.wallet import SolanaWallet
from modules.strategy import TradingStrategy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockAgent:
    """Mock agent for testing when OpenAI is not available"""
    
    def __init__(self):
        self.watchlist = set()
        self.active_threads = {}
        
    async def process_user_input(self, user_input: str, user_id: str = "default") -> str:
        """Mock processing of user input"""
        
        # Simple keyword-based responses for testing
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['scan', 'opportunities', 'tokens']):
            return """🔍 **MOCK SCAN RESULTS**
            
Found 3 potential opportunities:
• WIF: Good liquidity, 2.1% impact
• BONK: Moderate risk, 4.5% impact  
• POPCAT: High volume, trending up

*This is a mock response for testing*"""
        
        elif any(word in user_input_lower for word in ['balance', 'wallet']):
            return """💰 **MOCK WALLET BALANCE**
            
• USDC: $7.00
• BONK: 28,785.41 tokens
• SOL: 0.05 (~$9.30)
• Total: ~$16.30

*This is a mock response for testing*"""
        
        elif any(word in user_input_lower for word in ['buy', 'purchase']):
            return """💸 **MOCK BUY ORDER**
            
Buy order would be executed here.
⚠️ This is a test response - no real trades executed!

*Ready to integrate with real trading when OpenAI is connected*"""
        
        elif any(word in user_input_lower for word in ['sell']):
            return """💰 **MOCK SELL ORDER**
            
Sell order would be executed here.
⚠️ This is a test response - no real trades executed!

*Ready to integrate with real trading when OpenAI is connected*"""
        
        elif any(word in user_input_lower for word in ['help', 'what can you do']):
            return """🤖 **GROKBOT CAPABILITIES**
            
I can help you with:
• 🔍 Scan for trading opportunities  
• 💰 Buy/sell tokens via USDC swaps
• 📊 Check wallet balances and stats
• 👀 Manage watchlists
• 🤖 Control automated strategies

Try asking:
- "Scan for opportunities"
- "What's my balance?"
- "Buy 1 USDC of BONK"
- "Add WIF to watchlist"

*Mock mode - connect OpenAI for full functionality*"""
        
        elif any(word in user_input_lower for word in ['watch', 'watchlist']):
            if 'add' in user_input_lower or any(token in user_input_lower for token in ['wif', 'bonk', 'popcat']):
                return "👀 Added to watchlist! (Mock response)"
            else:
                return f"📋 **WATCHLIST**: {list(self.watchlist) if self.watchlist else 'Empty'} (Mock)"
        
        else:
            return f"""🤖 I heard: "{user_input}"

This is a mock response for testing. I understand you want to interact with GrokBot!

Try commands like:
• "Scan for opportunities" 
• "What's my balance?"
• "Help me trade"

*Connect OpenAI Assistant for full conversational AI*"""
    
    def clear_thread(self, user_id: str):
        """Mock thread clearing"""
        logger.info(f"Mock: Cleared thread for {user_id}")

async def test_agent_integration():
    """Test the agent with actual bot components"""
    
    # Check if we can use real OpenAI
    use_real_openai = bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_ASSISTANT_ID'))
    
    if use_real_openai:
        print("🧠 Using real OpenAI Agent...")
        # Initialize real components
        trader = GMGNTrader()
        wallet = SolanaWallet()
        strategy = TradingStrategy(trader, wallet)
        
        # Create real agent
        agent = GrokBotAgent(trader=trader, wallet=wallet, strategy=strategy)
    else:
        print("🎭 Using Mock Agent for testing...")
        agent = MockAgent()
    
    # Create chat interface
    chat_interface = ChatInterface(agent)
    cli = CLIInterface(chat_interface)
    
    print("\n" + "="*60)
    print("🚀 GROKBOT AGENT SDK - TEST CLI")
    print("="*60)
    print("Testing conversational AI integration with GrokBot")
    print("Type 'test' for sample queries or start chatting!")
    print("="*60)
    
    # Start CLI session
    await cli.start_cli_session()

async def run_sample_tests():
    """Run some sample test queries"""
    
    agent = MockAgent()
    chat_interface = ChatInterface(agent)
    
    test_queries = [
        "What's trending right now?",
        "Did we buy anything today?", 
        "Show me my balance",
        "Scan for new opportunities",
        "Buy 2 USDC of WIF",
        "Add BONK to my watchlist"
    ]
    
    print("\n🧪 RUNNING SAMPLE TESTS:")
    print("="*50)
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        response = await chat_interface.process_message(query, "test_user", "test")
        print(f"🤖 GrokBot: {response}")
        print("-" * 50)

if __name__ == "__main__":
    print("🧪 GrokBot Agent SDK Test Suite")
    print("\nChoose test mode:")
    print("1. Interactive CLI")
    print("2. Sample test queries")
    
    try:
        choice = input("\nEnter choice (1/2): ").strip()
        
        if choice == "2":
            asyncio.run(run_sample_tests())
        else:
            asyncio.run(test_agent_integration())
            
    except KeyboardInterrupt:
        print("\n👋 Test ended by user") 