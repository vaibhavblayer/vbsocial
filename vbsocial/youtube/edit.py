"""YouTube video edit command."""

import click
from googleapiclient.discovery import build

from .upload import get_credentials
from .info import _extract_video_id


@click.command()
@click.argument("video_id")
@click.option("-t", "--title", help="New title")
@click.option("-d", "--description", help="New description")
@click.option("--tags", help="New tags (comma-separated, replaces existing)")
@click.option("--add-tags", help="Tags to add (comma-separated)")
@click.option("--remove-tags", help="Tags to remove (comma-separated)")
@click.option(
    "-p", "--privacy",
    type=click.Choice(["private", "public", "unlisted"], case_sensitive=False),
    help="New privacy status",
)
@click.option("--category", type=int, help="Category ID (e.g., 27 for Education)")
def edit(
    video_id: str,
    title: str | None,
    description: str | None,
    tags: str | None,
    add_tags: str | None,
    remove_tags: str | None,
    privacy: str | None,
    category: int | None,
) -> None:
    """Update a video's title, description, tags, or privacy.
    
    VIDEO_ID can be the full URL or just the ID.
    
    Examples:
        vbsocial youtube edit VIDEO_ID -t "New Title"
        vbsocial youtube edit VIDEO_ID -d "New description"
        vbsocial youtube edit VIDEO_ID --tags "tag1,tag2,tag3"
        vbsocial youtube edit VIDEO_ID --add-tags "newtag1,newtag2"
        vbsocial youtube edit VIDEO_ID --remove-tags "oldtag"
        vbsocial youtube edit VIDEO_ID -p public
    """
    video_id = _extract_video_id(video_id)
    
    if not any([title, description, tags, add_tags, remove_tags, privacy, category]):
        raise click.ClickException(
            "Please specify at least one field to update:\n"
            "  -t/--title, -d/--description, --tags, --add-tags, --remove-tags, -p/--privacy, --category"
        )
    
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)
    
    # Get current video data
    response = youtube.videos().list(
        part="snippet,status",
        id=video_id,
    ).execute()
    
    if not response.get("items"):
        raise click.ClickException(f"Video not found: {video_id}")
    
    video = response["items"][0]
    snippet = video["snippet"]
    status = video["status"]
    
    # Track changes
    changes = []
    
    # Update snippet fields
    if title:
        snippet["title"] = title
        changes.append(f"Title → {title}")
    
    if description is not None:
        snippet["description"] = description
        changes.append("Description updated")
    
    # Handle tags
    current_tags = set(snippet.get("tags", []))
    
    if tags is not None:
        # Replace all tags
        new_tags = [t.strip() for t in tags.split(",") if t.strip()]
        snippet["tags"] = new_tags
        changes.append(f"Tags → {', '.join(new_tags)}")
    else:
        if add_tags:
            to_add = {t.strip() for t in add_tags.split(",") if t.strip()}
            current_tags.update(to_add)
            changes.append(f"Added tags: {', '.join(to_add)}")
        
        if remove_tags:
            to_remove = {t.strip() for t in remove_tags.split(",") if t.strip()}
            current_tags -= to_remove
            changes.append(f"Removed tags: {', '.join(to_remove)}")
        
        if add_tags or remove_tags:
            snippet["tags"] = list(current_tags)
    
    if category:
        snippet["categoryId"] = str(category)
        changes.append(f"Category → {category}")
    
    # Update status fields
    if privacy:
        status["privacyStatus"] = privacy.lower()
        changes.append(f"Privacy → {privacy}")
    
    # Build update request
    update_body = {
        "id": video_id,
        "snippet": {
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "categoryId": snippet["categoryId"],
        },
    }
    
    parts = ["snippet"]
    
    if privacy:
        update_body["status"] = {"privacyStatus": status["privacyStatus"]}
        parts.append("status")
    
    # Execute update
    click.echo(f"Updating video {video_id}...")
    
    youtube.videos().update(
        part=",".join(parts),
        body=update_body,
    ).execute()
    
    click.echo("\n✓ Video updated successfully!")
    for change in changes:
        click.echo(f"  • {change}")
    
    click.echo(f"\nView: https://youtube.com/watch?v={video_id}")
