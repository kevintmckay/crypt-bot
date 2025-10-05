# Trading Bot Quick Reference Guide

## Bot Comparison at a Glance

| Aspect | **CryptBot** 🪙 | **StockBot** 📈 |
|--------|----------------|----------------|
| **Path** | `/home/cryptbot/cryptbot` | `/home/stockbot/stockbot` |
| **Asset** | BTC/USD (Bitcoin) | SPY (S&P 500 ETF) |
| **Market** | 24/7/365 | Mon-Fri 9:30am-4pm ET |
| **User** | cryptbot | stockbot |
| **Git Remote** | (local only) | (local only) |

---

## Strategy Differences

| Parameter | CryptBot | StockBot | Why Different? |
|-----------|----------|----------|----------------|
| **SMA Period** | 50 days | 200 days | Crypto trends faster |
| **Rebalance Freq** | Weekly (Mondays) | Monthly (1st trading day) | Crypto more dynamic |
| **Data Granularity** | Hourly bars | Daily bars | Better volatility detection |
| **Position Size** | 50% of account | 95% of account | Crypto riskier |
| **Stop Loss** | 15% | 10% | Crypto more volatile |
| **Volatility Filter** | 10% (24hr range) | 5% (5-day range) | Crypto swings harder |
| **Share Precision** | 6 decimals (0.000001 BTC) | Whole shares only | Crypto allows fractions |

---

## Configuration Files

### CryptBot `.env`
```bash
# Trading
SYMBOL=BTC/USD
ACCOUNT_ALLOCATION=0.50
SMA_PERIOD=50
STOP_LOSS_PCT=0.15
VOLATILITY_THRESHOLD=0.10

# Alpaca
ALPACA_API_KEY=xxx
ALPACA_SECRET_KEY=xxx
ALPACA_PAPER=true

# Email (shared)
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_TO=kevintmckay@gmail.com
```

### StockBot `.env`
```bash
# Trading
SYMBOL=SPY
ACCOUNT_ALLOCATION=0.95
SMA_PERIOD=200
STOP_LOSS_PCT=0.10
VOLATILITY_THRESHOLD=0.05

# Alpaca
ALPACA_API_KEY=xxx
ALPACA_SECRET_KEY=xxx
ALPACA_PAPER=true

# Email (shared)
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_TO=kevintmckay@gmail.com
```

---

## File Structure

### CryptBot
```
/home/cryptbot/cryptbot/
├── main.py                      # BTC bot orchestrator (281 lines)
├── strategies/
│   └── crypto_trend.py          # 50-day SMA + stop loss + volatility (237 lines)
├── execution/
│   └── broker.py                # Crypto broker client (203 lines)
├── core/
│   ├── reliability.py           # Circuit breaker, retry, locking (250 lines)
│   └── notifications.py         # Email alerting (300 lines)
├── tests/                       # 28 tests
└── scripts/
    └── setup_email_password.sh
```

### StockBot
```
/home/stockbot/stockbot/
├── main.py                      # SPY bot orchestrator (310 lines)
├── strategies/
│   └── trend_following.py       # 200-day SMA + stop loss + volatility (220 lines)
├── execution/
│   └── broker.py                # Stock broker client (201 lines)
├── core/
│   ├── reliability.py           # Circuit breaker, retry, locking (250 lines)
│   ├── notifications.py         # Email alerting (300 lines)
│   ├── market_hours.py          # NYSE/NASDAQ calendar (450 lines) ⚠️ UNIQUE
│   └── config.py                # Security validation (400 lines) ⚠️ UNIQUE
├── tests/                       # 38 tests
└── deployment/
    └── systemd_setup.sh
```

---

## Key Class Differences

### Strategy Classes

**CryptBot:**
```python
class CryptoTrendStrategy:
    def __init__(self,
                 sma_period: int = 50,
                 stop_loss_pct: float = 0.15,
                 volatility_threshold: float = 0.10)

    def should_rebalance(self, current_date) -> bool:
        # Weekly on Mondays
        is_monday = current_date.weekday() == 0
        return is_monday and week_changed

    def check_volatility(self, prices) -> bool:
        # Last 24 hours (hourly data)
        recent_prices = prices.tail(24)
```

**StockBot:**
```python
class TrendFollowingStrategy:
    def __init__(self,
                 sma_period: int = 200,
                 stop_loss_pct: float = 0.10,
                 volatility_threshold: float = 0.05)

    def should_rebalance(self, current_date) -> bool:
        # Monthly (first trading day)
        current_month = (date.year, date.month)
        return current_month != last_month

    def check_volatility(self, prices) -> bool:
        # Last 5 days (daily data)
        recent_prices = prices.tail(5)
```

---

## Trading Schedule

### CryptBot
```
Market: 24/7/365
Check: Daily at 12:00 PST
Trade: Mondays only (if conditions met)
Holidays: None (crypto never sleeps)
```

### StockBot
```
Market: Mon-Fri 9:30am-4pm ET
Check: Daily at market open
Trade: First trading day of month (if conditions met)
Holidays: NYSE calendar (10+ holidays/year)
```

---

## Unique Features

### CryptBot Only
- ✅ **Hourly data support** - Better granularity
- ✅ **24/7 operation** - No market hours logic
- ✅ **Fractional quantities** - 0.05 BTC precision
- ✅ **Weekly rebalancing** - More responsive

### StockBot Only
- ✅ **Market hours checking** - 450 lines of calendar logic
- ✅ **Holiday awareness** - NYSE/NASDAQ holiday calendar
- ✅ **Config validation** - Security checks for API keys
- ✅ **Early close detection** - Half-day trading awareness
- ✅ **Timezone management** - ET/PST conversion utilities

