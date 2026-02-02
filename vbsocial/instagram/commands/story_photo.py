"""Instagram story photo posting command."""

import click

from ..auth import get_access_token, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


def _upload_to_fb_storage(photo_path: str, access_token: str) -> str:
    """Upload image to Facebook storage and get a URL."""
    session = get_session()
    
    upload_url = f"https://graph.facebook.com/{API_VERSION}/me/photos"
    
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
def post_story_photo(photo_path: str) -> dict:
    """Post a photo to Instagram Story."""
    config = load_config()
    access_token = get_access_token()
    instagram_account_id = config["instagram_account_id"]
    
    session = get_session()
    
    click.echo("Uploading image to get URL...")
    image_url = _upload_to_fb_storage(photo_path, access_token)
    click.echo("Image uploaded, URL obtained")
    
    # Create the story media container
    container_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media"
    params = {
        "access_token": access_token,
        "image_url": image_url,
        "is_carousel_item": "false",
        "media_type": "STORIES",
        "sharing_type": "STORY",
    }
    
    click.echo("Creating story container...")
    container_response = session.post(container_url, data=params, timeout=DEFAULT_TIMEOUT)
    container_response.raise_for_status()
    
    creation_id = container_response.json().get("id")
    if not creation_id:
        raise click.ClickException(f"Error creating story: {container_response.text}")
    
    click.echo("Story container created, publishing...")
    
    # Publish the story
    publish_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media_publish"
    publish_params = {
        "access_token": access_token,
        "creation_id": creation_id,
    }
    
    publish_response = session.post(publish_url, data=publish_params, timeout=DEFAULT_TIMEOUT)
    publish_response.raise_for_status()
    
    click.echo("Story photo posted successfully!")
    return publish_response.json()


@click.command()
@click.argument("photo_path", type=click.Path(exists=True))
def story_photo(photo_path: str) -> None:
    """Post a photo to Instagram Story."""
    post_story_photo(photo_path)
