"""Agent configuration management.

Config file: ~/.config/vbsocial/config.yaml

Example config:
```yaml
agents:
  caption:
    model: gpt-5-mini
    reasoning: low
  content_planner:
    model: gpt-5-mini
    reasoning: medium
  datamodel:
    model: gpt-5.1-codex-mini
    reasoning: high
```
"""

from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path.home() / ".config" / "vbsocial"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Default settings per agent type
DEFAULTS = {
    "caption": {
        "model": "gpt-5-mini",
        "reasoning": "low",
    },
    "content_planner": {
        "model": "gpt-5-mini",
        "reasoning": "medium",
    },
    "datamodel": {
        "model": "gpt-5.1-codex-mini",
        "reasoning": "high",
    },
}


def load_config() -> dict[str, Any]:
    """Load config from file, creating defaults if not exists."""
    if not CONFIG_FILE.exists():
        return {"agents": DEFAULTS.copy()}
    
    try:
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception:
        return {"agents": DEFAULTS.copy()}


def save_config(config: dict[str, Any]) -> None:
    """Save config to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_agent_config(agent_type: str) -> dict[str, str]:
    """Get model and reasoning config for an agent type.
    
    Args:
        agent_type: One of 'caption', 'content_planner', 'datamodel'
        
    Returns:
        Dict with 'model' and 'reasoning' keys
    """
    config = load_config()
    agents = config.get("agents", {})
    
    # Merge defaults with user config
    defaults = DEFAULTS.get(agent_type, {"model": "gpt-5-mini", "reasoning": "medium"})
    user_config = agents.get(agent_type, {})
    
    return {
        "model": user_config.get("model", defaults["model"]),
        "reasoning": user_config.get("reasoning", defaults.get("reasoning", "medium")),
    }


def set_agent_config(agent_type: str, model: str | None = None, reasoning: str | None = None) -> None:
    """Set model and reasoning for an agent type.
    
    Args:
        agent_type: One of 'caption', 'content_planner', 'datamodel'
        model: Model name (optional)
        reasoning: Reasoning effort: low, medium, high (optional)
    """
    config = load_config()
    if "agents" not in config:
        config["agents"] = {}
    
    if agent_type not in config["agents"]:
        config["agents"][agent_type] = DEFAULTS.get(agent_type, {}).copy()
    
    if model:
        config["agents"][agent_type]["model"] = model
    if reasoning:
        config["agents"][agent_type]["reasoning"] = reasoning
    
    save_config(config)


def init_default_config() -> Path:
    """Initialize config file with defaults if not exists."""
    if not CONFIG_FILE.exists():
        save_config({"agents": DEFAULTS.copy()})
    return CONFIG_FILE
