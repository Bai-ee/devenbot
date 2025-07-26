#!/usr/bin/env python3
"""
Test script for Grok Trading Bot USDC to SOL swap
This will test the complete swap flow using GMGN API
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.trades import GMGNTrader
from modules.wallet import SolanaWallet

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_usdc_to_sol_swap():
    """Test a $1 USDC to SOL swap"""
    
    print("🤖 Grok Trading Bot - USDC to SOL Swap Test")
    print("=" * 50)
    
    try:
        # Initialize components
        print("\n📋 Initializing components...")
        trader = GMGNTrader()
        wallet = SolanaWallet()
        
        print(f"✅ Wallet Address: {wallet.get_address()}")
        
        # Check wallet balance
        print("\n💰 Checking wallet balance...")
        balance_result = await wallet.get_balance()
        if balance_result['success']:
            print(f"✅ SOL Balance: {balance_result['balance']:.6f} SOL")
        else:
            print(f"❌ Balance check failed: {balance_result['error']}")
        
        # Token addresses
        USDC_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        SOL_ADDRESS = 'So11111111111111111111111111111111111111112'
        
        # Test parameters
        swap_amount = 1.0  # $1 USDC
        usdc_amount_units = int(swap_amount * 1_000_000)  # USDC has 6 decimals
        
        print(f"\n🔄 Getting swap route for {swap_amount} USDC → SOL...")
        print(f"   USDC Amount: {usdc_amount_units} units ({swap_amount} USDC)")
        
        # Get swap route from GMGN
        route_result = await trader.get_swap_route(
            token_in_address=USDC_ADDRESS,
            token_out_address=SOL_ADDRESS,
            in_amount=str(usdc_amount_units),
            from_address=wallet.get_address(),  # Use actual wallet address
            slippage=1.0,
            fee=0.0025,
            is_anti_mev=True,
            print_debug=True
        )
        
        if not route_result['success']:
            print(f"❌ Failed to get swap route: {route_result['error']}")
            return False
        
        # Display swap details
        quote = route_result.get('quote', {})
        raw_tx = route_result.get('raw_tx', {})
        
        print(f"\n📊 Swap Route Details:")
        print(f"   Input: {swap_amount} USDC")
        print(f"   Output: ~{float(quote.get('outAmount', 0)) / 1e9:.6f} SOL")
        print(f"   Price Impact: {quote.get('priceImpactPct', 0)}%")
        print(f"   Route: {quote.get('routePlan', [{}])[0].get('swapInfo', {}).get('label', 'Unknown DEX')}")
        print(f"   Platform Fee: {quote.get('platformFee', 0)} units")
        print(f"   USD Value In: ${route_result.get('amount_in_usd', 'N/A')}")
        print(f"   USD Value Out: ${route_result.get('amount_out_usd', 'N/A')}")
        
        print(f"\n⚠️  TRANSACTION READY")
        print(f"   Raw transaction received from GMGN")
        print(f"   Transaction size: {len(raw_tx)} characters")
        
        # Ask for confirmation
        print(f"\n🚨 CONFIRMATION REQUIRED")
        print(f"   This will execute a REAL transaction with your USDC!")
        print(f"   You will swap {swap_amount} USDC for approximately {float(quote.get('outAmount', 0)) / 1e9:.6f} SOL")
        
        confirmation = input("\n   Type 'YES' to confirm the swap, anything else to cancel: ")
        
        if confirmation.upper() != 'YES':
            print("❌ Swap cancelled by user")
            return False
        
        # Execute the swap
        print(f"\n🚀 Executing swap transaction...")
        
        # Get the actual raw transaction from GMGN response
        swap_transaction = raw_tx.get('swapTransaction', '')
        
        if not swap_transaction:
            print("❌ No swap transaction data received from GMGN")
            return False
        
        # Execute the transaction
        tx_result = await wallet.execute_swap(swap_transaction)
        
        if tx_result['success']:
            print(f"✅ Swap executed successfully!")
            print(f"   Transaction Hash: {tx_result['transaction_hash']}")
            print(f"   Status: {tx_result['status']}")
            print(f"   Explorer: {tx_result['explorer_url']}")
            
            print(f"\n🎉 Swap Complete!")
            print(f"   Your {swap_amount} USDC has been swapped for SOL")
            print(f"   Check your wallet balance to see the new SOL")
            
            return True
        else:
            print(f"❌ Swap execution failed: {tx_result['error']}")
            return False
    
    except Exception as e:
        print(f"❌ Error during swap test: {e}")
        logger.error(f"Swap test error: {e}")
        return False

async def main():
    """Main test function"""
    
    # Check environment variables
    required_vars = ['SOLANA_PRIVATE_KEY', 'SOLANA_RPC_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please update your .env file with your Solana credentials")
        return
    
    print("🔧 Environment check passed")
    
    # Run the swap test
    success = await test_usdc_to_sol_swap()
    
    if success:
        print(f"\n🎊 Test completed successfully!")
    else:
        print(f"\n💥 Test failed!")

if __name__ == "__main__":
    asyncio.run(main()) 