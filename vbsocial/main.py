"""Main CLI entry point with lazy loading for fast startup."""

import click

from .common.cli import LazyGroup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(
    cls=LazyGroup,
    context_settings=CONTEXT_SETTINGS,
    lazy_subcommands={
        "facebook": "vbsocial.facebook.facebook:facebook",
        "instagram": "vbsocial.instagram.instagram:instagram",
        "linkedin": "vbsocial.linkedin.linkedin:linkedin",
        "x": "vbsocial.x.x:x",
        "youtube": "vbsocial.youtube.youtube:youtube",
        "create-post": "vbsocial.post.create:create_post",
        "post-all": "vbsocial.post.post_all:post_all",
        "stats": "vbsocial.stats.all:stats",
        "generate": "vbsocial.generate.from_idea:generate",
        "from-image": "vbsocial.generate.from_image:from_image",
        "datamodel": "vbsocial.generate.datamodel_cli:datamodel",
        "config": "vbsocial.agents.cli:config_cli",
        "render": "vbsocial.generate.render:render_cmd",
        "add": "vbsocial.generate.add:add_component",
        "assemble": "vbsocial.generate.assemble:assemble",
    },
)
def main():
    """vbsocial - Post to social media from the command line."""
    pass


if __name__ == "__main__":
    main()
