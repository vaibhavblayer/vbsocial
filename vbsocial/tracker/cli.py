"""CLI commands for post tracking."""

import os
from datetime import datetime
from pathlib import Path

import click

from .db import PostStatus
from .manager import PostManager


def get_manager() -> PostManager:
    """Get PostManager with configured base path."""
    base_path = os.environ.get("VBSOCIAL_POSTS_PATH", "~/social_posts")
    return PostManager(base_path)


@click.group(name="track")
def track_cli():
    """Post tracking and management commands."""
    pass


@track_cli.command(name="inbox")
def inbox_cmd():
    """Show pending items in inbox folders."""
    manager = get_manager()
    inbox = manager.list_inbox()
    counts = manager.get_inbox_counts()
    
    click.echo(f"\n📥 Inbox: {manager.inbox_path}")
    click.echo(f"\n🖼️  Images ({counts['images']}):")
    if inbox["images"]:
        for img in inbox["images"]:
            click.echo(f"  • {img}")
    else:
        click.echo("  (empty)")
    
    click.echo(f"\n📄 TeX files ({counts['tex']}):")
    if inbox["tex"]:
        for tex in inbox["tex"]:
            click.echo(f"  • {tex}")
    else:
        click.echo("  (empty)")


@track_cli.command(name="process")
@click.argument("source", type=click.Path(exists=True), required=False)
@click.option("--type", "-t", "source_type", type=click.Choice(["image", "tex"]), default="image", help="Source type")
@click.option("--delete", "-d", is_flag=True, help="Delete source files after processing")
def process_cmd(source: str | None, source_type: str, delete: bool):
    """Process images or tex files into post folders.
    
    If SOURCE is provided, process files from that folder.
    Otherwise, process from inbox folders.
    
    Examples:
        vbsocial track process                    # Process inbox
        vbsocial track process ~/problems -t image
        vbsocial track process ~/tex_files -t tex -d
    """
    manager = get_manager()
    
    if source:
        results = manager.process_folder(Path(source), source_type, delete)
        click.echo(f"\n✓ Processed {len(results)} {source_type} files from {source}")
    else:
        img_results = manager.process_inbox_images(delete)
        tex_results = manager.process_inbox_tex(delete)
        results = img_results + tex_results
        click.echo(f"\n✓ Processed {len(img_results)} images, {len(tex_results)} tex files")
    
    if results:
        click.echo("\nCreated posts:")
        for post_id, folder_path in results:
            click.echo(f"  [{post_id}] {folder_path.name}")


@track_cli.command(name="list")
@click.option("--status", "-s", type=click.Choice(["draft", "ready", "posting", "posted", "failed"]), help="Filter by status")
@click.option("--limit", "-n", default=50, help="Max posts to show")
def list_cmd(status: str | None, limit: int):
    """List all tracked posts with status counts."""
    manager = get_manager()
    
    # Show counts
    counts = manager.db.count_by_status()
    total = sum(counts.values())
    
    click.echo(f"\n📊 Post Summary ({total} total):")
    click.echo(f"  📝 Draft:   {counts.get('draft', 0)}")
    click.echo(f"  ✅ Ready:   {counts.get('ready', 0)}")
    click.echo(f"  ⏳ Posting: {counts.get('posting', 0)}")
    click.echo(f"  📤 Posted:  {counts.get('posted', 0)}")
    click.echo(f"  ❌ Failed:  {counts.get('failed', 0)}")
    
    # List posts
    filter_status = PostStatus(status) if status else None
    posts = manager.db.list_posts(status=filter_status, limit=limit)
    
    if not posts:
        click.echo("\n(no posts)")
        return
    
    click.echo(f"\n📋 Posts{f' ({status})' if status else ''}:")
    for post in posts:
        status_icon = {
            "draft": "📝",
            "ready": "✅", 
            "posting": "⏳",
            "posted": "📤",
            "failed": "❌",
        }.get(post["status"], "❓")
        scheduled = ""
        if post["scheduled_for"]:
            sched_date = post["scheduled_for"][:10]
            scheduled = f" 📅 {sched_date}"
        
        error_hint = ""
        if post["status"] == "failed" and post.get("last_error"):
            error_hint = " ⚠️"
        
        title = post["title"] or "(untitled)"
        click.echo(f"  {status_icon} [{post['id']}] {title}{scheduled}{error_hint}")


