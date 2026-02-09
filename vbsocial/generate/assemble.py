"""Assemble main.tex from existing component files."""

from pathlib import Path
import shutil
import subprocess

import click

from .templates import assemble_modular_document, get_code_file_extension
from .add import get_existing_components, update_post_yaml
from ..agents.debug import debug_enabled, log_debug


def resolve_color(color: str) -> str:
    """Resolve color name or hex to hex value.
    
    Args:
        color: Color name (maroon, black, etc.) or hex (#B62F54)
        
    Returns:
        Hex color without # (e.g., "B62F54")
    """
    if color.startswith("#"):
        return color.lstrip("#")
    
    # Named colors
    color_map = {
        "maroon": "B62F54",
        "black": "000000",
        "white": "FFFFFF",
        "skin": "FCEDDB",
        "matteblack": "1a1a1a",
    }
    
    return color_map.get(color.lower(), "B62F54")  # Default to maroon


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
@click.option("--title", "-t", default="Physics", help="Title for the post")
@click.option("--code-theme", "-c", default="xcode", help="Code theme (name or number, default: xcode)")
@click.option("--fg-color", "--fg", default="maroon", help="Foreground text color (hex or name, default: maroon)")
@click.option("--list-themes", is_flag=True, help="List all available code themes")
@click.option("--render", "-r", is_flag=True, help="Render after assembling")
@click.option("--preview", "-p", is_flag=True, help="Open PDF/images in zathura after render")
@click.option("--debug", "-d", is_flag=True, help="Enable debug output")
def assemble(post_path: Path, title: str, code_theme: str, fg_color: str, list_themes: bool, render: bool, preview: bool, debug: bool) -> None:
    """Regenerate main.tex from existing component files.
    
    Useful when component files exist but main.tex is missing or outdated.
    
    Example:
        vbsocial assemble
        vbsocial assemble --list-themes
        vbsocial assemble --code-theme monokai
        vbsocial assemble --code-theme 5
        vbsocial assemble --fg-color maroon
        vbsocial assemble --fg "#B62F54"
        vbsocial assemble -r -p  # render and preview
        vbsocial assemble -d  # debug mode
    """
    from .code_themes import get_theme, list_themes as list_all_themes
    
    # List themes if requested
    if list_themes:
        click.echo(list_all_themes())
        return
    
    import os
    
    # Enable debug mode if flag is set
    if debug:
        os.environ["VBSOCIAL_DEBUG"] = "1"
        from ..agents.debug import reset_debug_cache
        reset_debug_cache()
    
    # Resolve theme name
    theme = get_theme(code_theme)
    
    # Resolve foreground color (hex or name)
    fg_hex = resolve_color(fg_color)
    
    # Check if valid post directory
    if not (post_path / "problem.tex").exists():
        raise click.ClickException(f"Not a valid post directory: {post_path} (no problem.tex)")
    
    click.echo(f"\n📁 Post directory: {post_path}")
    click.echo(f"  Code theme: {theme}")
    click.echo(f"  Foreground color: #{fg_hex}")
    
    if debug_enabled():
        log_debug("assemble_start", {"post_path": str(post_path), "title": title, "code_theme": theme, "fg_color": fg_hex})
    
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
    latex_content = assemble_modular_document(components, title=title, post_path=str(post_path), code_theme=theme, fg_color=fg_hex)
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
                dpi=320,
                blur=True,
                blur_radius=4,
                blur_opacity=0.3,
                blur_offset=(3, 3),
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
