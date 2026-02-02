import click
import os
import subprocess
from pathlib import Path
import json
import time


@click.command()
@click.option('-s', '--source',
              type=click.Path(exists=True),
              help='SSD directory path',
              default="/Volumes/T7 Shield/youtube_10xphysics",
              show_default=True)
@click.option('-d', '--destination',
              type=click.Path(),
              help='Local directory path',
              default=os.path.expanduser("~/youtube_10xphysics"),
              show_default=True)
@click.option('--force-direction',
              type=click.Choice(['to-local', 'to-ssd']),
              help='Force sync direction (optional)',
              default=None)
def sync(source, destination, force_direction):
    """Smart sync between SSD and local machine using timestamps."""

    # Ensure paths are absolute
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    # Create destination if it doesn't exist
    os.makedirs(destination, exist_ok=True)

    # Define excluded patterns
    exclude_patterns = [
        '*.mp4',
        '*.mov',
        '*.avi',
        '*.mkv',
        '*.wmv',
        '*.flv',
        '*.webm',
        '*.m4v',
        '.DS_Store',  # Exclude Mac system files
        '._*',  # Exclude hidden files
    ]

    # Build rsync exclude arguments
    exclude_args = ' '.join(
        [f'--exclude="{pattern}"' for pattern in exclude_patterns])

    # Determine sync direction based on timestamps if not forced
    if not force_direction:
        src_time = get_latest_modification_time(source)
        dst_time = get_latest_modification_time(destination)

        if src_time > dst_time:
            direction = 'to-local'
            click.echo(f"SSD is newer (modified {src_time})")
            click.echo(f"Local is older (modified {dst_time})")
        else:
            direction = 'to-ssd'
            click.echo(f"Local is newer (modified {dst_time})")
            click.echo(f"SSD is older (modified {src_time})")
    else:
        direction = force_direction
        click.echo(f"Forcing direction: {direction}")

    # Set source and destination based on direction
    if direction == 'to-local':
        src, dst = source, destination
        click.echo("Syncing from SSD to Local")
    else:
        src, dst = destination, source
        click.echo("Syncing from Local to SSD")

    # Ensure trailing slash on source for rsync
    src = str(Path(src)) + os.sep

    cmd = f'rsync -av --progress {exclude_args} "{src}" "{dst}"'

    click.echo("\nExcluding video files...")
    click.echo(f"From: {src}")
    click.echo(f"To: {dst}")

    try:
        # Execute rsync command
        subprocess.run(cmd, shell=True, check=True)
        click.echo("\nSync completed successfully!")

        # Save last sync time
        save_sync_time(source, destination)

    except subprocess.CalledProcessError as e:
        raise click.ClickException(f"Sync failed: {str(e)}")


def get_latest_modification_time(directory):
    """Get the latest modification time of any file in the directory."""
    latest_time = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not any(file.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v']):
                path = os.path.join(root, file)
                latest_time = max(latest_time, os.path.getmtime(path))
    return latest_time


def save_sync_time(source, destination):
    """Save the sync time to a hidden file."""
    sync_info = {
        'last_sync': time.time(),
        'source': source,
        'destination': destination
    }

    # Save in both locations
    for path in [source, destination]:
        sync_file = os.path.join(path, '.sync_info')
        with open(sync_file, 'w') as f:
            json.dump(sync_info, f, indent=4)


if __name__ == '__main__':
    sync()
