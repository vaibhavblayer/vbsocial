"""Helpers for uploading media and posting tweets to X (Twitter).

This module centralises the logic for image/video uploads and tweet creation.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import click
import requests
from requests_oauthlib import OAuth1

from .auth import create_oauth_session
from .config import API_BASE
from ..common.http import get_session, DEFAULT_TIMEOUT, with_retry

CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB


def _oauth1() -> OAuth1:
    """Build an OAuth1 session from env vars or raise."""
    api_key = os.getenv("API_KEY_X_10X")
    api_secret = os.getenv("API_SECRET_KEY_X_10X")
    user_token = os.getenv("X_ACCESS_TOKEN_10X")
    user_secret = os.getenv("X_ACCESS_TOKEN_SECRET_10X")
    
    if not all([api_key, api_secret, user_token, user_secret]):
        raise click.ClickException(
            "OAuth 1 credentials not set. Define API_KEY_X_10X, "
            "API_SECRET_KEY_X_10X, X_ACCESS_TOKEN_10X and "
            "X_ACCESS_TOKEN_SECRET_10X to enable video uploads."
        )
    
    return OAuth1(api_key, api_secret, user_token, user_secret)


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------


@with_retry(max_attempts=3, delay=1.0)
def upload_image(image_path: str, access_token: str) -> str:
    """Upload an image. Try v2 (OAuth2) first, then v1.1 (OAuth1)."""
    if not os.path.exists(image_path):
        raise click.ClickException(f"Image file not found: {image_path}")
    
    session = get_session()
    
    # --- v2 attempt ---
    try:
        with open(image_path, "rb") as fh:
            resp = session.post(
                "https://upload.twitter.com/2/media",
                files={"file": fh},
                data={"media_category": "tweet_image"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=DEFAULT_TIMEOUT,
            )
        
        if resp.status_code not in {401, 403}:
            resp.raise_for_status()
            data = resp.json()
            if "media_id" in data:
                return data["media_id"]
            raise click.ClickException(f"Unexpected upload response: {data}")
    except requests.exceptions.HTTPError:
        if resp.status_code not in {401, 403}:
            raise click.ClickException(f"Image upload failed: {resp.text}")
    
    # --- fallback to v1.1 with OAuth1 ---
    oauth1 = _oauth1()
    
    with open(image_path, "rb") as img_fh:
        resp = session.post(
            "https://upload.twitter.com/1.1/media/upload.json",
            files={"media": img_fh},
            auth=oauth1,
            timeout=DEFAULT_TIMEOUT,
        )
    
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        raise click.ClickException(f"Image upload failed: {resp.text}")
    
    return resp.json().get("media_id_string")


# ---------------------------------------------------------------------------
# Video upload
# ---------------------------------------------------------------------------


def _upload_video_v2(video_path: str, access_token: str) -> Optional[str]:
    """Attempt /2/media upload. Returns media_id on success or None."""
    session = get_session()
    
    with open(video_path, "rb") as fh:
        resp = session.post(
            "https://upload.twitter.com/2/media",
            files={"file": fh},
            data={"media_category": "tweet_video"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=(10, 300),  # Longer timeout for video
        )
    
    if resp.status_code in {401, 403}:
        return None
    
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        raise click.ClickException(f"Video upload failed: {resp.text}")
    
    data = resp.json()
    media_id = data.get("media_id")
    if not media_id:
        raise click.ClickException(f"Unexpected upload response: {data}")
    
    # Poll processing if necessary
    _poll_video_status_v2(media_id, access_token)
    
    return media_id


def _poll_video_status_v2(media_id: str, access_token: str) -> None:
    """Poll until video processing completes."""
    session = get_session()
    
    for _ in range(60):  # Max 5 minutes
        resp = session.get(
            f"https://upload.twitter.com/2/media/{media_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        
        processing = resp.json().get("processing_info", {})
        state = processing.get("state")
        
        if state is None or state == "succeeded":
            return
        
        if state == "failed":
            msg = processing.get("error", {}).get("message", "Unknown error")
            raise click.ClickException(f"Video processing failed: {msg}")
        
        check_after = processing.get("check_after_secs", 5)
        time.sleep(check_after)
    
    raise click.ClickException("Video processing timed out")


def _upload_video_v1(video_path: str, oauth1: OAuth1) -> str:
    """Chunked INIT/APPEND/FINALIZE upload (v1.1). Returns media_id."""
    session = get_session()
    total_bytes = os.path.getsize(video_path)
    
    # INIT
    init_resp = session.post(
        "https://upload.twitter.com/1.1/media/upload.json",
        data={
            "command": "INIT",
            "total_bytes": total_bytes,
            "media_type": "video/mp4",
            "media_category": "tweet_video",
        },
        auth=oauth1,
        timeout=DEFAULT_TIMEOUT,
    )
    init_resp.raise_for_status()
    media_id = init_resp.json()["media_id_string"]
    
    # APPEND chunks
    with open(video_path, "rb") as fh:
        segment = 0
        while True:
            chunk = fh.read(CHUNK_SIZE)
            if not chunk:
                break
            
            append_resp = session.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": segment,
                },
                files={"media": chunk},
                auth=oauth1,
                timeout=(10, 120),
            )
            append_resp.raise_for_status()
            segment += 1
    
    # FINALIZE
    finalize = session.post(
        "https://upload.twitter.com/1.1/media/upload.json",
        data={"command": "FINALIZE", "media_id": media_id},
        auth=oauth1,
        timeout=DEFAULT_TIMEOUT,
    )
    finalize.raise_for_status()
    
    # Poll for processing completion
    _poll_video_status_v1(media_id, oauth1)
    
    return media_id


def _poll_video_status_v1(media_id: str, oauth1: OAuth1) -> None:
    """Poll until v1.1 video processing completes."""
    session = get_session()
    
    for _ in range(60):  # Max 5 minutes
        status_resp = session.get(
            "https://upload.twitter.com/1.1/media/upload.json",
            params={"command": "STATUS", "media_id": media_id},
            auth=oauth1,
            timeout=DEFAULT_TIMEOUT,
        )
        status_resp.raise_for_status()
        
        processing = status_resp.json().get("processing_info", {})
        state = processing.get("state")
        
        if state is None or state == "succeeded":
            return
        
        if state == "failed":
            msg = processing.get("error", {}).get("message", "Unknown error")
            raise click.ClickException(f"Video processing failed: {msg}")
        
        check_after = processing.get("check_after_secs", 5)
        time.sleep(check_after)
    
    raise click.ClickException("Video processing timed out")


@with_retry(max_attempts=2, delay=2.0)
def upload_video(video_path: str, access_token: str) -> str:
    """Upload a video using v2 when allowed, else v1.1 OAuth1 fallback."""
    if not os.path.exists(video_path):
        raise click.ClickException(f"Video file not found: {video_path}")
    
    # Try v2 first
    media_id = _upload_video_v2(video_path, access_token)
    if media_id:
        return media_id
    
    # Fall back to OAuth1 flow
    oauth1 = _oauth1()
    return _upload_video_v1(video_path, oauth1)


# ---------------------------------------------------------------------------
# Tweet creation
# ---------------------------------------------------------------------------


@with_retry(max_attempts=3, delay=1.0)
def create_tweet(text: str, media_ids: list[str] | None = None) -> str:
    """Create a tweet and return its tweet-id."""
    access_token = create_oauth_session()
    session = get_session()
    
    payload: dict = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    
    resp = session.post(
        f"{API_BASE}/tweets",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code not in {200, 201}:
        raise click.ClickException(f"Error posting tweet: {resp.text}")
    
    return resp.json()["data"]["id"]
