BTC/USD Trend-Following Bot - Specification
This adapts your existing SPY trend-bot architecture for crypto with necessary modifications for 24/7 markets and higher volatility.

Core Differences from SPY Trend-Bot
AspectSPY BotBTC BotSMA Period200 days50 daysRebalancingMonthly (first trading day)Weekly (every Monday)Execution TimeDaily at 4:15pm ETDaily at 12:00 UTCMarket HoursCheck NYSE hoursAlways open (24/7)Position Size95% of equity50% of equity (more conservative)Stop LossNone15% from entryVolatility FilterNoneSkip if daily range >10%

Technical Specification
File Structure
btc-trend-bot/
├── core/
│   ├── reliability.py      # Reuse from SPY bot
│   ├── config.py           # Modified for crypto params
│   └── market_hours.py     # Simplified (always open)
├── strategies/
│   └── crypto_trend.py     # NEW - crypto-specific logic
├── execution/
│   └── broker.py           # Modified for crypto endpoints
├── main.py                 # Modified orchestrator
├── .env                    # Crypto-specific config
└── tests/
    ├── test_strategy.py
    └── test_volatility.py  # NEW - crypto volatility tests
Strategy Implementation
File: strategies/crypto_trend.py
pythonimport pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional

class CryptoTrendStrategy:
    """
    Trend-following adapted for crypto markets
    
    Key differences from equity strategy:
    1. Shorter SMA period (50 vs 200 days)
    2. Weekly rebalancing (vs monthly)
    3. Stop loss at 15% (crypto can crash fast)
    4. Volatility filter (skip trading during extreme moves)
    """
    
    def __init__(self, 
                 sma_period: int = 50,
                 stop_loss_pct: float = 0.15,
                 volatility_threshold: float = 0.10):
        self.sma_period = sma_period
        self.stop_loss_pct = stop_loss_pct
        self.volatility_threshold = volatility_threshold
        self.last_rebalance_date = None
        self.entry_price = None
    
    def calculate_sma(self, prices: pd.Series) -> Optional[float]:
        """Calculate simple moving average"""
        if len(prices) < self.sma_period:
            return None
        
        return prices.tail(self.sma_period).mean()
    
    def should_rebalance(self, current_date: datetime) -> bool:
        """
        Rebalance weekly on Mondays
        (Crypto markets don't have "first trading day of month")
        """
        if self.last_rebalance_date is None:
            return True
        
        # Check if current date is Monday and different week
        current_week = (current_date.year, current_date.isocalendar()[1])
        last_week = (self.last_rebalance_date.year, 
                    self.last_rebalance_date.isocalendar()[1])
        
        is_monday = current_date.weekday() == 0
        
        return is_monday and current_week != last_week
    
    def check_volatility(self, prices: pd.Series) -> bool:
        """
        Check if recent volatility is too high
        Skip trading if last 24h range > threshold
        
        Returns: True if safe to trade, False if too volatile
        """
        if len(prices) < 2:
            return False
        
        recent_prices = prices.tail(24)  # Last 24 hours
        daily_range = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()
        
        return daily_range < self.volatility_threshold
    
    def check_stop_loss(self, 
                       current_price: float,
                       has_position: bool) -> bool:
        """
        Check if stop loss triggered
        Exit if down 15% from entry
        
        Returns: True if should exit, False otherwise
        """
        if not has_position or self.entry_price is None:
            return False
        
        drawdown = (self.entry_price - current_price) / self.entry_price
        
        return drawdown > self.stop_loss_pct
    
    def generate_signal(self,
                       prices: pd.Series,
                       current_date: datetime,
                       has_position: bool) -> Tuple[str, Optional[float]]:
        """
        Generate BUY/SELL/HOLD signal
        
        Returns:
            signal: 'BUY', 'SELL', or 'HOLD'
            sma: Current SMA value (or None)
        """
        # Check if we have enough data
        if len(prices) < self.sma_period:
            return 'HOLD', None
        
        # Check if it's time to rebalance
        if not self.should_rebalance(current_date):
            return 'HOLD', None
        
        # Check volatility
        if not self.check_volatility(prices):
            return 'HOLD', None
        
        # Calculate indicators
        current_price = prices.iloc[-1]
        sma = self.calculate_sma(prices)
        
        if sma is None:
            return 'HOLD', None
        
        # Check stop loss first (overrides everything)
        if self.check_stop_loss(current_price, has_position):
            return 'SELL', sma
        
        # Generate trend signal
        if current_price > sma and not has_position:
            return 'BUY', sma
        elif current_price <= sma and has_position:
            return 'SELL', sma
        else:
            return 'HOLD', sma
    
    def mark_rebalanced(self, date: datetime):
        """Record rebalance date"""
        self.last_rebalance_date = date
    
    def set_entry_price(self, price: float):
        """Record entry price for stop loss calculation"""
        self.entry_price = price
    
    def clear_entry_price(self):
        """Clear entry price when position closed"""
        self.entry_price = None
