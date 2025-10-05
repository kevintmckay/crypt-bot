#!/usr/bin/env python3
"""
Core Reliability Infrastructure
Extracted from RSI bot - Circuit breaker, retry logic, and position locking
"""

import os
import time
import json
import fcntl
import random
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

# Base directory for state files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CIRCUIT_BREAKER_STATE_FILE = os.path.join(LOG_DIR, "circuit_breaker_state.json")
POSITION_LOCK_FILE = os.path.join(LOG_DIR, "position.lock")


class CircuitBreaker:
    """Circuit breaker pattern for API reliability with state persistence."""

    def __init__(self, name: str = "default", failure_threshold: int = 5, timeout_seconds: int = 300):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout_seconds
        self.logger = logging.getLogger(__name__)
        self.state_file = os.path.join(LOG_DIR, f"circuit_breaker_{name}.json")

        # Load persisted state
        self._load_state()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time < self.timeout:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN - service unavailable")
            else:
                self.state = "HALF_OPEN"
                self.logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def _load_state(self):
        """Load circuit breaker state from disk with file locking."""
        try:
            if os.path.exists(self.state_file):
                # Acquire read lock
                lock_file = self.state_file + '.lock'
                os.makedirs(os.path.dirname(lock_file), exist_ok=True)

                with open(lock_file, 'w') as lock_fd:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                    try:
                        with open(self.state_file, 'r') as f:
                            state_data = json.load(f)

                            self.failure_count = state_data.get('failure_count', 0)
                            self.state = state_data.get('state', 'CLOSED')

                            # Restore last_failure_time as timestamp
                            last_failure_str = state_data.get('last_failure_time')
                            if last_failure_str:
                                self.last_failure_time = datetime.fromisoformat(last_failure_str).timestamp()
                            else:
                                self.last_failure_time = None

                            self.logger.info(f"Circuit breaker '{self.name}' state loaded: {self.state} "
                                           f"({self.failure_count} failures)")
                    finally:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            else:
                self._reset_state()
        except Exception as e:
            self.logger.warning(f"Could not load circuit breaker state for '{self.name}': {e}")
            self._reset_state()

    def _reset_state(self):
        """Initialize circuit breaker state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def _save_state(self):
        """Persist circuit breaker state to disk with file locking (atomic write)."""
        try:
            state_data = {
                'failure_count': self.failure_count,
                'state': self.state,
                'last_failure_time': datetime.fromtimestamp(self.last_failure_time).isoformat()
                                    if self.last_failure_time else None,
                'last_updated': datetime.now().isoformat()
            }

            # Use atomic write pattern with file locking
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            temp_file = self.state_file + '.tmp'

            # Acquire lock before writing
            lock_file = self.state_file + '.lock'
            with open(lock_file, 'w') as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                try:
                    with open(temp_file, 'w') as f:
                        json.dump(state_data, f, indent=2)

                    os.replace(temp_file, self.state_file)
                    self.logger.debug(f"Circuit breaker '{self.name}' state saved")
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)

        except Exception as e:
            self.logger.error(f"Failed to save circuit breaker state for '{self.name}': {e}")
            # Clean up temp file if it exists
            temp_path = self.state_file + '.tmp'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def on_success(self):
        """Reset circuit breaker on successful call."""
        if self.state != "CLOSED":
            self.logger.info(f"Circuit breaker '{self.name}' closing after successful call")
        self.failure_count = 0
        self.state = "CLOSED"
        self._save_state()

    def on_failure(self):
        """Handle failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")

        self._save_state()


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0, max_delay: float = 60.0):
    """Decorator for exponential backoff retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on authentication errors or invalid parameters
                    if any(error_type in str(e).lower() for error_type in
                          ['auth', 'permission', 'invalid', 'not found', 'bad request']):
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise e

                    if attempt < max_retries:
                        # Calculate exponential backoff with jitter
                        delay = min(backoff_factor * (2 ** attempt) + random.uniform(0, 1), max_delay)
                        logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                                     f"Retrying in {delay:.2f}s")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")

            raise last_exception
        return wrapper
    return decorator


@contextmanager
def position_lock(timeout: int = 30):
    """
    Acquire exclusive lock for position checking and order placement.

    This prevents race conditions when multiple bot instances run concurrently.

    Args:
        timeout: Maximum seconds to wait for lock

    Yields:
        lock_file: File handle (released automatically on exit)

    Raises:
        TimeoutError: If lock cannot be acquired within timeout

    Example:
        with position_lock(timeout=30):
            positions = get_positions(client)
            if len(positions) < MAX_POSITIONS:
                place_order(...)
    """
    lock_file = None
    try:
        # Ensure lock directory exists
        os.makedirs(os.path.dirname(POSITION_LOCK_FILE), exist_ok=True)

        # Open lock file
        lock_file = open(POSITION_LOCK_FILE, 'w')

        # Try to acquire lock with timeout
        start_time = time.time()
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug("Position lock acquired")
                break
            except IOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire position lock within {timeout}s")
                time.sleep(0.1)  # Wait 100ms and retry

        yield lock_file

    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                logger.debug("Position lock released")
            except Exception as e:
                logger.warning(f"Error releasing position lock: {e}")
