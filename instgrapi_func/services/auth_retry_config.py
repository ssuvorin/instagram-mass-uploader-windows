"""
Configuration for authentication retry logic in instagrapi services.
This module provides centralized configuration for retry attempts and delays.
"""

from typing import Dict, Any
import os

class AuthRetryConfig:
    """Configuration class for authentication retry settings."""
    
    # Default retry configuration
    DEFAULT_CONFIG = {
        # Session restoration retry settings
        'session_restoration': {
            'max_retries': 1,  # Only one attempt - if session is invalid, retries won't help
            'base_delay_min': 0.0,  # No delay needed for single attempt
            'base_delay_max': 0.0,  # No delay needed for single attempt
            'exponential_multiplier': 1.0,  # Not used for single attempt
        },
        
        # Authentication retry settings (for actual login attempts)
        'authentication': {
            'max_retries': 3,  # Multiple attempts make sense for login (network issues, rate limits, etc.)
            'base_delay_min': 5.0,  # seconds
            'base_delay_max': 10.0,  # seconds
            'exponential_multiplier': 1.0,  # multiplier for each retry
        },
        
        # Fallback authentication retry settings (when session verification fails)
        'fallback_authentication': {
            'max_retries': 3,  # Multiple attempts make sense for login
            'base_delay_min': 5.0,  # seconds
            'base_delay_max': 10.0,  # seconds
            'exponential_multiplier': 1.0,  # multiplier for each retry
        },
        
        # Exception fallback authentication retry settings (when exceptions occur)
        'exception_fallback_authentication': {
            'max_retries': 3,  # Multiple attempts make sense for login
            'base_delay_min': 5.0,  # seconds
            'base_delay_max': 10.0,  # seconds
            'exponential_multiplier': 1.0,  # multiplier for each retry
        },
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize configuration with optional custom settings.
        
        Args:
            config: Optional custom configuration dictionary
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self._merge_config(config)
    
    def _merge_config(self, custom_config: Dict[str, Any]) -> None:
        """Merge custom configuration with default configuration."""
        for category, settings in custom_config.items():
            if category in self.config:
                self.config[category].update(settings)
            else:
                self.config[category] = settings
    
    def get_session_restoration_config(self) -> Dict[str, Any]:
        """Get session restoration retry configuration."""
        return self.config['session_restoration']
    
    def get_authentication_config(self) -> Dict[str, Any]:
        """Get authentication retry configuration."""
        return self.config['authentication']
    
    def get_fallback_authentication_config(self) -> Dict[str, Any]:
        """Get fallback authentication retry configuration."""
        return self.config['fallback_authentication']
    
    def get_exception_fallback_authentication_config(self) -> Dict[str, Any]:
        """Get exception fallback authentication retry configuration."""
        return self.config['exception_fallback_authentication']
    
    def calculate_delay(self, attempt: int, config_type: str) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            config_type: Type of configuration to use
            
        Returns:
            Delay in seconds
        """
        config = self.config.get(config_type, self.DEFAULT_CONFIG['authentication'])
        
        base_delay_min = config['base_delay_min']
        base_delay_max = config['base_delay_max']
        exponential_multiplier = config['exponential_multiplier']
        
        # Calculate exponential backoff
        multiplier = exponential_multiplier ** (attempt + 1)
        
        # Add some randomness to avoid thundering herd
        import random
        delay = random.uniform(base_delay_min, base_delay_max) * multiplier
        
        return delay
    
    @classmethod
    def from_env(cls) -> 'AuthRetryConfig':
        """
        Create configuration from environment variables.
        
        Environment variables:
        - AUTH_RETRY_SESSION_MAX_RETRIES: Max retries for session restoration
        - AUTH_RETRY_AUTH_MAX_RETRIES: Max retries for authentication
        - AUTH_RETRY_FALLBACK_MAX_RETRIES: Max retries for fallback authentication
        - AUTH_RETRY_EXCEPTION_FALLBACK_MAX_RETRIES: Max retries for exception fallback authentication
        - AUTH_RETRY_BASE_DELAY_MIN: Minimum base delay in seconds
        - AUTH_RETRY_BASE_DELAY_MAX: Maximum base delay in seconds
        - AUTH_RETRY_EXPONENTIAL_MULTIPLIER: Exponential multiplier for delays
        """
        config = {}
        
        # Session restoration settings
        if os.getenv('AUTH_RETRY_SESSION_MAX_RETRIES'):
            config['session_restoration'] = {
                'max_retries': int(os.getenv('AUTH_RETRY_SESSION_MAX_RETRIES'))
            }
        
        # Authentication settings
        if os.getenv('AUTH_RETRY_AUTH_MAX_RETRIES'):
            config['authentication'] = {
                'max_retries': int(os.getenv('AUTH_RETRY_AUTH_MAX_RETRIES'))
            }
        
        # Fallback authentication settings
        if os.getenv('AUTH_RETRY_FALLBACK_MAX_RETRIES'):
            config['fallback_authentication'] = {
                'max_retries': int(os.getenv('AUTH_RETRY_FALLBACK_MAX_RETRIES'))
            }
        
        # Exception fallback authentication settings
        if os.getenv('AUTH_RETRY_EXCEPTION_FALLBACK_MAX_RETRIES'):
            config['exception_fallback_authentication'] = {
                'max_retries': int(os.getenv('AUTH_RETRY_EXCEPTION_FALLBACK_MAX_RETRIES'))
            }
        
        # Global delay settings
        if os.getenv('AUTH_RETRY_BASE_DELAY_MIN'):
            base_delay_min = float(os.getenv('AUTH_RETRY_BASE_DELAY_MIN'))
            for category in config:
                config[category]['base_delay_min'] = base_delay_min
        
        if os.getenv('AUTH_RETRY_BASE_DELAY_MAX'):
            base_delay_max = float(os.getenv('AUTH_RETRY_BASE_DELAY_MAX'))
            for category in config:
                config[category]['base_delay_max'] = base_delay_max
        
        if os.getenv('AUTH_RETRY_EXPONENTIAL_MULTIPLIER'):
            exponential_multiplier = float(os.getenv('AUTH_RETRY_EXPONENTIAL_MULTIPLIER'))
            for category in config:
                config[category]['exponential_multiplier'] = exponential_multiplier
        
        return cls(config)

# Global configuration instance
auth_retry_config = AuthRetryConfig.from_env()
