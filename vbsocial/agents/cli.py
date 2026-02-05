"""CLI commands for agent configuration."""

import click

from .config import (
    load_config,
    save_config,
    get_agent_config,
    set_agent_config,
    init_default_config,
    CONFIG_FILE,
    DEFAULTS,
)
from .debug import reset_debug_cache


@click.group(name="config")
def config_cli():
    """Configure agent models."""
    pass


@config_cli.command(name="show")
def show_config():
    """Show current agent configuration."""
    config = load_config()
    
    click.echo(f"\n📁 Config file: {CONFIG_FILE}")
    click.echo("\n🤖 Agent Configuration:")
    click.echo("=" * 40)
    
    # Show debug mode
    debug_enabled = config.get("debug", False)
    click.echo(f"\n🐛 Debug mode: {'ON' if debug_enabled else 'OFF'}")
    click.echo("   (set VBSOCIAL_DEBUG=1 or use 'vbsocial config debug on')")
    
    for agent_type in ["caption", "content_planner", "datamodel"]:
        cfg = get_agent_config(agent_type)
        click.echo(f"\n{agent_type}:")
        click.echo(f"  model: {cfg['model']}")
        click.echo(f"  reasoning: {cfg['reasoning']}")


@config_cli.command(name="set")
@click.argument("agent_type", type=click.Choice(["caption", "content_planner", "datamodel"]))
@click.option("--model", "-m", help="Model name (e.g., gpt-5-mini, gpt-5.1-codex-mini)")
@click.option("--reasoning", "-r", type=click.Choice(["low", "medium", "high"]), help="Reasoning effort")
def set_config(agent_type: str, model: str | None, reasoning: str | None):
    """Set model and reasoning for an agent.
    
    Example:
        vbsocial config set caption --model gpt-5-mini --reasoning low
        vbsocial config set datamodel -m gpt-5.1-codex-mini -r high
    """
    if not model and not reasoning:
        raise click.ClickException("Provide --model and/or --reasoning")
    
    set_agent_config(agent_type, model=model, reasoning=reasoning)
    
    cfg = get_agent_config(agent_type)
    click.echo(f"✓ Updated {agent_type}:")
    click.echo(f"  model: {cfg['model']}")
    click.echo(f"  reasoning: {cfg['reasoning']}")


@config_cli.command(name="debug")
@click.argument("state", type=click.Choice(["on", "off"]))
def set_debug(state: str):
    """Enable or disable debug mode.
    
    When enabled, logs all agent calls and transformations to stderr in YAML format.
    
    Example:
        vbsocial config debug on
        vbsocial config debug off
        
    Or use environment variable:
        VBSOCIAL_DEBUG=1 vbsocial add --code rust
    """
    config = load_config()
    config["debug"] = (state == "on")
    save_config(config)
    reset_debug_cache()
    
    if state == "on":
        click.echo("🐛 Debug mode: ON")
        click.echo("   Agent calls and transformations will be logged to stderr")
    else:
        click.echo("🐛 Debug mode: OFF")


@config_cli.command(name="init")
def init_config():
    """Initialize config file with defaults."""
    path = init_default_config()
    click.echo(f"✓ Config initialized: {path}")
    
    click.echo("\nDefault settings:")
    for agent_type, cfg in DEFAULTS.items():
        click.echo(f"  {agent_type}: model={cfg['model']}, reasoning={cfg['reasoning']}")


@config_cli.command(name="edit")
def edit_config():
    """Open config file in editor."""
    import subprocess
    import os
    
    init_default_config()
    
    editor = os.environ.get("EDITOR", "nano")
    click.echo(f"Opening {CONFIG_FILE} in {editor}...")
    subprocess.run([editor, str(CONFIG_FILE)])