Broker Integration
File: execution/broker.py (modifications)
pythonclass CryptoBrokerClient:
    """
    Alpaca crypto trading client
    Modified for crypto-specific endpoints
    """
    
    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import CryptoHistoricalDataClient
        
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )
        
        # Crypto data client (no auth needed for historical data)
        self.data_client = CryptoHistoricalDataClient()
    
    def get_historical_prices(self, 
                            symbol: str,
                            lookback_days: int = 100) -> pd.Series:
        """
        Fetch hourly crypto prices
        
        Note: Using hourly instead of daily for crypto
        Need more granular data for volatility checks
        """
        from alpaca.data.requests import CryptoBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from datetime import datetime, timedelta
        
        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        
        request = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,  # Hourly bars
            start=start,
            end=end
        )
        
        bars = self.data_client.get_crypto_bars(request)
        df = bars.df
        
        # Extract close prices
        if isinstance(df.index, pd.MultiIndex):
            prices = df['close'].xs(symbol, level='symbol')
        else:
            prices = df['close']
        
        return prices
    
    def place_order(self, 
                   symbol: str,
                   side: str,
                   qty: float) -> Order:  # Note: qty is float for crypto
        """
        Place market order for crypto
        
        Crypto allows fractional quantities
        """
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        order_side = OrderSide.BUY if side == 'BUY' else OrderSide.SELL
        
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,  # Float allowed for crypto
            side=order_side,
            time_in_force=TimeInForce.GTC  # Good-til-canceled (crypto is 24/7)
        )
        
        return self.trading_client.submit_order(request)
Main Orchestrator
File: main.py
pythonimport time
from datetime import datetime
import logging
from strategies.crypto_trend import CryptoTrendStrategy
from execution.broker import CryptoBrokerClient
from core.reliability import position_lock, retry_with_backoff
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BTCTrendBot:
    def __init__(self):
        # Load config
        self.symbol = os.getenv('SYMBOL', 'BTC/USD')
        self.allocation = float(os.getenv('ACCOUNT_ALLOCATION', '0.50'))
        sma_period = int(os.getenv('SMA_PERIOD', '50'))
        
        # Initialize components
        self.strategy = CryptoTrendStrategy(sma_period=sma_period)
        self.broker = CryptoBrokerClient(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            paper=os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
        )
        
        logger.info(f"BTC Trend Bot initialized")
        logger.info(f"Symbol: {self.symbol}, SMA: {sma_period}, Allocation: {self.allocation}")
    
    def calculate_target_position(self,
                                 account_value: float,
                                 current_price: float) -> float:
        """
        Calculate target BTC quantity
        
        Returns: float (crypto allows fractional shares)
        """
        target_value = account_value * self.allocation
        target_qty = target_value / current_price
        
        # Round to 6 decimal places (standard for BTC)
        return round(target_qty, 6)
    
    def execute_rebalance(self):
        """Main trading logic"""
        try:
            logger.info("Starting daily check...")
            
            # No market hours check - crypto is 24/7
            
            with position_lock(timeout=30):
                # Fetch account info
                account = self.broker.get_account()
                account_value = float(account.equity)
                logger.info(f"Account equity: ${account_value:,.2f}")
                
                # Check current position
                position = self.broker.get_position(self.symbol)
                current_qty = float(position.qty) if position else 0
                has_position = current_qty > 0
                
                logger.info(f"Current position: {current_qty} BTC")
                
                # Fetch price data (last 100 days of hourly data)
                prices = self.broker.get_historical_prices(self.symbol, lookback_days=100)
                logger.info(f"Retrieved {len(prices)} hours of data")
                
                # Get current price
                current_price = prices.iloc[-1]
                logger.info(f"Current BTC price: ${current_price:,.2f}")
                
                # Generate signal
                signal, sma = self.strategy.generate_signal(
                    prices,
                    datetime.now(),
                    has_position
                )
                
                logger.info(f"Signal: {signal}")
                if sma:
                    logger.info(f"Price ${current_price:,.2f} vs SMA ${sma:,.2f}")
                
                # Execute if not HOLD
                if signal == 'HOLD':
                    logger.info("No action needed")
                    return
                
                # Calculate target position
                target_qty = self.calculate_target_position(account_value, current_price)
                
                if signal == 'BUY':
                    qty_to_buy = target_qty - current_qty
                    if qty_to_buy > 0.001:  # Minimum trade size
                        cost = qty_to_buy * current_price
                        logger.info(f"BUYING {qty_to_buy:.6f} BTC (${cost:,.2f})")
                        
                        order = self.broker.place_order(self.symbol, 'BUY', qty_to_buy)
                        logger.info(f"Order placed: {order.id}")
                        
                        # Record entry price for stop loss
                        self.strategy.set_entry_price(current_price)
                
                elif signal == 'SELL':
                    if current_qty > 0.001:
                        proceeds = current_qty * current_price
                        logger.info(f"SELLING {current_qty:.6f} BTC (${proceeds:,.2f})")
                        
                        order = self.broker.close_position(self.symbol)
                        logger.info(f"Order placed: {order.id}")
                        
                        # Clear entry price
                        self.strategy.clear_entry_price()
                
                # Mark rebalanced
                self.strategy.mark_rebalanced(datetime.now())
                
                logger.info("Daily check complete")
        
        except Exception as e:
            logger.error(f"Error in execution: {e}", exc_info=True)
    
    def run_continuous(self):
        """Run continuously, check daily at 12:00 UTC"""
        logger.info("Starting continuous mode (checks daily at 12:00 UTC)")
        
        while True:
            now = datetime.utcnow()
            
            # Run at 12:00 UTC daily
            if now.hour == 12 and now.minute < 5:
                self.execute_rebalance()
                time.sleep(3600)  # Sleep 1 hour after running
            
            time.sleep(60)  # Check every minute
    
    def run_once(self):
        """Run single execution (for testing)"""
        logger.info("Running single execution...")
        self.execute_rebalance()

