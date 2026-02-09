"""Post manager for file operations and workflow."""

import os
import shutil
from datetime import datetime
from pathlib import Path

import click

from .db import PostDB, PostStatus, generate_short_uuid


class PostManager:
    """Manages post folders and database operations."""
    
    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.db = PostDB(self.base_path / "posts.db")
        self.inbox_path = self.base_path / "inbox"
        self.inbox_path.mkdir(exist_ok=True)
        (self.inbox_path / "images").mkdir(exist_ok=True)
        (self.inbox_path / "tex").mkdir(exist_ok=True)
    
    def _make_folder_name(self, post_id: str, date: datetime, status: PostStatus) -> str:
        """Create folder name: uuid_YYYY_MM_DD_status."""
        date_str = date.strftime("%Y_%m_%d")
        return f"{post_id}_{date_str}_{status.value}"
    
    def _parse_folder_name(self, folder_name: str) -> tuple[str, str, str] | None:
        """Parse folder name into (uuid, date, status)."""
        parts = folder_name.split("_")
        if len(parts) >= 5:
            uuid = parts[0]
            date = "_".join(parts[1:4])
            status = "_".join(parts[4:])
            return uuid, date, status
        return None
    
    def create_post_from_image(self, image_path: Path | str, title: str | None = None) -> tuple[str, Path]:
        """Create a new post folder from an image file.
        
        Returns (post_id, folder_path).
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise click.ClickException(f"Image not found: {image_path}")
        
        post_id = generate_short_uuid()
        now = datetime.now()
        folder_name = self._make_folder_name(post_id, now, PostStatus.DRAFT)
        folder_path = self.base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Copy image to folder
        dest_image = folder_path / f"problem_image{image_path.suffix}"
        shutil.copy2(image_path, dest_image)
        
        # Create database entry
        self.db.create_post(
            post_id=post_id,
            folder_path=str(folder_path),
            source_type="image",
            source_file=image_path.name,
            title=title or image_path.stem,
        )
        
        return post_id, folder_path
    
    def create_post_from_tex(self, tex_path: Path | str, title: str | None = None) -> tuple[str, Path]:
        """Create a new post folder from a TeX file.
        
        Returns (post_id, folder_path).
        """
        tex_path = Path(tex_path)
        if not tex_path.exists():
            raise click.ClickException(f"TeX file not found: {tex_path}")
        
        post_id = generate_short_uuid()
        now = datetime.now()
        folder_name = self._make_folder_name(post_id, now, PostStatus.DRAFT)
        folder_path = self.base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Copy tex to folder as problem.tex
        dest_tex = folder_path / "problem.tex"
        shutil.copy2(tex_path, dest_tex)
        
        # Create database entry
        self.db.create_post(
            post_id=post_id,
            folder_path=str(folder_path),
            source_type="tex",
            source_file=tex_path.name,
            title=title or tex_path.stem,
        )
        
        return post_id, folder_path

    def process_inbox_images(self, delete_after: bool = False) -> list[tuple[str, Path]]:
        """Process all images in inbox/images folder.
        
        Returns list of (post_id, folder_path) tuples.
        """
        images_dir = self.inbox_path / "images"
        results = []
        
        for img_file in sorted(images_dir.iterdir()):
            if img_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
                post_id, folder_path = self.create_post_from_image(img_file)
                results.append((post_id, folder_path))
                
                if delete_after:
                    img_file.unlink()
        
        return results
    
    def process_inbox_tex(self, delete_after: bool = False) -> list[tuple[str, Path]]:
        """Process all TeX files in inbox/tex folder.
        
        Returns list of (post_id, folder_path) tuples.
        """
        tex_dir = self.inbox_path / "tex"
        results = []
        
        for tex_file in sorted(tex_dir.iterdir()):
            if tex_file.suffix.lower() == ".tex":
                post_id, folder_path = self.create_post_from_tex(tex_file)
                results.append((post_id, folder_path))
                
                if delete_after:
                    tex_file.unlink()
        
        return results
    
    def process_folder(self, folder_path: Path | str, source_type: str = "image", delete_after: bool = False) -> list[tuple[str, Path]]:
        """Process all files in a folder.
        
        Args:
            folder_path: Path to folder containing images or tex files
            source_type: "image" or "tex"
            delete_after: Delete source files after processing
        
        Returns list of (post_id, folder_path) tuples.
        """
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            raise click.ClickException(f"Not a directory: {folder_path}")
        
        results = []
        
        if source_type == "image":
            extensions = (".png", ".jpg", ".jpeg", ".gif")
            create_fn = self.create_post_from_image
        else:
            extensions = (".tex",)
            create_fn = self.create_post_from_tex
        
        for file_path in sorted(folder_path.iterdir()):
            if file_path.suffix.lower() in extensions:
                post_id, dest_path = create_fn(file_path)
                results.append((post_id, dest_path))
                
                if delete_after:
                    file_path.unlink()
        
        return results
    
    def update_status(self, post_id: str, new_status: PostStatus) -> Path | None:
        """Update post status and rename folder accordingly.
        
        Returns new folder path or None if failed.
        """
        post = self.db.get_post(post_id)
        if not post:
            return None
        
        old_path = Path(post["folder_path"])
        if not old_path.exists():
            return None
        
        # Parse old folder name to get date
        parsed = self._parse_folder_name(old_path.name)
        if not parsed:
            return None
        
        _, date_str, _ = parsed
        
        # Create new folder name
        new_folder_name = f"{post_id}_{date_str}_{new_status.value}"
        new_path = old_path.parent / new_folder_name
        
        # Rename folder
        old_path.rename(new_path)
        
        # Update database
        self.db.update_status(post_id, new_status)
        self.db.update_folder_path(post_id, str(new_path))
        
        return new_path
    
    def get_inbox_counts(self) -> dict[str, int]:
        """Get counts of files in inbox folders."""
        images_dir = self.inbox_path / "images"
        tex_dir = self.inbox_path / "tex"
        
        image_count = len([f for f in images_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")])
        tex_count = len([f for f in tex_dir.iterdir() if f.suffix.lower() == ".tex"])
        
        return {"images": image_count, "tex": tex_count}
    
    def list_inbox(self) -> dict[str, list[str]]:
        """List files in inbox folders."""
        images_dir = self.inbox_path / "images"
        tex_dir = self.inbox_path / "tex"
        
        images = sorted([f.name for f in images_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")])
        tex_files = sorted([f.name for f in tex_dir.iterdir() if f.suffix.lower() == ".tex"])
        
        return {"images": images, "tex": tex_files}