@track_cli.command(name="status")
@click.argument("post_id")
@click.argument("new_status", type=click.Choice(["draft", "ready", "posted"]))
def status_cmd(post_id: str, new_status: str):
    """Change post status and rename folder.
    
    Note: Use 'retry' command for failed posts.
    
    Examples:
        vbsocial track status a1b2c3 ready
        vbsocial track status a1b2c3 posted
    """
    manager = get_manager()
    status = PostStatus(new_status)
    
    new_path = manager.update_status(post_id, status)
    if new_path:
        click.echo(f"✓ [{post_id}] → {status.value}")
        click.echo(f"  Folder: {new_path.name}")
    else:
        raise click.ClickException(f"Post not found or update failed: {post_id}")


@track_cli.command(name="schedule")
@click.argument("post_id")
@click.argument("date", required=False)
@click.option("--clear", "-c", is_flag=True, help="Clear schedule")
def schedule_cmd(post_id: str, date: str | None, clear: bool):
    """Schedule a ready post for a specific date.
    
    DATE format: YYYY-MM-DD or YYYY_MM_DD
    
    Examples:
        vbsocial track schedule a1b2c3 2026-02-10
        vbsocial track schedule a1b2c3 --clear
    """
    manager = get_manager()
    
    if clear:
        if manager.db.unschedule_post(post_id):
            click.echo(f"✓ [{post_id}] Schedule cleared")
        else:
            raise click.ClickException(f"Failed to clear schedule: {post_id}")
        return
    
    if not date:
        raise click.ClickException("Provide a date or use --clear")
    
    # Parse date
    date = date.replace("_", "-")
    try:
        scheduled_dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.ClickException(f"Invalid date format: {date}. Use YYYY-MM-DD")
    
    # Check post is ready
    post = manager.db.get_post(post_id)
    if not post:
        raise click.ClickException(f"Post not found: {post_id}")
    
    if post["status"] != PostStatus.READY.value:
        raise click.ClickException(f"Only ready posts can be scheduled. Current status: {post['status']}")
    
    if manager.db.schedule_post(post_id, scheduled_dt):
        click.echo(f"✓ [{post_id}] Scheduled for {date}")
    else:
        raise click.ClickException(f"Failed to schedule: {post_id}")


@track_cli.command(name="scheduled")
def scheduled_cmd():
    """Show all scheduled posts."""
    manager = get_manager()
    posts = manager.db.get_scheduled_posts(datetime(2099, 12, 31))  # Get all scheduled
    
    if not posts:
        click.echo("\n(no scheduled posts)")
        return
    
    click.echo(f"\n📅 Scheduled Posts ({len(posts)}):")
    now = datetime.now()
    
    for post in posts:
        sched_dt = datetime.fromisoformat(post["scheduled_for"])
        is_due = sched_dt <= now
        due_marker = " ⏰ DUE" if is_due else ""
        
        title = post["title"] or "(untitled)"
        click.echo(f"  [{post['id']}] {sched_dt.strftime('%Y-%m-%d')} - {title}{due_marker}")


@track_cli.command(name="info")
@click.argument("post_id")
def info_cmd(post_id: str):
    """Show detailed info about a post."""
    manager = get_manager()
    post = manager.db.get_post(post_id)
    
    if not post:
        raise click.ClickException(f"Post not found: {post_id}")
    
    status_icon = {
        "draft": "📝",
        "ready": "✅", 
        "posting": "⏳",
        "posted": "📤",
        "failed": "❌",
    }.get(post["status"], "❓")
    
    click.echo(f"\n📋 Post [{post_id}]")
    click.echo(f"  Title:       {post['title'] or '(untitled)'}")
    click.echo(f"  Status:      {status_icon} {post['status']}")
    click.echo(f"  Created:     {post['created_at'][:19]}")
    click.echo(f"  Updated:     {post['updated_at'][:19]}")
    click.echo(f"  Source:      {post['source_type']} - {post['source_file']}")
    click.echo(f"  Folder:      {post['folder_path']}")
    
    if post["scheduled_for"]:
        click.echo(f"  Scheduled:   {post['scheduled_for'][:10]}")
    
    if post.get("posted_at"):
        click.echo(f"  Posted at:   {post['posted_at'][:19]}")
    
    if post.get("last_error"):
        click.echo(f"  Last Error:  {post['last_error']}")
    
    if post.get("post_ids"):
        import json
        ids = json.loads(post["post_ids"])
        click.echo(f"  Platform IDs:")
        for platform, pid in ids.items():
            click.echo(f"    • {platform}: {pid}")


@track_cli.command(name="daemon")
@click.option("--interval", "-i", default=300, help="Check interval in seconds (default 300 = 5 min)")
def daemon_cmd(interval: int):
    """Run the scheduler daemon (for LaunchAgent)."""
    from .scheduler import Scheduler
    
    scheduler = Scheduler(check_interval=interval)
    scheduler.run_daemon()


