"""Per-user rate limiting."""
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls: int = 30, period: float = 60.0):
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

    def cleanup(self):
        """Remove stale entries to prevent memory leak."""
        now = time.time()
        stale = [uid for uid, calls in self._calls.items() if not calls or now - calls[-1] > self.period * 2]
        for uid in stale:
            del self._calls[uid]

rate_limiter = RateLimiter()
