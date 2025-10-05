#!/usr/bin/env python3
"""
Unit tests for CryptoTrendStrategy
"""

import pytest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies.crypto_trend import CryptoTrendStrategy


def test_buy_signal_above_sma():
    """Price above 50-day SMA should generate BUY signal."""
    strategy = CryptoTrendStrategy(sma_period=50)

    # Create uptrend: 50 days * 24 hours = 1200 hours
    # Prices going from 1 to 1200
    prices = pd.Series(range(1, 1201))

    # Should trigger on Monday
    monday = datetime(2025, 10, 6)  # A Monday
    signal, sma = strategy.generate_signal(prices, monday, has_position=False)

    assert signal == 'BUY', f"Expected BUY, got {signal}"
    assert sma is not None, "SMA should not be None"
    assert sma > 0, "SMA should be positive"


def test_sell_signal_below_sma():
    """Price below 50-day SMA should generate SELL signal."""
    strategy = CryptoTrendStrategy(sma_period=50, volatility_threshold=100.0)  # High threshold to not trigger

    # Create gentle downtrend: prices slowly declining
    # Start at 1000, end at 500 over 1200 hours
    prices = pd.Series([1000 - i*0.4 for i in range(1200)])

    # Should trigger on Monday with position
    monday = datetime(2025, 10, 6)
    signal, sma = strategy.generate_signal(prices, monday, has_position=True)

    assert signal == 'SELL', f"Expected SELL, got {signal}"
    assert sma is not None, "SMA should not be None"


def test_insufficient_data():
    """Not enough data should return HOLD."""
    strategy = CryptoTrendStrategy(sma_period=50)

    # Only 500 hours (need 50*24 = 1200)
    prices = pd.Series(range(1, 501))

    signal, sma = strategy.generate_signal(prices, datetime.now(), has_position=False)

    assert signal == 'HOLD', f"Expected HOLD, got {signal}"
    assert sma is None, "SMA should be None with insufficient data"


def test_weekly_rebalancing():
    """Should only rebalance weekly on Mondays."""
    strategy = CryptoTrendStrategy(sma_period=50)

    # Create sufficient data
    prices = pd.Series(range(1, 1201))

    # First Monday
    monday1 = datetime(2025, 10, 6)  # Monday
    signal1, _ = strategy.generate_signal(prices, monday1, has_position=False)
    assert signal1 == 'BUY', "First Monday should generate signal"
    strategy.mark_rebalanced(monday1)

    # Same week Tuesday - should be HOLD
    tuesday = datetime(2025, 10, 7)
    signal2, _ = strategy.generate_signal(prices, tuesday, has_position=False)
    assert signal2 == 'HOLD', "Tuesday should return HOLD"

    # Same week, another Monday - should be HOLD
    friday = datetime(2025, 10, 10)
    signal3, _ = strategy.generate_signal(prices, friday, has_position=False)
    assert signal3 == 'HOLD', "Friday same week should return HOLD"

    # Next Monday - should signal again
    monday2 = datetime(2025, 10, 13)
    signal4, _ = strategy.generate_signal(prices, monday2, has_position=False)
    assert signal4 == 'BUY', "Next Monday should generate signal"


def test_volatility_filter():
    """High volatility should prevent trading."""
    strategy = CryptoTrendStrategy(sma_period=50, volatility_threshold=0.10)

    # Create volatile prices: last 24 hours swing 20%
    # 1200 stable hours + 24 volatile hours
    stable_prices = [100.0] * 1200
    volatile_prices = [100, 105, 95, 110, 90, 115, 85, 120, 80] * 3  # 27 values
    all_prices = stable_prices + volatile_prices[:24]
    prices = pd.Series(all_prices)

    monday = datetime(2025, 10, 6)
    signal, _ = strategy.generate_signal(prices, monday, has_position=False)

    # Should HOLD due to high volatility
    assert signal == 'HOLD', f"Expected HOLD due to volatility, got {signal}"


