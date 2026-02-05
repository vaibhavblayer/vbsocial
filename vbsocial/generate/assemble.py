"""Assemble main.tex from existing component files."""

from pathlib import Path
import shutil
import subprocess

import click

from .templates import assemble_modular_document, get_code_file_extension
from .add import get_existing_components, update_post_yaml
from ..agents.debug import debug_enabled, log_debug


def copy_post_sty(post_path: Path) -> None:
    """Copy post.sty to the post directory if not present."""
    sty_dest = post_path / "post.sty"
    if not sty_dest.exists():
        sty_src = Path(__file__).parent / "post.sty"
        if sty_src.exists():
            shutil.copy(sty_src, sty_dest)


def preview_content(content: str, head: int = 30, tail: int = 30) -> str:
    """Get preview of content: first N chars ... last N chars."""
    content = content.strip()
    if len(content) <= head + tail + 10:
        return content
    return f"{content[:head]}...{content[-tail:]}"


def log_component(name: str, filename: str, content: str) -> None:
    """Log a component being added."""
    if not debug_enabled():
        return
    log_debug("component", {
        "file": filename,
        "preview": preview_content(content),
        "length": len(content),
    })


def log_file_output(filename: str, content: str) -> None:
    """Log a generated file with full content."""
    if not debug_enabled():
        return
    log_debug("file_output", {
        "filename": filename,
        "content": content,
        "length": len(content),
    })


@click.command(name="assemble")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--title", "-t", default="PHYSICS", help="Title for the post")
@click.option("--render", "-r", is_flag=True, help="Render after assembling")
@click.option("--preview", "-p", is_flag=True, help="Open PDF/images in zathura after render")
@click.option("--debug", "-d", is_flag=True, help="Enable debug output")
def assemble(post_path: Path, title: str, render: bool, preview: bool, debug: bool) -> None:
    """Regenerate main.tex from existing component files.
    
    Useful when component files exist but main.tex is missing or outdated.
    
    Example:
        cd ~/social_posts/2026_02_04_physics
        vbsocial assemble
        vbsocial assemble -r
        vbsocial assemble -r -p  # render and preview
        vbsocial assemble -d  # debug mode
    """
    import os
    
    # Enable debug mode if flag is set
    if debug:
        os.environ["VBSOCIAL_DEBUG"] = "1"
        from ..agents.debug import reset_debug_cache
        reset_debug_cache()
    
    # Check if valid post directory
    if not (post_path / "problem.tex").exists():
        raise click.ClickException(f"Not a valid post directory: {post_path} (no problem.tex)")
    
    click.echo(f"\n📁 Post directory: {post_path}")
    
    if debug_enabled():
        log_debug("assemble_start", {"post_path": str(post_path), "title": title})
    
    # Get existing components
    components = get_existing_components(post_path)
    click.echo(f"  Found components: {', '.join(components)}")
    
    if not components:
        raise click.ClickException("No component files found")
    
    # Log each component's content preview
    if debug_enabled():
        click.echo("\n🐛 DEBUG: Component contents:")
        for comp in components:
            # Determine file path
            if comp in ("rust", "python", "swift", "c", "zig", "go", "cpp"):
                ext = get_code_file_extension(comp)
                filename = f"datamodel.{ext}"
            else:
                filename = f"{comp}.tex"
            
            file_path = post_path / filename
            if file_path.exists():
                content = file_path.read_text()
                log_component(comp, filename, content)
                click.echo(f"  [{filename}] {preview_content(content)}")
    
    # Copy post.sty
    copy_post_sty(post_path)
    
    # Generate main.tex
    click.echo("\n📄 Generating main.tex...")
    latex_content = assemble_modular_document(components, title=title, post_path=str(post_path))
    (post_path / "main.tex").write_text(latex_content)
    
    # Log main.tex
    if debug_enabled():
        click.echo("\n🐛 DEBUG: main.tex content:")
        click.echo("-" * 60)
        click.echo(latex_content)
        click.echo("-" * 60)
        log_file_output("main.tex", latex_content)
    
    # Log code.tex if it was generated
    code_tex_path = post_path / "code.tex"
    if code_tex_path.exists() and debug_enabled():
        code_content = code_tex_path.read_text()
        click.echo("\n🐛 DEBUG: code.tex content:")
        click.echo("-" * 60)
        click.echo(code_content)
        click.echo("-" * 60)
        log_file_output("code.tex", code_content)
    
    # Update post.yaml
    update_post_yaml(post_path, components)
    
    click.echo("  ✓ Created main.tex")
    
    # Render if requested
    if render:
        click.echo("\n🖼️  Rendering...")
        subprocess.run(
            ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "main.tex"],
            cwd=post_path,
            capture_output=True,
        )
        
        pdf_path = post_path / "main.pdf"
        images_dir = post_path / "images"
        
        if pdf_path.exists():
            # Open PDF in zathura if preview requested
            if preview:
                click.echo("  📖 Opening PDF in zathura...")
                subprocess.Popen(
                    ["zathura", str(pdf_path)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            
            from .render import render_pdf_to_pngs
            render_pdf_to_pngs(
                pdf_path=pdf_path,
                output_dir=images_dir,
                dpi=300,
            )
            click.echo("  ✓ Rendered images")
            
            # Open images folder with 'open' (macOS Finder)
            if preview and images_dir.exists():
                images = sorted(images_dir.glob("*.png"))
                if images:
                    click.echo(f"  📖 Opening images folder...")
                    subprocess.Popen(
                        ["open", str(images_dir)],
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
        else:
            click.echo("  ⚠️  PDF not created, check LaTeX errors")
    
    click.echo("\n✅ Done!")
