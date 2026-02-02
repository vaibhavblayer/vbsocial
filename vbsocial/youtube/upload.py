"""YouTube upload command."""

import os
import socket

import click
import google.oauth2.credentials
import google_auth_oauthlib.flow
import google.auth.transport.requests

from .youtubeuploader import YouTubeUploader

# OAuth 2.0 scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtubepartner",
]

CLIENT_SECRETS_FILE = os.path.expanduser("~/.vbsocial/youtube/client_secret.json")
TOKEN_FILE = os.path.expanduser("~/.vbsocial/youtube/token.json")


def _find_free_port(start: int = 8080, end: int = 8100) -> int:
    """Find a free port in the given range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    raise click.ClickException(f"No free port found in range {start}-{end}")


def get_credentials():
    """Get valid user credentials from storage or create new ones."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    
    credentials = None
    
    # Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        try:
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
                TOKEN_FILE, SCOPES
            )
        except Exception:
            credentials = None
    
    # Check if credentials need refresh or re-auth
    if credentials:
        if credentials.expired and credentials.refresh_token:
            try:
                click.echo("Refreshing YouTube token...")
                credentials.refresh(google.auth.transport.requests.Request())
                _save_credentials(credentials)
            except Exception as e:
                click.echo(f"Token refresh failed: {e}")
                click.echo("Re-authenticating...")
                credentials = None
                _delete_token()
        elif not credentials.valid:
            credentials = None
    
    # If no valid credentials, start fresh OAuth flow
    if not credentials:
        if not os.path.exists(CLIENT_SECRETS_FILE):
            raise click.ClickException(
                f"Client secrets file not found: {CLIENT_SECRETS_FILE}\n"
                "Please download your OAuth client credentials from Google Cloud Console "
                "and save them to this location."
            )
        
        # Find a free port
        port = _find_free_port()
        click.echo(f"Starting YouTube OAuth flow on port {port}...")
        
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES
        )
        
        # Allow insecure transport for local development
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
        try:
            credentials = flow.run_local_server(
                port=port,
                open_browser=True,
                access_type="offline",
                prompt="consent",
            )
        except OSError as e:
            raise click.ClickException(
                f"Failed to start OAuth server: {e}\n"
                "Try killing any process using port 8080-8100:\n"
                "  lsof -ti:8080 | xargs kill -9"
            )
        
        _save_credentials(credentials)
        click.echo("YouTube authentication successful!")
    
    return credentials


def _save_credentials(credentials):
    """Save credentials to token file."""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())
    os.chmod(TOKEN_FILE, 0o600)


def _delete_token():
    """Delete the token file if it exists."""
    try:
        os.remove(TOKEN_FILE)
    except FileNotFoundError:
        pass


@click.command()
@click.option(
    "-m", "--metadata",
    type=click.Path(exists=True),
    help="JSON file containing video metadata",
    required=True,
)
@click.option(
    "-p", "--privacy",
    type=click.Choice(["private", "public", "unlisted"], case_sensitive=False),
    default="private",
    help="Video privacy status (default: private)",
)
def upload(metadata: str, privacy: str) -> None:
    """Upload a video to YouTube with metadata."""
    credentials = get_credentials()
    uploader = YouTubeUploader(credentials)
    uploader.upload(metadata_file=metadata, privacy_status=privacy.lower())
