# 🚀 Deploy Your Grok Trading Bot

## 🎯 Quick Deploy to Railway (FREE)

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 2: Login & Deploy
```bash
# Login to Railway
railway login

# Deploy from your project directory
railway init
railway up
```

### Step 3: Set Environment Variables
In Railway dashboard, add these environment variables:
- `TELEGRAM_TOKEN` = `7510065315:AAFTwyomR...` (your bot token)
- `SOLANA_PRIVATE_KEY` = `4duAUGxB2zQh...` (your wallet private key)
- `SOLANA_RPC_URL` = `https://api.mainnet-beta.solana.com`
- `ADMIN_CHAT_ID` = `1508863163` (your Telegram user ID)

### Step 4: Start Bot
Your bot will auto-start! Check logs in Railway dashboard.

---

## 🔄 Alternative: Heroku (FREE)

### Deploy to Heroku
```bash
# Install Heroku CLI first
heroku create your-grok-bot
git push heroku main

# Set environment variables
heroku config:set TELEGRAM_TOKEN=7510065315:AAFTwyomR...
heroku config:set SOLANA_PRIVATE_KEY=4duAUGxB2zQh...
heroku config:set SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
heroku config:set ADMIN_CHAT_ID=1508863163

# Scale worker (not web)
heroku ps:scale worker=1
```

---

## 🎉 After Deployment

1. **Test the bot**: Go to https://t.me/ebrenillabDegen_Bot
2. **Start automation**: Send `/start_auto` 
3. **Check status**: Send `/auto_status`
4. **Monitor**: The bot will scan for opportunities every 30s!

## 🤖 Bot Features After Deploy

✅ **24/7 Operation** - Runs even when your computer is off  
✅ **Automated Trading** - Scans for opportunities every 30s  
✅ **Risk Management** - Max $5 per trade, 10 trades daily  
✅ **Real-time Alerts** - Notifies you of all trades  
✅ **Manual Override** - You can still trade manually  

## 🔧 Monitoring

- **Railway**: Check logs at railway.app dashboard
- **Heroku**: `heroku logs --tail` to see live logs
- **Telegram**: Bot sends you all trade notifications

---

## 🆘 Troubleshooting

**Bot not responding?**
- Check environment variables are set correctly
- Verify logs for errors in dashboard
- Make sure worker process is running (not web process)

**No trades happening?**
- Send `/auto_status` to check if automation is running
- Send `/start_auto` to start automated trading
- Check your balance with `/balance`

**Need help?**
- Check Railway/Heroku logs for detailed error messages
- All trades are logged with transaction links 