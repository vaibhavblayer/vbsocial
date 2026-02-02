"""Instagram video posting command."""

import time

import click

from ..auth import get_access_token, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


def _upload_to_fb_storage(video_path: str, access_token: str) -> str:
    """Upload video to Facebook storage and get a URL."""
    session = get_session()
    
    upload_url = f"https://graph.facebook.com/{API_VERSION}/me/videos"
    
    with open(video_path, "rb") as f:
        files = {"source": f}
        params = {
            "access_token": access_token,
            "published": "false",
        }
        
        response = session.post(upload_url, files=files, data=params, timeout=(10, 600))
        response.raise_for_status()
        video_id = response.json().get("id")
    
    # Poll until processing is finished
    status_url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
    
    for _ in range(60):  # Wait up to ~5 minutes
        info_resp = session.get(
            status_url,
            params={"fields": "source", "access_token": access_token},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if info_resp.status_code == 200:
            video_url = info_resp.json().get("source")
            if video_url:
                return video_url
        
        time.sleep(5)
    
    raise click.ClickException("Could not get video URL after processing")


def _wait_for_processing(creation_id: str, access_token: str, max_wait: int = 300) -> None:
    """Wait for Instagram to process the video."""
    session = get_session()
    
    status_url = f"https://graph.facebook.com/{API_VERSION}/{creation_id}"
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        resp = session.get(
            status_url,
            params={"fields": "status_code", "access_token": access_token},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        
        status = resp.json().get("status_code")
        
        if status == "FINISHED":
            return
        
        if status == "ERROR":
            raise click.ClickException("Instagram failed to process the video")
        
        time.sleep(5)
    
    raise click.ClickException("Video not processed within timeout")


@with_retry(max_attempts=2, delay=2.0)
def post_video(video_path: str, caption: str | None) -> dict:
    """Post a video to Instagram."""
    config = load_config()
    access_token = get_access_token()
    instagram_account_id = config["instagram_account_id"]
    
    session = get_session()
    
    click.echo("Uploading video to get URL...")
    video_url = _upload_to_fb_storage(video_path, access_token)
    click.echo("Video uploaded, URL obtained")
    
    # Create the media container
    container_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media"
    params = {
        "access_token": access_token,
        "video_url": video_url,
        "caption": caption or "",
        "media_type": "REELS",
        "share_to_feed": "true",
    }
    
    click.echo("Creating media container...")
    container_response = session.post(container_url, data=params, timeout=DEFAULT_TIMEOUT)
    container_response.raise_for_status()
    
    creation_id = container_response.json().get("id")
    if not creation_id:
        raise click.ClickException(f"Error creating media: {container_response.text}")
    
    click.echo("Media container created, waiting for processing...")
    _wait_for_processing(creation_id, access_token)
    
    click.echo("Media container processed, publishing…")
    
    # Publish the container
    publish_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media_publish"
    publish_params = {
        "access_token": access_token,
        "creation_id": creation_id,
    }
    
    publish_response = session.post(publish_url, data=publish_params, timeout=DEFAULT_TIMEOUT)
    publish_response.raise_for_status()
    
    click.echo("Video posted successfully!")
    return publish_response.json()


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--caption", "-c", help="Caption for the video")
def video(video_path: str, caption: str | None) -> None:
    """Post a video to Instagram."""
    post_video(video_path, caption)
