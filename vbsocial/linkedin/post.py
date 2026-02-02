import click
from .linkedinpost import LinkedInPost
import os


@click.command()
@click.option("--message", "-m", help="Message to post", required=True)
@click.option("--url", "-u", help="URL to post")
@click.option("--image", "-i", help="Image file to post")
@click.option("--video", "-v", help="Video file to post")
@click.option(
    "--org-id",
    "-o",
    help="LinkedIn Organization (Company Page) ID to post as. If omitted, the CLI looks for the LINKEDIN_ORGANIZATION_ID environment variable.",
)
@click.option(
    "--personal",
    "-p",
    is_flag=True,
    default=False,
    help="Post to your personal profile even if an organization ID is configured.",
)
def post(message, url, image, video, org_id, personal):
    """Post content to LinkedIn"""
    if personal:
        # Explicitly chosen to post on personal profile
        org_id = None
    else:
        # Default behaviour is to post on an organisation page. Source the ID
        # from CLI first, then environment variable.
        if not org_id:
            org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")

        if not org_id:
            raise click.ClickException(
                "No organisation ID supplied. Provide one with --org-id/-o or set the LINKEDIN_ORGANIZATION_ID environment variable. Use --personal to post on your own profile instead."
            )

    post = LinkedInPost(organization_id=org_id)

    try:
        if video:
            result = post.create_post_with_video(message, video)
            click.echo("✓ Successfully posted video to LinkedIn")
        elif image:
            result = post.create_post_with_image(message, image)
            click.echo("✓ Successfully posted message with image to LinkedIn")
        elif url:
            result = post.create_post_with_url(message, url)
            click.echo("✓ Successfully posted message with URL to LinkedIn")
        else:
            result = post.create_text_post(message)
            click.echo("✓ Successfully posted message to LinkedIn")

        post_id = result.get('id', '').split(':')[-1]
        if post_id:
            click.echo(f"Post ID: {post_id}")

        return result
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")
