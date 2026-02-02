"""Instagram story video posting command."""

import time

import click

from ..auth import get_access_token, load_config, API_VERSION
from ...common.http import get_session, DEFAULT_TIMEOUT, with_retry


def _upload_to_fb_storage(video_path: str, access_token: str, page_id: str) -> str:
    """Upload video to Facebook page storage and get a URL."""
    session = get_session()
    
    upload_url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/videos"
    
    with open(video_path, "rb") as f:
        files = {"source": f}
        params = {
            "access_token": access_token,
            "published": "false",
        }
        
        response = session.post(upload_url, files=files, data=params, timeout=(10, 600))
        response.raise_for_status()
        video_id = response.json().get("id")
    
    # Poll until video source is available
    status_url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
    
    for _ in range(60):  # Wait up to ~5 minutes
        resp = session.get(
            status_url,
            params={"fields": "source", "access_token": access_token},
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            video_url = resp.json().get("source")
            if video_url:
                return video_url
        
        time.sleep(5)
    
    raise click.ClickException("Could not get video URL after processing")


def _wait_for_processing(creation_id: str, access_token: str, max_wait: int = 300) -> None:
    """Wait for Instagram to process the story video."""
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
            raise click.ClickException("Instagram failed to process the story video")
        
        time.sleep(5)
    
    raise click.ClickException("Story video not processed within timeout")


@with_retry(max_attempts=2, delay=2.0)
def post_story_video(video_path: str) -> dict:
    """Post a video to Instagram Story."""
    config = load_config()
    access_token = get_access_token()
    instagram_account_id = config["instagram_account_id"]
    page_id = config.get("page_id")
    
    if not page_id:
        raise click.ClickException(
            "Missing page_id in config. Re-run 'vbsocial instagram configure'."
        )
    
    session = get_session()
    
    click.echo("Uploading video to get URL...")
    video_url = _upload_to_fb_storage(video_path, access_token, page_id)
    click.echo("Video uploaded, URL obtained")
    
    # Create the story media container
    container_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media"
    params = {
        "access_token": access_token,
        "video_url": video_url,
        "media_type": "STORIES",
    }
    
    click.echo("Creating story container...")
    container_response = session.post(container_url, data=params, timeout=DEFAULT_TIMEOUT)
    container_response.raise_for_status()
    
    creation_id = container_response.json().get("id")
    if not creation_id:
        raise click.ClickException(f"Error creating story: {container_response.text}")
    
    click.echo("Waiting for Instagram to process the story video…")
    _wait_for_processing(creation_id, access_token)
    
    click.echo("Story container processed, publishing…")
    
    # Publish the story
    publish_url = f"https://graph.facebook.com/{API_VERSION}/{instagram_account_id}/media_publish"
    publish_params = {
        "access_token": access_token,
        "creation_id": creation_id,
    }
    
    publish_response = session.post(publish_url, data=publish_params, timeout=DEFAULT_TIMEOUT)
    publish_response.raise_for_status()
    
    click.echo("Story video posted successfully!")
    return publish_response.json()


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
def story_video(video_path: str) -> None:
    """Post a video to Instagram Story."""
    post_story_video(video_path)
