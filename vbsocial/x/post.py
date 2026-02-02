"""X (Twitter) post command."""

import click

from .auth import create_oauth_session
from .functions import upload_image, upload_video, create_tweet


@click.command(name="post")
@click.option("--message", "-m", default="", help="Message to post to X")
@click.option("--image", "-i", type=click.Path(exists=True), help="Image file to attach")
@click.option("--video", "-v", type=click.Path(exists=True), help="Video file to attach")
def post(message: str, image: str | None, video: str | None) -> None:
    """Post text, image, or video to X (Twitter)."""
    if image and video:
        raise click.ClickException("Please provide either an image or a video, not both")
    
    access_token = create_oauth_session()
    
    media_id = None
    if video:
        click.echo("Uploading video…")
        media_id = upload_video(video, access_token)
    elif image:
        click.echo("Uploading image…")
        media_id = upload_image(image, access_token)
    
    tweet_id = create_tweet(message, [media_id] if media_id else None)
    click.echo(f"✓ Successfully posted to X (tweet id {tweet_id})")
