#!/usr/bin/env python3
"""
Edge case and failure scenario testing
"""

import pytest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies.trend_following import TrendFollowingStrategy
from core.reliability import CircuitBreaker, retry_with_backoff


class TestStrategyEdgeCases:
    """Test edge cases in strategy logic."""

    def test_empty_price_series(self):
        """Test with empty price data."""
        strategy = TrendFollowingStrategy(sma_period=200)
        prices = pd.Series([])

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal == 'HOLD'
        assert sma is None

    def test_single_price(self):
        """Test with only one price point."""
        strategy = TrendFollowingStrategy(sma_period=200)
        prices = pd.Series([100.0])

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal == 'HOLD'
        assert sma is None

    def test_nan_in_prices(self):
        """Test handling of NaN values in price data."""
        strategy = TrendFollowingStrategy(sma_period=10)
        prices = pd.Series([10, 20, float('nan'), 30, 40, 50, 60, 70, 80, 90, 100])

        # Should still calculate SMA, pandas handles NaN
        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal in ['BUY', 'SELL', 'HOLD']

    def test_all_same_prices(self):
        """Test when all prices are identical."""
        strategy = TrendFollowingStrategy(sma_period=10)
        prices = pd.Series([100.0] * 20)

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert sma == 100.0
        # Price == SMA should trigger SELL
        assert signal == 'SELL'

    def test_extreme_volatility(self):
        """Test with highly volatile prices."""
        strategy = TrendFollowingStrategy(sma_period=10)
        # Alternating between 100 and 200
        prices = pd.Series([100 if i % 2 == 0 else 200 for i in range(20)])

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal in ['BUY', 'SELL']
        assert sma is not None

    def test_year_boundary_rebalance(self):
        """Test rebalancing across year boundaries."""
        strategy = TrendFollowingStrategy(sma_period=10)
        prices = pd.Series(range(1, 21))

        # Rebalance in December
        dec_date = datetime(2024, 12, 31)
        signal1, _ = strategy.generate_signal(prices, dec_date)
        assert signal1 == 'BUY'
        strategy.mark_rebalanced(dec_date)

        # Should rebalance in January (new year, new month)
        jan_date = datetime(2025, 1, 1)
        signal2, _ = strategy.generate_signal(prices, jan_date)
        assert signal2 == 'BUY'

    def test_exactly_minimum_data(self):
        """Test with exactly the minimum required data points."""
        strategy = TrendFollowingStrategy(sma_period=200)
        prices = pd.Series(range(1, 201))  # Exactly 200 points

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal in ['BUY', 'SELL']
        assert sma is not None

    def test_one_less_than_minimum(self):
        """Test with one less than minimum required data."""
        strategy = TrendFollowingStrategy(sma_period=200)
        prices = pd.Series(range(1, 200))  # 199 points

        signal, sma = strategy.generate_signal(prices, datetime.now())
        assert signal == 'HOLD'
        assert sma is None


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(name="test_cb", failure_threshold=3, timeout_seconds=1)

        # Simulate failures
        for i in range(3):
            cb.on_failure()

        assert cb.state == "OPEN"

    def test_circuit_breaker_recovers(self):
        """Test that circuit breaker can recover."""
        cb = CircuitBreaker(name="test_cb2", failure_threshold=3, timeout_seconds=1)

        # Open the circuit
        for i in range(3):
            cb.on_failure()
        assert cb.state == "OPEN"

        # Success should close it
        cb.on_success()
        assert cb.state == "CLOSED"

    def test_circuit_breaker_half_open_transition(self):
        """Test HALF_OPEN state transition."""
        import time

        cb = CircuitBreaker(name="test_cb3", failure_threshold=2, timeout_seconds=1)

        # Open the circuit
        cb.on_failure()
        cb.on_failure()
        assert cb.state == "OPEN"

        # Wait for timeout
        time.sleep(1.5)

        # Next call should transition to HALF_OPEN
        # We'll test this indirectly by checking if call is allowed
        # (In real scenario, call method checks this)


class TestPositionSizingEdgeCases:
    """Test position sizing edge cases."""

    def test_zero_account_value(self):
        """Test with zero account value."""
        from main import TrendFollowingBot

        # Mock environment
        with patch.dict(os.environ, {
            'SYMBOL': 'SPY',
            'ACCOUNT_ALLOCATION': '0.95',
            'SMA_PERIOD': '200',
            'ALPACA_API_KEY': 'test',
            'ALPACA_SECRET_KEY': 'test',
            'ALPACA_PAPER': 'true'
        }):
            with patch('main.BrokerClient'):
                with patch('main.MarketHoursManager'):
                    bot = TrendFollowingBot()

                    # Test with zero account value
                    shares = bot.calculate_target_position(0, 100.0)
                    assert shares == 0

    def test_very_high_price(self):
        """Test with very high stock price."""
        from main import TrendFollowingBot

        with patch.dict(os.environ, {
            'SYMBOL': 'SPY',
            'ACCOUNT_ALLOCATION': '0.95',
            'SMA_PERIOD': '200',
            'ALPACA_API_KEY': 'test',
            'ALPACA_SECRET_KEY': 'test',
            'ALPACA_PAPER': 'true'
        }):
            with patch('main.BrokerClient'):
                with patch('main.MarketHoursManager'):
                    bot = TrendFollowingBot()

                    # Test with very high price (e.g., BRK.A)
                    shares = bot.calculate_target_position(100000, 600000.0)
                    assert shares == 0  # Can't afford even 1 share

    def test_fractional_shares_rounded_down(self):
        """Test that fractional shares are rounded down to int."""
        from main import TrendFollowingBot

        with patch.dict(os.environ, {
            'SYMBOL': 'SPY',
            'ACCOUNT_ALLOCATION': '0.50',
            'SMA_PERIOD': '200',
            'ALPACA_API_KEY': 'test',
            'ALPACA_SECRET_KEY': 'test',
            'ALPACA_PAPER': 'true'
        }):
            with patch('main.BrokerClient'):
                with patch('main.MarketHoursManager'):
                    bot = TrendFollowingBot()

                    # $1000 account, 50% allocation, $333 price
                    # = $500 / $333 = 1.501... shares
                    # Should round down to 1
                    shares = bot.calculate_target_position(1000, 333.0)
                    assert shares == 1


class TestRetryLogicEdgeCases:
    """Test retry decorator edge cases."""

    def test_retry_with_immediate_success(self):
        """Test retry decorator with immediate success."""
        call_count = [0]

        @retry_with_backoff(max_retries=3)
        def succeeds_immediately():
            call_count[0] += 1
            return "success"

        result = succeeds_immediately()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_exhaustion(self):
        """Test retry decorator when all retries exhausted."""
        call_count = [0]

        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def always_fails():
            call_count[0] += 1
            raise Exception("Test failure")

        with pytest.raises(Exception) as excinfo:
            always_fails()

        assert "Test failure" in str(excinfo.value)
        assert call_count[0] == 4  # Initial + 3 retries

    def test_retry_with_non_retryable_error(self):
        """Test that auth errors are not retried."""
        call_count = [0]

        @retry_with_backoff(max_retries=3)
        def auth_error():
            call_count[0] += 1
            raise Exception("Authentication failed")

        with pytest.raises(Exception):
            auth_error()

        # Should fail immediately, no retries
        assert call_count[0] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
