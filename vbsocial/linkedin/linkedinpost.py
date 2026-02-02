"""LinkedIn posting functionality."""

from __future__ import annotations

import click

from .auth import create_oauth_session
from ..common.http import get_session, handle_response, DEFAULT_TIMEOUT, with_retry

# Chunk size for streaming video uploads (5 MB)
VIDEO_CHUNK_SIZE = 5 * 1024 * 1024


class LinkedInPost:
    """Helper class for posting content to LinkedIn."""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, organization_id: str | None = None):
        """Create a helper for posting to LinkedIn.
        
        Args:
            organization_id: If provided, posts will be created on behalf of the
                given Organisation / Company Page. If omitted, posts are created
                on the authenticated member's profile.
        """
        self.access_token = create_oauth_session()
        self.session = get_session()
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        
        self.organization_id = organization_id
        
        if organization_id:
            self.author_urn = f"urn:li:organization:{organization_id}"
            self.linkedin_id = None
        else:
            self.linkedin_id = self._get_linkedin_id()
            self.author_urn = f"urn:li:person:{self.linkedin_id}"
    
    def _get_linkedin_id(self) -> str:
        """Get the user's LinkedIn ID."""
        # Try userinfo endpoint first
        resp = self.session.get(
            "https://api.linkedin.com/v2/userinfo",
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            linkedin_id = data.get("sub")
            if linkedin_id:
                return linkedin_id
        
        # Fallback to /me endpoint
        resp = self.session.get(
            f"{self.BASE_URL}/me",
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            linkedin_id = data.get("id")
            if linkedin_id:
                return linkedin_id
        
        raise click.ClickException(
            "Could not get LinkedIn ID. Please try authenticating again."
        )
    
    def _build_post_data(
        self,
        message: str,
        media_category: str = "NONE",
        media: list | None = None,
    ) -> dict:
        """Build the UGC post data structure."""
        share_content = {
            "shareCommentary": {"text": message},
            "shareMediaCategory": media_category,
        }
        
        if media:
            share_content["media"] = media
        
        return {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
    
    @with_retry(max_attempts=3, delay=1.0)
    def _create_ugc_post(self, post_data: dict) -> dict:
        """Create a UGC post and return the response."""
        resp = self.session.post(
            f"{self.BASE_URL}/ugcPosts",
            headers=self.headers,
            json=post_data,
            timeout=DEFAULT_TIMEOUT,
        )
        
        if resp.status_code != 201:
            try:
                error_msg = resp.json().get("message", "Unknown error")
            except ValueError:
                error_msg = resp.text
            raise click.ClickException(f"Failed to post: {error_msg}")
        
        return resp.json()
    
    def create_text_post(self, message: str) -> dict:
        """Create a simple text post on LinkedIn."""
        post_data = self._build_post_data(message)
        return self._create_ugc_post(post_data)
    
    def create_post_with_url(self, message: str, url: str) -> dict:
        """Create a post with a URL preview."""
        media = [{
            "status": "READY",
            "originalUrl": url,
            "title": {"text": "Shared URL"},
            "description": {"text": message},
        }]
        
        post_data = self._build_post_data(message, "ARTICLE", media)
        return self._create_ugc_post(post_data)
    
    @with_retry(max_attempts=2, delay=2.0)
    def create_post_with_image(self, message: str, image_path: str) -> dict:
        """Create a post with an image."""
        # Register the upload
        register_resp = self.session.post(
            f"{self.BASE_URL}/assets?action=registerUpload",
            headers=self.headers,
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": self.author_urn,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }],
                }
            },
            timeout=DEFAULT_TIMEOUT,
        )
        register_resp.raise_for_status()
        upload_data = register_resp.json()
        
        upload_url = upload_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = upload_data["value"]["asset"]
        
        # Upload the image
        with open(image_path, "rb") as f:
            upload_resp = self.session.put(
                upload_url,
                data=f,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=(10, 120),
            )
            upload_resp.raise_for_status()
        
        # Create the post
        media = [{"status": "READY", "media": asset_urn}]
        post_data = self._build_post_data(message, "IMAGE", media)
        return self._create_ugc_post(post_data)
    
    @with_retry(max_attempts=2, delay=2.0)
    def create_post_with_video(self, message: str, video_path: str) -> dict:
        """Create a post with a video using streaming upload."""
        import os
        
        file_size = os.path.getsize(video_path)
        
        # Register the upload
        register_resp = self.session.post(
            f"{self.BASE_URL}/assets?action=registerUpload",
            headers=self.headers,
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                    "owner": self.author_urn,
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }],
                }
            },
            timeout=DEFAULT_TIMEOUT,
        )
        register_resp.raise_for_status()
        upload_data = register_resp.json()["value"]
        
        upload_url = upload_data["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = upload_data["asset"]
        
        # Stream upload the video in chunks
        def file_reader(path: str, chunk_size: int):
            """Generator that yields file chunks."""
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        put_resp = self.session.put(
            upload_url,
            data=file_reader(video_path, VIDEO_CHUNK_SIZE),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/octet-stream",
                "Content-Length": str(file_size),
            },
            timeout=(10, 600),  # 10 min timeout for large videos
        )
        put_resp.raise_for_status()
        
        # Create the post
        media = [{"status": "READY", "media": asset_urn}]
        post_data = self._build_post_data(message, "VIDEO", media)
        return self._create_ugc_post(post_data)
