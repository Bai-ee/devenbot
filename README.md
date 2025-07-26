# 🤖 Grok Trading Bot - Automated Solana Memecoin Trader

A fully automated, modular Solana memecoin trading bot with Telegram interface, real-time market scanning, and risk-managed trading strategies.

## 🚀 **Features**

### 🔄 **Manual Trading**
- Real-time wallet balance checking
- Manual token swaps via Telegram commands
- Support for popular Solana tokens (WIF, BONK, POPCAT, etc.)
- Live SOL price integration via CoinGecko API

### 🤖 **Automated Trading** 
- **Passive income generation** - bot scans and trades automatically
- Configurable risk management (2% min profit, $5 max trades)
- Daily trade limits (10 trades/day by default)
- Real-time opportunity scanning every 30 seconds

### 🔍 **Market Analysis**
- **One-shot market scanner** (`/scan` command)
- Analyzes 8+ popular Solana memecoins simultaneously
- Price impact analysis and liquidity testing
- Detailed rejection reasons when no opportunities found

### 🛡️ **Security & Risk Management**
- Admin-only automation controls
- Wallet signature authentication
- Transaction staleness prevention
- Configurable position sizing and profit thresholds

---

## 🛠️ **Tech Stack**

### **Core Technologies**
- **Python 3.11+** - Main application language
- **Solana Web3** - Blockchain interaction (`solana`, `solders`, `anchorpy`)
- **GMGN API** - DEX aggregator for swap routing (no API key required)
- **Telegram Bot API** - User interface and notifications
- **Railway** - Cloud deployment platform
- **Docker** - Containerization (optional)

### **Key Dependencies**
```python
# Solana & Blockchain
solana>=0.30.0
solders>=0.18.0
anchorpy>=0.18.0
base58>=2.1.1

# Telegram Bot
python-telegram-bot>=20.0

# HTTP & API
aiohttp>=3.8.0
requests>=2.28.0
httpx>=0.24.0

# Data & Analysis
pandas>=1.5.0
numpy>=1.24.0
python-dateutil>=2.8.0

# Environment & Config
python-dotenv>=0.19.0
colorlog>=6.7.0

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

### **External APIs**
- **GMGN Solana Trading API** - Swap routing and transaction generation
- **CoinGecko API** - Real-time price data
- **Solana RPC** - Blockchain interaction (`https://api.mainnet-beta.solana.com`)

---

## 🚀 **Deployment Guide**

### **Method 1: Railway (Recommended - FREE)**

#### **Prerequisites**
```bash
npm install -g @railway/cli
```

#### **Step-by-Step Deployment**

1. **Clone & Setup**
```bash
git clone https://github.com/Bai-ee/devenbot.git
cd devenbot
```

2. **Install Dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure Environment**
Create `.env` file:
```bash
# Telegram Bot (Get from @BotFather)
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_telegram_user_id

# Solana Configuration
SOLANA_PRIVATE_KEY=your_solana_private_key
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Optional: Custom RPC for better performance
# SOLANA_RPC_URL=https://rpc.hellomoon.io/your-api-key
```

4. **Deploy to Railway**
```bash
# Login to Railway
railway login

# Initialize project (AVOID TEMPLATES!)
railway init

# Deploy using existing service
railway up --detach
```

5. **Set Environment Variables in Railway Dashboard**
- Go to Railway project dashboard
- Click "Variables" tab
- Add all variables from your `.env` file

6. **Verify Deployment**
```bash
railway logs  # Check if bot started successfully
```

### **Method 2: Local Development**

1. **Run Locally**
```bash
source venv/bin/activate
python start_telegram_bot.py
```

2. **Bot will be available at:** `https://t.me/your_bot_username`

---

## 📱 **Bot Commands**

### **Manual Trading**
- `/balance` - Check wallet balance
- `/swap <amount> <from> <to>` - Execute token swap
- `/analyze <token_address>` - Analyze specific token

