"""
Concurrency config scaffold (not enforced yet).
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Concurrency:
    max_parallel_accounts: int = 5  # Maximum 5 accounts in parallel to avoid anti-fraud
    per_account_semaphore: int = 1
    account_start_delay: float = 2.0  # Delay between account starts (seconds)
    min_delay: float = 1.0  # Minimum delay between requests
    max_delay: float = 5.0  # Maximum delay between requests

DEFAULT_CONCURRENCY = Concurrency()

__all__ = ["Concurrency", "DEFAULT_CONCURRENCY"]
