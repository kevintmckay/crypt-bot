#!/usr/bin/env python3
"""
200-Day SMA Trend Following Strategy

Logic:
- BUY if price > 200-day SMA
- SELL if price < 200-day SMA
- Rebalance monthly (first trading day of month)
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class TrendFollowingStrategy:
    """Simple trend-following strategy based on 200-day SMA."""

    def __init__(self, sma_period: int = 200):
        """
        Initialize strategy.

        Args:
            sma_period: Number of days for SMA calculation (default: 200)
        """
        self.sma_period = sma_period
        self.last_rebalance_date = None
        logger.info(f"TrendFollowingStrategy initialized with {sma_period}-day SMA")

    def calculate_sma(self, prices: pd.Series) -> Optional[float]:
        """
        Calculate simple moving average.

        Args:
            prices: Series of historical closing prices

        Returns:
            SMA value, or None if insufficient data
        """
        if len(prices) < self.sma_period:
            logger.warning(f"Insufficient data for SMA: {len(prices)} < {self.sma_period}")
            return None

        sma = prices.tail(self.sma_period).mean()
        return float(sma)

    def should_rebalance(self, current_date: datetime) -> bool:
        """
        Determine if rebalancing should occur.

        Rebalance on first trading day of each month.

        Args:
            current_date: Current date/time

        Returns:
            True if should rebalance, False otherwise
        """
        if self.last_rebalance_date is None:
            logger.info("First rebalance - no previous date")
            return True

        current_month = (current_date.year, current_date.month)
        last_month = (self.last_rebalance_date.year, self.last_rebalance_date.month)

        should_rebal = current_month != last_month

        if should_rebal:
            logger.info(f"Month changed from {last_month} to {current_month} - rebalancing")
        else:
            logger.debug(f"Same month {current_month} - no rebalance needed")

        return should_rebal

    def generate_signal(self,
                       prices: pd.Series,
                       current_date: datetime) -> Tuple[str, Optional[float]]:
        """
        Generate trading signal.

        Args:
            prices: Series of historical closing prices
            current_date: Current date/time

        Returns:
            Tuple of (signal, sma_value) where:
            - signal is 'BUY', 'SELL', or 'HOLD'
            - sma_value is the calculated SMA or None
        """
        # Need enough data for SMA
        if len(prices) < self.sma_period:
            logger.warning(f"Not enough price data: {len(prices)} < {self.sma_period}")
            return ('HOLD', None)

        # Only rebalance monthly
        if not self.should_rebalance(current_date):
            return ('HOLD', None)

        current_price = float(prices.iloc[-1])
        sma_value = self.calculate_sma(prices)

        if sma_value is None:
            logger.warning("SMA calculation returned None")
            return ('HOLD', None)

        # Simple trend following rule
        if current_price > sma_value:
            signal = 'BUY'
            logger.info(f"BUY signal: price ${current_price:.2f} > SMA ${sma_value:.2f}")
        else:
            signal = 'SELL'
            logger.info(f"SELL signal: price ${current_price:.2f} <= SMA ${sma_value:.2f}")

        return (signal, sma_value)

    def mark_rebalanced(self, date: datetime):
        """
        Record that we rebalanced on this date.

        Args:
            date: Date of rebalance
        """
        self.last_rebalance_date = date
        logger.info(f"Rebalance marked for {date.strftime('%Y-%m-%d')}")
