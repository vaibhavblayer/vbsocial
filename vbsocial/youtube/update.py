import click
from .youtubeuploader import YouTubeUploader
from .upload import get_credentials


@click.command()
@click.option(
    '-m',
    '--metadata',
    type=click.Path(exists=True),
    help='Metadata file with YouTube ID',
    required=True
)
def update(metadata):
    """Update an existing video using metadata file."""
    try:
        credentials = get_credentials()
        uploader = YouTubeUploader(credentials)
        uploader.update_video_by_id(metadata)
    except Exception as e:
        raise click.ClickException(f"An error occurred: {str(e)}")


if __name__ == '__main__':
    update()
