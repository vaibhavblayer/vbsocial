"""YouTube community post command.

NOTE: The YouTube Data API does not currently support creating community posts.
This is a placeholder for when/if Google adds this functionality.
Community posts can only be created through the YouTube Studio web interface.
"""

import click


@click.command()
@click.option("-m", "--message", required=True, help="Post message")
@click.option("-i", "--image", type=click.Path(exists=True), help="Image to attach")
def post(message: str, image: str | None) -> None:
    """Create a YouTube community post.
    
    NOTE: YouTube Data API does not support community posts yet.
    This command will guide you to use YouTube Studio instead.
    """
    click.echo("⚠️  YouTube Data API does not support community posts.")
    click.echo("")
    click.echo("To create a community post, use YouTube Studio:")
    click.echo("  1. Go to https://studio.youtube.com")
    click.echo("  2. Click 'Create' → 'Create post'")
    click.echo("  3. Add your content")
    click.echo("")
    click.echo("Your message:")
    click.echo(f"  {message}")
    if image:
        click.echo(f"  Image: {image}")
    click.echo("")
    click.echo("Opening YouTube Studio...")
    
    import webbrowser
    webbrowser.open("https://studio.youtube.com/channel/UC/community/tab-community")
