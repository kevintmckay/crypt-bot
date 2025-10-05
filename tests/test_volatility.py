#!/usr/bin/env python3
"""
Unit tests for crypto volatility handling
Tests the volatility filter and edge cases
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies.crypto_trend import CryptoTrendStrategy


def test_extreme_volatility_flash_crash():
    """Test handling of flash crash scenario."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Simulate flash crash: stable then sudden 30% drop
    stable = [50000.0] * 20
    crash = [50000, 45000, 40000, 35000]  # 30% crash in 4 hours
    prices = pd.Series(stable + crash)

    is_safe = strategy.check_volatility(prices)
    assert is_safe == False, "Flash crash should trigger volatility filter"


def test_gradual_decline_acceptable():
    """Test that gradual decline doesn't trigger volatility filter."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Gradual 5% decline over 24 hours
    prices = pd.Series([50000 - i*100 for i in range(24)])

    is_safe = strategy.check_volatility(prices)
    assert is_safe == True, "Gradual 5% decline should be acceptable"


def test_volatility_calculation_accuracy():
    """Test accuracy of volatility calculation."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.08)  # Lower threshold

    # Create known volatility scenario
    # Mean = 100, range = 10 (95 to 105), volatility = 10/100 = 10%
    prices = pd.Series([95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105] * 3)

    is_safe = strategy.check_volatility(prices.tail(24))

    # Volatility is ~10%, threshold is 8%, so should be False
    # Range: 105 - 95 = 10, Mean = 100, Ratio = 10/100 = 0.10
    # Since 0.10 is NOT < 0.08, should return False
    assert is_safe == False, "Volatility above threshold should not be safe"


def test_low_volatility_sideways_market():
    """Test low volatility in sideways market."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Tight range: 49900 to 50100 (0.4% range)
    prices = pd.Series([50000 + (i % 3 - 1) * 100 for i in range(24)])

    is_safe = strategy.check_volatility(prices)
    assert is_safe == True, "Low volatility sideways market should be safe"


def test_volatility_with_pump_and_dump():
    """Test pump and dump scenario."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Pump and dump: +20% then -20%
    prices = pd.Series([50000] * 8 + [60000] * 8 + [48000] * 8)

    is_safe = strategy.check_volatility(prices)
    assert is_safe == False, "Pump and dump should trigger filter"


def test_insufficient_data_for_volatility():
    """Test volatility check with insufficient data."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Only 10 hours of data
    prices = pd.Series([50000] * 10)

    is_safe = strategy.check_volatility(prices)
    assert is_safe == False, "Insufficient data should return False (unsafe)"


def test_different_volatility_thresholds():
    """Test different volatility thresholds."""
    # Same price data, different thresholds
    prices = pd.Series([100, 105, 95, 104, 96] * 5)  # ~10% range

    # Strict threshold (5%)
    strict_strategy = CryptoTrendStrategy(volatility_threshold=0.05)
    assert strict_strategy.check_volatility(prices) == False

    # Loose threshold (15%)
    loose_strategy = CryptoTrendStrategy(volatility_threshold=0.15)
    assert loose_strategy.check_volatility(prices) == True


def test_volatility_with_gaps():
    """Test volatility with price gaps (like after halts)."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.08)

    # Gap up scenario: stable at 50k, gap to 56k (12% gap)
    before_gap = [50000] * 12
    after_gap = [56000] * 12
    prices = pd.Series(before_gap + after_gap)

    is_safe = strategy.check_volatility(prices)
    # 12% gap should trigger filter with 8% threshold
    assert is_safe == False, "12% gap should trigger volatility filter"


def test_volatility_edge_case_single_spike():
    """Test single spike in otherwise stable market."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Stable with one spike
    prices_list = [50000] * 24
    prices_list[12] = 56000  # Single 12% spike
    prices = pd.Series(prices_list)

    is_safe = strategy.check_volatility(prices)
    assert is_safe == False, "Single large spike should trigger filter"


def test_volatility_with_realistic_btc_data():
    """Test with realistic BTC price movement."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Realistic BTC hourly data: small random walks
    np.random.seed(42)
    base_price = 50000
    changes = np.random.normal(0, 200, 24)  # ~0.4% std dev
    prices = pd.Series([base_price + sum(changes[:i+1]) for i in range(24)])

    is_safe = strategy.check_volatility(prices)
    # Normal market movement should be safe
    assert is_safe == True, "Normal BTC movement should be safe"


def test_volatility_zero_range():
    """Test volatility with zero price movement."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # All prices identical
    prices = pd.Series([50000.0] * 24)

    is_safe = strategy.check_volatility(prices)
    assert is_safe == True, "Zero volatility should be safe"


def test_stop_loss_boundary_cases():
    """Test stop loss at exact boundary."""
    strategy = CryptoTrendStrategy(stop_loss_pct=0.15)

    # Entry at 100
    strategy.set_entry_price(100.0)

    # Exactly 15% down (boundary)
    should_trigger_exact = strategy.check_stop_loss(85.0, has_position=True)
    assert should_trigger_exact == False, "Exactly 15% down should not trigger (need >15%)"

    # Just over 15% down
    should_trigger_over = strategy.check_stop_loss(84.99, has_position=True)
    assert should_trigger_over == True, "Over 15% down should trigger"

    # Under 15% down
    should_not_trigger = strategy.check_stop_loss(85.01, has_position=True)
    assert should_not_trigger == False, "Under 15% down should not trigger"


def test_stop_loss_without_position():
    """Test stop loss when no position held."""
    strategy = CryptoTrendStrategy(stop_loss_pct=0.15)

    strategy.set_entry_price(100.0)

    # No position, even with large drawdown
    should_trigger = strategy.check_stop_loss(50.0, has_position=False)
    assert should_trigger == False, "Stop loss should not trigger without position"


def test_stop_loss_without_entry_price():
    """Test stop loss when entry price not set."""
    strategy = CryptoTrendStrategy(stop_loss_pct=0.15)

    # No entry price set
    should_trigger = strategy.check_stop_loss(50.0, has_position=True)
    assert should_trigger == False, "Stop loss should not trigger without entry price"


def test_multiple_volatility_measurements():
    """Test volatility calculated correctly over different windows."""
    strategy = CryptoTrendStrategy(volatility_threshold=0.10)

    # Window 1: High volatility in recent 24 hours
    old_stable = [50000] * 100
    recent_volatile = [50000, 45000, 55000] * 8  # Last 24 hours
    prices1 = pd.Series(old_stable + recent_volatile)

    # Window 2: High volatility in old data, stable recently
    old_volatile = [50000, 45000, 55000] * 40
    recent_stable = [50000] * 24
    prices2 = pd.Series(old_volatile + recent_stable)

    # Only recent volatility matters
    assert strategy.check_volatility(prices1) == False, "Recent volatility should trigger"
    assert strategy.check_volatility(prices2) == True, "Old volatility should not matter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
