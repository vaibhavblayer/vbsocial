"""Facebook photo posting command."""

import click

from ..auth import get_access_token, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


@with_retry(max_attempts=3, delay=1.0)
def post_photo(photo_path: str, message: str | None) -> dict:
    """Post a photo to Facebook."""
    access_token = get_access_token()
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/me/photos"
    
    with open(photo_path, "rb") as f:
        files = {"source": f}
        data = {
            "access_token": access_token,
            "message": message or "",
        }
        
        response = session.post(url, files=files, data=data, timeout=(10, 120))
    
    if response.status_code == 200:
        click.echo("Photo posted successfully!")
        return response.json()
    else:
        raise click.ClickException(f"Error posting photo: {response.text}")


def _upload_photo_unpublished(photo_path: str, access_token: str) -> str:
    """Upload a photo without publishing, return the photo ID."""
    session = get_session()
    url = f"https://graph.facebook.com/{API_VERSION}/me/photos"
    
    with open(photo_path, "rb") as f:
        files = {"source": f}
        data = {
            "access_token": access_token,
            "published": "false",
        }
        response = session.post(url, files=files, data=data, timeout=(10, 120))
    
    if response.status_code != 200:
        raise click.ClickException(f"Error uploading photo: {response.text}")
    
    return response.json()["id"]


@with_retry(max_attempts=2, delay=2.0)
def post_multiple_photos(photo_paths: list[str], message: str | None) -> dict:
    """Post multiple photos as a single Facebook post."""
    if len(photo_paths) == 1:
        return post_photo(photo_paths[0], message)
    
    access_token = get_access_token()
    session = get_session()
    
    # Upload all photos unpublished
    photo_ids = []
    for idx, path in enumerate(photo_paths, 1):
        click.echo(f"  Uploading photo {idx}/{len(photo_paths)}...")
        photo_id = _upload_photo_unpublished(path, access_token)
        photo_ids.append(photo_id)
    
    # Create feed post with all photos attached
    click.echo("  Creating multi-photo post...")
    url = f"https://graph.facebook.com/{API_VERSION}/me/feed"
    
    data = {
        "access_token": access_token,
        "message": message or "",
    }
    
    # Add attached_media for each photo
    for idx, photo_id in enumerate(photo_ids):
        data[f"attached_media[{idx}]"] = f'{{"media_fbid":"{photo_id}"}}'
    
    response = session.post(url, data=data, timeout=DEFAULT_TIMEOUT)
    
    if response.status_code == 200:
        click.echo("Multi-photo post created successfully!")
        return response.json()
    else:
        raise click.ClickException(f"Error creating post: {response.text}")


@click.command()
@click.argument("photo_path", type=click.Path(exists=True))
@click.option("--message", "-m", help="Caption for the photo")
def photo(photo_path: str, message: str | None) -> None:
    """Post a photo to Facebook."""
    post_photo(photo_path, message)
