"""Instagram CLI commands."""

import click

from ..common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        "post": "vbsocial.instagram.post:post",
        "configure": "vbsocial.instagram.commands.configure:configure",
        "refresh": "vbsocial.instagram.commands.refresh:refresh",
    },
)
def instagram():
    """Instagram CLI commands."""
    pass
