"""Generate social media post from an idea/topic."""

import subprocess
from datetime import date
from pathlib import Path

import click
import yaml

from ..agents.caption import generate_captions
from ..agents.content_planner import plan_content, ContentPlan
from ..agents.datamodel import generate_datamodel
from ..post.create import get_posts_dir
from .templates import (
    assemble_modular_document,
    create_code_slide_from_file,
    get_code_file_extension,
)


LATEX_TEMPLATE = r"""\documentclass[border=0pt]{{standalone}}
\usepackage[paperwidth=5in, paperheight=5in, margin=0.3in]{{geometry}}
\usepackage{{xcolor}}
\usepackage{{amsmath, amssymb}}
\usepackage{{tikz}}
\usepackage{{minted}}
\usepackage{{tcolorbox}}
\tcbuselibrary{{minted, skins}}

% Colors
\definecolor{{bg}}{{HTML}}{{FFFFFF}}
\definecolor{{primary}}{{HTML}}{{1a1a1a}}
\definecolor{{accent}}{{HTML}}{{3b82f6}}
\definecolor{{codebg}}{{HTML}}{{282c34}}
\definecolor{{codefg}}{{HTML}}{{abb2bf}}

\begin{{document}}

{slides}

\end{{document}}
"""

SLIDE_TEMPLATE = r"""% Slide {num}: {title}
\begin{{tikzpicture}}[remember picture, overlay]
    \fill[bg] (current page.south west) rectangle (current page.north east);
\end{{tikzpicture}}

\begin{{minipage}}[c][5in][c]{{4.4in}}
    \centering
    {{\Large\bfseries\color{{primary}} {title}}}
    
    \vspace{{0.3in}}
    
    {{\color{{primary}} {content}}}
\end{{minipage}}
"""


def content_plan_to_latex(plan: ContentPlan, code_slide: str | None = None) -> str:
    """Convert a content plan to LaTeX slides.
    
    Args:
        plan: The content plan with slides
        code_slide: Optional code slide LaTeX to append
    """
    slides_latex = []
    
    for i, slide in enumerate(plan.slides, 1):
        # Escape special LaTeX characters in content
        content = slide.content
        # Basic escaping - might need more
        content = content.replace("&", r"\&")
        content = content.replace("%", r"\%")
        content = content.replace("$", r"\$") if "$" not in content else content
        
        slide_latex = SLIDE_TEMPLATE.format(
            num=i,
            title=slide.title,
            content=content,
        )
        slides_latex.append(slide_latex)
    
    # Add code slide if provided
    if code_slide:
        slides_latex.append(code_slide)
    
    # Join slides with newpage
    slides_content = "\n\\newpage\n\n".join(slides_latex)
    
    return LATEX_TEMPLATE.format(slides=slides_content)


def create_post_folder(
    topic: str,
    latex_content: str,
    captions: dict,
    folder_name: str | None = None,
    code_file: tuple[str, str] | None = None,
) -> Path:
    """Create the post folder with all files.
    
    Args:
        topic: Post topic
        latex_content: Main LaTeX content
        captions: Platform captions dict
        folder_name: Override folder name
        code_file: Optional (language, code) tuple for datamodel
    """
    today = date.today().strftime("%Y_%m_%d")
    name = folder_name if folder_name else f"{today}_{topic.replace(' ', '_').lower()}"
    
    posts_dir = get_posts_dir()
    post_path = posts_dir / name
    
    if post_path.exists():
        # Add suffix if exists
        i = 1
        while (posts_dir / f"{name}_{i}").exists():
            i += 1
        post_path = posts_dir / f"{name}_{i}"
    
    # Create directories
    post_path.mkdir(parents=True)
    (post_path / "images").mkdir()
    
    # Write main.tex
    (post_path / "main.tex").write_text(latex_content)
    
    # Write code file if provided
    if code_file:
        lang, code = code_file
        ext = get_code_file_extension(lang)
        (post_path / f"datamodel.{ext}").write_text(code)
        
        # Create code slide tex that uses \inputminted
        code_slide = create_code_slide_from_file(lang)
        (post_path / f"code_{lang}.tex").write_text(code_slide)
        
        # Append code slide to main.tex
        with open(post_path / "main.tex", "r") as f:
            content = f.read()
        
        # Insert before \end{document}
        content = content.replace(
            r"\end{document}",
            f"\n\\newpage\n\n\\input{{code_{lang}}}\n\n\\end{{document}}"
        )
        (post_path / "main.tex").write_text(content)
    
    # Write post.yaml
    yaml_content = {
        "title": topic,
        "date": today,
        "captions": captions,
    }
    if code_file:
        yaml_content["datamodel"] = f"datamodel.{get_code_file_extension(code_file[0])}"
    
    with open(post_path / "post.yaml", "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)
    
    return post_path


def render_latex(post_path: Path) -> bool:
    """Render LaTeX to PDF and convert to PNGs with shadow effect."""
    try:
        # Compile LaTeX with shell-escape for minted
        click.echo("  Compiling LaTeX...")
        result = subprocess.run(
            ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "main.tex"],
            cwd=post_path,
            capture_output=True,
            timeout=60,
        )
        
        if not (post_path / "main.pdf").exists():
            click.echo("  ⚠️  LaTeX compilation failed")
            return False
        
        # Render PDF to PNG
        click.echo("  Converting to PNG...")
        from .render import render_pdf_to_pngs
        
        paths = render_pdf_to_pngs(
            pdf_path=post_path / "main.pdf",
            output_dir=post_path / "images",
            dpi=300,
        )
        
        if paths:
            click.echo(f"  ✓ Created {len(paths)} image(s)")
            return True
        else:
            click.echo("  ⚠️  No images created")
            return False
            
    except subprocess.TimeoutExpired:
        click.echo("  ⚠️  LaTeX compilation timed out")
        return False
    except FileNotFoundError as e:
        click.echo(f"  ⚠️  Command not found: {e}")
        return False
    except Exception as e:
        click.echo(f"  ⚠️  Render failed: {e}")
        return False


