"""Facebook CLI commands."""

import click

from ..common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        "post": "vbsocial.facebook.post:post",
        "configure": "vbsocial.facebook.commands.configure:configure",
    },
)
def facebook():
    """Facebook CLI commands."""
    pass
