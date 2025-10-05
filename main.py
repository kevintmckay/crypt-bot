#!/usr/bin/env python3
"""
BTC/USD Trend Following Trading Bot
Runs weekly rebalancing of BTC/USD based on 50-day SMA
Adapted for 24/7 crypto markets
"""

import os
import sys
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

from core.reliability import position_lock
from strategies.crypto_trend import CryptoTrendStrategy
from execution.broker import CryptoBrokerClient

# Load environment variables
load_dotenv()

# Setup logging
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BTCTrendBot:
    """Main bot orchestrator for BTC trend-following strategy."""

    def __init__(self):
        """Initialize bot with configuration from environment."""
        # Configuration
        self.symbol = os.getenv('SYMBOL', 'BTC/USD')
        self.account_allocation = float(os.getenv('ACCOUNT_ALLOCATION', '0.50'))
        self.sma_period = int(os.getenv('SMA_PERIOD', '50'))
        self.stop_loss_pct = float(os.getenv('STOP_LOSS_PCT', '0.15'))
        self.volatility_threshold = float(os.getenv('VOLATILITY_THRESHOLD', '0.10'))

        # Validate configuration
        if not (0.0 < self.account_allocation <= 1.0):
            raise ValueError(f"ACCOUNT_ALLOCATION must be between 0 and 1, got {self.account_allocation}")

        # Initialize components
        self.strategy = CryptoTrendStrategy(
            sma_period=self.sma_period,
            stop_loss_pct=self.stop_loss_pct,
            volatility_threshold=self.volatility_threshold
        )

        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'

        if not api_key or not secret_key:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")

        self.broker = CryptoBrokerClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        logger.info("=" * 70)
        logger.info("BTC Trend Following Bot Initialized")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"SMA Period: {self.sma_period} days")
        logger.info(f"Account Allocation: {self.account_allocation:.1%}")
        logger.info(f"Stop Loss: {self.stop_loss_pct:.1%}")
        logger.info(f"Volatility Threshold: {self.volatility_threshold:.1%}")
        logger.info(f"Paper Trading: {paper}")
        logger.info("=" * 70)

    def calculate_target_position(self,
                                 account_value: float,
                                 current_price: float) -> float:
        """
        Calculate target BTC quantity

        Returns: float (crypto allows fractional shares)

        Args:
            account_value: Total account value
            current_price: Current price of BTC

        Returns:
            Quantity of BTC to hold (rounded to 6 decimals)
        """
        target_dollars = account_value * self.account_allocation
        target_qty = target_dollars / current_price

        # Round to 6 decimal places (standard for BTC)
        return round(target_qty, 6)

    def execute_rebalance(self):
        """
        Main rebalancing logic.

        1. Get current position
        2. Generate signal
        3. Execute trades if needed

        Note: No market hours check - crypto is 24/7
        """
        logger.info("Starting rebalance check...")

        # Acquire lock to prevent race conditions
        with position_lock(timeout=30):
            # Get account info
            account = self.broker.get_account()
            account_value = float(account.equity)
            buying_power = float(account.buying_power)

            logger.info(f"Account equity: ${account_value:,.2f}")
            logger.info(f"Buying power: ${buying_power:,.2f}")

            # Get current position
            position = self.broker.get_position(self.symbol)
            current_qty = float(position.qty) if position else 0.0
            current_price = float(position.current_price) if position else None
            has_position = current_qty > 0

            logger.info(f"Current position: {current_qty:.6f} BTC")

            # Get historical prices (last 100 days of hourly data)
            prices = self.broker.get_historical_prices(
                self.symbol,
                lookback_days=100
            )

            if current_price is None:
                current_price = float(prices.iloc[-1])

            logger.info(f"Current BTC price: ${current_price:,.2f}")

            # Generate signal
            signal, sma_value = self.strategy.generate_signal(
                prices,
                datetime.now(),
                has_position
            )

            logger.info(f"Signal: {signal}")
            if sma_value:
                logger.info(f"{self.sma_period}-day SMA: ${sma_value:.2f}")
                pct_diff = ((current_price - sma_value) / sma_value) * 100
                logger.info(f"Price vs SMA: {pct_diff:+.2f}%")

            if signal == 'HOLD':
                logger.info("No rebalancing needed")
                return

            # Calculate target position
            if signal == 'BUY':
                target_qty = self.calculate_target_position(
                    account_value,
                    current_price
                )
                logger.info(f"Target position: {target_qty} shares (${target_qty * current_price:,.2f})")
            else:  # SELL
                target_qty = 0
                logger.info("Target position: 0 shares (liquidate)")

            # Execute trades
            delta = target_qty - current_qty

            if abs(delta) < 0.001:  # Minimum trade size for BTC
                logger.info("Already at target position - no trades needed")
            elif delta > 0:
                qty_to_buy = delta
                cost = qty_to_buy * current_price
                logger.info(f"BUYING {qty_to_buy:.6f} BTC (${cost:,.2f})")
                order = self.broker.place_order(self.symbol, 'BUY', qty_to_buy)
                logger.info(f"Buy order placed: {order.id}")

                # Record entry price for stop loss
                self.strategy.set_entry_price(current_price)

            else:  # delta < 0
                qty_to_sell = abs(delta)
                proceeds = qty_to_sell * current_price
                logger.info(f"SELLING {qty_to_sell:.6f} BTC (${proceeds:,.2f})")

                if qty_to_sell >= current_qty * 0.99:  # Close if selling >99%
                    # Close entire position
                    order = self.broker.close_position(self.symbol)
                    logger.info("Position closed completely")
                else:
                    order = self.broker.place_order(
                        self.symbol,
                        'SELL',
                        qty_to_sell
                    )
                    logger.info(f"Sell order placed: {order.id}")

                # Clear entry price
                self.strategy.clear_entry_price()

            # Mark rebalanced
            self.strategy.mark_rebalanced(datetime.now())
            logger.info("Rebalance complete")

    def run_continuous(self):
        """Run bot continuously, check daily at 12:00 PST"""
        logger.info("Starting continuous operation")
        logger.info("Daily check at 12:00 PST")

        while True:
            try:
                # Get current time in PST
                from datetime import timezone, timedelta
                pst = timezone(timedelta(hours=-8))
                now = datetime.now(pst)

                logger.info("=" * 70)
                logger.info(f"Daily Check - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logger.info("=" * 70)

                # Run at 12:00 PST daily
                if now.hour == 12 and now.minute < 5:
                    self.execute_rebalance()
                    logger.info("Daily check complete")
                    logger.info("Sleeping for 1 hour...")
                    time.sleep(3600)  # Sleep 1 hour after running
                else:
                    logger.debug(f"Not 12:00 PST yet (current: {now.hour:02d}:{now.minute:02d})")

            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
                logger.info("Waiting 1 hour before retry...")
                time.sleep(3600)  # Wait 1 hour on error
                continue

            # Check every minute
            time.sleep(60)

    def run_once(self):
        """Run a single rebalance check (for testing)."""
        logger.info("Running single rebalance check")
        try:
            self.execute_rebalance()
            logger.info("Single run complete")
        except Exception as e:
            logger.error(f"Error during execution: {e}", exc_info=True)
            raise


def main():
    """Main entry point."""
    # Check for run-once mode
    run_once = '--once' in sys.argv

    try:
        bot = BTCTrendBot()

        if run_once:
            bot.run_once()
        else:
            bot.run_continuous()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
