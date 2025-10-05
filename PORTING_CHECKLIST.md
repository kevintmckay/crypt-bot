# Feature Porting Checklist

## Purpose
This checklist ensures features added to one bot are systematically ported to the other bot with appropriate adaptations.

---

## Before You Start

### 1. Identify Feature Type

**Core Logic** → Port Exactly (No Changes)
- Circuit breaker
- Retry logic
- Position locking
- Email notifications
- Logging utilities
- Error handling

**Strategy Logic** → Adapt Parameters
- Stop loss thresholds
- Volatility filters
- SMA periods
- Rebalancing frequency
- Position sizing

**Bot-Specific** → Don't Port
- Market hours checking (StockBot only)
- Holiday calendar (StockBot only)
- Fractional share handling (CryptBot only)
- Hourly vs daily data fetching

### 2. Check Reference Guide
📖 See `docs/bot-comparison-reference.md` for parameter differences

---

## Porting Workflow

### Step 1: Implement in Source Bot

- [ ] **Write the feature**
  - Clean, documented code
  - Follow existing patterns
  - Add docstrings

- [ ] **Write tests**
  - Unit tests for new functionality
  - Integration tests if needed
  - Aim for >80% coverage

- [ ] **Run all tests**
  ```bash
  ./venv/bin/python -m pytest tests/ -v
  ```

- [ ] **Manual testing**
  - Run bot with `--once` flag
  - Verify logs look correct
  - Check for errors

- [ ] **Commit with clear message**
  ```bash
  git add .
  git commit -m "Add [feature]: [description]"
  ```
  - Include what changed
  - Include why it was added
  - Reference any issues

### Step 2: Determine If Porting Is Needed

Ask yourself:
1. **Is this core infrastructure?** → Yes, port it
2. **Is this strategy improvement?** → Yes, port with adaptations
3. **Is this bot-specific?** → No, don't port
4. **Is this a bug fix?** → Check if bug exists in other bot

**Decision Matrix:**

| Change Type | Example | Port to Other Bot? |
|-------------|---------|-------------------|
| Bug fix | Fix off-by-one error | ✅ Yes, if code exists |
| Core feature | Add email alerts | ✅ Yes, exactly |
| Strategy feature | Add volatility filter | ✅ Yes, adapt params |
| Performance | Optimize SMA calc | ✅ Yes, exactly |
| Bot-specific | Add market hours | ❌ No |
| Config | New env variable | ✅ Yes, document |
| Dependency | Add new package | ✅ Yes, sync versions |

### Step 3: Adapt for Target Bot

**Parameter Adaptation Table:**

| Parameter | CryptBot | StockBot | Notes |
|-----------|----------|----------|-------|
| **Stop Loss** | 15% | 10% | Crypto more volatile |
| **Volatility Threshold** | 10% | 5% | Crypto swings harder |
| **Volatility Lookback** | 24 hours | 5 days | Hourly vs daily data |
| **SMA Period** | 50 days | 200 days | Crypto trends faster |
| **Rebalance Frequency** | Weekly | Monthly | Crypto more dynamic |
| **Position Size** | 50% | 95% | Crypto riskier |
| **Share Precision** | 6 decimals | 0 decimals | Fractional vs whole |
| **Data Granularity** | Hourly | Daily | Better volatility detection |

**Example Adaptations:**

```python
# CryptBot - strategies/crypto_trend.py
class CryptoTrendStrategy:
    def __init__(self,
                 sma_period: int = 50,              # ← Crypto
                 stop_loss_pct: float = 0.15,       # ← Crypto
                 volatility_threshold: float = 0.10) # ← Crypto

    def check_volatility(self, prices):
        recent_prices = prices.tail(24)  # ← 24 hours

# StockBot - strategies/trend_following.py
class TrendFollowingStrategy:
    def __init__(self,
                 sma_period: int = 200,             # ← Stock
                 stop_loss_pct: float = 0.10,       # ← Stock
                 volatility_threshold: float = 0.05) # ← Stock

    def check_volatility(self, prices):
        recent_prices = prices.tail(5)   # ← 5 days
```

**Configuration Adaptation:**

```bash
# CryptBot .env
STOP_LOSS_PCT=0.15
VOLATILITY_THRESHOLD=0.10
SMA_PERIOD=50

# StockBot .env
STOP_LOSS_PCT=0.10
VOLATILITY_THRESHOLD=0.05
SMA_PERIOD=200
```

