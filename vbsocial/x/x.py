"""X (Twitter) CLI commands."""

import click

from ..common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        "post": "vbsocial.x.post:post",
    },
)
def x():
    """X (Twitter) CLI commands."""
    pass