### **Automated Trading**
- `/start_auto` - **Start passive income mode**
- `/stop_auto` - Stop automated trading
- `/auto_status` - Check automation status

### **Market Analysis**
- `/scan` - **One-shot market opportunity scan**
- `/help` - Show all commands
- `/status` - Bot health check

---

## 🔧 **Development Guidelines**

### **Adding New Features**

#### **⚠️ Critical: Avoid Breaking Changes**

1. **Never modify core wallet signing logic** in `modules/wallet.py`
2. **Don't change GMGN API integration** without testing
3. **Always test with small amounts first**
4. **Railway deployment uses `railway up --detach`** (no templates!)

#### **Safe Development Practices**

1. **Create feature branches**
```bash
git checkout -b feature/new-scanner
```

2. **Test locally first**
```bash
python start_telegram_bot.py
# Test in Telegram before deploying
```

3. **Deploy to Railway**
```bash
railway up --detach  # NOT railway deploy
```

#### **Architecture Overview**

```
GrokBot/
├── modules/
│   ├── auth.py          # Telegram & wallet authentication
│   ├── trades.py        # GMGN API integration
│   ├── wallet.py        # Solana wallet operations  
│   ├── metrics.py       # Token analysis
│   ├── strategy.py      # Trading algorithms
│   └── telegram_bot.py  # Bot interface
├── start_telegram_bot.py # Main entry point
├── requirements.txt     # Dependencies
└── railway.json        # Railway config
```

#### **Key Integration Points**

1. **GMGN API** (`modules/trades.py`)
   - No API key required
   - Base URL: `https://gmgn.ai/defi/router/v1/sol`
   - Returns `VersionedTransaction` objects

2. **Solana Wallet** (`modules/wallet.py`)
   - Uses `solders` for transaction signing
   - Handles both `Transaction` and `VersionedTransaction`
   - Real-time balance fetching via RPC

3. **Strategy Engine** (`modules/strategy.py`)
   - Configurable risk parameters
   - Market scanning with 8+ tokens
   - Price impact and liquidity analysis

---

## 🐛 **Common Issues & Solutions**

### **Railway Deployment**
- **Problem**: "Select template" prompt
- **Solution**: Use `railway up --detach` instead of `railway deploy`

### **Transaction Signing**
- **Problem**: `VersionedTransaction has no attribute 'sign'`
- **Solution**: Already handled in `modules/wallet.py` - don't modify

### **GMGN API**
- **Problem**: `fee must be number` error
- **Solution**: Already includes required `fee` and `is_anti_mev` parameters

### **Balance Issues**
- **Problem**: Zero balances showing
- **Solution**: RPC rate limiting handled with fallbacks and delays

---

## 💰 **Live Trading Results**

✅ **Verified Working:**
- Manual swaps: USDC ↔ SOL confirmed
- Real balance tracking: $19.31 wallet verified
- Transaction execution: Multiple successful swaps
- 24/7 Railway deployment: Running continuously

---

## 🔐 **Security Notes**

- **Private keys** stored as environment variables only
- **Admin controls** prevent unauthorized automation
- **Transaction signing** happens locally, never shared
- **Railway environment** variables encrypted at rest

---

## 📈 **Roadmap**

- [ ] Multi-wallet support
- [ ] Advanced technical indicators
- [ ] Portfolio rebalancing
- [ ] Discord integration
- [ ] Web dashboard
- [ ] Mobile app

---

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Test thoroughly with small amounts
4. Submit a pull request

---

## ⚠️ **Disclaimer**

This bot trades with real cryptocurrency. **Use at your own risk.** Start with small amounts and understand the code before deploying. The developers are not responsible for any financial losses.

**Not financial advice. DYOR (Do Your Own Research).**

---

## 📞 **Support**

- **Issues**: Open a GitHub issue
- **Telegram**: Contact bot admin
- **Documentation**: This README

---

**Built with ❤️ for the Solana memecoin community** 