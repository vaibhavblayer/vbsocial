"""Scheduler daemon for automatic posting."""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from .db import PostDB, PostStatus
from .manager import PostManager

# Setup logging
LOG_PATH = Path("~/social_posts/scheduler.log").expanduser()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class Scheduler:
    """Background scheduler for automatic posting."""
    
    def __init__(self, base_path: str = "~/social_posts", check_interval: int = 300):
        """
        Args:
            base_path: Base path for posts
            check_interval: Seconds between checks (default 5 minutes)
        """
        self.manager = PostManager(base_path)
        self.check_interval = check_interval
        self.running = False
    
    def post_single(self, post: dict) -> tuple[bool, str, dict]:
        """Post a single post to all platforms.
        
        Returns (success, error_message, platform_ids).
        """
        from pathlib import Path
        
        folder_path = Path(post["folder_path"])
        if not folder_path.exists():
            return False, f"Folder not found: {folder_path}", {}
        
        # Import post functions
        from ..post.post_all import (
            load_post_config,
            get_images,
            post_to_facebook,
            post_to_instagram,
            post_to_linkedin,
            post_to_x,
        )
        
        try:
            config = load_post_config(folder_path)
            images = get_images(folder_path)
            captions = config.get("captions", {})
        except Exception as e:
            return False, f"Failed to load post config: {e}", {}
        
        post_ids = {}
        errors = []
        
        # Post to each platform
        platforms = [
            ("facebook", post_to_facebook),
            ("instagram", post_to_instagram),
            ("linkedin", post_to_linkedin),
            ("x", post_to_x),
        ]
        
        for platform, post_fn in platforms:
            caption = captions.get(platform, "")
            if not caption:
                continue
            
            try:
                result = post_fn(images, caption)
                if result:
                    post_ids[platform] = result
                    logger.info(f"  ✓ Posted to {platform}: {result}")
            except Exception as e:
                error_msg = f"{platform}: {e}"
                errors.append(error_msg)
                logger.error(f"  ✗ {error_msg}")
        
        if errors and not post_ids:
            return False, "; ".join(errors), post_ids
        
        return True, "", post_ids
    
    def check_and_post(self):
        """Check for due posts and post them."""
        due_posts = self.manager.db.get_due_posts()
        
        if not due_posts:
            logger.debug("No posts due")
            return
        
        logger.info(f"Found {len(due_posts)} due post(s)")
        
        for post in due_posts:
            post_id = post["id"]
            title = post["title"] or "(untitled)"
            
            logger.info(f"Posting [{post_id}] {title}...")
            
            # Mark as posting
            self.manager.db.mark_posting(post_id)
            
            # Attempt to post
            success, error, platform_ids = self.post_single(post)
            
            if success:
                self.manager.db.mark_posted(post_id, platform_ids)
                # Update folder name to posted
                self.manager.update_status(post_id, PostStatus.POSTED)
                logger.info(f"✓ [{post_id}] Posted successfully")
            else:
                self.manager.db.mark_failed(post_id, error)
                logger.error(f"✗ [{post_id}] Failed: {error}")

    def run_once(self):
        """Run a single check (for cron/manual use)."""
        logger.info("Running scheduled post check...")
        self.check_and_post()
        logger.info("Check complete")
    
    def run_daemon(self):
        """Run as a daemon, checking periodically."""
        logger.info(f"Scheduler daemon started (interval: {self.check_interval}s)")
        self.running = True
        
        # Handle signals for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        while self.running:
            try:
                self.check_and_post()
            except Exception as e:
                logger.error(f"Error during check: {e}")
            
            # Sleep in small intervals to respond to signals
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("Scheduler daemon stopped")


def create_launchagent():
    """Create macOS LaunchAgent plist for automatic scheduling."""
    plist_dir = Path("~/Library/LaunchAgents").expanduser()
    plist_dir.mkdir(parents=True, exist_ok=True)
    
    plist_path = plist_dir / "com.vbsocial.scheduler.plist"
    
    # Get Python path
    python_path = sys.executable
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vbsocial.scheduler</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>vbsocial</string>
        <string>track</string>
        <string>daemon</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>{Path("~/social_posts/scheduler.log").expanduser()}</string>
    
    <key>StandardErrorPath</key>
    <string>{Path("~/social_posts/scheduler.log").expanduser()}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:{Path(python_path).parent}</string>
    </dict>
</dict>
</plist>
"""
    
    plist_path.write_text(plist_content)
    return plist_path


def install_launchagent():
    """Install and load the LaunchAgent."""
    plist_path = create_launchagent()
    
    # Unload if already loaded
    os.system(f"launchctl unload {plist_path} 2>/dev/null")
    
    # Load the agent
    result = os.system(f"launchctl load {plist_path}")
    
    return plist_path, result == 0


def uninstall_launchagent():
    """Unload and remove the LaunchAgent."""
    plist_path = Path("~/Library/LaunchAgents/com.vbsocial.scheduler.plist").expanduser()
    
    if plist_path.exists():
        os.system(f"launchctl unload {plist_path}")
        plist_path.unlink()
        return True
    return False


def is_daemon_running() -> bool:
    """Check if the scheduler daemon is running."""
    result = os.popen("launchctl list | grep com.vbsocial.scheduler").read()
    return "com.vbsocial.scheduler" in result
