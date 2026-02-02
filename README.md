# vbsocial

A command-line tool for posting to multiple social media platforms.

## Supported Platforms

| Platform | Features |
|----------|----------|
| **Instagram** | Photos, carousels, videos (reels), stories |
| **Facebook** | Photos, videos, stories |
| **LinkedIn** | Text posts, images, videos, URL shares |
| **X (Twitter)** | Text, images, videos |
| **YouTube** | Video uploads, shorts, analytics, video management |

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vbsocial.git
cd vbsocial

# Install with pip
pip install -e .

# Or with poetry
poetry install
```

## Quick Start

```bash
# Post to Instagram
vbsocial instagram post -i photo.jpg -c "Hello Instagram!"

# Post a carousel
vbsocial instagram post -i img1.jpg -i img2.jpg -c "Carousel post"

# Post to Instagram Story
vbsocial instagram post -s -i story.jpg

# Post to Facebook
vbsocial facebook post photo image.jpg -m "Hello Facebook!"

# Post to LinkedIn
vbsocial linkedin post -m "Hello LinkedIn!" -i image.jpg

# Post to X (Twitter)
vbsocial x post -m "Hello X!" -i image.jpg

# Upload to YouTube
vbsocial youtube upload -m metadata.json -p public

# Upload a YouTube Short
vbsocial youtube shorts video.mp4 -t "My Short" -d "Description"
```

## Configuration

Each platform requires initial setup:

### Instagram & Facebook

```bash
vbsocial instagram configure
vbsocial facebook configure
```

You'll need:
- Facebook App ID and Secret from [developers.facebook.com](https://developers.facebook.com)
- Access token from Graph API Explorer

### LinkedIn

Set environment variables:
```bash
export LINKEDIN_CLIENT_ID_10X='your_client_id'
export LINKEDIN_CLIENT_SECRET_10X='your_client_secret'
```

Then run any LinkedIn command to trigger OAuth flow.

### X (Twitter)

Set environment variables:
```bash
export X_CLIENT_ID_10X='your_client_id'
export X_CLIENT_SECRET_10X='your_client_secret'
```

Then run any X command to trigger OAuth flow.

### YouTube

Place your OAuth client credentials at:
```
~/.vbsocial/youtube/client_secret.json
```

Get credentials from [Google Cloud Console](https://console.cloud.google.com/).

## Commands Reference

### Instagram

```bash
vbsocial instagram configure          # Setup credentials
vbsocial instagram post -i IMG -c TXT # Post photo/carousel
vbsocial instagram post -v VID -c TXT # Post video (reel)
vbsocial instagram post -s -i IMG     # Post story (photo)
vbsocial instagram post -s -v VID     # Post story (video)
vbsocial instagram refresh            # Refresh access token
```

### Facebook

```bash
vbsocial facebook configure                    # Setup credentials
vbsocial facebook post photo IMG -m TXT        # Post photo
vbsocial facebook post video VID -m TXT        # Post video
vbsocial facebook post story_photo IMG         # Post story photo
vbsocial facebook post story_video VID         # Post story video
```

### LinkedIn

```bash
vbsocial linkedin post -m TXT                  # Text post
vbsocial linkedin post -m TXT -i IMG           # Post with image
vbsocial linkedin post -m TXT -v VID           # Post with video
vbsocial linkedin post -m TXT -u URL           # Post with URL preview
vbsocial linkedin post -m TXT --personal       # Post to personal profile
vbsocial linkedin post -m TXT -o ORG_ID        # Post to organization page
```

### X (Twitter)

```bash
vbsocial x post -m TXT                         # Text tweet
vbsocial x post -m TXT -i IMG                  # Tweet with image
vbsocial x post -m TXT -v VID                  # Tweet with video
```

### YouTube

```bash
vbsocial youtube upload -m META -p PRIVACY     # Upload video
vbsocial youtube shorts VID -t TITLE           # Upload Short
vbsocial youtube info VIDEO_ID                 # View video details
vbsocial youtube edit VIDEO_ID -t TITLE        # Update video
vbsocial youtube stats                         # Channel statistics
vbsocial youtube videos                        # List videos
vbsocial youtube sync                          # Sync local/SSD files
```

## Token Storage

All tokens are stored securely in `~/.vbsocial/` with restricted file permissions (600).

```
~/.vbsocial/
├── facebook/config.json
├── instagram/config.json
├── linkedin/token.json
├── x/token.json
└── youtube/
    ├── client_secret.json
    └── token.json
```

## Development

```bash
# Install dev dependencies
poetry install

# Run tests
pytest

# Run a specific test
pytest tests/test_common.py -v
```

## License

MIT