### Shared Features
- ✅ Circuit breaker pattern
- ✅ Retry with exponential backoff
- ✅ Position locking (prevent race conditions)
- ✅ Email notifications via postfix
- ✅ Stop loss protection
- ✅ Volatility filtering
- ✅ Comprehensive testing
- ✅ Alpaca broker integration

---

## Running the Bots

### CryptBot
```bash
# Test run
cd /home/cryptbot/cryptbot
./venv/bin/python main.py --once

# Continuous
./venv/bin/python main.py

# Tests
./venv/bin/python -m pytest tests/ -v
```

### StockBot
```bash
# Test run
cd /home/stockbot/stockbot
./venv/bin/python main.py --once

# Continuous
./venv/bin/python main.py

# Tests
./venv/bin/python -m pytest tests/ -v
```

---

## Testing Commands

### CryptBot
```bash
cd /home/cryptbot/cryptbot

# All tests (28 total)
./venv/bin/python -m pytest tests/ -v

# Strategy tests
./venv/bin/python -m pytest tests/test_crypto_strategy.py -v

# Volatility tests
./venv/bin/python -m pytest tests/test_volatility.py -v

# Notifications test
./venv/bin/python test_notifications.py
```

### StockBot
```bash
cd /home/stockbot/stockbot

# All tests (38 total)
./venv/bin/python -m pytest tests/ -v

# Strategy tests
./venv/bin/python -m pytest tests/test_strategy.py -v

# Risk management tests
./venv/bin/python -m pytest tests/test_risk_management.py -v

# Edge cases
./venv/bin/python -m pytest tests/test_edge_cases.py -v

# Notifications test
./venv/bin/python test_notifications.py
```

---

## Git Workflow

### CryptBot
```bash
cd /home/cryptbot/cryptbot
git status
git add .
git commit -m "message"
git log --oneline -5
```

### StockBot
```bash
cd /home/stockbot/stockbot
sudo bash -c 'cd /home/stockbot/stockbot && sudo -u stockbot git status'
sudo bash -c 'cd /home/stockbot/stockbot && sudo -u stockbot git add .'
sudo bash -c 'cd /home/stockbot/stockbot && sudo -u stockbot git commit -m "message"'
```

**Note:** StockBot requires sudo because of user permissions.

---

## Common Mistakes to Avoid ⚠️

| Mistake | Wrong | Right |
|---------|-------|-------|
| **Wrong stop loss** | StockBot with 15% | StockBot uses 10% |
| **Wrong SMA** | CryptBot with 200-day | CryptBot uses 50-day |
| **Wrong allocation** | CryptBot with 95% | CryptBot uses 50% |
| **Wrong volatility** | StockBot with 10% | StockBot uses 5% |
| **Wrong data** | StockBot with hourly | StockBot uses daily |
| **Wrong schedule** | StockBot weekly | StockBot monthly |

---

## When Porting Features

### From CryptBot → StockBot

1. **Reduce volatility thresholds** (10% → 5%)
2. **Reduce stop loss** (15% → 10%)
3. **Change to daily data** (hourly → daily)
4. **Add market hours checks** (if needed)
5. **Use whole shares** (not fractional)

### From StockBot → CryptBot

1. **Increase volatility thresholds** (5% → 10%)
2. **Increase stop loss** (10% → 15%)
3. **Change to hourly data** (daily → hourly)
4. **Remove market hours checks**
5. **Allow fractional quantities**

---

## Email Notifications (Shared)

Both bots use the same email configuration:

```bash
From: cryptbot@trader.lan (rewritten to kevintmckay@sonic.net)
To: kevintmckay@gmail.com
Via: Local postfix → smtp.sonic.net:587
```

**Notification triggers:**
- ✅ Trade executions (BUY/SELL)
- ✅ Errors/exceptions
- ✅ Circuit breaker trips
- ✅ Circuit breaker resets

---

## Performance Tracking

### CryptBot Expected Activity
- **Checks:** Daily at 12:00 PST
- **Trades:** ~52/year (weekly rebalancing)
- **Max trades/month:** ~4-5
- **Position:** 50% of account in BTC or 0%

### StockBot Expected Activity
- **Checks:** Daily at market open
- **Trades:** ~12/year (monthly rebalancing)
- **Max trades/month:** ~1-2
- **Position:** 95% of account in SPY or 0%

---

## Quick Sanity Checks

Before making changes, verify:

```bash
# Which bot am I in?
pwd
# Should see /home/cryptbot/cryptbot OR /home/stockbot/stockbot

# Which user?
whoami
# cryptbot for CryptBot, your-user for StockBot

# What are the current settings?
grep -E "SMA_PERIOD|STOP_LOSS|VOLATILITY|ALLOCATION" .env

# What's the strategy class?
grep "class.*Strategy" strategies/*.py
```

---

## Emergency Reference

| Need | CryptBot | StockBot |
|------|----------|----------|
| **Stop bot** | `pkill -f "cryptbot.*main.py"` | `pkill -f "stockbot.*main.py"` |
| **Check logs** | `tail -f logs/bot.log` | `tail -f logs/bot.log` |
| **Email log** | `tail -f logs/notifications.log` | `tail -f logs/notifications.log` |
| **Mail status** | `sudo tail -f /var/log/mail.log` | (same - shared postfix) |

---

## Version History

- **2025-10-05:** Added risk management features to both bots
- **2025-10-05:** Added email notifications via postfix
- **2025-10-04:** Initial bot creation

---

## Notes

- Both bots use **paper trading** by default
- Both bots use the **same Alpaca account**
- Both bots send email to **same address**
- Both bots **never trade simultaneously** (different schedules)
- CryptBot is more **conservative** (50% allocation)
- StockBot is more **aggressive** (95% allocation)

---

*Last Updated: 2025-10-05*
*Maintained by: Claude Code*