### Step 4: Port to Target Bot

- [ ] **Navigate to target bot**
  ```bash
  # If porting CryptBot → StockBot
  cd /home/stockbot/stockbot

  # If porting StockBot → CryptBot
  cd /home/cryptbot/cryptbot
  ```

- [ ] **Copy/modify the code**
  - Copy file structure
  - Adapt parameters (see table above)
  - Update imports if needed
  - Update class names if needed

- [ ] **Update configuration**
  - [ ] Update `.env.template`
  - [ ] Add new config variables
  - [ ] Document in comments

- [ ] **Update tests**
  - [ ] Port test file
  - [ ] Adapt test parameters
  - [ ] Add bot-specific test cases

- [ ] **Run target bot tests**
  ```bash
  ./venv/bin/python -m pytest tests/ -v
  ```

- [ ] **Fix any failures**
  - Review errors carefully
  - Check parameter adaptations
  - Verify imports

- [ ] **Manual test target bot**
  ```bash
  ./venv/bin/python main.py --once
  ```

- [ ] **Commit target bot changes**
  ```bash
  git add .
  git commit -m "Port [feature] from [source-bot]

  Adapted parameters:
  - [param1]: [source value] → [target value]
  - [param2]: [source value] → [target value]

  Source commit: [commit-hash]"
  ```

### Step 5: Verify Sync

- [ ] **Compare implementations**
  ```bash
  # Example: Compare strategy files
  diff /home/cryptbot/cryptbot/strategies/crypto_trend.py \
       /home/stockbot/stockbot/strategies/trend_following.py
  ```
  - Differences should only be parameters/bot-specific logic

- [ ] **Run both bot test suites**
  ```bash
  # CryptBot
  cd /home/cryptbot/cryptbot
  ./venv/bin/python -m pytest tests/ -v

  # StockBot
  cd /home/stockbot/stockbot
  ./venv/bin/python -m pytest tests/ -v
  ```

- [ ] **Test email notifications** (if changed)
  ```bash
  # CryptBot
  cd /home/cryptbot/cryptbot
  ./venv/bin/python test_notifications.py

  # StockBot
  cd /home/stockbot/stockbot
  ./venv/bin/python test_notifications.py
  ```

### Step 6: Document

- [ ] **Update bot-comparison-reference.md** (if needed)
  - New parameters
  - New features
  - Changed behavior

- [ ] **Update README** (if needed)
  - New dependencies
  - New environment variables
  - Changed setup steps

- [ ] **Create CHANGELOG entry** (optional)
  ```markdown
  ## [Unreleased]
  ### Added
  - [Feature name]: [Brief description]

  ### Changed
  - [What changed]: [Why it changed]
  ```

---

## Common Porting Scenarios

### Scenario 1: Adding Stop Loss (Real Example)

**Source:** CryptBot already has it
**Target:** StockBot needs it

**Steps:**
1. ✅ Copy `check_stop_loss()` method → No changes (core logic)
2. ✅ Copy `set_entry_price()` / `clear_entry_price()` → No changes
3. ⚠️ Adapt stop loss threshold: 15% → 10%
4. ✅ Copy test cases
5. ⚠️ Adapt test expectations: 15% → 10%
6. ✅ Update main.py to call new methods
7. ✅ Update .env.template with `STOP_LOSS_PCT=0.10`

### Scenario 2: Bug Fix in Circuit Breaker

**Source:** Found in CryptBot
**Target:** Likely exists in StockBot too

**Steps:**
1. ✅ Fix bug in CryptBot
2. ✅ Write test to prevent regression
3. ✅ Copy EXACT fix to StockBot (no adaptations needed)
4. ✅ Copy test to StockBot
5. ✅ Verify both bots pass tests

### Scenario 3: New Email Notification Type

**Source:** Either bot
**Target:** Both should have it

**Steps:**
1. ✅ Add new method to `core/notifications.py`
2. ✅ Update both bots (core code is identical)
3. ✅ Write test in one bot
4. ✅ Copy test to other bot
5. ✅ Test email delivery from both

### Scenario 4: Market Hours Feature (StockBot Only)

**Source:** StockBot
**Target:** Not applicable to CryptBot

