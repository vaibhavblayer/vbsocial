"""Assemble main.tex from existing component files."""

from pathlib import Path
import shutil
import subprocess

import click

from .templates import assemble_modular_document
from .add import get_existing_components, update_post_yaml


def copy_post_sty(post_path: Path) -> None:
    """Copy post.sty to the post directory if not present."""
    sty_dest = post_path / "post.sty"
    if not sty_dest.exists():
        sty_src = Path(__file__).parent / "post.sty"
        if sty_src.exists():
            shutil.copy(sty_src, sty_dest)


@click.command(name="assemble")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--title", "-t", default="PHYSICS", help="Title for the post")
@click.option("--render", "-r", is_flag=True, help="Render after assembling")
def assemble(post_path: Path, title: str, render: bool) -> None:
    """Regenerate main.tex from existing component files.
    
    Useful when component files exist but main.tex is missing or outdated.
    
    Example:
        cd ~/social_posts/2026_02_04_physics
        vbsocial assemble
        vbsocial assemble -r
    """
    # Check if valid post directory
    if not (post_path / "problem.tex").exists():
        raise click.ClickException(f"Not a valid post directory: {post_path} (no problem.tex)")
    
    click.echo(f"\n📁 Post directory: {post_path}")
    
    # Get existing components
    components = get_existing_components(post_path)
    click.echo(f"  Found components: {', '.join(components)}")
    
    if not components:
        raise click.ClickException("No component files found")
    
    # Copy post.sty
    copy_post_sty(post_path)
    
    # Generate main.tex
    click.echo("\n📄 Generating main.tex...")
    latex_content = assemble_modular_document(components, title=title)
    (post_path / "main.tex").write_text(latex_content)
    
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
        
        if (post_path / "main.pdf").exists():
            from .render import render_pdf_to_pngs
            render_pdf_to_pngs(
                pdf_path=post_path / "main.pdf",
                output_dir=post_path / "images",
                dpi=300,
            )
            click.echo("  ✓ Rendered images")
        else:
            click.echo("  ⚠️  PDF not created, check LaTeX errors")
    
    click.echo("\n✅ Done!")