@track_cli.command(name="post-due")
def post_due_cmd():
    """Post all due scheduled posts (one-time check)."""
    from .scheduler import Scheduler
    
    scheduler = Scheduler()
    scheduler.run_once()


@track_cli.command(name="scheduler")
@click.argument("action", type=click.Choice(["install", "uninstall", "status", "logs"]))
def scheduler_cmd(action: str):
    """Manage the automatic scheduler daemon.
    
    Actions:
        install   - Install and start the scheduler daemon
        uninstall - Stop and remove the scheduler daemon
        status    - Check if daemon is running
        logs      - Show recent scheduler logs
    """
    from .scheduler import install_launchagent, uninstall_launchagent, is_daemon_running
    
    if action == "install":
        plist_path, success = install_launchagent()
        if success:
            click.echo(f"✓ Scheduler daemon installed and started")
            click.echo(f"  Plist: {plist_path}")
            click.echo(f"  Logs:  ~/social_posts/scheduler.log")
            click.echo("\n  The daemon will automatically post scheduled posts.")
        else:
            click.echo("✗ Failed to install scheduler daemon")
    
    elif action == "uninstall":
        if uninstall_launchagent():
            click.echo("✓ Scheduler daemon uninstalled")
        else:
            click.echo("Scheduler daemon was not installed")
    
    elif action == "status":
        if is_daemon_running():
            click.echo("✓ Scheduler daemon is running")
        else:
            click.echo("✗ Scheduler daemon is not running")
            click.echo("  Run: vbsocial track scheduler install")
    
    elif action == "logs":
        import subprocess
        log_path = Path("~/social_posts/scheduler.log").expanduser()
        if log_path.exists():
            subprocess.run(["tail", "-50", str(log_path)])
        else:
            click.echo("No logs yet")


@track_cli.command(name="retry")
@click.argument("post_id")
def retry_cmd(post_id: str):
    """Retry a failed post."""
    manager = get_manager()
    
    post = manager.db.get_post(post_id)
    if not post:
        raise click.ClickException(f"Post not found: {post_id}")
    
    if post["status"] != PostStatus.FAILED.value:
        raise click.ClickException(f"Post is not failed. Status: {post['status']}")
    
    if manager.db.retry_failed(post_id):
        click.echo(f"✓ [{post_id}] Reset to ready status")
        click.echo("  Will be posted on next scheduled check, or run:")
        click.echo(f"  vbsocial track post-due")
    else:
        raise click.ClickException("Failed to reset post status")


@track_cli.command(name="failed")
def failed_cmd():
    """Show failed posts with error messages."""
    manager = get_manager()
    posts = manager.db.list_posts(status=PostStatus.FAILED)
    
    if not posts:
        click.echo("\n✓ No failed posts")
        return
    
    click.echo(f"\n❌ Failed Posts ({len(posts)}):")
    for post in posts:
        title = post["title"] or "(untitled)"
        error = post["last_error"] or "(no error message)"
        click.echo(f"\n  [{post['id']}] {title}")
        click.echo(f"    Error: {error}")
        click.echo(f"    Retry: vbsocial track retry {post['id']}")


@track_cli.command(name="gen")
@click.argument("post_id")
@click.option("--topic", "-t", help="Topic/title for the post")
@click.option("--type", "-q", "question_type", 
              type=click.Choice(["subjective", "mcq_sc", "mcq_mc", "assertion_reason", "passage", "match"]),
              default="subjective", help="Question type")
