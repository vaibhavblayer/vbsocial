"""PDF to PNG rendering with blur layer and background stacking.

Uses PyMuPDF (fitz) for fast PDF rendering.
Similar approach to vbimage: blur, layer, stack.
"""

from pathlib import Path

import click
import fitz  # PyMuPDF
from PIL import Image, ImageFilter

# Default background image path
DEFAULT_BG_IMAGE = Path.home() / "10xphysics/backgrounds/bg_instagram.jpg"


def pdf_to_images(pdf_path: Path, dpi: int = 300) -> list[Image.Image]:
    """Convert PDF pages to PIL Images using PyMuPDF.
    
    No border/padding - exact PDF size.
    """
    doc = fitz.open(str(pdf_path))
    images = []
    
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=True)
        img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
        images.append(img)
    
    doc.close()
    return images


def blur_image(image: Image.Image, radius: int = 2, opacity: float = 1.0) -> Image.Image:
    """Blur image with optional opacity adjustment.
    
    Args:
        image: Source RGBA image
        radius: Gaussian blur radius
        opacity: Opacity multiplier for alpha channel (0-1)
        
    Returns:
        Blurred RGBA image
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    blurred = image.filter(ImageFilter.GaussianBlur(radius))
    
    # Adjust opacity
    if opacity < 1.0:
        datas = blurred.getdata()
        new_data = []
        for item in datas:
            new_data.append((item[0], item[1], item[2], int(opacity * item[3])))
        blurred.putdata(new_data)
    
    return blurred


def create_blurred_version(
    image: Image.Image,
    blur_radius: int = 2,
    blur_opacity: float = 1,
) -> Image.Image:
    """Create blurred version of the original image.
    
    Args:
        image: Source RGBA image
        blur_radius: Blur radius
        blur_opacity: Opacity of blurred image
        
    Returns:
        Blurred RGBA image
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # Blur the original image itself
    blurred = blur_image(image, radius=blur_radius, opacity=blur_opacity)
    
    return blurred


def color_layer(image: Image.Image, color: tuple[int, int, int], opacity: float = 1.0) -> Image.Image:
    """Replace image colors with solid color, keeping alpha.
    
    Args:
        image: Source RGBA image
        color: RGB color to apply
        opacity: Opacity multiplier
        
    Returns:
        Colored RGBA image (shadow layer)
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    img = image.copy()
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        if item[3] != 0:
            new_data.append((color[0], color[1], color[2], int(opacity * item[3])))
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img


def stack_images(front: Image.Image, background: Image.Image, position: tuple[int, int] = (0, 0)) -> Image.Image:
    """Stack front image on background.
    
    Args:
        front: Front RGBA image
        background: Background image (will be resized to match front)
        position: Offset from center
        
    Returns:
        Composited RGBA image
    """
    front = front.convert("RGBA")
    bg = background.convert("RGBA")
    bg = bg.resize((front.width, front.height), Image.Resampling.LANCZOS)
    
    width = (bg.width - front.width) // 2
    height = (bg.height - front.height) // 2
    bg.paste(front, (width + position[0], height + position[1]), front)
    
    return bg


def create_blurred_version(
    image: Image.Image,
    blur_radius: int = 25,
    blur_opacity: float = 0.8,
) -> Image.Image:
    """Create blurred version of the image.
    
    Args:
        image: Source RGBA image
        blur_radius: Blur radius
        blur_opacity: Opacity of blurred image
        
    Returns:
        Blurred RGBA image
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # Blur the entire image
    blurred = blur_image(image, radius=blur_radius, opacity=blur_opacity)
    
    return blurred


