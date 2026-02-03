"""Post to all platforms command."""

import webbrowser
from pathlib import Path

import click
import yaml

from ..facebook.commands.photo import post_photo as fb_post_photo, post_multiple_photos as fb_post_multiple
from ..instagram.commands.photo import post_photo as ig_post_photo, post_carousel as ig_post_carousel
from ..linkedin.linkedinpost import LinkedInPost
from ..x.auth import create_oauth_session
from ..x.functions import upload_image, create_tweet


PLATFORMS = ["facebook", "instagram", "linkedin", "x", "youtube"]


def load_post_config(post_path: Path) -> dict:
    """Load post.yaml from post folder."""
    yaml_path = post_path / "post.yaml"
    if not yaml_path.exists():
        raise click.ClickException(f"post.yaml not found in {post_path}")
    
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def get_images(post_path: Path) -> list[Path]:
    """Get sorted list of images from images/ folder."""
    images_dir = post_path / "images"
    if not images_dir.exists():
        raise click.ClickException(f"images/ folder not found in {post_path}")
    
    images = sorted(images_dir.glob("*.png")) + sorted(images_dir.glob("*.jpg"))
    if not images:
        raise click.ClickException(f"No images found in {images_dir}")
    
    return images


def post_to_facebook(images: list[Path], caption: str) -> None:
    """Post to Facebook (supports multiple images)."""
    click.echo("\n📘 Posting to Facebook...")
    if len(images) == 1:
        fb_post_photo(str(images[0]), caption)
    else:
        fb_post_multiple([str(img) for img in images], caption)
    click.echo("✓ Posted to Facebook")


def post_to_instagram(images: list[Path], caption: str) -> None:
    """Post to Instagram."""
    click.echo("\n📸 Posting to Instagram...")
    if len(images) == 1:
        ig_post_photo(str(images[0]), caption)
    else:
        ig_post_carousel([str(img) for img in images], caption)


def post_to_linkedin(images: list[Path], caption: str) -> None:
    """Post to LinkedIn (supports multiple images via MultiImage API)."""
    import os
    click.echo("\n💼 Posting to LinkedIn...")
    
    org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
    post = LinkedInPost(organization_id=org_id)
    
    if images:
        post.create_post_with_images(caption, [str(img) for img in images])
    else:
        post.create_text_post(caption)
    
    click.echo("✓ Posted to LinkedIn")


def post_to_x(images: list[Path], caption: str) -> None:
    """Post to X (Twitter)."""
    click.echo("\n🐦 Posting to X...")
    
    access_token = create_oauth_session()
    
    media_ids = []
    for img in images[:4]:  # X allows max 4 images
        click.echo(f"  Uploading {img.name}...")
        media_id = upload_image(str(img), access_token)
        media_ids.append(media_id)
    
    tweet_id = create_tweet(caption, media_ids if media_ids else None)
    click.echo(f"✓ Posted to X (tweet id {tweet_id})")


def post_to_youtube(images: list[Path], caption: str) -> None:
    """Open YouTube Studio for community post."""
    click.echo("\n▶️  YouTube Community Post...")
    click.echo(f"  Caption: {caption[:100]}..." if len(caption) > 100 else f"  Caption: {caption}")
    click.echo("  Opening YouTube Studio in browser...")
    webbrowser.open("https://studio.youtube.com")
    click.echo("  ⚠️  Please create community post manually")


@click.command(name="post-all")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--skip", "-s", multiple=True, type=click.Choice(PLATFORMS), help="Platforms to skip")
@click.option("--dry-run", is_flag=True, help="Show what would be posted without posting")
def post_all(post_path: Path, skip: tuple, dry_run: bool) -> None:
    """Post to all platforms from a post folder.
    
    Reads images from <post_path>/images/ and captions from post.yaml,
    then posts to Facebook, Instagram, LinkedIn, X, and YouTube.
    
    Example:
        vbsocial post-all ~/social_posts/2026_02_03_my_topic
        vbsocial post-all ~/social_posts/2026_02_03_my_topic --skip youtube --skip linkedin
    """
    config = load_post_config(post_path)
    images = get_images(post_path)
    captions = config.get("captions", {})
    
    click.echo(f"📁 Post: {config.get('title', 'Untitled')}")
    click.echo(f"📅 Date: {config.get('date', 'Unknown')}")
    click.echo(f"🖼️  Images: {len(images)}")
    
    if dry_run:
        click.echo("\n🔍 DRY RUN - Would post to:")
        for platform in PLATFORMS:
            if platform in skip:
                click.echo(f"  ⏭️  {platform}: SKIPPED")
            else:
                caption = captions.get(platform, "")
                preview = caption[:50] + "..." if len(caption) > 50 else caption
                click.echo(f"  ✓ {platform}: \"{preview}\"")
        return
    
    skip_set = set(skip)
    
    if "facebook" not in skip_set:
        try:
            post_to_facebook(images, captions.get("facebook", ""))
        except Exception as e:
            click.echo(f"  ❌ Facebook failed: {e}")
    
    if "instagram" not in skip_set:
        try:
            post_to_instagram(images, captions.get("instagram", ""))
        except Exception as e:
            click.echo(f"  ❌ Instagram failed: {e}")
    
    if "linkedin" not in skip_set:
        try:
            post_to_linkedin(images, captions.get("linkedin", ""))
        except Exception as e:
            click.echo(f"  ❌ LinkedIn failed: {e}")
    
    if "x" not in skip_set:
        try:
            post_to_x(images, captions.get("x", ""))
        except Exception as e:
            click.echo(f"  ❌ X failed: {e}")
    
    if "youtube" not in skip_set:
        post_to_youtube(images, captions.get("youtube", ""))
    
    click.echo("\n✅ Done!")
