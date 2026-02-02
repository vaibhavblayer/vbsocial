"""YouTube CLI commands."""

import click

from ..common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        # Upload commands
        "upload": "vbsocial.youtube.upload:upload",
        "shorts": "vbsocial.youtube.shorts:shorts",
        "post": "vbsocial.youtube.community:post",
        # Video management
        "info": "vbsocial.youtube.info:info",
        "edit": "vbsocial.youtube.edit:edit",
        "update": "vbsocial.youtube.update:update",
        # Analytics
        "stats": "vbsocial.youtube.analytics:stats",
        "videos": "vbsocial.youtube.analytics:videos",
        # Utilities
        "sync": "vbsocial.youtube.sync:sync",
    },
)
def youtube():
    """YouTube CLI commands."""
    pass
