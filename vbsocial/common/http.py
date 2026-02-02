"""Shared HTTP utilities with retry logic and error handling."""

from __future__ import annotations

import time
from typing import Any, Callable
from functools import wraps

import click
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Default timeout for all requests (connect, read)
DEFAULT_TIMEOUT = (10, 60)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


def create_session() -> requests.Session:
    """Create a requests session with retry logic and connection pooling."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
        raise_on_status=False,
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


# Global session for reuse
_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Get or create the global requests session."""
    global _session
    if _session is None:
        _session = create_session()
    return _session


def handle_response(response: requests.Response, context: str = "API call") -> dict[str, Any]:
    """Handle API response with consistent error handling."""
    try:
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.exceptions.HTTPError:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message") or error_data.get("message") or str(error_data)
        except (ValueError, KeyError):
            error_msg = response.text or f"HTTP {response.status_code}"
        raise click.ClickException(f"{context} failed: {error_msg}")


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (requests.exceptions.RequestException,),
) -> Callable:
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator
