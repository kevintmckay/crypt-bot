# CryptBot - BTC/USD Trend Following Trading Bot

A systematic cryptocurrency trading bot that implements a 50-day SMA trend-following strategy for Bitcoin (BTC/USD) using the Alpaca API. The bot features automated weekly rebalancing, stop-loss protection, volatility filtering, and comprehensive reliability mechanisms.

## Features

### Trading Strategy
- **50-day SMA trend following** - Buy when price > SMA, sell when price < SMA
- **Weekly rebalancing** - Trades on Mondays (vs monthly for stocks)
- **15% stop loss** - Protection against crypto volatility
- **10% volatility filter** - Skips trading during extreme market moves
- **50% position sizing** - Conservative account allocation
- **24/7 operation** - Daily checks at 12:00 UTC (PST timezone)

### Reliability & Safety
- **Circuit breaker** - Automatic API failure detection and recovery
- **Retry logic** - Exponential backoff for transient failures
- **Position locking** - Prevents concurrent trade execution
- **Paper trading mode** - Safe testing with simulated funds

### Technical Features
- Hourly data granularity for better volatility detection
- Fractional BTC quantities (6 decimal precision)
- Comprehensive logging and error handling
- Systemd service for auto-start and monitoring

## Project Structure

```
cryptbot/
├── main.py                    # Main bot orchestrator
├── strategies/
│   ├── crypto_trend.py        # Crypto-specific strategy logic
│   └── trend_following.py     # Base trend-following strategy
├── execution/
│   └── broker.py              # Alpaca crypto API integration
├── core/
│   ├── config.py              # Secure configuration validation
│   ├── market_hours.py        # 24/7 crypto market handling
│   └── reliability.py         # Circuit breaker, retry, locking
├── tests/                     # Comprehensive test suite (28 tests)
├── logs/                      # Application and systemd logs
├── scripts/                   # Utility scripts
└── docs/                      # Additional documentation
```

## Installation

### Prerequisites
- Python 3.8+
- Alpaca API account (paper trading recommended)
- Linux system with systemd (for auto-start)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cryptbot
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.template .env
   nano .env  # Edit with your API keys
   ```

5. **Run setup script**
   ```bash
   ./setup.sh
   ```

## Configuration

Edit `.env` file with your settings:

```bash
# Alpaca API Configuration
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true

# Trading Strategy Configuration
SYMBOL=BTC/USD
SMA_PERIOD=50                    # 50-day SMA
ACCOUNT_ALLOCATION=0.50          # Use 50% of account
STOP_LOSS_PCT=0.15               # 15% stop loss
VOLATILITY_THRESHOLD=0.10        # 10% volatility filter

# Logging
LOG_LEVEL=INFO
```

## Usage

### Manual Execution
```bash
source venv/bin/activate
python main.py
```

### Systemd Service (Recommended)
```bash
# Copy service file
sudo cp trend-bot.service /etc/systemd/system/cryptbot.service

# Edit paths in service file if needed
sudo nano /etc/systemd/system/cryptbot.service

# Enable and start
sudo systemctl enable cryptbot.service
sudo systemctl start cryptbot.service

# Check status
sudo systemctl status cryptbot.service
```

### Monitoring Logs
```bash
# Real-time application logs
tail -f logs/bot.log

# View systemd logs
sudo journalctl -u cryptbot.service -f

# Filter for trades only
grep "BUY\|SELL" logs/bot.log

# Check for errors
grep "ERROR" logs/bot.log
```

## Testing

Run the comprehensive test suite:

```bash
# All tests
./venv/bin/python -m pytest tests/ -v

# Specific test files
./venv/bin/python -m pytest tests/test_crypto_strategy.py -v
./venv/bin/python -m pytest tests/test_volatility.py -v

# With coverage
./venv/bin/python -m pytest tests/ -v --cov=.
```

## Architecture

### Strategy Logic
- `strategies/crypto_trend.py` - Crypto-specific SMA trend following
- Hourly data granularity (1200 hours = 50 days)
- Fractional BTC quantities with 6 decimal precision
- Integrated volatility filter and stop-loss tracking

### Broker Integration
- `execution/broker.py` - Alpaca crypto API wrapper
- Supports both paper and live trading
- Comprehensive error handling
- Circuit breaker integration

### Reliability Components
- **Circuit Breaker** - Tracks API failures, opens after 5 consecutive errors
- **Retry Logic** - Exponential backoff with jitter (max 3 retries)
- **Position Locking** - File-based locks prevent concurrent trades
- **Persistent State** - Circuit breaker state survives restarts

### Market Hours
- 24/7 operation for crypto markets
- Daily checks at 12:00 UTC (configured for PST timezone)
- Weekly rebalancing on Mondays

## Monitoring

See `MONITORING_TODO.md` for current capabilities and planned improvements.

### Current Metrics Logged
- Account equity & buying power
- Current BTC position & price
- 50-day SMA calculation
- Buy/sell signals with reasoning
- Order IDs and execution status
- Stop-loss tracking
- Circuit breaker state changes
- Volatility filter triggers

## Safety & Risk Management

### Built-in Protections
1. **Paper trading mode** - Test with simulated funds
2. **Position limits** - 50% account allocation by default
3. **Stop loss** - 15% protection against large moves
4. **Volatility filter** - Pauses trading during 10%+ volatility
5. **Circuit breaker** - Prevents repeated API failures
6. **Position locking** - No concurrent trade execution

### Recommended Practices
- Start with paper trading mode
- Monitor logs regularly
- Set conservative position sizes
- Review trades weekly
- Keep API keys secure (never commit to git)

## Troubleshooting

### Common Issues

**Bot not trading**
- Check logs for errors: `tail -f logs/bot.log`
- Verify API keys are valid
- Ensure market conditions meet strategy criteria
- Check circuit breaker state: `cat logs/circuit_breaker_alpaca.json`

**Systemd service fails**
- Check status: `sudo systemctl status cryptbot.service`
- View logs: `sudo journalctl -u cryptbot.service -n 50`
- Verify file paths in service file
- Ensure proper permissions on script files

**API errors**
- Circuit breaker may be open - wait for automatic reset (5 minutes)
- Check Alpaca API status
- Verify API keys and permissions
- Review rate limits

## Development

### Adding New Features
1. Create feature branch
2. Add tests for new functionality
3. Update documentation
4. Run test suite
5. Submit pull request

### Code Style
- Follow PEP 8
- Add docstrings to all functions
- Keep functions focused and testable
- Use type hints where helpful

## License

See LICENSE file for details.

## Disclaimer

This trading bot is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.

**Important**: Always test with paper trading before using real funds.

## Support

For issues or questions:
1. Check existing documentation
2. Review logs for error messages
3. Consult `MONITORING_TODO.md` for known limitations
4. Open an issue with detailed information
