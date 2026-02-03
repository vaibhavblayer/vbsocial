"""LinkedIn analytics."""

import os

import click

from ..linkedin.auth import create_oauth_session
from ..common.http import get_session, DEFAULT_TIMEOUT

LINKEDIN_VERSION = "202601"


def get_headers(access_token: str) -> dict:
    """Get headers for LinkedIn API."""
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
    }


def get_profile_info(access_token: str) -> dict:
    """Get LinkedIn profile info."""
    session = get_session()
    
    resp = session.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_org_info(access_token: str, org_id: str) -> dict:
    """Get organization info."""
    session = get_session()
    
    resp = session.get(
        f"https://api.linkedin.com/rest/organizations/{org_id}",
        headers=get_headers(access_token),
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code != 200:
        return {"localizedName": f"Org {org_id}"}
    
    return resp.json()


def get_org_followers(access_token: str, org_id: str) -> int:
    """Get organization follower count."""
    session = get_session()
    
    resp = session.get(
        f"https://api.linkedin.com/rest/networkSizes/urn:li:organization:{org_id}",
        headers=get_headers(access_token),
        params={"edgeType": "COMPANY_FOLLOWED_BY_MEMBER"},
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code != 200:
        return 0
    
    return resp.json().get("firstDegreeSize", 0)


def get_recent_posts(access_token: str, author_urn: str, limit: int = 10) -> list:
    """Get recent posts with metrics."""
    session = get_session()
    
    resp = session.get(
        "https://api.linkedin.com/rest/posts",
        headers=get_headers(access_token),
        params={
            "author": author_urn,
            "q": "author",
            "count": limit,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code != 200:
        return []
    
    return resp.json().get("elements", [])


def get_post_stats(access_token: str, post_urn: str) -> dict:
    """Get stats for a specific post."""
    session = get_session()
    
    resp = session.get(
        f"https://api.linkedin.com/rest/socialActions/{post_urn}",
        headers=get_headers(access_token),
        timeout=DEFAULT_TIMEOUT,
    )
    
    if resp.status_code != 200:
        return {}
    
    data = resp.json()
    return {
        "likes": data.get("likesSummary", {}).get("totalLikes", 0),
        "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
    }


@click.command(name="stats")
@click.option("--posts", "-p", default=5, help="Number of recent posts to show")
def linkedin_stats(posts: int) -> None:
    """Show LinkedIn stats and recent post metrics."""
    try:
        access_token = create_oauth_session()
        org_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
        
        if org_id:
            org_info = get_org_info(access_token, org_id)
            followers = get_org_followers(access_token, org_id)
            author_urn = f"urn:li:organization:{org_id}"
            name = org_info.get("localizedName", f"Org {org_id}")
            
            click.echo(f"\n💼 LinkedIn (Org): {name}")
            click.echo("=" * 50)
            click.echo(f"Followers: {followers:,}")
        else:
            profile = get_profile_info(access_token)
            author_urn = f"urn:li:person:{profile.get('sub')}"
            name = profile.get("name", "Unknown")
            
            click.echo(f"\n💼 LinkedIn: {name}")
            click.echo("=" * 50)
        
        if posts > 0:
            post_list = get_recent_posts(access_token, author_urn, posts)
            if post_list:
                click.echo(f"\n📊 Recent Posts:")
                click.echo(f"{'Date':<12} {'Likes':>8} {'Comments':>10} {'Commentary':<30}")
                click.echo("-" * 65)
                
                for item in post_list:
                    created = item.get("createdAt", 0)
                    if created:
                        from datetime import datetime
                        date = datetime.fromtimestamp(created / 1000).strftime("%Y-%m-%d")
                    else:
                        date = "N/A"
                    
                    post_urn = item.get("id", "")
                    stats = get_post_stats(access_token, post_urn)
                    
                    commentary = (item.get("commentary") or "")[:28]
                    if len(item.get("commentary") or "") > 28:
                        commentary += "…"
                    
                    click.echo(f"{date:<12} {stats.get('likes', 0):>8,} {stats.get('comments', 0):>10,} {commentary:<30}")
    
    except Exception as e:
        click.echo(f"❌ LinkedIn: {e}")
