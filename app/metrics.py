"""Thread-safe in-process metrics: counters, latency percentiles, quality signals."""
import math
import threading
import time
from collections import Counter, deque


def percentile(values, pct: float) -> float:
    """Nearest-rank percentile. Returns 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(len(ordered) * pct / 100))
    return float(ordered[rank - 1])


class Metrics:
    def __init__(self, window: int = 1000):
        self._lock = threading.Lock()
        self._started = time.time()
        self._latencies = deque(maxlen=window)
        self.requests = 0
        self.errors = 0
        self.llm_failures = 0
        self.tests_valid = 0
        self.tests_invalid = 0
        self.statuses = Counter()
        self.severities = Counter()

    def record_request(self, latency_ms: float, status: int) -> None:
        with self._lock:
            self.requests += 1
            self._latencies.append(latency_ms)
            self.statuses[str(status)] += 1
            if status >= 400:
                self.errors += 1

    def record_llm_failure(self) -> None:
        with self._lock:
            self.llm_failures += 1

    def record_issues(self, severities) -> None:
        with self._lock:
            self.severities.update(severities)

    def record_test_check(self, valid: bool) -> None:
        with self._lock:
            if valid:
                self.tests_valid += 1
            else:
                self.tests_invalid += 1

    def snapshot(self) -> dict:
        with self._lock:
            lat = list(self._latencies)
            checked = self.tests_valid + self.tests_invalid
            return {
                "uptime_s": round(time.time() - self._started, 1),
                "requests": self.requests,
                "errors": self.errors,
                "error_rate": round(self.errors / self.requests, 4) if self.requests else 0.0,
                "llm_failures": self.llm_failures,
                "latency_ms": {
                    "p50": round(percentile(lat, 50), 1),
                    "p95": round(percentile(lat, 95), 1),
                    "max": round(max(lat), 1) if lat else 0.0,
                },
                "recent_latencies_ms": [round(x, 1) for x in lat[-30:]],
                "statuses": dict(self.statuses),
                "issues_by_severity": dict(self.severities),
                "ai_tests": {
                    "valid": self.tests_valid,
                    "invalid": self.tests_invalid,
                    "valid_rate": round(self.tests_valid / checked, 4) if checked else None,
                },
            }
