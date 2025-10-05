#!/usr/bin/env python3
"""
Notification system for critical trading events.
Supports multiple channels: email, file logging, and extensible for future channels.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """Notification priority levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    FILE = "file"
    CONSOLE = "console"

class NotificationManager:
    """Manages notifications across multiple channels."""

    def __init__(self,
                 email_enabled: bool = None,
                 smtp_host: str = None,
                 smtp_port: int = None,
                 smtp_user: str = None,
                 smtp_password: str = None,
                 alert_email_to: str = None,
                 alert_email_from: str = None,
                 notification_log_file: str = None):
        """
        Initialize notification manager.

        Args:
            email_enabled: Enable email notifications (default: from env ALERT_EMAIL_ENABLED)
            smtp_host: SMTP server host (default: from env SMTP_HOST)
            smtp_port: SMTP server port (default: from env SMTP_PORT or 587)
            smtp_user: SMTP username (default: from env SMTP_USER)
            smtp_password: SMTP password (default: from env SMTP_PASSWORD)
            alert_email_to: Recipient email address (default: from env ALERT_EMAIL_TO)
            alert_email_from: Sender email address (default: from env ALERT_EMAIL_FROM)
            notification_log_file: Path to notification log file (default: logs/notifications.log)
        """
        # Email configuration
        self.email_enabled = email_enabled if email_enabled is not None else os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = smtp_user or os.getenv('SMTP_USER', '')
        self.smtp_password = smtp_password or os.getenv('SMTP_PASSWORD', '')
        self.alert_email_to = alert_email_to or os.getenv('ALERT_EMAIL_TO', '')
        self.alert_email_from = alert_email_from or os.getenv('ALERT_EMAIL_FROM', self.smtp_user)

        # File logging configuration
        self.notification_log_file = notification_log_file or os.getenv('NOTIFICATION_LOG_FILE', 'logs/notifications.log')
        self._setup_notification_log()

        # Validate email configuration if enabled
        if self.email_enabled:
            if not all([self.smtp_user, self.smtp_password, self.alert_email_to]):
                logger.warning("Email notifications enabled but missing configuration. Disabling email alerts.")
                logger.warning("Required: SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO")
                self.email_enabled = False
            else:
                logger.info(f"Email notifications enabled: {self.alert_email_to}")

    def _setup_notification_log(self):
        """Setup dedicated notification log file."""
        log_path = Path(self.notification_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler for notifications
        self.notification_logger = logging.getLogger('notifications')
        self.notification_logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.notification_logger.handlers.clear()

        file_handler = logging.FileHandler(self.notification_log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.notification_logger.addHandler(file_handler)

    def send_email(self, subject: str, body: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """
        Send email notification.

        Args:
            subject: Email subject
            body: Email body (plain text)
            level: Notification level

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.email_enabled:
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{level.value}] {subject}"
            msg['From'] = self.alert_email_from
            msg['To'] = self.alert_email_to

            # Add level indicator to body
            full_body = f"Alert Level: {level.value}\n\n{body}"
            msg.attach(MIMEText(full_body, 'plain'))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email notification sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def log_notification(self, event: str, details: str, level: NotificationLevel = NotificationLevel.INFO):
        """
        Log notification to file.

        Args:
            event: Event name/type
            details: Event details
            level: Notification level
        """
        message = f"[{event}] {details}"

        if level == NotificationLevel.CRITICAL:
            self.notification_logger.critical(message)
        elif level == NotificationLevel.ERROR:
            self.notification_logger.error(message)
        elif level == NotificationLevel.WARNING:
            self.notification_logger.warning(message)
        else:
            self.notification_logger.info(message)

    def notify(self,
               event: str,
               details: str,
               level: NotificationLevel = NotificationLevel.INFO,
               channels: List[NotificationChannel] = None,
               email_subject: str = None):
        """
        Send notification across multiple channels.

        Args:
            event: Event name (e.g., "TRADE_EXECUTED", "STOP_LOSS_TRIGGERED")
            details: Detailed description of the event
            level: Notification level
            channels: List of channels to use (default: [FILE, CONSOLE, EMAIL if critical])
            email_subject: Custom email subject (default: event name)
        """
        # Default channels
        if channels is None:
            channels = [NotificationChannel.FILE, NotificationChannel.CONSOLE]
            # Auto-add email for critical/error events
            if level in [NotificationLevel.CRITICAL, NotificationLevel.ERROR]:
                channels.append(NotificationChannel.EMAIL)

        # Log to file
        if NotificationChannel.FILE in channels:
            self.log_notification(event, details, level)

        # Log to console
        if NotificationChannel.CONSOLE in channels:
            console_msg = f"[{level.value}] {event}: {details}"
            if level == NotificationLevel.CRITICAL:
                logger.critical(console_msg)
            elif level == NotificationLevel.ERROR:
                logger.error(console_msg)
            elif level == NotificationLevel.WARNING:
                logger.warning(console_msg)
            else:
                logger.info(console_msg)

        # Send email
        if NotificationChannel.EMAIL in channels and self.email_enabled:
            subject = email_subject or f"CryptBot Alert: {event}"
            self.send_email(subject, details, level)

    # Convenience methods for common events

    def notify_trade_executed(self, symbol: str, side: str, quantity: float, price: float, order_id: str):
        """Notify when a trade is executed."""
        details = (
            f"Symbol: {symbol}\n"
            f"Side: {side}\n"
            f"Quantity: {quantity}\n"
            f"Price: ${price:,.2f}\n"
            f"Order ID: {order_id}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.notify("TRADE_EXECUTED", details, NotificationLevel.INFO,
                   channels=[NotificationChannel.FILE, NotificationChannel.CONSOLE, NotificationChannel.EMAIL])

    def notify_stop_loss_triggered(self, symbol: str, entry_price: float, current_price: float, loss_pct: float):
        """Notify when stop loss is triggered."""
        details = (
            f"Symbol: {symbol}\n"
            f"Entry Price: ${entry_price:,.2f}\n"
            f"Current Price: ${current_price:,.2f}\n"
            f"Loss: {loss_pct:.2f}%\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.notify("STOP_LOSS_TRIGGERED", details, NotificationLevel.WARNING,
                   channels=[NotificationChannel.FILE, NotificationChannel.CONSOLE, NotificationChannel.EMAIL])

    def notify_error(self, error_type: str, error_message: str, traceback_info: str = None):
        """Notify when an error occurs."""
        details = (
            f"Error Type: {error_type}\n"
            f"Message: {error_message}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if traceback_info:
            details += f"\n\nTraceback:\n{traceback_info}"

        self.notify("ERROR_OCCURRED", details, NotificationLevel.ERROR)

    def notify_circuit_breaker_tripped(self, api_name: str, failure_count: int):
        """Notify when circuit breaker trips."""
        details = (
            f"API: {api_name}\n"
            f"Consecutive Failures: {failure_count}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Trading suspended until circuit breaker resets."
        )
        self.notify("CIRCUIT_BREAKER_TRIPPED", details, NotificationLevel.CRITICAL)

    def notify_circuit_breaker_reset(self, api_name: str):
        """Notify when circuit breaker resets."""
        details = (
            f"API: {api_name}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Trading operations can resume."
        )
        self.notify("CIRCUIT_BREAKER_RESET", details, NotificationLevel.INFO)

    def notify_order_fill_failed(self, symbol: str, order_id: str, reason: str):
        """Notify when an order fails to fill."""
        details = (
            f"Symbol: {symbol}\n"
            f"Order ID: {order_id}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.notify("ORDER_FILL_FAILED", details, NotificationLevel.ERROR)

    def notify_health_check_failed(self, check_name: str, reason: str):
        """Notify when a health check fails."""
        details = (
            f"Check: {check_name}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.notify("HEALTH_CHECK_FAILED", details, NotificationLevel.CRITICAL)

# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    """Get or create global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager

def init_notifications(**kwargs) -> NotificationManager:
    """
    Initialize global notification manager with custom settings.

    Args:
        **kwargs: Configuration parameters passed to NotificationManager

    Returns:
        Initialized NotificationManager instance
    """
    global _notification_manager
    _notification_manager = NotificationManager(**kwargs)
    return _notification_manager
