"""
Lightweight In-Memory Sliding Window Rate Limiter
-------------------------------------------------
Provides endpoint-level abuse defense against brute-force attacks and denial-of-service,
without introducing heavy external cache dependencies (Redis/Memcached).

Features:
- Thread-safe sliding window tracking using collections.deque
- Automatic pruning of stale timestamps
- Bypass in testing environments (TESTING=True) for lightning-fast unit tests
- Custom client identification (Remote IP or Authenticated User ID)
- Structured HTTP 429 response generation with 'Retry-After' header
"""

from collections import defaultdict, deque
from datetime import datetime, timezone
from functools import wraps
import logging
import threading
import time
from typing import Callable, Optional
from flask import request, current_app, jsonify, make_response
from app.utils.errors import create_error_response, RateLimitExceededError

logger = logging.getLogger("fraud_detection.limiter")


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        # Mapping: key -> deque of Unix epoch timestamps
        self._requests = defaultdict(deque)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Evaluates whether a request with the given key is allowed.

        Returns:
            (is_allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._requests[key]

            # Prune records older than current sliding window
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            current_count = len(timestamps)
            if current_count < max_requests:
                timestamps.append(now)
                remaining = max_requests - (current_count + 1)
                return True, remaining, 0

            # Rate limit reached: calculate cooldown duration
            oldest_timestamp = timestamps[0]
            retry_after = max(1, int(oldest_timestamp + window_seconds - now))
            return False, 0, retry_after

    def reset(self):
        """Clears all tracked client rates (useful for testing)."""
        with self._lock:
            self._requests.clear()


# Global in-memory rate limiter singleton
limiter = InMemoryRateLimiter()


def get_client_identifier() -> str:
    """
    Extracts the unique client fingerprint (IP address or session user ID).
    Inspects standard X-Forwarded-For reverse proxy headers safely.
    """
    from app.utils.auth import get_current_user
    user = get_current_user()
    if user and user.id:
        return f"user:{user.id}"

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in comma-separated list represents the original client
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.remote_addr or "127.0.0.1"

    return f"ip:{client_ip}"


def rate_limit(max_requests: int = 60, window_seconds: int = 60, key_prefix: str = "default"):
    """
    Decorator that applies rate limiting to sensitive endpoints.

    Args:
        max_requests: Maximum requests allowed in the time window.
        window_seconds: Window length in seconds.
        key_prefix: Unique namespace for the endpoint.
    """
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Bypass rate limiter in testing environment
            if current_app.config.get("TESTING", False) or not current_app.config.get("RATE_LIMITING_ENABLED", True):
                return f(*args, **kwargs)

            client_id = get_client_identifier()
            rate_key = f"{key_prefix}:{client_id}"

            allowed, remaining, retry_after = limiter.is_allowed(
                rate_key,
                max_requests=max_requests,
                window_seconds=window_seconds
            )

            if not allowed:
                logger.warning(
                    "Rate limit exceeded for %s on %s (limit: %d/%ds, retry_after: %ds)",
                    rate_key, request.path, max_requests, window_seconds, retry_after
                )

                # Generate centralized 429 response
                resp, status_code = create_error_response(
                    status_code=429,
                    error_type="TooManyRequests",
                    message=f"Too many requests. Please slow down and retry in {retry_after} seconds.",
                    details={"retry_after_seconds": retry_after, "limit": max_requests, "window_seconds": window_seconds}
                )
                response = make_response(resp, status_code)
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))
                return response

            response = make_response(f(*args, **kwargs))
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        return decorated_function
    return decorator
