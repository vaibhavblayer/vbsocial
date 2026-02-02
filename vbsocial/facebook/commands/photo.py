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


@click.command()
@click.argument("photo_path", type=click.Path(exists=True))
@click.option("--message", "-m", help="Caption for the photo")
def photo(photo_path: str, message: str | None) -> None:
    """Post a photo to Facebook."""
    post_photo(photo_path, message)
