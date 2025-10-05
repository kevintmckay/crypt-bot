#!/usr/bin/env python3
"""
Unit tests for TrendFollowingStrategy
"""

import pytest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies.trend_following import TrendFollowingStrategy


def test_buy_signal_above_sma():
    """Price above SMA should generate BUY signal."""
    strategy = TrendFollowingStrategy(sma_period=200)

    # Create uptrend: prices 1-250
    prices = pd.Series(range(1, 251))

    signal, sma = strategy.generate_signal(prices, datetime.now())

    assert signal == 'BUY', f"Expected BUY, got {signal}"
    assert sma is not None, "SMA should not be None"
    assert sma > 0, "SMA should be positive"


def test_sell_signal_below_sma():
    """Price below SMA should generate SELL signal."""
    strategy = TrendFollowingStrategy(sma_period=200)

    # Create downtrend: prices 250-1
    prices = pd.Series(range(250, 0, -1))

    signal, sma = strategy.generate_signal(prices, datetime.now())

    assert signal == 'SELL', f"Expected SELL, got {signal}"
    assert sma is not None, "SMA should not be None"


def test_insufficient_data():
    """Not enough data should return HOLD."""
    strategy = TrendFollowingStrategy(sma_period=200)

    # Only 100 prices
    prices = pd.Series(range(1, 101))

    signal, sma = strategy.generate_signal(prices, datetime.now())

    assert signal == 'HOLD', f"Expected HOLD, got {signal}"
    assert sma is None, "SMA should be None with insufficient data"


def test_monthly_rebalancing():
    """Should only rebalance once per month."""
    strategy = TrendFollowingStrategy(sma_period=200)

    prices = pd.Series(range(1, 251))

    # First call in January
    jan_1 = datetime(2025, 1, 1)
    signal1, _ = strategy.generate_signal(prices, jan_1)
    assert signal1 == 'BUY', "First signal should be BUY"
    strategy.mark_rebalanced(jan_1)

    # Second call same month - should be HOLD
    jan_15 = datetime(2025, 1, 15)
    signal2, _ = strategy.generate_signal(prices, jan_15)
    assert signal2 == 'HOLD', "Same month should return HOLD"

    # Call in February - should signal again
    feb_1 = datetime(2025, 2, 1)
    signal3, _ = strategy.generate_signal(prices, feb_1)
    assert signal3 == 'BUY', "New month should return BUY"


def test_sma_calculation():
    """Test SMA calculation accuracy."""
    strategy = TrendFollowingStrategy(sma_period=10)

    # Create known prices
    prices = pd.Series([10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30])

    sma = strategy.calculate_sma(prices)

    # Last 10 values: 12-30, mean = 21
    expected_sma = sum(range(12, 31, 2)) / 10
    assert abs(sma - expected_sma) < 0.01, f"Expected {expected_sma}, got {sma}"


def test_should_rebalance_logic():
    """Test rebalance timing logic."""
    strategy = TrendFollowingStrategy(sma_period=200)

    # First call - should rebalance
    assert strategy.should_rebalance(datetime(2025, 1, 1)) == True

    # Mark rebalanced
    strategy.mark_rebalanced(datetime(2025, 1, 1))

    # Same month - should not rebalance
    assert strategy.should_rebalance(datetime(2025, 1, 15)) == False

    # Different month - should rebalance
    assert strategy.should_rebalance(datetime(2025, 2, 1)) == True


def test_edge_case_exact_sma():
    """Test behavior when price exactly equals SMA."""
    strategy = TrendFollowingStrategy(sma_period=5)

    # Create prices where last price equals SMA
    # SMA of [10, 10, 10, 10, 10] = 10
    prices = pd.Series([10, 10, 10, 10, 10])

    signal, sma = strategy.generate_signal(prices, datetime.now())

    # Price = SMA, so should SELL (not greater than)
    assert signal == 'SELL', f"Expected SELL when price = SMA, got {signal}"
    assert abs(sma - 10.0) < 0.01, f"Expected SMA=10, got {sma}"


def test_real_world_scenario():
    """Test with realistic stock price data."""
    strategy = TrendFollowingStrategy(sma_period=50)

    # Simulate price going from bearish to bullish
    # Start at 100, decline to 80, then rally to 120
    downtrend = list(range(100, 80, -1))
    uptrend = list(range(80, 121))
    prices = pd.Series(downtrend + uptrend)

    # At the end, price (120) should be above 50-day SMA
    signal, sma = strategy.generate_signal(prices, datetime.now())

    assert signal == 'BUY', f"Expected BUY in uptrend, got {signal}"
    assert sma < 120, f"SMA should be below current price of 120"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
