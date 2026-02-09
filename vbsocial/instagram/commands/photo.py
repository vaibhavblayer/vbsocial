"""Instagram photo posting commands."""

from __future__ import annotations

import click

from ..auth import get_access_token, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


def _upload_to_fb_storage(photo_path: str, access_token: str, page_id: str) -> str:
    """Upload image to Facebook storage and get a URL."""
    session = get_session()
    
    upload_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/photos"
    
    with open(photo_path, "rb") as f:
        files = {"source": f}
        params = {
            "access_token": access_token,
            "published": "false",
        }
        
        response = session.post(upload_url, files=files, data=params, timeout=(10, 120))
        response.raise_for_status()
        photo_id = response.json().get("id")
    
    # Get the image URL
    photo_url = f"https://graph.facebook.com/{API_VERSION}/{photo_id}"
    url_response = session.get(
        photo_url,
        params={"fields": "images", "access_token": access_token},
        timeout=DEFAULT_TIMEOUT,
    )
    url_response.raise_for_status()
    
    images = url_response.json().get("images", [])
    if not images:
        raise click.ClickException("Could not get image URL")
    
    return images[0]["source"]


@with_retry(max_attempts=3, delay=1.0)
def post_photo(photo_path: str, caption: str | None) -> dict:
    """Post a photo to Instagram."""
    config = load_config()
    access_token = get_access_token()
    instagram_account_id = config["instagram_account_id"]
    page_id = config.get("page_id")
    
    if not page_id:
        raise click.ClickException(
            "Missing page_id in config. Please re-run 'vbsocial instagram configure'."
        )
    
    session = get_session()
    
    click.echo("Uploading image to get URL...")
    image_url = _upload_to_fb_storage(photo_path, access_token, page_id)
    click.echo("Image uploaded, URL obtained")
    
    # Create the media container
    container_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media"
    params = {
        "access_token": access_token,
        "image_url": image_url,
        "caption": caption or "",
        "media_type": "IMAGE",
    }
    
    click.echo("Creating media container...")
    container_response = session.post(container_url, data=params, timeout=DEFAULT_TIMEOUT)
    container_response.raise_for_status()
    
    creation_id = container_response.json().get("id")
    if not creation_id:
        raise click.ClickException(f"Error creating media: {container_response.text}")
    
    click.echo("Media container created, publishing...")
    
    # Publish the container
    publish_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media_publish"
    publish_params = {
        "access_token": access_token,
        "creation_id": creation_id,
    }
    
    publish_response = session.post(publish_url, data=publish_params, timeout=DEFAULT_TIMEOUT)
    publish_response.raise_for_status()
    
    click.echo("Photo posted successfully!")
    return publish_response.json()


@with_retry(max_attempts=2, delay=2.0)
def post_carousel(photo_paths: list[str], caption: str | None) -> dict:
    """Post up to 10 images as a carousel."""
    if len(photo_paths) > 10:
        raise click.ClickException("Instagram allows maximum 10 images in a carousel")
    
    config = load_config()
    access_token = get_access_token()
    instagram_account_id = config["instagram_account_id"]
    page_id = config.get("page_id")
    
    if not page_id:
        raise click.ClickException(
            "Missing page_id in config. Please re-run 'vbsocial instagram configure'."
        )
    
    session = get_session()
    container_ids: list[str] = []
    
    # Create child media containers
    for idx, path in enumerate(photo_paths, start=1):
        click.echo(f"Uploading image {idx}/{len(photo_paths)} to Facebook storage…")
        image_url = _upload_to_fb_storage(path, access_token, page_id)
        click.echo("Creating media container for carousel item…")
        
        container_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media"
        params = {
            "access_token": access_token,
            "image_url": image_url,
            "is_carousel_item": "true",
        }
        
        resp = session.post(container_url, data=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        
        creation_id = resp.json().get("id")
        if not creation_id:
            raise click.ClickException("Did not receive creation_id for child item")
        container_ids.append(creation_id)
    
    # Create parent carousel container
    click.echo("Creating parent carousel container…")
    parent_params = {
        "access_token": access_token,
        "children": ",".join(container_ids),
        "caption": caption or "",
        "media_type": "CAROUSEL",
    }
    
    parent_resp = session.post(
        f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media",
        data=parent_params,
        timeout=DEFAULT_TIMEOUT,
    )
    parent_resp.raise_for_status()
    
    parent_creation_id = parent_resp.json().get("id")
    if not parent_creation_id:
        raise click.ClickException("Did not receive creation_id for carousel parent")
    
    # Publish with retry and better error handling
    click.echo("Publishing carousel…")
    
    import time
    max_publish_attempts = 3
    for attempt in range(max_publish_attempts):
        publish_resp = session.post(
            f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media_publish",
            data={"access_token": access_token, "creation_id": parent_creation_id},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if publish_resp.status_code == 200:
            click.echo("Carousel posted successfully!")
            return publish_resp.json()
        
        # Parse error
        try:
            error_data = publish_resp.json().get("error", {})
            error_code = error_data.get("code")
            error_msg = error_data.get("message", publish_resp.text)
        except Exception:
            error_code = None
            error_msg = publish_resp.text
        
        # Error 9007 = media not ready yet, retry after delay
        if error_code == 9007 or "not ready" in error_msg.lower():
            if attempt < max_publish_attempts - 1:
                click.echo(f"  Media not ready, waiting 10s... (attempt {attempt + 1}/{max_publish_attempts})")
                time.sleep(10)
                continue
        
        # Other errors - fail immediately
        raise click.ClickException(f"Failed to publish carousel: {error_msg}")
    
    raise click.ClickException("Failed to publish carousel after retries")


@click.command()
@click.option(
    "--image", "-i", "photo_paths",
    multiple=True,
    type=click.Path(exists=True),
    help="Path(s) to image file(s). Provide multiple -i options for a carousel.",
)
@click.option("--caption", "-c", help="Caption for the photo or carousel")
@click.argument("legacy_photo_path", required=False, type=click.Path(exists=True))
def photo(photo_paths: tuple, caption: str | None, legacy_photo_path: str | None) -> None:
    """Post a photo or carousel to Instagram.

    Examples:
        vbsocial instagram post photo -i img.jpg -c "Hello"
        vbsocial instagram post photo -i img1.jpg -i img2.jpg -c "Carousel"
        # Legacy single-argument syntax still works
        vbsocial instagram post photo img.jpg -c "Hello"
    """
    # Backward-compatibility
    if photo_paths and legacy_photo_path:
        raise click.ClickException(
            "Provide images either via -i/--image or positional argument, not both"
        )
    
    if not photo_paths:
        if not legacy_photo_path:
            raise click.ClickException(
                "Please provide image path(s) using -i or positional argument"
            )
        photo_paths = (legacy_photo_path,)
    
    photo_list = list(photo_paths)
    
    if len(photo_list) == 1:
        post_photo(photo_list[0], caption)
    else:
        post_carousel(photo_list, caption)
