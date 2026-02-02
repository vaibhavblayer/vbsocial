import click

# Re-use existing helper functions from the individual modules so we don't
# duplicate Facebook Graph logic.
from .commands.photo import post_photo, post_carousel  # feed
from .commands.video import post_video  # feed
from .commands.story_photo import post_story_photo  # story
from .commands.story_video import post_story_video  # story


@click.command(name="post")
@click.option("--feed", "-f", is_flag=True, help="Post to feed (default)")
@click.option("--story", "-s", is_flag=True, help="Post to story")
@click.option(
    "--image",
    "-i",
    multiple=True,
    type=click.Path(exists=True),
    help="Path to image file(s). Provide multiple -i for carousel (feed only).",
)
@click.option("--video", "-v", type=click.Path(exists=True), help="Path to video file")
@click.option("--caption", "-c", help="Caption for the post")
def post(feed, story, image, video, caption):
    """Unified Instagram post command.

    Examples:
        # Single photo to feed
        vbsocial instagram post -i pic.jpg -c "Hello"

        # Carousel to feed
        vbsocial instagram post -i pic1.jpg -i pic2.jpg -c "Carousel"

        # Video to feed
        vbsocial instagram post -v clip.mp4 -c "Watch this"

        # Story image
        vbsocial instagram post -s -i story.jpg

        # Story video
        vbsocial instagram post -s -v story.mp4
    """

    # Validate mutually exclusive flags
    if feed and story:
        raise click.ClickException("Choose either --feed or --story, not both")

    # Default to feed if neither flag passed
    target_story = story and not feed

    if image and video:
        raise click.ClickException(
            "Provide either image(s) or a video, not both")

    if not image and not video:
        raise click.ClickException("Please supply --image/-i or --video/-v")

    if target_story:
        # Story posting
        if video:
            post_story_video(video)
        else:
            # Instagram stories allow only one image
            if len(image) > 1:
                click.echo("Stories support only one image – using the first.")
            post_story_photo(image[0])
    else:
        # Feed posting
        if video:
            post_video(video, caption)
        else:
            images = list(image)
            if len(images) == 1:
                post_photo(images[0], caption)
            else:
                post_carousel(images, caption)