if __name__ == "__main__":
    import sys
    
    bot = BTCTrendBot()
    
    if '--once' in sys.argv:
        bot.run_once()
    else:
        bot.run_continuous()
Configuration
File: .env
bash# Alpaca API (Paper Trading)
ALPACA_API_KEY=your_paper_key
ALPACA_SECRET_KEY=your_paper_secret
ALPACA_PAPER=true

# Strategy Parameters
SYMBOL=BTC/USD
SMA_PERIOD=50
ACCOUNT_ALLOCATION=0.50  # Only 50% in BTC (conservative)
STOP_LOSS_PCT=0.15       # Exit if down 15%
VOLATILITY_THRESHOLD=0.10 # Skip trading if 24h range >10%

# Logging
LOG_LEVEL=INFO

Testing
File: tests/test_crypto_strategy.py
pythonimport pytest
import pandas as pd
from datetime import datetime, timedelta
from strategies.crypto_trend import CryptoTrendStrategy

def test_buy_signal_above_sma():
    """Price above 50-day SMA should generate BUY"""
    strategy = CryptoTrendStrategy(sma_period=50)
    
    # Create uptrend
    prices = pd.Series(range(1, 101))
    
    signal, sma = strategy.generate_signal(prices, datetime.now(), has_position=False)
    assert signal == 'BUY'

def test_volatility_filter():
    """High volatility should prevent trading"""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)
    
    # Create volatile prices (20% range in 24 hours)
    prices = pd.Series([100] * 24 + [120] * 24 + [100] * 24)
    
    is_safe = strategy.check_volatility(prices)
    assert is_safe == False  # Too volatile

def test_stop_loss_triggers():
    """15% drawdown should trigger stop loss"""
    strategy = CryptoTrendStrategy(stop_loss_pct=0.15)
    strategy.set_entry_price(100.0)
    
    should_exit = strategy.check_stop_loss(
        current_price=84.0,  # Down 16%
        has_position=True
    )
    assert should_exit == True

def test_weekly_rebalancing():
    """Should only rebalance on Mondays"""
    strategy = CryptoTrendStrategy()
    
    # First Monday
    monday1 = datetime(2025, 10, 6)  # Monday
    assert strategy.should_rebalance(monday1) == True
    strategy.mark_rebalanced(monday1)
    
    # Same week Tuesday - should not rebalance
    tuesday = datetime(2025, 10, 7)
    assert strategy.should_rebalance(tuesday) == False
    
    # Next Monday - should rebalance
    monday2 = datetime(2025, 10, 13)
    assert strategy.should_rebalance(monday2) == True

Expected Behavior
Realistic expectations for BTC trend-following:
MetricValueAnnual Return-20% to +80% (high variance)Sharpe Ratio0.4-0.8 (worse than SPY)Max Drawdown30-50%Trades per Year15-30 (weekly checks)Win Rate40-50%
This will likely underperform SPY buy-and-hold over long periods. The value is:

Learning crypto market dynamics
Testing your infrastructure on 24/7 markets
Understanding volatility management
Fun side project


Deployment

Verify Alpaca crypto support:

bash   # Check if BTC/USD available in paper

Setup:

bash   cp -r trend-bot btc-trend-bot
   cd btc-trend-bot
   # Replace strategy files
   cp .env.template .env
   # Edit with crypto params

Test:

bash   python main.py --once

Deploy (if Alpaca supports):

bash   # Run as separate service from SPY bot
This gives you a crypto bot to experiment with while your SPY bot does the actual wealth-building. Treat this as education, not investment.RetryClaude can make mistakes. Please double-check responses. Sonnet 4.5
