"""Debug mode for agent calls and transformations.

Enable debug mode:
- Set environment variable: VBSOCIAL_DEBUG=1
- Or in config: debug: true

Logs all agent calls and data transformations to stdout in YAML format.
"""

import functools
import json
import os
import sys
from datetime import datetime
from typing import Any, Callable

import yaml


# Check if debug mode is enabled
def is_debug_enabled() -> bool:
    """Check if debug mode is enabled via env var or config."""
    if os.environ.get("VBSOCIAL_DEBUG", "").lower() in ("1", "true", "yes"):
        return True
    
    try:
        from .config import load_config
        config = load_config()
        return config.get("debug", False)
    except Exception:
        return False


# Global debug state
_DEBUG = None


def debug_enabled() -> bool:
    """Cached check for debug mode."""
    global _DEBUG
    if _DEBUG is None:
        _DEBUG = is_debug_enabled()
    return _DEBUG


def reset_debug_cache() -> None:
    """Reset debug cache (for testing)."""
    global _DEBUG
    _DEBUG = None


def log_debug(event_type: str, data: dict[str, Any]) -> None:
    """Log debug event to stdout in YAML format.
    
    Args:
        event_type: Type of event (agent_call, agent_result, transform, etc.)
        data: Event data to log
    """
    if not debug_enabled():
        return
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **data,
    }
    
    # Print separator and YAML
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"[DEBUG] {event_type.upper()}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    print(yaml.dump(event, default_flow_style=False, allow_unicode=True, width=120), file=sys.stderr)


def log_agent_call(agent_name: str, input_text: str, **kwargs: Any) -> None:
    """Log an agent call."""
    log_debug("agent_call", {
        "agent": agent_name,
        "input": input_text[:500] + "..." if len(input_text) > 500 else input_text,
        "input_length": len(input_text),
        "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
    })


def log_agent_result(agent_name: str, result: str, duration_ms: float | None = None) -> None:
    """Log an agent result."""
    log_debug("agent_result", {
        "agent": agent_name,
        "output": result[:1000] + "..." if len(result) > 1000 else result,
        "output_length": len(result),
        "duration_ms": duration_ms,
    })


def log_transform(func_name: str, input_data: Any, output_data: Any, **kwargs: Any) -> None:
    """Log a data transformation."""
    def truncate(data: Any, max_len: int = 500) -> Any:
        if isinstance(data, str):
            return data[:max_len] + "..." if len(data) > max_len else data
        elif isinstance(data, list):
            return [truncate(item, max_len // 2) for item in data[:5]]
        elif isinstance(data, dict):
            return {k: truncate(v, max_len // 2) for k, v in list(data.items())[:5]}
        return str(data)[:max_len]
    
    log_debug("transform", {
        "function": func_name,
        "input": truncate(input_data),
        "output": truncate(output_data),
        **kwargs,
    })


def debug_agent(func: Callable) -> Callable:
    """Decorator to log agent function calls and results."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not debug_enabled():
            return func(*args, **kwargs)
        
        import time
        
        # Extract agent name from function or first arg
        agent_name = func.__name__
        
        # Log call
        input_text = ""
        if args:
            input_text = str(args[0])[:500] if args[0] else ""
        log_agent_call(agent_name, input_text, **kwargs)
        
        # Execute
        start = time.time()
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start) * 1000
        
        # Log result
        log_agent_result(agent_name, str(result) if result else "", duration_ms)
        
        return result
    
    return wrapper


def debug_transform(func: Callable) -> Callable:
    """Decorator to log transformation functions."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not debug_enabled():
            return func(*args, **kwargs)
        
        result = func(*args, **kwargs)
        
        # Log transformation
        input_data = args[0] if args else kwargs
        log_transform(func.__name__, input_data, result)
        
        return result
    
    return wrapper
