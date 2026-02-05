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


def post_to_facebook(images: list[Path], caption: str) -> str | None:
    """Post to Facebook (supports multiple images). Returns post ID."""
    click.echo("\n📘 Posting to Facebook...")
    if len(images) == 1:
        result = fb_post_photo(str(images[0]), caption)
    else:
        result = fb_post_multiple([str(img) for img in images], caption)
    click.echo("✓ Posted to Facebook")
    # Extract post ID from result if available
    if isinstance(result, dict):
        return result.get("id") or result.get("post_id")
    return None


def post_to_instagram(images: list[Path], caption: str) -> str | None:
    """Post to Instagram. Returns media ID."""
    click.echo("\n📸 Posting to Instagram...")
    if len(images) == 1:
        result = ig_post_photo(str(images[0]), caption)
    else:
        result = ig_post_carousel([str(img) for img in images], caption)
    # Extract media ID
    if isinstance(result, dict):
        return result.get("id")
    return None


def post_to_linkedin(images: list[Path], caption: str) -> str | None:
    """Post to LinkedIn (supports multiple images via MultiImage API). Returns post ID."""
    import os
    click.echo("\n💼 Posting to LinkedIn...")
    
    org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
    post = LinkedInPost(organization_id=org_id)
    
    if images:
        result = post.create_post_with_images(caption, [str(img) for img in images])
    else:
        result = post.create_text_post(caption)
    
    click.echo("✓ Posted to LinkedIn")
    if isinstance(result, dict):
        return result.get("id")
    return None


def post_to_x(images: list[Path], caption: str) -> str | None:
    """Post to X (Twitter). Returns tweet ID."""
    click.echo("\n🐦 Posting to X...")
    
    access_token = create_oauth_session()
    
    media_ids = []
    for img in images[:4]:  # X allows max 4 images
        click.echo(f"  Uploading {img.name}...")
        media_id = upload_image(str(img), access_token)
        media_ids.append(media_id)
    
    tweet_id = create_tweet(caption, media_ids if media_ids else None)
    click.echo(f"✓ Posted to X (tweet id {tweet_id})")
    return tweet_id


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
    
    Post IDs are saved to post.yaml for later deletion if needed.
    
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
    post_ids = config.get("post_ids", {})
    
    if "facebook" not in skip_set:
        try:
            post_id = post_to_facebook(images, captions.get("facebook", ""))
            if post_id:
                post_ids["facebook"] = post_id
        except Exception as e:
            click.echo(f"  ❌ Facebook failed: {e}")
    
    if "instagram" not in skip_set:
        try:
            post_id = post_to_instagram(images, captions.get("instagram", ""))
            if post_id:
                post_ids["instagram"] = post_id
        except Exception as e:
            click.echo(f"  ❌ Instagram failed: {e}")
    
    if "linkedin" not in skip_set:
        try:
            post_id = post_to_linkedin(images, captions.get("linkedin", ""))
            if post_id:
                post_ids["linkedin"] = post_id
        except Exception as e:
            click.echo(f"  ❌ LinkedIn failed: {e}")
    
    if "x" not in skip_set:
        try:
            post_id = post_to_x(images, captions.get("x", ""))
            if post_id:
                post_ids["x"] = post_id
        except Exception as e:
            click.echo(f"  ❌ X failed: {e}")
    
    if "youtube" not in skip_set:
        post_to_youtube(images, captions.get("youtube", ""))
    
    # Save post IDs to post.yaml
    if post_ids:
        config["post_ids"] = post_ids
        yaml_path = post_path / "post.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        click.echo(f"\n📝 Saved post IDs to post.yaml")
    
    click.echo("\n✅ Done!")


# ---------------------------------------------------------------------------
# Delete functions
# ---------------------------------------------------------------------------


