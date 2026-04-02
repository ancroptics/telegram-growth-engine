"""Per-user rate limiting."""
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls: int = 5, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self._calls = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        now = time.time()
        calls = self._calls[user_id]
        calls[:] = [t for t in calls if now - t < self.period]
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True

rate_limiter = RateLimiter()