@click.option("--code", "-c", type=click.Choice(["rust", "python", "swift", "c", "zig", "go"]), help="Include code")
@click.option("--render", "-r", is_flag=True, help="Render to images after generation")
def gen_cmd(post_id: str, topic: str | None, question_type: str, code: str | None, render: bool):
    """Generate post content from a tracked post's source image.
    
    This runs the full generation pipeline on the problem_image in the post folder.
    
    Example:
        vbsocial track gen 17d945
        vbsocial track gen 17d945 -t "Heat conduction" -c rust -r
    """
    import subprocess
    
    manager = get_manager()
    post = manager.db.get_post(post_id)
    
    if not post:
        raise click.ClickException(f"Post not found: {post_id}")
    
    folder_path = Path(post["folder_path"])
    if not folder_path.exists():
        raise click.ClickException(f"Folder not found: {folder_path}")
    
    # Find the problem image
    image_path = None
    for pattern in ["problem_image.*", "problem.*"]:
        for ext in [".png", ".jpg", ".jpeg", ".gif"]:
            matches = list(folder_path.glob(f"problem_image{ext}")) + list(folder_path.glob(f"problem{ext}"))
            if matches:
                image_path = matches[0]
                break
        if image_path:
            break
    
    if not image_path:
        raise click.ClickException(f"No problem image found in {folder_path}")
    
    click.echo(f"📷 Image: {image_path.name}")
    click.echo(f"📁 Output: {folder_path}")
    
    # Build command
    cmd = ["python", "-m", "vbsocial", "from-image", str(image_path), 
           "--name", folder_path.name, "-t", question_type]
    
    if code:
        cmd.extend(["-c", code])
    if render:
        cmd.append("-r")
    
    # Run from-image (it will create in posts dir, but we want in existing folder)
    # Actually, let's use the internal function directly
    from ..generate.from_image import (
        run_vbagent_scan,
        parse_scan_results,
        run_vbagent_idea,
    )
    from ..generate.templates import (
        replace_item_with_lambda,
        create_solution_slide,
        create_idea_slide,
        assemble_modular_document,
        has_diagram_reference,
        get_code_file_extension,
    )
    
    click.echo(f"\n🔍 Scanning image with vbagent (type: {question_type})...")
    
    results = [run_vbagent_scan(str(image_path), question_type)]
    problem, solution = parse_scan_results(results)
    
    if not problem:
        raise click.ClickException("Could not extract problem from image")
    
    components = []
    
    # Save problem.tex
    click.echo("📝 Creating problem.tex...")
    problem_content = replace_item_with_lambda(problem)
    (folder_path / "problem.tex").write_text(problem_content)
    components.append("problem")
    
    # Check for diagram
    if has_diagram_reference(problem_content):
        click.echo("🎨 Generating TikZ diagram...")
        try:
            from ..agents.tikz import generate_tikz
            tikz_code = generate_tikz(problem=problem, solution=solution, image_path=str(image_path))
            if tikz_code:
                (folder_path / "diagram.tex").write_text(tikz_code)
                components.append("diagram")
        except Exception as e:
            click.echo(f"  ⚠️  Diagram failed: {e}")
    
    # Save solution.tex
    if solution:
        click.echo("✅ Creating solution.tex...")
        (folder_path / "solution.tex").write_text(create_solution_slide(solution))
        components.append("solution")
    
    # Save idea.tex
    click.echo("💡 Extracting key idea...")
    full_latex = "\n\n".join(r.latex for r in results if r.latex)
    idea = run_vbagent_idea(full_latex)
    if idea:
        if r"\begin{idea}" in idea:
            idea_content = idea.split(r"\begin{idea}")[1].split(r"\end{idea}")[0].strip()
        else:
            idea_content = idea
        (folder_path / "idea.tex").write_text(create_idea_slide(idea_content))
        components.append("idea")
    
    # Code generation
    if code:
        click.echo(f"💻 Generating {code} data model...")
        try:
            from ..agents.datamodel import generate_datamodel
            code_content = generate_datamodel(problem=problem, language=code, solution=solution)
            if code_content:
                ext = get_code_file_extension(code)
                (folder_path / f"datamodel.{ext}").write_text(code_content)
                components.append(code)
        except Exception as e:
            click.echo(f"  ⚠️  Code failed: {e}")
    
    # Assemble main.tex
    click.echo("📄 Assembling main.tex...")
    latex_content = assemble_modular_document(components, post_path=str(folder_path))
    (folder_path / "main.tex").write_text(latex_content)
    
    # Render if requested
    if render:
        click.echo("\n🖼️  Rendering...")
        subprocess.run(
            ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "main.tex"],
            cwd=folder_path,
            capture_output=True,
        )
        if (folder_path / "main.pdf").exists():
            from ..generate.render import render_pdf_to_pngs
            (folder_path / "images").mkdir(exist_ok=True)
            render_pdf_to_pngs(folder_path / "main.pdf", folder_path / "images", dpi=300)
    
    click.echo(f"\n✓ Generated content in [{post_id}]")
    click.echo(f"  Components: {', '.join(components)}")
    click.echo(f"\n  Next steps:")
    click.echo(f"    vbsocial add <component> {folder_path}")
    click.echo(f"    vbsocial assemble {folder_path} -r")


@track_cli.command(name="open")
@click.argument("post_id")
def open_cmd(post_id: str):
    """Open post folder in Finder."""
    import subprocess
    
    manager = get_manager()
    post = manager.db.get_post(post_id)
    
    if not post:
        raise click.ClickException(f"Post not found: {post_id}")
    
    folder_path = Path(post["folder_path"])
    if not folder_path.exists():
        raise click.ClickException(f"Folder not found: {folder_path}")
    
    subprocess.run(["open", str(folder_path)])
    click.echo(f"📂 Opened {folder_path.name}")
