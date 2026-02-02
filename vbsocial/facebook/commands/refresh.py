"""Facebook token refresh command."""

import click

from ..auth import load_config, _refresh_token


@click.command()
def refresh() -> None:
    """Manually refresh the access token."""
    config = load_config()
    _refresh_token(config)
    click.echo("Token refreshed successfully!")
