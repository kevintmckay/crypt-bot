#!/usr/bin/env python3
"""
Market Hours and Timezone Management
Handles US stock market hours with proper timezone handling and holiday awareness
"""

import logging
from datetime import datetime, time, date
from typing import Optional, Tuple, Dict
import pytz
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarketSession:
    """Represents a market trading session"""
    name: str
    start_time: time
    end_time: time
    timezone: str
    description: str

class MarketHoursManager:
    """
    Comprehensive market hours management with timezone support
    Handles US stock market regular and extended hours
    """

    def __init__(self):
        # US market timezone
        self.market_tz = pytz.timezone('America/New_York')

        # Market sessions (all times in ET)
        self.sessions = {
            'premarket': MarketSession(
                name='premarket',
                start_time=time(4, 0),    # 4:00 AM ET
                end_time=time(9, 30),     # 9:30 AM ET
                timezone='America/New_York',
                description='Pre-market trading session'
            ),
            'regular': MarketSession(
                name='regular',
                start_time=time(9, 30),   # 9:30 AM ET
                end_time=time(16, 0),     # 4:00 PM ET
                timezone='America/New_York',
                description='Regular trading hours'
            ),
            'afterhours': MarketSession(
                name='afterhours',
                start_time=time(16, 0),   # 4:00 PM ET
                end_time=time(20, 0),     # 8:00 PM ET
                timezone='America/New_York',
                description='After-hours trading session'
            )
        }

        # Market holidays (2024-2025) - these are observance dates
        self.market_holidays = {
            # 2024 holidays
            date(2024, 1, 1),   # New Year's Day
            date(2024, 1, 15),  # Martin Luther King Jr. Day
            date(2024, 2, 19),  # Presidents Day
            date(2024, 3, 29),  # Good Friday
            date(2024, 5, 27),  # Memorial Day
            date(2024, 6, 19),  # Juneteenth
            date(2024, 7, 4),   # Independence Day
            date(2024, 9, 2),   # Labor Day
            date(2024, 11, 28), # Thanksgiving
            date(2024, 12, 25), # Christmas

            # 2025 holidays
            date(2025, 1, 1),   # New Year's Day
            date(2025, 1, 20),  # Martin Luther King Jr. Day
            date(2025, 2, 17),  # Presidents Day
            date(2025, 4, 18),  # Good Friday
            date(2025, 5, 26),  # Memorial Day
            date(2025, 6, 19),  # Juneteenth
            date(2025, 7, 4),   # Independence Day
            date(2025, 9, 1),   # Labor Day
            date(2025, 11, 27), # Thanksgiving
            date(2025, 12, 25), # Christmas
        }

        # Early close days (1:00 PM ET close)
        self.early_close_days = {
            date(2024, 11, 29), # Day after Thanksgiving 2024
            date(2024, 12, 24), # Christmas Eve 2024
            date(2025, 11, 28), # Day after Thanksgiving 2025
            date(2025, 12, 24), # Christmas Eve 2025
        }

    def get_current_et_time(self) -> datetime:
        """Get current time in Eastern Time"""
        return datetime.now(self.market_tz)

    def is_market_holiday(self, check_date: Optional[date] = None) -> bool:
        """Check if given date (or today) is a market holiday"""
        if check_date is None:
            check_date = self.get_current_et_time().date()
        return check_date in self.market_holidays

    def is_early_close_day(self, check_date: Optional[date] = None) -> bool:
        """Check if given date (or today) is an early close day"""
        if check_date is None:
            check_date = self.get_current_et_time().date()
        return check_date in self.early_close_days

    def is_weekend(self, check_date: Optional[date] = None) -> bool:
        """Check if given date (or today) is a weekend"""
        if check_date is None:
            check_date = self.get_current_et_time().date()
        return check_date.weekday() >= 5  # Saturday = 5, Sunday = 6

    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """Check if given date (or today) is a trading day"""
        if check_date is None:
            check_date = self.get_current_et_time().date()

        return (not self.is_weekend(check_date) and
                not self.is_market_holiday(check_date))

    def get_market_session(self, check_time: Optional[datetime] = None) -> Optional[str]:
        """
        Get current market session name
        Returns: 'premarket', 'regular', 'afterhours', or None if closed
        """
        if check_time is None:
            check_time = self.get_current_et_time()

        # Convert to ET if needed
        if check_time.tzinfo != self.market_tz:
            check_time = check_time.astimezone(self.market_tz)

        current_time = check_time.time()
        current_date = check_time.date()

        # Check if it's a trading day
        if not self.is_trading_day(current_date):
            return None

        # Handle early close days
        if self.is_early_close_day(current_date):
            # Early close at 1:00 PM ET
            if time(9, 30) <= current_time <= time(13, 0):
                return 'regular'
            elif time(4, 0) <= current_time <= time(9, 30):
                return 'premarket'
            else:
                return None

        # Regular trading day
        for session_name, session in self.sessions.items():
            if session.start_time <= current_time <= session.end_time:
                return session_name

        return None

    def is_market_open(self, session: str = 'regular', check_time: Optional[datetime] = None) -> bool:
        """
        Check if market is open for specified session
        Args:
            session: 'premarket', 'regular', 'afterhours', or 'any'
            check_time: Time to check (defaults to now)
        """
        if check_time is None:
            check_time = self.get_current_et_time()

        current_session = self.get_market_session(check_time)

        if session == 'any':
            return current_session is not None
        else:
            return current_session == session

    def get_next_market_open(self, session: str = 'regular') -> datetime:
        """Get the next market open time for specified session"""
        current_et = self.get_current_et_time()
        check_date = current_et.date()

        # Look up to 10 days ahead to find next trading day
        for days_ahead in range(10):
            candidate_date = date.fromordinal(check_date.toordinal() + days_ahead)

            if self.is_trading_day(candidate_date):
                session_info = self.sessions[session]
                next_open = self.market_tz.localize(
                    datetime.combine(candidate_date, session_info.start_time)
                )

                # If it's today, check if session hasn't started yet
                if days_ahead == 0:
                    if current_et.time() < session_info.start_time:
                        return next_open
                else:
                    return next_open

        # Fallback - shouldn't happen unless there are 10+ consecutive holidays
        fallback_date = date.fromordinal(check_date.toordinal() + 7)
        session_info = self.sessions[session]
        return self.market_tz.localize(
            datetime.combine(fallback_date, session_info.start_time)
        )

    def get_market_close_time(self, check_date: Optional[date] = None) -> Optional[time]:
        """Get market close time for given date (or today)"""
        if check_date is None:
            check_date = self.get_current_et_time().date()

        if not self.is_trading_day(check_date):
            return None

        if self.is_early_close_day(check_date):
            return time(13, 0)  # 1:00 PM ET
        else:
            return time(16, 0)  # 4:00 PM ET

    def get_market_status(self) -> Dict:
        """Get comprehensive market status information"""
        current_et = self.get_current_et_time()
        current_date = current_et.date()
        current_session = self.get_market_session()

        status = {
            'current_time_et': current_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'is_trading_day': self.is_trading_day(),
            'is_weekend': self.is_weekend(),
            'is_holiday': self.is_market_holiday(),
            'is_early_close': self.is_early_close_day(),
            'current_session': current_session,
            'market_open': {
                'regular': self.is_market_open('regular'),
                'premarket': self.is_market_open('premarket'),
                'afterhours': self.is_market_open('afterhours'),
                'any': self.is_market_open('any')
            }
        }

        # Add close time for today
        close_time = self.get_market_close_time()
        if close_time:
            status['market_close_today'] = close_time.strftime('%H:%M ET')

        # Add next market open
        if not self.is_market_open('regular'):
            next_open = self.get_next_market_open('regular')
            status['next_market_open'] = next_open.strftime('%Y-%m-%d %H:%M:%S %Z')

        return status

    def should_trade_stocks(self, require_regular_hours: bool = True) -> Tuple[bool, str]:
        """
        Determine if stock trading should proceed
        Returns: (should_trade, reason)
        """
        current_et = self.get_current_et_time()

        # Check if it's a trading day
        if not self.is_trading_day():
            if self.is_weekend():
                return False, "Weekend - market closed"
            elif self.is_market_holiday():
                return False, "Market holiday"
            else:
                return False, "Market closed"

        # Check market hours
        if require_regular_hours:
            if self.is_market_open('regular'):
                return True, "Regular market hours"
            else:
                current_session = self.get_market_session()
                if current_session == 'premarket':
                    return False, "Pre-market hours - waiting for regular hours"
                elif current_session == 'afterhours':
                    return False, "After-hours - regular hours closed"
                else:
                    next_open = self.get_next_market_open('regular')
                    return False, f"Market closed - next open: {next_open.strftime('%Y-%m-%d %H:%M %Z')}"
        else:
            # Allow extended hours trading
            if self.is_market_open('any'):
                session = self.get_market_session()
                return True, f"Market open ({session} session)"
            else:
                next_open = self.get_next_market_open('regular')
                return False, f"Market closed - next open: {next_open.strftime('%Y-%m-%d %H:%M %Z')}"

    def log_market_status(self):
        """Log current market status for debugging"""
        status = self.get_market_status()
        logger.info(f"Market Status: {status['current_time_et']}")
        logger.info(f"Trading Day: {status['is_trading_day']}, Session: {status['current_session']}")
        logger.info(f"Regular Hours Open: {status['market_open']['regular']}")

        if 'next_market_open' in status:
            logger.info(f"Next Market Open: {status['next_market_open']}")