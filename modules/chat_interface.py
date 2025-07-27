"""
📟 Chat Interface Module for GrokBot Agent SDK
Handles different chat platforms (CLI, Telegram, Discord) and routes to OpenAI Agent
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from .agent_sdk import GrokBotAgent

logger = logging.getLogger(__name__)

class ChatInterface:
    """Multi-platform chat interface for GrokBot Agent SDK"""
    
    def __init__(self, agent: GrokBotAgent):
        self.agent = agent
        self.active_sessions = {}  # platform_user_id -> session_data
        
        logger.info("📟 Chat Interface initialized")
    
    async def process_message(self, message: str, user_id: str, platform: str = "cli") -> str:
        """
        Process incoming message and return response
        
        Args:
            message: User's message
            user_id: Unique user identifier
            platform: Platform identifier (cli, telegram, discord)
        """
        try:
            # Create session key
            session_key = f"{platform}_{user_id}"
            
            # Update session info
            self.active_sessions[session_key] = {
                'last_activity': datetime.now(),
                'platform': platform,
                'user_id': user_id,
                'message_count': self.active_sessions.get(session_key, {}).get('message_count', 0) + 1
            }
            
            # Process through agent
            response = await self.agent.process_user_input(message, session_key)
            
            # Log interaction
            logger.info(f"💬 [{platform}:{user_id}] {message[:50]}... -> {response[:50]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Chat interface error: {e}")
            return f"🤖 Sorry, I'm having trouble processing that. Error: {str(e)}"
    
    def get_session_info(self, user_id: str, platform: str = "cli") -> Dict[str, Any]:
        """Get session information for a user"""
        session_key = f"{platform}_{user_id}"
        return self.active_sessions.get(session_key, {})
    
    def clear_session(self, user_id: str, platform: str = "cli"):
        """Clear session data for a user"""
        session_key = f"{platform}_{user_id}"
        if session_key in self.active_sessions:
            del self.active_sessions[session_key]
        
        # Also clear agent thread
        self.agent.clear_thread(session_key)
        logger.info(f"🗑️ Cleared session for {session_key}")

class CLIInterface:
    """Command Line Interface for GrokBot Agent"""
    
    def __init__(self, chat_interface: ChatInterface):
        self.chat = chat_interface
        self.user_id = "cli_user"
        
    async def start_cli_session(self):
        """Start interactive CLI session"""
        print("\n🤖 GrokBot Agent CLI - Type 'exit' to quit, 'clear' to reset conversation\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() in ['clear', 'reset']:
                    self.chat.clear_session(self.user_id, "cli")
                    print("🗑️ Conversation cleared!")
                    continue
                
                if not user_input:
                    continue
                
                print("🤖 Thinking...")
                response = await self.chat.process_message(user_input, self.user_id, "cli")
                print(f"GrokBot: {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

class TelegramAgentInterface:
    """Telegram interface integration for Agent SDK"""
    
    def __init__(self, chat_interface: ChatInterface):
        self.chat = chat_interface
    
    async def handle_telegram_message(self, message: str, user_id: int) -> str:
        """Handle message from Telegram bot"""
        return await self.chat.process_message(message, str(user_id), "telegram")
    
    async def handle_telegram_command(self, command: str, args: list, user_id: int) -> str:
        """Handle Telegram commands through natural language"""
        
        # Convert commands to natural language for the agent
        command_map = {
            '/scan': "scan for new token opportunities",
            '/balance': "show my wallet balance",
            '/status': "show bot status",
            '/watchlist': "show my watchlist",
            '/trades': "show recent trades",
            '/help': "show what you can do",
            '/clear': "clear conversation"
        }
        
        if command == '/clear':
            self.chat.clear_session(str(user_id), "telegram")
            return "🗑️ Conversation history cleared!"
        
        # Convert command to natural language query
        natural_query = command_map.get(command, command)
        
        # Add args if present
        if args:
            natural_query += f" {' '.join(args)}"
        
        return await self.chat.process_message(natural_query, str(user_id), "telegram")

# Utility functions for testing
async def test_cli_interface():
    """Test function for CLI interface"""
    from .agent_sdk import GrokBotAgent
    
    # Initialize components (mock for testing)
    agent = GrokBotAgent()
    chat_interface = ChatInterface(agent)
    cli = CLIInterface(chat_interface)
    
    await cli.start_cli_session()

async def test_agent_response(query: str):
    """Test agent response for a specific query"""
    from .agent_sdk import GrokBotAgent
    
    agent = GrokBotAgent()
    chat_interface = ChatInterface(agent)
    
    response = await chat_interface.process_message(query, "test_user", "test")
    print(f"Query: {query}")
    print(f"Response: {response}")
    
    return response

if __name__ == "__main__":
    # Run CLI interface for testing
    asyncio.run(test_cli_interface()) 