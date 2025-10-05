#!/usr/bin/env python3
"""
Alpaca Broker Integration
Handles all interactions with Alpaca API for trading and data
Supports both stock and crypto trading
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.reliability import CircuitBreaker, retry_with_backoff

logger = logging.getLogger(__name__)

# Circuit breaker for Alpaca API
alpaca_circuit_breaker = CircuitBreaker(
    name="alpaca",
    failure_threshold=5,
    timeout_seconds=300  # 5 minutes
)


class CryptoBrokerClient:
    """
    Alpaca crypto trading client
    Modified for crypto-specific endpoints
    """

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        """
        Initialize crypto broker client.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Use paper trading (default: True)
        """
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        # Crypto data client (no auth needed for historical data)
        self.data_client = CryptoHistoricalDataClient()
        self.paper = paper
        logger.info(f"CryptoBrokerClient initialized (paper={paper})")

    @retry_with_backoff(max_retries=3, backoff_factor=1.5)
    def get_account(self):
        """
        Get account information.

        Returns:
            Account object with equity, buying_power, etc.
        """
        logger.debug("Fetching account info")
        account = alpaca_circuit_breaker.call(
            self.trading_client.get_account
        )
        logger.debug(f"Account equity: ${float(account.equity):,.2f}")
        return account

    def get_position(self, symbol: str):
        """
        Get position for symbol.

        Args:
            symbol: Crypto symbol (e.g., 'BTC/USD')

        Returns:
            Position object, or None if no position exists
        """
        logger.debug(f"Fetching position for {symbol}")
        try:
            position = alpaca_circuit_breaker.call(
                self.trading_client.get_open_position,
                symbol
            )
            logger.debug(f"Position found: {position.qty} {symbol} @ ${position.current_price}")
            return position
        except Exception as e:
            # Handle both "position does not exist" and 404 Not Found errors
            error_str = str(e).lower()
            if 'position does not exist' in error_str or 'not found' in error_str or '404' in error_str:
                logger.debug(f"No position found for {symbol}")
                return None
            raise

    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def get_historical_prices(self,
                            symbol: str,
                            lookback_days: int = 100) -> pd.Series:
        """
        Fetch hourly crypto prices

        Note: Using hourly instead of daily for crypto
        Need more granular data for volatility checks

        Args:
            symbol: Crypto symbol (e.g., 'BTC/USD')
            lookback_days: Number of calendar days to look back (default: 100)

        Returns:
            pandas Series with hourly closing prices indexed by timestamp
        """
        logger.info(f"Fetching {lookback_days} days of hourly data for {symbol}")

        end = datetime.now()
        start = end - timedelta(days=lookback_days)

        request = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,  # Hourly bars
            start=start,
            end=end
        )

        bars = alpaca_circuit_breaker.call(
            self.data_client.get_crypto_bars,
            request
        )

        df = bars.df
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        # Extract close prices as series
        if isinstance(df.index, pd.MultiIndex):
            prices = df['close'].xs(symbol, level='symbol')
        else:
            prices = df['close']

        logger.info(f"Retrieved {len(prices)} hours of data")
        logger.debug(f"Date range: {prices.index[0]} to {prices.index[-1]}")
        logger.debug(f"Latest price: ${prices.iloc[-1]:,.2f}")

        return prices

    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def place_order(self, symbol: str, side: str, qty: float) -> dict:
        """
        Place market order for crypto

        Crypto allows fractional quantities

        Args:
            symbol: Crypto symbol (e.g., 'BTC/USD')
            side: 'BUY' or 'SELL'
            qty: Quantity (float allowed for crypto)

        Returns:
            Order object
        """
        if qty <= 0:
            raise ValueError(f"Invalid quantity: {qty}")

        order_side = OrderSide.BUY if side == 'BUY' else OrderSide.SELL

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,  # Float allowed for crypto
            side=order_side,
            time_in_force=TimeInForce.GTC  # Good-til-canceled (crypto is 24/7)
        )

        logger.info(f"Placing {side} order: {qty:.6f} {symbol}")

        order = alpaca_circuit_breaker.call(
            self.trading_client.submit_order,
            order_request
        )

        logger.info(f"Order submitted: ID {order.id}, status {order.status}")
        return order

    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def close_position(self, symbol: str):
        """
        Close entire position.

        Args:
            symbol: Crypto symbol

        Returns:
            Order object
        """
        logger.info(f"Closing entire position for {symbol}")

        result = alpaca_circuit_breaker.call(
            self.trading_client.close_position,
            symbol
        )

        logger.info(f"Position close order submitted for {symbol}")
        return result

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for symbol.

        Args:
            symbol: Crypto symbol

        Returns:
            Current price as float
        """
        # Get latest hourly bar
        prices = self.get_historical_prices(symbol, lookback_days=2)
        return float(prices.iloc[-1])
