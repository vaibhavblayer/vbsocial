"""Generate background PNG from LaTeX template."""

import subprocess
from pathlib import Path

import click


def generate_bg_png(
    output_path: Path,
    color: str = "skin",
    dpi: int = 320,
) -> Path:
    """Generate background PNG from LaTeX code.
    
    Args:
        output_path: Output PNG path
        color: Color name or hex (default: skin)
        dpi: Resolution for rendering
        
    Returns:
        Path to generated PNG
    """
    # Generate LaTeX code on the fly
    if color.startswith("#"):
        # Hex color
        hex_color = color.lstrip("#")
        color_def = f"\\definecolor{{bgcol}}{{HTML}}{{{hex_color}}}"
    else:
        # Named color
        color_map = {
            "skin": "FCEDDB",
            "matteblack": "1a1a1a",
            "black": "000000",
            "white": "FFFFFF",
            "maroon": "B62F54",  # RGB(182, 47, 84)
        }
        hex_color = color_map.get(color.lower(), "FCEDDB")
        color_def = f"\\definecolor{{bgcol}}{{HTML}}{{{hex_color}}}"
    
    latex_content = f"""\\documentclass{{article}}

% Same dimensions as post.sty
\\usepackage[paperwidth=5in, paperheight=5in, margin=0in]{{geometry}}
\\usepackage{{xcolor}}
\\usepackage{{pagecolor}}

% Define background color
{color_def}

% Set page color
\\pagecolor{{bgcol}}

% Remove page numbers
\\pagestyle{{empty}}

\\begin{{document}}

% Empty page with just the background color
~

\\end{{document}}
"""
    
    # Create temp directory for compilation
    temp_dir = output_path.parent / ".bg_temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Write LaTeX file
    temp_tex = temp_dir / "bg.tex"
    temp_tex.write_text(latex_content)
    
    # Compile LaTeX
    click.echo(f"  Compiling background...")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "bg.tex"],
        cwd=temp_dir,
        capture_output=True,
        text=True,
    )
    
    pdf_path = temp_dir / "bg.pdf"
    if not pdf_path.exists():
        raise click.ClickException(f"Failed to compile background:\n{result.stderr}")
    
    # Convert PDF to PNG using PyMuPDF
    import fitz
    from PIL import Image
    
    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    page = doc[0]
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    doc.close()
    
    # Save PNG
    img.save(output_path, "PNG")
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir)
    
    return output_path


@click.command(name="gen-bg")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output PNG path")
@click.option("--color", "-c", default="skin", help="Color (hex #FCEDDB or name)")
@click.option("--dpi", "-d", default=300, help="Resolution (default: 300)")
def gen_bg_cmd(output: Path | None, color: str, dpi: int) -> None:
    """Generate background PNG for rendering.
    
    Creates a 5x5 inch solid color background matching post dimensions.
    
    Examples:
        vbsocial gen-bg                    # Default skin color
        vbsocial gen-bg -c "#2a2a2a"       # Custom hex color
        vbsocial gen-bg -c black           # Named color
        vbsocial gen-bg -o ~/bg.png -d 600 # High res
    """
    output_path = output or Path.cwd() / "bg.png"
    
    click.echo(f"🎨 Generating background...")
    click.echo(f"  Color: {color}")
    click.echo(f"  DPI: {dpi}")
    click.echo(f"  Output: {output_path}")
    
    try:
        result_path = generate_bg_png(output_path, color, dpi)
        click.echo(f"\n✓ Created {result_path}")
        click.echo(f"\n  Use with render:")
        click.echo(f"    vbsocial render main.pdf --bg {result_path}")
    except Exception as e:
        raise click.ClickException(str(e))