def render_pdf_to_pngs(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 300,
    blur: bool = True,
    blur_radius: int = 25,
    blur_opacity: float = 0.8,
    blur_offset: tuple[int, int] = (5, 5),
    bg_image_path: Path | None = None,
    bg_color: tuple[int, int, int] | None = None,
    prefix: str = "slide",
    debug: bool = False,
) -> list[Path]:
    """Render PDF to PNG images with blur and background.

    Pipeline:
    1. PDF -> PNG (transparent background) = original
    2. Blur the original image = blurred_original
    3. Generate background PNG from bg.tex if not provided
    4. Stack: bg + blurred_original (offset 5px,5px) + original (centered, no offset)

    Args:
        debug: If True, save intermediate stages in .debug/ folder
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create debug directory if needed
    debug_dir = None
    if debug:
        debug_dir = output_dir / ".debug"
        debug_dir.mkdir(exist_ok=True)

    # Generate or load background
    bg_image = None
    if bg_image_path and bg_image_path.exists():
        bg_image = Image.open(bg_image_path)
    elif not bg_color:
        # Generate default skin background
        from .bg_gen import generate_bg_png
        bg_temp = output_dir / ".bg_temp.png"
        generate_bg_png(bg_temp, color="skin", dpi=dpi)
        bg_image = Image.open(bg_temp)

    # Save background in debug mode
    if debug and bg_image:
        bg_image.save(debug_dir / "bg.png", "PNG")

    # Convert PDF to images
    pages = pdf_to_images(pdf_path, dpi=dpi)

    output_paths = []
    for i, page in enumerate(pages, 1):
        # Stage 1: Original (no blur, no bg)
        original = page.copy()
        if debug:
            original.save(debug_dir / f"{prefix}-{i}_1_original.png", "PNG")

        # Stage 2: Create blurred version of original image
        blurred_original = None
        if blur:
            blurred_original = create_blurred_version(
                page,
                blur_radius=blur_radius,
                blur_opacity=blur_opacity,
            )
            if debug:
                blurred_original.save(debug_dir / f"{prefix}-{i}_2_blurred.png", "PNG")

        # Stage 3: Stack on background: bg + blurred_original (offset) + original (centered)
        final = original
        if bg_image or bg_color:
            # Create background canvas
            if bg_image:
                bg_resized = bg_image.resize((original.width, original.height), Image.Resampling.LANCZOS)
                canvas = bg_resized.convert("RGBA")
            else:
                canvas = Image.new("RGBA", original.size, (*bg_color, 255))
            
            # Stack: blurred original (with offset) then sharp original (centered)
            if blur and blurred_original:
                canvas.paste(blurred_original, blur_offset, blurred_original)
            canvas.paste(original, (0, 0), original)
            final = canvas

        # Save final
        output_path = output_dir / f"{prefix}-{i}.png"
        final.save(output_path, "PNG")
        output_paths.append(output_path)

        if debug:
            # Also save as stage 3
            final.save(debug_dir / f"{prefix}-{i}_3_final.png", "PNG")

    # Cleanup temp background
    bg_temp = output_dir / ".bg_temp.png"
    if bg_temp.exists():
        bg_temp.unlink()

    return output_paths


@click.command(name="render")
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.option("--dpi", "-d", default=320, help="Resolution (default: 300)")
@click.option("--no-blur", is_flag=True, help="Disable blur effect")
@click.option("--blur-radius", "-r", default=4, help="Blur radius (default: 25)")
@click.option("--blur-opacity", default=0.3, help="Blur opacity (default: 0.8)")
@click.option("--blur-offset", type=(int, int), default=(3, 3), help="Blur offset x y (default: 5 5)")
@click.option("--bg", type=click.Path(exists=True, path_type=Path), help="Background image path")
@click.option("--color", "-c", help="Background color (hex or name: skin, red, black, white)")
@click.option("--prefix", "-p", default="slide", help="Filename prefix")
@click.option("--debug", is_flag=True, help="Save intermediate stages in .debug/ folder")
def render_cmd(
    pdf_path: Path,
    output: Path | None,
    dpi: int,
    no_blur: bool,
    blur_radius: int,
    blur_opacity: float,
    blur_offset: tuple[int, int],
    bg: Path | None,
    color: str | None,
    prefix: str,
    debug: bool,
) -> None:
    """Render PDF to PNG images with blur and background.
    
    Stacking order: bg + blur (offset) + original (centered)
    
    Example:
        vbsocial render main.pdf
        vbsocial render main.pdf --bg ~/backgrounds/bg.jpg
        vbsocial render main.pdf -c black
        vbsocial render main.pdf --blur-radius 30 --blur-opacity 0.9
        vbsocial render main.pdf --debug
    """
    output_dir = output or pdf_path.parent / "images"
    
    # Parse background color
    bg_color = None
    if color:
        color_map = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (180, 30, 30),
            "blue": (30, 60, 180),
            "green": (30, 120, 60),
            "purple": (100, 40, 140),
            "orange": (220, 120, 30),
            "matteblack": (26, 26, 26),
            "skin": (252, 237, 219),
            "maroon": (182, 47, 84),
        }
        if color.lower() in color_map:
            bg_color = color_map[color.lower()]
        else:
            try:
                c = color.lstrip("#")
                bg_color = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
            except (ValueError, IndexError):
                raise click.ClickException(f"Invalid color: {color}")
    
    click.echo(f"🖼️  Rendering {pdf_path.name}...")
    click.echo(f"  DPI: {dpi}")
    click.echo(f"  Blur: {'no' if no_blur else f'radius={blur_radius}, opacity={blur_opacity}, offset={blur_offset}'}")
    if bg:
        click.echo(f"  Background: {bg}")
    elif bg_color:
        click.echo(f"  Background: #{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}")
    else:
        click.echo(f"  Background: auto-generated skin color")
    
    try:
        paths = render_pdf_to_pngs(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=dpi,
            blur=not no_blur,
            blur_radius=blur_radius,
            blur_opacity=blur_opacity,
            blur_offset=blur_offset,
            bg_image_path=bg,
            bg_color=bg_color,
            prefix=prefix,
            debug=debug,
        )
        
        click.echo(f"\n✓ Created {len(paths)} image(s) in {output_dir}")
        for p in paths:
            click.echo(f"  - {p.name}")
        
        if debug:
            click.echo(f"\n🔍 Debug stages saved in {output_dir / '.debug'}")
            click.echo("  - bg.png (background)")
            click.echo("  - *_1_original.png (sharp original, no bg)")
            click.echo("  - *_2_blurred.png (blurred original)")
            click.echo("  - *_3_final.png (bg + blurred original offset + sharp original centered)")
            
    except Exception as e:
        raise click.ClickException(str(e))