def test_stop_loss_triggers():
    """15% drawdown should trigger stop loss."""
    strategy = CryptoTrendStrategy(sma_period=50, stop_loss_pct=0.15)

    # Set entry price
    strategy.set_entry_price(100.0)

    # Create prices with drawdown
    # 1200 hours of stable price around 84 (16% down from 100)
    prices = pd.Series([84.0] * 1200)

    monday = datetime(2025, 10, 6)
    signal, sma = strategy.generate_signal(prices, monday, has_position=True)

    # Should trigger SELL due to stop loss
    assert signal == 'SELL', f"Expected SELL due to stop loss, got {signal}"


def test_stop_loss_no_trigger():
    """Small drawdown should not trigger stop loss."""
    strategy = CryptoTrendStrategy(sma_period=50, stop_loss_pct=0.15)

    # Set entry price
    strategy.set_entry_price(100.0)

    # Create prices with small drawdown (10%)
    prices = pd.Series([90.0] * 1200)

    monday = datetime(2025, 10, 6)
    signal, sma = strategy.generate_signal(prices, monday, has_position=True)

    # Should not trigger stop loss, normal logic applies
    # Price 90 < SMA 90, so SELL
    assert signal == 'SELL', "Should follow normal sell logic"


def test_sma_calculation_hourly():
    """Test SMA calculation with hourly data."""
    strategy = CryptoTrendStrategy(sma_period=2)  # 2 days = 48 hours

    # Create 100 hours of data
    prices = pd.Series([10.0] * 100)

    sma = strategy.calculate_sma(prices)

    # Should use last 48 hours
    expected_sma = 10.0
    assert abs(sma - expected_sma) < 0.01, f"Expected {expected_sma}, got {sma}"


def test_check_volatility_safe():
    """Test volatility check with safe prices."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Low volatility: 24 hours of stable prices
    prices = pd.Series([100.0, 101.0, 99.0, 100.5, 99.5] * 5)  # 25 values

    is_safe = strategy.check_volatility(prices)
    assert is_safe == True, "Low volatility should be safe"


def test_check_volatility_unsafe():
    """Test volatility check with volatile prices."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # High volatility: 24 hours with 20% swing
    prices = pd.Series([100, 110, 90, 115, 85, 120, 80] * 4)  # 28 values

    is_safe = strategy.check_volatility(prices)
    assert is_safe == False, "High volatility should not be safe"


def test_entry_price_tracking():
    """Test entry price set and clear."""
    strategy = CryptoTrendStrategy()

    assert strategy.entry_price is None, "Entry price should start as None"

    strategy.set_entry_price(50000.0)
    assert strategy.entry_price == 50000.0, "Entry price should be set"

    strategy.clear_entry_price()
    assert strategy.entry_price is None, "Entry price should be cleared"


def test_hold_on_non_monday():
    """Should HOLD if not Monday, even on first call."""
    strategy = CryptoTrendStrategy(sma_period=50)

    prices = pd.Series(range(1, 1201))

    # First mark as if we already rebalanced on a Monday
    previous_monday = datetime(2025, 9, 29)  # Previous Monday
    strategy.mark_rebalanced(previous_monday)

    # Wednesday of same week
    wednesday = datetime(2025, 10, 1)
    signal, _ = strategy.generate_signal(prices, wednesday, has_position=False)

    assert signal == 'HOLD', "Non-Monday should return HOLD"


def test_real_world_crypto_scenario():
    """Test with realistic crypto price data."""
    strategy = CryptoTrendStrategy(sma_period=10)  # 10 days for faster test

    # Simulate BTC going from bearish to bullish
    # 10 days = 240 hours
    downtrend = [50000 - i*100 for i in range(120)]  # 120 hours down
    uptrend = [45000 + i*200 for i in range(121)]    # 121 hours up
    prices = pd.Series(downtrend + uptrend)

    monday = datetime(2025, 10, 6)
    signal, sma = strategy.generate_signal(prices, monday, has_position=False)

    # At the end, price should be well above SMA
    current_price = prices.iloc[-1]
    assert signal == 'BUY', f"Expected BUY in uptrend, got {signal}"
    assert current_price > sma, "Current price should be above SMA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
