"""LinkedIn CLI commands."""

import click

from ..common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        "post": "vbsocial.linkedin.post:post",
    },
)
def linkedin():
    """LinkedIn CLI commands."""
    pass
