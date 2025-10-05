#!/usr/bin/env python3
"""
Crypto Trend Following Strategy

Adapted for crypto markets with:
- 50-day SMA (vs 200 for stocks)
- Weekly rebalancing on Mondays (vs monthly)
- 15% stop loss protection
- Volatility filter (skip trading if 24h range >10%)
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


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
        """
        Initialize crypto strategy.

        Args:
            sma_period: Number of days for SMA calculation (default: 50)
            stop_loss_pct: Stop loss percentage from entry (default: 0.15 = 15%)
            volatility_threshold: Max 24h volatility to allow trading (default: 0.10 = 10%)
        """
        self.sma_period = sma_period
        self.stop_loss_pct = stop_loss_pct
        self.volatility_threshold = volatility_threshold
        self.last_rebalance_date = None
        self.entry_price = None

        logger.info(f"CryptoTrendStrategy initialized:")
        logger.info(f"  SMA Period: {sma_period} days")
        logger.info(f"  Stop Loss: {stop_loss_pct:.1%}")
        logger.info(f"  Volatility Threshold: {volatility_threshold:.1%}")

    def calculate_sma(self, prices: pd.Series) -> Optional[float]:
        """
        Calculate simple moving average.

        Args:
            prices: Series of historical prices (hourly)

        Returns:
            SMA value, or None if insufficient data
        """
        # Convert hourly prices to daily (need sma_period days worth of data)
        # For 50-day SMA, we need at least 50*24 = 1200 hourly bars
        min_hours = self.sma_period * 24

        if len(prices) < min_hours:
            logger.warning(f"Insufficient data for SMA: {len(prices)} hours < {min_hours}")
            return None

        # Use last sma_period*24 hours and calculate mean
        sma = prices.tail(min_hours).mean()
        return float(sma)

    def should_rebalance(self, current_date: datetime) -> bool:
        """
        Rebalance weekly on Mondays
        (Crypto markets don't have "first trading day of month")

        Args:
            current_date: Current date/time

        Returns:
            True if should rebalance, False otherwise
        """
        if self.last_rebalance_date is None:
            logger.info("First rebalance - no previous date")
            return True

        # Check if current date is Monday and different week
        current_week = (current_date.year, current_date.isocalendar()[1])
        last_week = (self.last_rebalance_date.year,
                    self.last_rebalance_date.isocalendar()[1])

        is_monday = current_date.weekday() == 0

        should_rebal = is_monday and current_week != last_week

        if should_rebal:
            logger.info(f"Week changed from {last_week} to {current_week} (Monday) - rebalancing")
        else:
            logger.debug(f"Not Monday or same week - no rebalance needed")

        return should_rebal

    def check_volatility(self, prices: pd.Series) -> bool:
        """
        Check if recent volatility is too high
        Skip trading if last 24h range > threshold

        Args:
            prices: Series of hourly prices

        Returns:
            True if safe to trade, False if too volatile
        """
        if len(prices) < 24:
            logger.warning("Insufficient data for volatility check")
            return False

        recent_prices = prices.tail(24)  # Last 24 hours
        daily_range = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()

        is_safe = daily_range < self.volatility_threshold

        if not is_safe:
            logger.warning(f"Volatility too high: {daily_range:.2%} > {self.volatility_threshold:.2%}")
        else:
            logger.debug(f"Volatility OK: {daily_range:.2%}")

        return is_safe

    def check_stop_loss(self,
                       current_price: float,
                       has_position: bool) -> bool:
        """
        Check if stop loss triggered
        Exit if down 15% from entry

        Args:
            current_price: Current BTC price
            has_position: Whether we currently hold BTC

        Returns:
            True if should exit, False otherwise
        """
        if not has_position or self.entry_price is None:
            return False

        drawdown = (self.entry_price - current_price) / self.entry_price

        if drawdown > self.stop_loss_pct:
            logger.warning(f"STOP LOSS TRIGGERED: {drawdown:.2%} drawdown from ${self.entry_price:,.2f}")
            return True

        return False

    def generate_signal(self,
                       prices: pd.Series,
                       current_date: datetime,
                       has_position: bool) -> Tuple[str, Optional[float]]:
        """
        Generate BUY/SELL/HOLD signal

        Args:
            prices: Series of hourly prices
            current_date: Current date/time
            has_position: Whether we currently hold BTC

        Returns:
            Tuple of (signal, sma_value) where:
            - signal is 'BUY', 'SELL', or 'HOLD'
            - sma_value is the calculated SMA or None
        """
        # Check if we have enough data
        min_hours = self.sma_period * 24
        if len(prices) < min_hours:
            logger.warning(f"Not enough price data: {len(prices)} hours < {min_hours}")
            return ('HOLD', None)

        # Check if it's time to rebalance
        if not self.should_rebalance(current_date):
            return ('HOLD', None)

        # Check volatility
        if not self.check_volatility(prices):
            logger.info("Skipping trade due to high volatility")
            return ('HOLD', None)

        # Calculate indicators
        current_price = prices.iloc[-1]
        sma = self.calculate_sma(prices)

        if sma is None:
            return ('HOLD', None)

        # Check stop loss first (overrides everything)
        if self.check_stop_loss(current_price, has_position):
            logger.info("Stop loss triggered - forcing SELL")
            return ('SELL', sma)

        # Generate trend signal
        if current_price > sma and not has_position:
            logger.info(f"BUY signal: price ${current_price:,.2f} > SMA ${sma:,.2f}")
            return ('BUY', sma)
        elif current_price <= sma and has_position:
            logger.info(f"SELL signal: price ${current_price:,.2f} <= SMA ${sma:,.2f}")
            return ('SELL', sma)
        else:
            return ('HOLD', sma)

    def mark_rebalanced(self, date: datetime):
        """
        Record that we rebalanced on this date.

        Args:
            date: Date of rebalance
        """
        self.last_rebalance_date = date
        logger.info(f"Rebalance marked for {date.strftime('%Y-%m-%d')}")

    def set_entry_price(self, price: float):
        """
        Record entry price for stop loss calculation.

        Args:
            price: Entry price for position
        """
        self.entry_price = price
        logger.info(f"Entry price set: ${price:,.2f}")

    def clear_entry_price(self):
        """Clear entry price when position closed."""
        self.entry_price = None
        logger.info("Entry price cleared")
