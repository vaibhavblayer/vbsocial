"""Facebook video posting command."""

import click

from ..auth import get_access_token, API_VERSION
from ...common.http import get_session, with_retry


@with_retry(max_attempts=2, delay=2.0)
def post_video(video_path: str, message: str | None) -> dict:
    """Post a video to Facebook."""
    access_token = get_access_token()
    session = get_session()
    
    url = f"https://graph.facebook.com/{API_VERSION}/me/videos"
    
    with open(video_path, "rb") as f:
        files = {"source": f}
        data = {
            "access_token": access_token,
            "description": message or "",
        }
        
        response = session.post(url, files=files, data=data, timeout=(10, 600))
    
    if response.status_code == 200:
        click.echo("Video posted successfully!")
        return response.json()
    else:
        raise click.ClickException(f"Error posting video: {response.text}")


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--message", "-m", help="Caption for the video")
def video(video_path: str, message: str | None) -> None:
    """Post a video to Facebook."""
    post_video(video_path, message)
