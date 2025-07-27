"""
🧠 OpenAI Agent SDK Module for GrokBot
Enables natural-language conversational interactions with trading bot functionality
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class GrokBotAgent:
    """OpenAI Agent SDK integration for conversational trading bot interface"""
    
    def __init__(self, trader=None, wallet=None, strategy=None, scanner=None, safety=None):
        """Initialize the OpenAI Agent with bot components"""
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('OPENAI_ASSISTANT_ID')
        
        # Bot component references
        self.trader = trader
        self.wallet = wallet
        self.strategy = strategy
        self.scanner = scanner
        self.safety = safety
        
        # Thread management for conversation context
        self.active_threads = {}  # user_id -> thread_id mapping
        
        # Tool registry
        self.tools = {}
        self._register_tools()
        
        # Memory storage (in-memory for now, could be DB later)
        self.watchlist = set()
        self.user_preferences = {}
        self.trade_history = []
        
        logger.info("🧠 GrokBot Agent SDK initialized")
        
    def _register_tools(self):
        """Register available tools with the assistant"""
        self.tools = {
            'get_recent_trades': self._get_recent_trades,
            'scan_tokens': self._scan_tokens,
            'watch_token': self._watch_token,
            'sell_token': self._sell_token,
            'buy_token': self._buy_token,
            'get_token_stats': self._get_token_stats,
            'get_balance': self._get_balance,
            'get_watchlist': self._get_watchlist,
            'remove_from_watchlist': self._remove_from_watchlist,
            'get_market_summary': self._get_market_summary,
            'start_auto_trading': self._start_auto_trading,
            'stop_auto_trading': self._stop_auto_trading,
            'get_bot_status': self._get_bot_status
        }
        
        logger.info(f"🔧 Registered {len(self.tools)} tools with agent")
    
    async def process_user_input(self, user_input: str, user_id: str = "default") -> str:
        """
        Process natural language input and return conversational response
        """
        try:
            # Get or create thread for this user
            thread_id = await self._get_or_create_thread(user_id)
            
            # Add user message to thread
            await self._add_message_to_thread(thread_id, "user", user_input)
            
            # Run the assistant
            response = await self._run_assistant(thread_id, user_input)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return f"🤖 Sorry, I encountered an error: {str(e)}"
    
    async def _get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create new one for user"""
        if user_id not in self.active_threads:
            try:
                thread = self.client.beta.threads.create()
                self.active_threads[user_id] = thread.id
                logger.info(f"📝 Created new thread {thread.id} for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create thread: {e}")
                raise
        
        return self.active_threads[user_id]
    
    async def _add_message_to_thread(self, thread_id: str, role: str, content: str):
        """Add message to conversation thread"""
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role=role,
                content=content
            )
        except Exception as e:
            logger.error(f"Failed to add message to thread: {e}")
            raise
    
    async def _run_assistant(self, thread_id: str, user_input: str) -> str:
        """Run the assistant and handle tool calls"""
        try:
            # Create and poll the run
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                instructions=f"""
You are GrokBot, a fast, smart crypto trading assistant focused on Solana meme coin trading. 
You can check new tokens, evaluate risks, and trigger trades based on real-time data.

Current capabilities:
- Scan for new trading opportunities
- Buy/sell tokens via USDC swaps
- Track watchlists and trading history
- Provide market analysis and token stats
- Execute automated trading strategies

Always confirm with the user if a token looks suspicious or risky.
Be conversational but concise. Use emojis to make responses engaging.

User input: {user_input}
                """,
                tools=[
                    {"type": "function", "function": {
                        "name": "get_recent_trades",
                        "description": "Get the bot's recent trading history",
                        "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "description": "Number of trades to return"}}}
                    }},
                    {"type": "function", "function": {
                        "name": "scan_tokens",
                        "description": "Scan for new token opportunities",
                        "parameters": {"type": "object", "properties": {"detailed": {"type": "boolean", "description": "Whether to return detailed analysis"}}}
                    }},
                    {"type": "function", "function": {
                        "name": "watch_token",
                        "description": "Add a token to the watchlist",
                        "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Token symbol or address"}}, "required": ["symbol"]}
                    }},
                    {"type": "function", "function": {
                        "name": "sell_token",
                        "description": "Sell a token position",
                        "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Token symbol to sell"}}, "required": ["symbol"]}
                    }},
                    {"type": "function", "function": {
                        "name": "buy_token",
                        "description": "Buy a token with USDC",
                        "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Token symbol to buy"}, "amount": {"type": "number", "description": "USDC amount to spend"}}, "required": ["symbol", "amount"]}
                    }},
                    {"type": "function", "function": {
                        "name": "get_token_stats",
                        "description": "Get current token statistics and market data",
                        "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Token symbol or address"}}, "required": ["symbol"]}
                    }},
                    {"type": "function", "function": {
                        "name": "get_balance",
                        "description": "Get current wallet balance",
                        "parameters": {"type": "object", "properties": {}}
                    }},
                    {"type": "function", "function": {
                        "name": "get_watchlist",
                        "description": "Get current watchlist tokens",
                        "parameters": {"type": "object", "properties": {}}
                    }},
                    {"type": "function", "function": {
                        "name": "get_market_summary",
                        "description": "Get overall market summary and trending tokens",
                        "parameters": {"type": "object", "properties": {}}
                    }},
                    {"type": "function", "function": {
                        "name": "start_auto_trading",
                        "description": "Start automated trading strategy",
                        "parameters": {"type": "object", "properties": {}}
                    }},
                    {"type": "function", "function": {
                        "name": "stop_auto_trading",
                        "description": "Stop automated trading strategy",
                        "parameters": {"type": "object", "properties": {}}
                    }},
                    {"type": "function", "function": {
                        "name": "get_bot_status",
                        "description": "Get current bot status and health",
                        "parameters": {"type": "object", "properties": {}}
                    }}
                ]
            )
            
            # Handle tool calls if present
            if run.status == 'requires_action':
                tool_outputs = []
                
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Executing tool: {function_name} with args: {function_args}")
                    
                    # Execute the tool function
                    if function_name in self.tools:
                        try:
                            result = await self.tools[function_name](**function_args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(result) if isinstance(result, dict) else str(result)
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": f"Error: {str(e)}"
                            })
                    else:
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": f"Unknown function: {function_name}"
                        })
                
                # Submit tool outputs and poll for completion
                run = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            
            # Get the assistant's response
            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                latest_message = messages.data[0]
                
                # Extract text content
                response_text = ""
                for content in latest_message.content:
                    if content.type == 'text':
                        response_text += content.text.value
                
                return response_text
            else:
                return f"🤖 I'm having trouble processing that right now. Status: {run.status}"
                
        except Exception as e:
            logger.error(f"Assistant run error: {e}")
            return f"🤖 Sorry, I encountered an error: {str(e)}"
    
    # Tool Functions (called by the assistant)
    
    async def _get_recent_trades(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent trading history"""
        try:
            # This would integrate with actual trade history
            recent_trades = self.trade_history[-limit:] if self.trade_history else []
            
            if not recent_trades:
                return {
                    "status": "success",
                    "message": "No recent trades found",
                    "trades": []
                }
            
            return {
                "status": "success",
                "trades": recent_trades,
                "count": len(recent_trades)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _scan_tokens(self, detailed: bool = False) -> Dict[str, Any]:
        """Scan for new token opportunities"""
        try:
            if not self.strategy:
                return {"status": "error", "message": "Strategy module not available"}
            
            # Trigger market scan
            scan_results = await self.strategy.scan_market_opportunities()
            
            if detailed:
                return {
                    "status": "success",
                    "scan_results": scan_results,
                    "opportunities": len(scan_results.get('opportunities', [])),
                    "rejections": len(scan_results.get('rejected_tokens', []))
                }
            else:
                opportunities = scan_results.get('opportunities', [])
                return {
                    "status": "success",
                    "message": f"Found {len(opportunities)} opportunities",
                    "top_opportunity": opportunities[0] if opportunities else None
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _watch_token(self, symbol: str) -> Dict[str, Any]:
        """Add token to watchlist"""
        try:
            self.watchlist.add(symbol.upper())
            return {
                "status": "success",
                "message": f"Added {symbol} to watchlist",
                "watchlist_size": len(self.watchlist)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _sell_token(self, symbol: str) -> Dict[str, Any]:
        """Sell a token position"""
        try:
            if not self.trader or not self.wallet:
                return {"status": "error", "message": "Trading components not available"}
            
            # This would integrate with actual selling logic
            # For now, return a placeholder
            return {
                "status": "success",
                "message": f"Sell order initiated for {symbol}",
                "action": "sell_initiated"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _buy_token(self, symbol: str, amount: float) -> Dict[str, Any]:
        """Buy token with specified USDC amount"""
        try:
            if not self.trader or not self.wallet:
                return {"status": "error", "message": "Trading components not available"}
            
            # This would integrate with actual buying logic
            # For now, return placeholder
            return {
                "status": "success",
                "message": f"Buy order initiated: {amount} USDC for {symbol}",
                "action": "buy_initiated",
                "amount": amount,
                "symbol": symbol
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_token_stats(self, symbol: str) -> Dict[str, Any]:
        """Get token statistics"""
        try:
            # This would fetch real token data
            return {
                "status": "success",
                "symbol": symbol,
                "message": f"Token stats for {symbol} would be fetched here",
                "placeholder": True
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_balance(self) -> Dict[str, Any]:
        """Get current wallet balance"""
        try:
            if not self.wallet:
                return {"status": "error", "message": "Wallet module not available"}
            
            balances = await self.wallet.get_all_balances()
            return {
                "status": "success",
                "balances": balances,
                "message": "Current wallet balances retrieved"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_watchlist(self) -> Dict[str, Any]:
        """Get current watchlist"""
        return {
            "status": "success",
            "watchlist": list(self.watchlist),
            "count": len(self.watchlist)
        }
    
    async def _remove_from_watchlist(self, symbol: str) -> Dict[str, Any]:
        """Remove token from watchlist"""
        try:
            self.watchlist.discard(symbol.upper())
            return {
                "status": "success",
                "message": f"Removed {symbol} from watchlist",
                "watchlist_size": len(self.watchlist)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_market_summary(self) -> Dict[str, Any]:
        """Get market summary"""
        try:
            if not self.strategy:
                return {"status": "error", "message": "Strategy module not available"}
            
            # This would get real market data
            return {
                "status": "success",
                "message": "Market summary would be provided here",
                "placeholder": True
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _start_auto_trading(self) -> Dict[str, Any]:
        """Start automated trading"""
        try:
            if not self.strategy:
                return {"status": "error", "message": "Strategy module not available"}
            
            # This would start the auto trading loop
            return {
                "status": "success",
                "message": "Automated trading started",
                "action": "auto_trading_started"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _stop_auto_trading(self) -> Dict[str, Any]:
        """Stop automated trading"""
        try:
            return {
                "status": "success",
                "message": "Automated trading stopped",
                "action": "auto_trading_stopped"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_bot_status(self) -> Dict[str, Any]:
        """Get bot health and status"""
        return {
            "status": "success",
            "bot_status": "running",
            "components": {
                "trader": self.trader is not None,
                "wallet": self.wallet is not None,
                "strategy": self.strategy is not None,
                "scanner": self.scanner is not None,
                "safety": self.safety is not None
            },
            "watchlist_size": len(self.watchlist),
            "active_threads": len(self.active_threads)
        }
    
    def clear_thread(self, user_id: str):
        """Clear conversation thread for user"""
        if user_id in self.active_threads:
            del self.active_threads[user_id]
            logger.info(f"🗑️ Cleared thread for user {user_id}") 