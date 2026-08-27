"""
Simple cache-based rate limiter for Django views.

No DRF required — uses Django's cache framework.
"""

import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render


def rate_limit(
    key_prefix,
    max_requests=5,
    window_seconds=300,
    block_message="Too many attempts. Please try again later.",
    render_response=None,
):
    """Decorator that limits view access by IP address.

    Args:
        key_prefix: Cache key prefix (e.g. 'login', 'result_search')
        max_requests: Maximum allowed requests in the window
        window_seconds: Time window in seconds (default 5 minutes)
        block_message: Message shown when rate limit is exceeded
        render_response: Optional callable(request, message) for custom response.
                         If None, returns 429 JSON for AJAX or redirects with message.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # Get client IP (X-Forwarded-For for reverse proxies, else REMOTE_ADDR)
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            if not ip:
                ip = request.META.get("REMOTE_ADDR", "unknown")

            cache_key = f"ratelimit:{key_prefix}:{ip}"
            now = time.time()

            # Fetch existing request log: list of timestamps
            request_log = cache.get(cache_key, [])

            # Filter to only requests within the current window
            window_start = now - window_seconds
            request_log = [t for t in request_log if t > window_start]

            if len(request_log) >= max_requests:
                # Rate limit exceeded
                retry_after = int(request_log[0] + window_seconds - now) + 1

                if render_response:
                    return render_response(request, block_message)

                # For AJAX requests, return JSON
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"error": block_message, "retry_after": retry_after},
                        status=429,
                    )

                # For normal requests, add message and redirect back
                from django.contrib import messages
                from django.http import HttpResponseRedirect

                messages.error(request, block_message)
                return HttpResponseRedirect(request.path)

            # Record this request
            request_log.append(now)
            cache.set(cache_key, request_log, window_seconds)

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
