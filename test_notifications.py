#!/usr/bin/env python3
"""
Test script for email notification system
"""

import logging
from core.notifications import init_notifications

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("Testing Email Notification System")
    print("=" * 50)

    # Initialize notifications
    notifier = init_notifications()

    print("\n1. Testing trade execution notification...")
    notifier.notify_trade_executed(
        symbol="BTC/USD",
        side="BUY",
        quantity=0.05,
        price=67500.00,
        order_id="test-order-12345"
    )
    print("✓ Trade notification sent")

    print("\n2. Testing error notification...")
    notifier.notify_error(
        error_type="TestError",
        error_message="This is a test error notification",
        traceback_info="Test traceback info"
    )
    print("✓ Error notification sent")

    print("\n3. Testing circuit breaker notification...")
    notifier.notify_circuit_breaker_tripped(
        api_name="alpaca",
        failure_count=5
    )
    print("✓ Circuit breaker notification sent")

    print("\n" + "=" * 50)
    print("All test notifications sent successfully!")
    print("Check kevintmckay@gmail.com for emails")

if __name__ == "__main__":
    main()
