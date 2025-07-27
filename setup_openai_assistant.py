"""
🛠️ Setup script for OpenAI Assistant - GrokBot Agent SDK
Creates and configures the OpenAI assistant with trading tools
"""

import os
from openai import OpenAI

def create_grokbot_assistant():
    """Create GrokBot assistant with trading tools"""
    
    # Initialize OpenAI client
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("Please set OPENAI_API_KEY in your .env file")
        return None
    
    client = OpenAI(api_key=openai_key)
    
    # Define tools for the assistant
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_recent_trades",
                "description": "Get the bot's recent trading history",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of trades to return",
                            "default": 10
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scan_tokens",
                "description": "Scan for new token opportunities on Solana",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Whether to return detailed analysis",
                            "default": False
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "watch_token",
                "description": "Add a token to the watchlist for monitoring",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Token symbol or contract address"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sell_token",
                "description": "Sell a token position from the wallet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Token symbol to sell"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buy_token",
                "description": "Buy a token with USDC from the wallet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Token symbol or contract address to buy"
                        },
                        "amount": {
                            "type": "number",
                            "description": "USDC amount to spend on the purchase"
                        }
                    },
                    "required": ["symbol", "amount"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_token_stats",
                "description": "Get current token statistics and market data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Token symbol or contract address"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_balance",
                "description": "Get current wallet balance including all tokens",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_watchlist",
                "description": "Get the current list of tokens being watched",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_market_summary",
                "description": "Get overall market summary and trending tokens",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "start_auto_trading",
                "description": "Start the automated trading strategy",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "stop_auto_trading",
                "description": "Stop the automated trading strategy",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_bot_status",
                "description": "Get current bot status and health information",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]
    
    # Create the assistant
    assistant = client.beta.assistants.create(
        name="GrokBot - Solana Meme Coin Trading Assistant",
        instructions="""
You are GrokBot, a fast, smart crypto trading assistant focused on Solana meme coin trading and sniping. 
You help users discover, analyze, and trade new meme coins on Solana with real-time data and automated strategies.

## Your Capabilities:
- 🔍 Scan for new trading opportunities on Solana
- 💰 Execute buy/sell orders via USDC swaps  
- 📊 Analyze token statistics, liquidity, and risk factors
- 👀 Manage watchlists for tracking interesting tokens
- 🤖 Control automated trading strategies
- 💼 Check wallet balances and trading history

## Your Personality:
- Be conversational but concise
- Use emojis to make responses engaging
- Always confirm with the user if a token looks suspicious or risky
- Explain trading decisions clearly
- Be proactive about risk management

## Trading Safety:
- Always warn about high-risk tokens
- Confirm large trades with the user
- Explain price impact and liquidity concerns
- Suggest position sizes based on risk level

## Response Style:
- Keep responses under 200 words when possible
- Use bullet points for lists
- Include relevant numbers (prices, percentages, amounts)
- Always include next steps or suggested actions

Remember: You're helping with high-risk meme coin trading. Always prioritize user safety and education.
        """,
        model="gpt-4o",
        tools=tools
    )
    
    print(f"✅ GrokBot Assistant created successfully!")
    print(f"🆔 Assistant ID: {assistant.id}")
    print(f"📝 Name: {assistant.name}")
    print(f"🔧 Tools: {len(tools)} functions registered")
    
    print(f"\n📋 Add this to your environment variables:")
    print(f"OPENAI_ASSISTANT_ID={assistant.id}")
    
    return assistant.id

if __name__ == "__main__":
    assistant_id = create_grokbot_assistant() 