def delete_from_facebook(post_id: str) -> bool:
    """Delete a post from Facebook."""
    from ..facebook.auth import get_access_token, API_VERSION
    from ..common.http import get_session, DEFAULT_TIMEOUT
    
    click.echo(f"\n📘 Deleting from Facebook (ID: {post_id})...")
    
    session = get_session()
    token = get_access_token()
    
    resp = session.delete(
        f"https://graph.facebook.com/{API_VERSION}/{post_id}",
        params={"access_token": token},
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code == 200:
        click.echo("  ✓ Deleted from Facebook")
        return True
    else:
        click.echo(f"  ❌ Failed: {resp.text}")
        return False


def delete_from_instagram(media_id: str) -> bool:
    """Delete a post from Instagram.
    
    Note: Instagram Graph API doesn't support deleting media directly.
    Users must delete from the app.
    """
    click.echo(f"\n📸 Instagram (ID: {media_id})...")
    click.echo("  ⚠️  Instagram API doesn't support deletion.")
    click.echo("  Please delete manually from the Instagram app.")
    return False


def delete_from_linkedin(post_id: str) -> bool:
    """Delete a post from LinkedIn."""
    from ..linkedin.auth import create_oauth_session
    from ..common.http import get_session, DEFAULT_TIMEOUT
    
    click.echo(f"\n💼 Deleting from LinkedIn (ID: {post_id})...")
    
    session = get_session()
    token = create_oauth_session()
    
    # Try UGC Posts API
    resp = session.delete(
        f"https://api.linkedin.com/v2/ugcPosts/{post_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code in (200, 204):
        click.echo("  ✓ Deleted from LinkedIn")
        return True
    
    # Try Posts API (REST)
    resp = session.delete(
        f"https://api.linkedin.com/rest/posts/{post_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202601",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code in (200, 204):
        click.echo("  ✓ Deleted from LinkedIn")
        return True
    else:
        click.echo(f"  ❌ Failed: {resp.text}")
        return False


def delete_from_x(tweet_id: str) -> bool:
    """Delete a tweet from X.
    
    Uses OAuth 2.0 with tweet.write scope (same as create_tweet).
    """
    from ..x.auth import create_oauth_session
    from ..x.config import API_BASE
    from ..common.http import get_session, DEFAULT_TIMEOUT
    
    click.echo(f"\n🐦 Deleting from X (ID: {tweet_id})...")
    
    session = get_session()
    access_token = create_oauth_session()
    
    resp = session.delete(
        f"{API_BASE}/tweets/{tweet_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("data", {}).get("deleted"):
            click.echo("  ✓ Deleted from X")
            return True
        else:
            click.echo(f"  ⚠️  Response: {data}")
            return False
    else:
        click.echo(f"  ❌ Failed: {resp.text}")
        return False


@click.command(name="delete-all")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--skip", "-s", multiple=True, type=click.Choice(PLATFORMS), help="Platforms to skip")
@click.option("--confirm", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
def delete_all(post_path: Path, skip: tuple, confirm: bool, dry_run: bool) -> None:
    """Delete posts from all platforms using saved post IDs.
    
    Reads post IDs from post.yaml (saved during post-all) and deletes
    from each platform.
    
    Note: Instagram doesn't support API deletion - must delete manually.
    
    Example:
        vbsocial delete-all ~/social_posts/2026_02_03_my_topic
        vbsocial delete-all ~/social_posts/2026_02_03_my_topic --dry-run  # preview
        vbsocial delete-all ~/social_posts/2026_02_03_my_topic -y  # skip confirmation
        vbsocial delete-all ~/social_posts/2026_02_03_my_topic --skip instagram
    """
    config = load_post_config(post_path)
    post_ids = config.get("post_ids", {})
    
    if not post_ids:
        raise click.ClickException(
            "No post IDs found in post.yaml.\n"
            "Post IDs are saved when using 'vbsocial post-all'."
        )
    
    click.echo(f"📁 Post: {config.get('title', 'Untitled')}")
    click.echo("\n🗑️  Posts to delete:")
    for platform, post_id in post_ids.items():
        if platform in skip:
            click.echo(f"  ⏭️  {platform}: SKIPPED")
        else:
            click.echo(f"  • {platform}: {post_id}")
    
    if dry_run:
        click.echo("\n🔍 DRY RUN - No posts will be deleted")
        click.echo("  Remove --dry-run to actually delete")
        return
    
    if not confirm:
        if not click.confirm("\n⚠️  Are you sure you want to delete these posts?"):
            click.echo("Cancelled.")
            return
    
    skip_set = set(skip)
    deleted = []
    
    if "facebook" in post_ids and "facebook" not in skip_set:
        if delete_from_facebook(post_ids["facebook"]):
            deleted.append("facebook")
    
    if "instagram" in post_ids and "instagram" not in skip_set:
        delete_from_instagram(post_ids["instagram"])
        # Don't add to deleted since it requires manual deletion
    
    if "linkedin" in post_ids and "linkedin" not in skip_set:
        if delete_from_linkedin(post_ids["linkedin"]):
            deleted.append("linkedin")
    
    if "x" in post_ids and "x" not in skip_set:
        if delete_from_x(post_ids["x"]):
            deleted.append("x")
    
    # Remove deleted post IDs from config
    if deleted:
        for platform in deleted:
            del post_ids[platform]
        
        if post_ids:
            config["post_ids"] = post_ids
        else:
            del config["post_ids"]
        
        yaml_path = post_path / "post.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        click.echo(f"\n📝 Updated post.yaml (removed deleted IDs)")
    
    click.echo("\n✅ Done!")
