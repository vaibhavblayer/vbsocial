"""Facebook story video posting command."""

import time

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


def _init_video_upload(page_id: str, access_token: str) -> tuple[str, str]:
    """Initialize video upload and get upload URL."""
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_stories"
    params = {
        "access_token": access_token,
        "upload_phase": "start",
    }
    
    response = session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    
    return data.get("video_id"), data.get("upload_url")


def _upload_video_binary(upload_url: str, video_path: str, access_token: str) -> dict:
    """Upload the video binary data."""
    session = get_session()
    
    headers = {"Authorization": f"OAuth {access_token}"}
    
    with open(video_path, "rb") as f:
        response = session.post(
            upload_url,
            headers=headers,
            data=f,
            timeout=(10, 600),
        )
        response.raise_for_status()
        return response.json()


def _check_upload_status(video_id: str, access_token: str, max_wait: int = 300) -> bool:
    """Check the status of video upload and processing."""
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/{video_id}"
    params = {
        "access_token": access_token,
        "fields": "status",
    }
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        status = response.json().get("status", {})
        
        uploading = status.get("uploading_phase", {}).get("status")
        processing = status.get("processing_phase", {}).get("status")
        
        if uploading == "complete" and processing == "complete":
            return True
        
        click.echo("Video processing... Please wait...")
        time.sleep(3)
    
    raise click.ClickException("Video processing timed out")


def _finish_video_upload(page_id: str, video_id: str, access_token: str) -> dict:
    """Finish the video upload process."""
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/{page_id}/video_stories"
    params = {
        "access_token": access_token,
        "upload_phase": "finish",
        "video_id": video_id,
    }
    
    response = session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


@with_retry(max_attempts=2, delay=2.0)
def post_story_video(video_path: str) -> dict:
    """Post a video to Facebook Story."""
    config = load_config()
    access_token = get_access_token()
    page_id = config["page_id"]
    
    # Get page access token
    page_token = _get_page_token(page_id, access_token)
    
    # Initialize the upload
    click.echo("Initializing video upload...")
    video_id, upload_url = _init_video_upload(page_id, page_token)
    
    # Upload the video binary
    click.echo("Uploading video...")
    _upload_video_binary(upload_url, video_path, page_token)
    
    # Check upload status
    click.echo("Checking upload status...")
    _check_upload_status(video_id, page_token)
    
    # Finish the upload
    click.echo("Finalizing story...")
    result = _finish_video_upload(page_id, video_id, page_token)
    
    if result.get("success"):
        click.echo("Story video posted successfully!")
        if post_id := result.get("post_id"):
            click.echo(f"Post ID: {post_id}")
        return result
    else:
        raise click.ClickException("Story creation was not successful")


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
def story_video(video_path: str) -> None:
    """Post a video to Facebook Story."""
    post_story_video(video_path)
