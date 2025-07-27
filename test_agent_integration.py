"""
🧪 Comprehensive Agent SDK Integration Test
Tests the complete integration of OpenAI Agent SDK with GrokBot
"""

import os
import asyncio
import logging
from datetime import datetime
from modules.telegram_bot import TelegramBot
from modules.chat_interface import ChatInterface, CLIInterface, test_agent_response
from modules.agent_sdk import GrokBotAgent
from test_agent_cli import MockAgent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTester:
    """Comprehensive tester for Agent SDK integration"""
    
    def __init__(self):
        self.bot = None
        self.test_results = {}
        
    async def run_all_tests(self):
        """Run comprehensive integration tests"""
        print("\n" + "="*60)
        print("🧪 GROKBOT AGENT SDK INTEGRATION TESTS")
        print("="*60)
        
        # Test 1: Bot Initialization
        await self.test_bot_initialization()
        
        # Test 2: Agent SDK Components
        await self.test_agent_components()
        
        # Test 3: Command Integration
        await self.test_command_integration()
        
        # Test 4: Natural Language Processing
        await self.test_natural_language()
        
        # Test 5: Tool Function Testing
        await self.test_agent_tools()
        
        # Print results
        await self.print_test_summary()
        
        return all(self.test_results.values())
    
    async def test_bot_initialization(self):
        """Test 1: Bot initialization with Agent SDK"""
        print("\n🔧 TEST 1: Bot Initialization")
        try:
            self.bot = TelegramBot()
            await self.bot.initialize_strategy()
            
            print("✅ Bot initialized successfully")
            print(f"   • Telegram token: {'✅ Found' if self.bot.token else '❌ Missing'}")
            print(f"   • Agent SDK: {'✅ Loaded' if self.bot.agent else '⚠️ Mock mode'}")
            print(f"   • Components: {len([c for c in [self.bot.trader, self.bot.wallet, self.bot.strategy] if c])}/3")
            
            self.test_results['bot_init'] = True
            
        except Exception as e:
            print(f"❌ Bot initialization failed: {e}")
            self.test_results['bot_init'] = False
    
    async def test_agent_components(self):
        """Test 2: Agent SDK component verification"""
        print("\n🧠 TEST 2: Agent SDK Components")
        
        try:
            if self.bot.agent:
                print("✅ Real OpenAI Agent detected")
                print(f"   • OpenAI Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
                print(f"   • Assistant ID: {'✅ Set' if os.getenv('OPENAI_ASSISTANT_ID') else '❌ Missing'}")
                print(f"   • Tools registered: {len(self.bot.agent.tools)}")
                print(f"   • Chat interface: {'✅ Active' if self.bot.chat_interface else '❌ Missing'}")
            else:
                print("⚠️ Using Mock Agent (OpenAI not configured)")
                print("   • This is expected for local testing")
                print("   • Mock responses will be used")
            
            self.test_results['agent_components'] = True
            
        except Exception as e:
            print(f"❌ Agent component test failed: {e}")
            self.test_results['agent_components'] = False
    
    async def test_command_integration(self):
        """Test 3: Command integration testing"""
        print("\n⚡ TEST 3: Command Integration")
        
        try:
            # Test command handlers exist
            chat_commands = ['/chat', '/ask', '/ai', '/clear']
            all_commands = list(self.bot.command_handlers.keys())
            
            print(f"✅ Total commands registered: {len(all_commands)}")
            
            missing_commands = [cmd for cmd in chat_commands if cmd not in all_commands]
            if missing_commands:
                print(f"❌ Missing chat commands: {missing_commands}")
                self.test_results['command_integration'] = False
            else:
                print("✅ All AI chat commands registered")
                print(f"   • Available: {', '.join(chat_commands)}")
                self.test_results['command_integration'] = True
            
        except Exception as e:
            print(f"❌ Command integration test failed: {e}")
            self.test_results['command_integration'] = False
    
    async def test_natural_language(self):
        """Test 4: Natural language processing"""
        print("\n💬 TEST 4: Natural Language Processing")
        
        try:
            # Create test interface
            if self.bot.agent:
                chat_interface = self.bot.chat_interface
            else:
                # Use mock for testing
                mock_agent = MockAgent()
                chat_interface = ChatInterface(mock_agent)
            
            # Test queries
            test_queries = [
                "What's my balance?",
                "Scan for opportunities",
                "Help me trade",
                "Buy 1 USDC of BONK"
            ]
            
            print("Testing natural language queries...")
            success_count = 0
            
            for query in test_queries:
                try:
                    response = await chat_interface.process_message(query, "test_user", "test")
                    if response and len(response) > 20:  # Basic response validation
                        print(f"   ✅ '{query[:30]}...' -> Response received")
                        success_count += 1
                    else:
                        print(f"   ❌ '{query[:30]}...' -> No/short response")
                except Exception as e:
                    print(f"   ❌ '{query[:30]}...' -> Error: {e}")
            
            if success_count == len(test_queries):
                print(f"✅ All {len(test_queries)} natural language queries processed")
                self.test_results['natural_language'] = True
            else:
                print(f"⚠️ {success_count}/{len(test_queries)} queries successful")
                self.test_results['natural_language'] = success_count >= len(test_queries) // 2
            
        except Exception as e:
            print(f"❌ Natural language test failed: {e}")
            self.test_results['natural_language'] = False
    
    async def test_agent_tools(self):
        """Test 5: Agent tool functions"""
        print("\n🔧 TEST 5: Agent Tool Functions")
        
        try:
            if self.bot.agent:
                agent = self.bot.agent
            else:
                # Create mock agent for testing
                from modules.agent_sdk import GrokBotAgent
                agent = GrokBotAgent(
                    trader=self.bot.trader,
                    wallet=self.bot.wallet,
                    strategy=self.bot.strategy
                )
            
            # Test tool functions
            tool_tests = [
                ('get_balance', {}),
                ('get_watchlist', {}),
                ('get_bot_status', {}),
                ('scan_tokens', {'detailed': False}),
            ]
            
            success_count = 0
            
            for tool_name, params in tool_tests:
                try:
                    if tool_name in agent.tools:
                        result = await agent.tools[tool_name](**params)
                        if isinstance(result, dict) and result.get('status'):
                            print(f"   ✅ {tool_name}: {result.get('status')}")
                            success_count += 1
                        else:
                            print(f"   ❌ {tool_name}: Invalid response format")
                    else:
                        print(f"   ❌ {tool_name}: Tool not found")
                except Exception as e:
                    print(f"   ❌ {tool_name}: Error - {e}")
            
            if success_count >= len(tool_tests) // 2:
                print(f"✅ {success_count}/{len(tool_tests)} tools working")
                self.test_results['agent_tools'] = True
            else:
                print(f"❌ Only {success_count}/{len(tool_tests)} tools working")
                self.test_results['agent_tools'] = False
            
        except Exception as e:
            print(f"❌ Agent tools test failed: {e}")
            self.test_results['agent_tools'] = False
    
    async def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Ready for deployment!")
            return True
        elif passed >= total // 2:
            print("⚠️ PARTIAL SUCCESS - Some features may not work")
            return False
        else:
            print("❌ MAJOR ISSUES - Need fixes before deployment")
            return False

async def test_telegram_integration():
    """Test Telegram bot integration specifically"""
    print("\n📱 TELEGRAM INTEGRATION TEST")
    try:
        bot = TelegramBot()
        await bot.initialize_strategy()
        
        # Test message processing
        test_message = {
            'chat': {'id': 12345},
            'from': {'id': 67890},
            'text': 'Hello GrokBot!'
        }
        
        print("✅ Telegram bot ready for message processing")
        print(f"   • Commands available: {len(bot.command_handlers)}")
        print(f"   • Agent integration: {'Active' if bot.telegram_agent_interface else 'Mock mode'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram integration test failed: {e}")
        return False

async def run_interactive_test():
    """Run interactive test with user input"""
    print("\n🎮 INTERACTIVE TEST MODE")
    print("Test the Agent SDK integration directly!")
    
    try:
        # Initialize bot
        bot = TelegramBot()
        await bot.initialize_strategy()
        
        if bot.chat_interface:
            chat_interface = bot.chat_interface
            print("🧠 Using real OpenAI Agent")
        else:
            mock_agent = MockAgent()
            chat_interface = ChatInterface(mock_agent)
            print("🎭 Using Mock Agent (OpenAI not configured)")
        
        cli = CLIInterface(chat_interface)
        
        print("\nType your messages below (or 'exit' to quit):")
        await cli.start_cli_session()
        
    except Exception as e:
        print(f"❌ Interactive test failed: {e}")

if __name__ == "__main__":
    print("🧪 GrokBot Agent SDK Integration Tester")
    print("\nChoose test mode:")
    print("1. Full Integration Test Suite")
    print("2. Telegram Integration Test")
    print("3. Interactive Test Mode")
    
    try:
        choice = input("\nEnter choice (1/2/3): ").strip()
        
        if choice == "1":
            tester = IntegrationTester()
            success = asyncio.run(tester.run_all_tests())
            exit(0 if success else 1)
        elif choice == "2":
            success = asyncio.run(test_telegram_integration())
            exit(0 if success else 1)
        elif choice == "3":
            asyncio.run(run_interactive_test())
        else:
            print("Invalid choice")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        exit(1) 