@click.command(name="generate")
@click.option("--idea", "-i", required=True, help="Topic or idea for the post")
@click.option("--slides", "-s", type=int, default=None, help="Target number of slides")
@click.option("--render", "-r", is_flag=True, help="Render LaTeX to images after generation")
@click.option("--name", "-n", help="Override folder name")
@click.option("--code", "-c", type=click.Choice(["rust", "python", "swift"]), 
              help="Include data model code slide in specified language")
def generate(idea: str, slides: int | None, render: bool, name: str | None, code: str | None) -> None:
    """Generate a complete social media post from an idea.
    
    This command uses AI to:
    1. Plan the content structure (slides)
    2. Generate platform-specific captions
    3. Create LaTeX template
    4. Optionally generate data model code
    5. Optionally render to images
    
    Examples:
        vbsocial generate -i "projectile motion basics"
        vbsocial generate -i "pursuit problem kinematics" -s 4 -r
        vbsocial generate -i "Newton's laws" --code rust -r
    """
    click.echo(f"\n🚀 Generating post for: {idea}")
    click.echo("=" * 50)
    
    # Step 1: Plan content
    click.echo("\n📝 Planning content structure...")
    try:
        plan = plan_content(idea, num_slides=slides, include_code=bool(code))
        click.echo(f"  ✓ Planned {len(plan.slides)} slides")
        click.echo(f"  Topic: {plan.topic}")
        click.echo(f"  Difficulty: {plan.difficulty}")
    except Exception as e:
        raise click.ClickException(f"Content planning failed: {e}")
    
    # Step 2: Generate captions
    click.echo("\n✍️  Generating captions...")
    try:
        content_summary = "\n".join([f"- {s.title}: {s.content[:100]}..." for s in plan.slides])
        captions_output = generate_captions(
            topic=plan.topic,
            content_summary=content_summary,
            difficulty=plan.difficulty,
        )
        captions = {
            "facebook": captions_output.facebook,
            "instagram": captions_output.instagram,
            "linkedin": captions_output.linkedin,
            "x": captions_output.x,
            "youtube": captions_output.youtube,
        }
        click.echo("  ✓ Generated captions for all platforms")
    except Exception as e:
        raise click.ClickException(f"Caption generation failed: {e}")
    
    # Step 3: Generate code file if requested
    code_slide_file = None
    if code:
        click.echo(f"\n💻 Generating {code} data model...")
        try:
            datamodel_code = generate_datamodel(idea, code)
            if datamodel_code:
                code_slide_file = (code, datamodel_code)
                click.echo(f"  ✓ Generated {code} data model")
        except Exception as e:
            click.echo(f"  ⚠️  Code generation failed: {e}")
    
    # Step 4: Generate LaTeX
    click.echo("\n📄 Generating LaTeX...")
    latex_content = content_plan_to_latex(plan, code_slide=None)  # Code handled separately
    click.echo("  ✓ LaTeX template created")
    
    # Step 5: Create folder
    click.echo("\n📁 Creating post folder...")
    post_path = create_post_folder(
        topic=plan.topic,
        latex_content=latex_content,
        captions=captions,
        folder_name=name,
        code_file=code_slide_file,
    )
    click.echo(f"  ✓ Created: {post_path}")
    
    # Step 6: Optionally render
    if render:
        click.echo("\n🖼️  Rendering images...")
        render_latex(post_path)
    
    # Summary
    click.echo("\n" + "=" * 50)
    click.echo("✅ Post generated successfully!")
    click.echo(f"\n📍 Location: {post_path}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Edit main.tex if needed")
    if not render:
        click.echo(f"  2. Render: cd {post_path} && pdflatex -shell-escape main.tex && vbpdf topng")
    click.echo(f"  3. Post: vbsocial post-all {post_path}")