**Steps:**
1. ✅ Implement in StockBot
2. ✅ Test thoroughly
3. ✅ Commit
4. ❌ **DO NOT** port to CryptBot
5. ✅ Update `bot-comparison-reference.md` to note difference

---

## Porting Anti-Patterns (Don't Do This!)

### ❌ Copy-Paste Without Thinking
```python
# DON'T: Copy CryptBot stop loss to StockBot without changing threshold
class TrendFollowingStrategy:
    def __init__(self):
        self.stop_loss_pct = 0.15  # ❌ WRONG! Should be 0.10 for stocks
```

### ❌ Port Bot-Specific Features
```python
# DON'T: Add market hours checking to CryptBot
class CryptoTrendStrategy:
    def should_trade(self):
        if not market_hours.is_open():  # ❌ Crypto is 24/7!
            return False
```

### ❌ Skip Testing
```python
# DON'T: Port without running tests
# "It works in CryptBot, so it'll work in StockBot"
# ❌ Different parameters might break assumptions!
```

### ❌ Forget Configuration
```python
# DON'T: Add feature but forget to update .env.template
# User won't know about STOP_LOSS_PCT=0.10
```

### ❌ Inconsistent Parameter Names
```python
# CryptBot
VOLATILITY_THRESHOLD=0.10

# StockBot
VOL_FILTER=0.05  # ❌ Use same name: VOLATILITY_THRESHOLD
```

---

## Quick Reference: File Locations

### CryptBot
```
/home/cryptbot/cryptbot/
├── main.py                      # Bot orchestrator
├── strategies/
│   └── crypto_trend.py          # Strategy logic
├── core/
│   ├── reliability.py           # Circuit breaker, retry
│   └── notifications.py         # Email alerts
├── execution/
│   └── broker.py                # Alpaca integration
├── tests/                       # Test suite
├── .env.template                # Config template
└── PORTING_CHECKLIST.md         # This file
```

### StockBot
```
/home/stockbot/stockbot/
├── main.py                      # Bot orchestrator
├── strategies/
│   └── trend_following.py       # Strategy logic
├── core/
│   ├── reliability.py           # Circuit breaker, retry
│   ├── notifications.py         # Email alerts
│   ├── market_hours.py          # 🔶 Stock-only
│   └── config.py                # 🔶 Stock-only
├── execution/
│   └── broker.py                # Alpaca integration
├── tests/                       # Test suite
├── .env.template                # Config template
└── PORTING_CHECKLIST.md         # This file
```

🔶 = Bot-specific, do NOT port

---

## Porting History

Track what's been ported to maintain parity:

### ✅ Synchronized Features
- Circuit breaker pattern
- Retry with exponential backoff
- Position locking
- Email notifications
- Stop loss protection
- Volatility filtering
- Entry price tracking

### 🔶 Bot-Specific Features (Not Ported)
- **StockBot only:**
  - Market hours checking
  - Holiday calendar
  - Config security validation
  - Early close detection

- **CryptBot only:**
  - 24/7 operation
  - Hourly data fetching
  - Fractional quantity support

### 📋 Pending Ports
*None currently*

---

## Questions to Ask Before Porting

1. **Does this improve reliability?** → Port it
2. **Does this improve safety?** → Port it
3. **Does this fix a bug?** → Port if bug exists in both
4. **Does this improve logging?** → Port it
5. **Is this market-specific logic?** → Adapt parameters
6. **Is this asset-specific logic?** → Don't port

---

## Getting Help

**If you're unsure whether to port:**
1. Check `docs/bot-comparison-reference.md`
2. Review this checklist
3. Ask: "Would the other bot benefit from this?"
4. When in doubt, port with adaptations

**If porting breaks tests:**
1. Review parameter adaptations (stop loss, volatility, etc.)
2. Check for bot-specific assumptions
3. Verify imports and paths
4. Test manually with `--once` flag

---

## Automation Ideas (Future)

*Possible improvements to this process:*

- [ ] Pre-commit git hook that reminds you to port
- [ ] Script to diff common files between bots
- [ ] Automated parameter adaptation
- [ ] Shared core library
- [ ] Monorepo migration

---

## Version History

- **2025-10-05:** Initial porting checklist created
  - After implementing risk management in both bots
  - Documented parameter adaptation tables
  - Added anti-patterns section

---

*Last Updated: 2025-10-05*
*Maintained by: Claude Code & Human Review*
