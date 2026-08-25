"""Small in-process guard against accidental duplicate AI requests."""

import time
from typing import Dict, Tuple


class AIRequestGuard:
    """Throttle identical explicit requests without persisting AI responses."""

    def __init__(self, cooldown_seconds: float = 10.0):
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._last_requests: Dict[Tuple[str, str, str, str], float] = {}

    def allow(self, flow: str, scope_id: str, task: str, deterministic_hash: str) -> bool:
        now = time.monotonic()
        key = (flow, scope_id, task, deterministic_hash)
        last_request = self._last_requests.get(key)
        self._last_requests[key] = now
        self._prune(now)
        return last_request is None or now - last_request >= self.cooldown_seconds

    def _prune(self, now: float) -> None:
        expiry = now - max(self.cooldown_seconds, 60.0)
        stale_keys = [key for key, timestamp in self._last_requests.items() if timestamp < expiry]
        for key in stale_keys:
            self._last_requests.pop(key, None)
