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


def render_with_blur_shadow(
    image: Image.Image,
    blur_radius: int = 15,
    blur_opacity: float = 0.6,
    shadow_color: tuple[int, int, int] = (0, 0, 0),
    shadow_opacity: float = 0.4,
    shadow_offset: tuple[int, int] = (5, 5),
) -> Image.Image:
    """Create image with blur glow and shadow effect.
    
    Pipeline:
    1. Create blurred version (glow)
    2. Create shadow layer (colored + blurred)
    3. Stack: shadow -> blur -> original
    
    Args:
        image: Source RGBA image
        blur_radius: Blur radius for glow
        blur_opacity: Opacity of blur layer
        shadow_color: RGB color for shadow
        shadow_opacity: Opacity of shadow
        shadow_offset: Shadow offset (x, y)
        
    Returns:
        Composited RGBA image
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # Create blur layer (glow effect)
    blur_layer = blur_image(image, radius=blur_radius, opacity=blur_opacity)
    
    # Create shadow layer
    shadow = color_layer(image, shadow_color, opacity=shadow_opacity)
    shadow = blur_image(shadow, radius=blur_radius)
    
    # Create canvas
    canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
    
    # Stack: shadow (offset) -> blur -> original
    canvas.paste(shadow, shadow_offset, shadow)
    canvas.paste(blur_layer, (0, 0), blur_layer)
    canvas.paste(image, (0, 0), image)
    
    return canvas


def render_pdf_to_pngs(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 300,
    blur: bool = True,
    blur_radius: int = 15,
    blur_opacity: float = 0.6,
    shadow_color: tuple[int, int, int] = (0, 0, 0),
    shadow_opacity: float = 0.4,
    shadow_offset: tuple[int, int] = (5, 5),
    bg_image_path: Path | None = None,
    bg_color: tuple[int, int, int] | None = None,
    prefix: str = "slide",
) -> list[Path]:
    """Render PDF to PNG images with blur/shadow and background.
    
    Pipeline:
    1. PDF -> PNG (no border)
    2. Add blur glow + shadow
    3. Stack on background image or solid color
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load background image if specified
    bg_image = None
    if bg_image_path and bg_image_path.exists():
        bg_image = Image.open(bg_image_path)
    elif not bg_color and DEFAULT_BG_IMAGE.exists():
        bg_image = Image.open(DEFAULT_BG_IMAGE)
    
    # Convert PDF to images
    pages = pdf_to_images(pdf_path, dpi=dpi)
    
    output_paths = []
    for i, page in enumerate(pages, 1):
        # Add blur/shadow effect
        if blur:
            page = render_with_blur_shadow(
                page,
                blur_radius=blur_radius,
                blur_opacity=blur_opacity,
                shadow_color=shadow_color,
                shadow_opacity=shadow_opacity,
                shadow_offset=shadow_offset,
            )
        
        # Stack on background
        if bg_image:
            page = stack_images(page, bg_image)
        elif bg_color:
            bg = Image.new("RGBA", page.size, (*bg_color, 255))
            page = stack_images(page, bg)
        
        # Save
        output_path = output_dir / f"{prefix}-{i}.png"
        page.save(output_path, "PNG")
        output_paths.append(output_path)
    
    return output_paths


@click.command(name="render")
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.option("--dpi", "-d", default=300, help="Resolution (default: 300)")
@click.option("--no-blur", is_flag=True, help="Disable blur/shadow effect")
@click.option("--blur-radius", "-r", default=15, help="Blur radius (default: 15)")
@click.option("--blur-opacity", default=0.6, help="Blur opacity (default: 0.6)")
@click.option("--shadow-color", type=(int, int, int), default=(0, 0, 0), help="Shadow RGB color")
@click.option("--shadow-opacity", default=0.4, help="Shadow opacity (default: 0.4)")
@click.option("--shadow-offset", type=(int, int), default=(5, 5), help="Shadow offset x y")
@click.option("--bg", type=click.Path(exists=True, path_type=Path), help="Background image path")
@click.option("--color", "-c", help="Background color (hex or name: red, black, white)")
@click.option("--prefix", "-p", default="slide", help="Filename prefix")
def render_cmd(
    pdf_path: Path,
    output: Path | None,
    dpi: int,
    no_blur: bool,
    blur_radius: int,
    blur_opacity: float,
    shadow_color: tuple[int, int, int],
    shadow_opacity: float,
    shadow_offset: tuple[int, int],
    bg: Path | None,
    color: str | None,
    prefix: str,
) -> None:
    """Render PDF to PNG images with blur glow, shadow, and background.
    
    Example:
        vbsocial render main.pdf
        vbsocial render main.pdf --bg ~/backgrounds/bg.jpg
        vbsocial render main.pdf -c black
        vbsocial render main.pdf --blur-radius 20 --shadow-opacity 0.5
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
    click.echo(f"  Blur: {'no' if no_blur else f'radius={blur_radius}, opacity={blur_opacity}'}")
    click.echo(f"  Shadow: color={shadow_color}, opacity={shadow_opacity}, offset={shadow_offset}")
    if bg:
        click.echo(f"  Background: {bg}")
    elif bg_color:
        click.echo(f"  Background: #{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}")
    else:
        click.echo(f"  Background: {DEFAULT_BG_IMAGE}")
    
    try:
        paths = render_pdf_to_pngs(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=dpi,
            blur=not no_blur,
            blur_radius=blur_radius,
            blur_opacity=blur_opacity,
            shadow_color=shadow_color,
            shadow_opacity=shadow_opacity,
            shadow_offset=shadow_offset,
            bg_image_path=bg,
            bg_color=bg_color,
            prefix=prefix,
        )
        
        click.echo(f"\n✓ Created {len(paths)} image(s) in {output_dir}")
        for p in paths:
            click.echo(f"  - {p.name}")
            
    except Exception as e:
        raise click.ClickException(str(e))
