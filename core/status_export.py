"""
Status Export Module
Exports bot status to shared status file for web dashboard
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

STATUS_FILE = Path("/var/www/trading-status/data/cryptbot-status.json")


def export_status(
    symbol: str,
    status: str,
    current_position: Optional[float] = None,
    current_price: Optional[float] = None,
    account_value: Optional[float] = None,
    last_signal: Optional[str] = None,
    circuit_breaker_status: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Export current bot status to shared status file

    Args:
        symbol: Trading symbol (e.g., 'BTC/USD')
        status: Bot status ('running', 'stopped', 'error')
        current_position: Current position quantity
        current_price: Current asset price
        account_value: Total account value
        last_signal: Last trading signal ('BUY', 'SELL', 'HOLD')
        circuit_breaker_status: Circuit breaker state ('CLOSED', 'OPEN', 'HALF_OPEN')
        additional_data: Any additional key-value pairs to include

    Returns:
        bool: True if export succeeded, False otherwise
    """
    try:
        status_data = {
            'symbol': symbol,
            'status': status,
            'timestamp': datetime.now().isoformat(),
        }

        # Add optional fields if provided
        if current_position is not None:
            status_data['current_position'] = current_position
        if current_price is not None:
            status_data['current_price'] = current_price
        if account_value is not None:
            status_data['account_value'] = account_value
        if last_signal:
            status_data['last_signal'] = last_signal
        if circuit_breaker_status:
            status_data['circuit_breaker_status'] = circuit_breaker_status

        # Merge any additional data
        if additional_data:
            status_data.update(additional_data)

        # Ensure directory exists
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically using temp file
        temp_file = STATUS_FILE.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(status_data, f, indent=2)

        # Atomic rename
        temp_file.rename(STATUS_FILE)

        # Set permissions for group read
        STATUS_FILE.chmod(0o664)

        logger.debug(f"Status exported to {STATUS_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to export status: {e}")
        return False
