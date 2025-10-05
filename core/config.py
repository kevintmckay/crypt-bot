#!/usr/bin/env python3
"""
Secure Configuration Management for RSI Trading Bot
Validates environment variables and prevents insecure credential patterns
"""

import os
import sys
import logging
import warnings
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration and validation rules."""
    min_api_key_length: int = 20
    max_api_key_length: int = 200
    forbidden_test_values: List[str] = None
    required_env_vars: List[str] = None

    def __post_init__(self):
        if self.forbidden_test_values is None:
            self.forbidden_test_values = [
                'your_api_key_here',
                'your_secret_key_here',
                'your_claude_api_key_here',
                'test_key',
                'demo_key',
                'placeholder',
                'changeme',
                'example',
                'sample'
            ]

        if self.required_env_vars is None:
            self.required_env_vars = [
                'APCA_API_KEY_ID',
                'APCA_API_SECRET_KEY',
                'TRADING_MODE'
            ]

class SecureConfigValidator:
    """Validates and secures environment configuration."""

    def __init__(self, security_config: SecurityConfig = None):
        self.security_config = security_config or SecurityConfig()
        self.validation_errors: List[str] = []
        self.security_warnings: List[str] = []

    def validate_api_key(self, key_name: str, key_value: str) -> bool:
        """Validate an API key for security compliance."""
        if not key_value:
            self.validation_errors.append(f"{key_name} is empty or missing")
            return False

        # Check for placeholder values
        key_lower = key_value.lower()
        for forbidden in self.security_config.forbidden_test_values:
            if forbidden.lower() in key_lower:
                self.validation_errors.append(
                    f"{key_name} contains placeholder value '{forbidden}' - replace with real credentials"
                )
                return False

        # Check key length
        if len(key_value) < self.security_config.min_api_key_length:
            self.validation_errors.append(
                f"{key_name} is too short ({len(key_value)} chars, minimum {self.security_config.min_api_key_length})"
            )
            return False

        if len(key_value) > self.security_config.max_api_key_length:
            self.validation_errors.append(
                f"{key_name} is too long ({len(key_value)} chars, maximum {self.security_config.max_api_key_length})"
            )
            return False

        # Check for obvious test patterns
        if key_value.startswith(('test_', 'demo_', 'sample_')):
            self.security_warnings.append(
                f"{key_name} appears to be a test key - ensure this is intentional"
            )

        return True

    def validate_alpaca_credentials(self) -> bool:
        """Validate Alpaca API credentials."""
        api_key = os.getenv('APCA_API_KEY_ID', '')
        secret_key = os.getenv('APCA_API_SECRET_KEY', '')

        api_key_valid = self.validate_api_key('APCA_API_KEY_ID', api_key)
        secret_key_valid = self.validate_api_key('APCA_API_SECRET_KEY', secret_key)

        # Additional Alpaca-specific validations
        if api_key_valid and not api_key.startswith(('PK', 'AK')):
            self.security_warnings.append(
                "APCA_API_KEY_ID doesn't start with expected prefix (PK/AK) - verify this is correct"
            )

        if api_key_valid and secret_key_valid and api_key == secret_key:
            self.validation_errors.append(
                "APCA_API_KEY_ID and APCA_API_SECRET_KEY are identical - this is invalid"
            )
            return False

        return api_key_valid and secret_key_valid

    def validate_claude_credentials(self) -> bool:
        """Validate Claude API credentials if LLM analysis is enabled."""
        llm_enabled = os.getenv('LLM_ANALYSIS_ENABLED', 'false').lower() == 'true'

        if not llm_enabled:
            logger.info("LLM analysis disabled - skipping Claude credential validation")
            return True

        api_key = os.getenv('LLM_API_KEY', '')

        if not api_key:
            self.validation_errors.append(
                "LLM_ANALYSIS_ENABLED=true but LLM_API_KEY is missing"
            )
            return False

        api_key_valid = self.validate_api_key('LLM_API_KEY', api_key)

        # Claude-specific validation
        if api_key_valid and not api_key.startswith('sk-ant-'):
            self.security_warnings.append(
                "LLM_API_KEY doesn't start with expected Claude prefix (sk-ant-) - verify this is correct"
            )

        return api_key_valid

    def validate_required_env_vars(self) -> bool:
        """Validate that all required environment variables are present."""
        missing_vars = []

        for var_name in self.security_config.required_env_vars:
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(var_name)

        if missing_vars:
            self.validation_errors.append(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            return False

        return True

    def validate_trading_parameters(self) -> bool:
        """Validate trading configuration parameters."""
        try:
            # Validate numeric parameters
            max_positions = int(os.getenv('MAX_POSITIONS', 1))
            if max_positions < 1 or max_positions > 10:
                self.validation_errors.append(
                    f"MAX_POSITIONS ({max_positions}) must be between 1 and 10"
                )
                return False

            dollars_per_trade = int(os.getenv('DOLLARS_PER_TRADE', 500))
            if dollars_per_trade < 100 or dollars_per_trade > 100000:
                self.validation_errors.append(
                    f"DOLLARS_PER_TRADE ({dollars_per_trade}) must be between 100 and 100000"
                )
                return False

            # Validate RSI thresholds for stocks
            rsi_threshold = int(os.getenv('STOCK_RSI_THRESHOLD', 5))
            rsi_exit = int(os.getenv('STOCK_RSI_EXIT', 70))

            if rsi_threshold < 1 or rsi_threshold > 50:
                self.validation_errors.append(
                    f"RSI threshold ({rsi_threshold}) must be between 1 and 50"
                )
                return False

            if rsi_exit < 50 or rsi_exit > 99:
                self.validation_errors.append(
                    f"RSI exit ({rsi_exit}) must be between 50 and 99"
                )
                return False

            if rsi_threshold >= rsi_exit:
                self.validation_errors.append(
                    f"RSI threshold ({rsi_threshold}) must be less than RSI exit ({rsi_exit})"
                )
                return False

            # Validate risk management ratios
            take_profit = float(os.getenv('TAKE_PROFIT_MULT', 1.5))
            if take_profit < 1.0 or take_profit > 10.0:
                self.validation_errors.append(
                    f"TAKE_PROFIT_MULT ({take_profit}) must be between 1.0 and 10.0"
                )
                return False

            stop_loss = float(os.getenv('STOP_LOSS_MULT', 2.0))
            if stop_loss < 1.0 or stop_loss > 10.0:
                self.validation_errors.append(
                    f"STOP_LOSS_MULT ({stop_loss}) must be between 1.0 and 10.0"
                )
                return False

            # Validate RSI periods for stocks
            rsi_period = int(os.getenv('STOCK_RSI_PERIOD', 2))

            if rsi_period < 2 or rsi_period > 100:
                self.validation_errors.append(
                    f"RSI period ({rsi_period}) must be between 2 and 100"
                )
                return False

            # Validate timeframes for stocks
            valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']
            timeframe = os.getenv('STOCK_TIMEFRAME', '1d')

            if timeframe not in valid_timeframes:
                self.validation_errors.append(
                    f"Timeframe ({timeframe}) must be one of: {', '.join(valid_timeframes)}"
                )
                return False

            # Validate trading interval
            trading_interval = int(os.getenv('TRADING_INTERVAL_MINUTES', 60))
            if trading_interval < 1 or trading_interval > 1440:  # 1 minute to 24 hours
                self.validation_errors.append(
                    f"TRADING_INTERVAL_MINUTES ({trading_interval}) must be between 1 and 1440"
                )
                return False

            # Validate trading mode (stocks only)
            trading_mode = os.getenv('TRADING_MODE', 'STOCKS').upper()
            if trading_mode != 'STOCKS':
                self.validation_errors.append(
                    f"TRADING_MODE must be 'STOCKS' (found: {trading_mode})"
                )
                return False

            # Validate stock universe
            universe = os.getenv('STOCK_UNIVERSE', 'SPY,QQQ,VTI,IWM').split(',')
            universe = [asset.strip() for asset in universe if asset.strip()]

            if len(universe) == 0:
                self.validation_errors.append("Stock universe cannot be empty")
                return False

            if len(universe) > 50:
                self.validation_errors.append(
                    f"Stock universe ({len(universe)} assets) should not exceed 50 assets"
                )
                return False

            return True

        except ValueError as e:
            self.validation_errors.append(f"Invalid numeric parameter: {e}")
            return False

    def check_file_security(self) -> bool:
        """Check for security issues in configuration files."""
        env_file = Path('.env')

        if env_file.exists():
            try:
                # Check file permissions
                stat_info = env_file.stat()
                file_mode = oct(stat_info.st_mode)[-3:]

                # Skip permission warning in Docker containers (mounted files show host permissions)
                is_docker = os.path.exists('/.dockerenv')
                if file_mode != '600' and not is_docker:
                    self.security_warnings.append(
                        f".env file permissions ({file_mode}) should be 600 (owner read/write only)"
                    )

                # Check for common secrets in file
                with open(env_file, 'r') as f:
                    content = f.read()

                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if line_stripped.startswith('#') or not line_stripped:
                        continue

                    if '=' in line_stripped:
                        key, value = line_stripped.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # Whitelist of legitimate secret/password keys
                        legitimate_secret_keys = {
                            'APCA_API_SECRET_KEY',
                            'ANTHROPIC_API_KEY',
                            'TELEGRAM_BOT_TOKEN',
                            'SMTP_PASSWORD'
                        }

                        # Check for obvious secrets in inappropriate places
                        # Skip warning for whitelisted legitimate API keys
                        if 'password' in key.lower() or 'secret' in key.lower():
                            if key not in legitimate_secret_keys:
                                if len(value) > 10 and not any(test in value.lower() for test in self.security_config.forbidden_test_values):
                                    logger.warning(f"Line {line_num}: Potential secret detected in .env file: {key}")

            except Exception as e:
                self.security_warnings.append(f"Could not check .env file security: {e}")

        return True

    def validate_all(self) -> bool:
        """Run comprehensive validation of all configuration."""
        logger.info("🔒 Starting secure configuration validation...")

        # Clear previous results
        self.validation_errors.clear()
        self.security_warnings.clear()

        # Run all validations
        validations = [
            self.validate_required_env_vars(),
            self.validate_alpaca_credentials(),
            self.validate_claude_credentials(),
            self.validate_trading_parameters(),
            self.check_file_security()
        ]

        all_valid = all(validations)

        # Report results
        if self.validation_errors:
            logger.error("❌ Configuration validation failed:")
            for error in self.validation_errors:
                logger.error(f"  • {error}")

        if self.security_warnings:
            logger.warning("⚠️ Security warnings:")
            for warning in self.security_warnings:
                logger.warning(f"  • {warning}")

        if all_valid and not self.validation_errors:
            logger.info("✅ Configuration validation passed")
            if not self.security_warnings:
                logger.info("🔒 No security warnings detected")

        return all_valid and not self.validation_errors

    def get_sanitized_env_summary(self) -> Dict[str, str]:
        """Get environment summary with sensitive values redacted."""
        summary = {}

        for key, value in os.environ.items():
            if any(sensitive in key.upper() for sensitive in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                if value and len(value) > 4:
                    summary[key] = f"{value[:4]}...***"
                else:
                    summary[key] = "***"
            else:
                summary[key] = value

        return summary

def validate_configuration() -> bool:
    """Main configuration validation function."""
    validator = SecureConfigValidator()
    return validator.validate_all()

def secure_env_var(var_name: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
    """Safely retrieve environment variable with validation."""
    value = os.getenv(var_name, default)

    if required and not value:
        logger.error(f"Required environment variable {var_name} is missing")
        return None

    # Basic security check
    if value and any(test in value.lower() for test in ['your_', 'test_', 'demo_', 'sample_']):
        logger.warning(f"Environment variable {var_name} appears to contain placeholder value")

    return value

if __name__ == "__main__":
    # Allow running this module directly for configuration testing
    import os
    from dotenv import load_dotenv

    # Load environment variables from parent directory when running standalone
    parent_dir = Path(__file__).parent.parent
    env_file = parent_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if validate_configuration():
        print("✅ Configuration validation passed")
        sys.exit(0)
    else:
        print("❌ Configuration validation failed")
        sys.exit(1)