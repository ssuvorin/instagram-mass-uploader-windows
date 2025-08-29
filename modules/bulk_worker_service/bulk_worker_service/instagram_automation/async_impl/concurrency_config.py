"""
Concurrency config scaffold (not enforced yet).
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Concurrency:
    max_parallel_accounts: int = 4
    per_account_semaphore: int = 1

DEFAULT_CONCURRENCY = Concurrency()

__all__ = ["Concurrency", "DEFAULT_CONCURRENCY"]
