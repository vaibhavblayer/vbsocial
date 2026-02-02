"""Facebook story photo posting command."""

import click

from ..auth import get_access_token, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


def _get_page_token(page_id: str, access_token: str) -> str:
    """Get the page access token."""
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}"
    params = {
        "access_token": access_token,
        "fields": "access_token",
    }
    
    response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    page_token = response.json().get("access_token")
    if not page_token:
        raise click.ClickException("Could not get page access token")
    
    return page_token


def _upload_to_fb_storage(photo_path: str, access_token: str, page_id: str) -> str:
    """Upload photo to Facebook and get photo ID."""
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/photos"
    
    with open(photo_path, "rb") as f:
        files = {"source": f}
        params = {
            "access_token": access_token,
            "published": "false",
        }
        
        response = session.post(url, files=files, data=params, timeout=(10, 120))
        response.raise_for_status()
        return response.json().get("id")


@with_retry(max_attempts=3, delay=1.0)
def post_story_photo(photo_path: str) -> dict:
    """Post a photo to Facebook Story."""
    config = load_config()
    access_token = get_access_token()
    page_id = config["page_id"]
    
    session = get_session()
    
    # Get page access token
    page_token = _get_page_token(page_id, access_token)
    
    # Upload the photo
    click.echo("Uploading photo...")
    photo_id = _upload_to_fb_storage(photo_path, page_token, page_id)
    click.echo("Photo uploaded, creating story...")
    
    # Create the story
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/photo_stories"
    params = {
        "access_token": page_token,
        "photo_id": photo_id,
    }
    
    response = session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    result = response.json()
    if result.get("success"):
        click.echo("Story photo posted successfully!")
        if post_id := result.get("post_id"):
            click.echo(f"Post ID: {post_id}")
        return result
    else:
        raise click.ClickException("Story creation was not successful")


@click.command()
@click.argument("photo_path", type=click.Path(exists=True))
def story_photo(photo_path: str) -> None:
    """Post a photo to Facebook Story."""
    post_story_photo(photo_path)
