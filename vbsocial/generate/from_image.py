"""Generate social media post from a physics problem image."""

import subprocess
from datetime import date
from pathlib import Path

import click
import yaml

from vbagent.agents.scanner import scan_with_type, ScanResult
from vbagent.agents.idea import generate_idea_latex
from vbagent.agents.alternate import generate_alternate

from ..agents.caption import generate_captions
from ..agents.datamodel import generate_datamodel
from ..agents.tikz import generate_tikz
from ..post.create import get_posts_dir
from .templates import (
    assemble_modular_document,
    create_solution_slide,
    create_idea_slide,
    get_code_file_extension,
    replace_item_with_lambda,
    has_diagram_reference,
)


def run_vbagent_scan(image_path: str, question_type: str | None = None) -> ScanResult:
    """Run vbagent scan to extract LaTeX from image.
    
    Args:
        image_path: Path to image
        question_type: Question type (subjective, mcq_sc, etc.) - defaults to subjective
    """
    qtype = question_type or "subjective"
    return scan_with_type(image_path, qtype)


def run_vbagent_scan_multiple(image_paths: list[str], question_type: str | None = None) -> list[ScanResult]:
    """Run vbagent scan on multiple images.
    
    Args:
        image_paths: List of image paths
        question_type: Question type (defaults to subjective)
    """
    results = []
    qtype = question_type or "subjective"
    
    for i, img in enumerate(image_paths, 1):
        click.echo(f"  Scanning image {i}/{len(image_paths)}: {Path(img).name}...")
        try:
            result = scan_with_type(img, qtype)
            results.append(result)
        except Exception as e:
            click.echo(f"  ⚠️  Failed to scan {img}: {e}")
    
    if not results:
        raise click.ClickException("Failed to scan any images")
    
    return results


def run_vbagent_idea(full_content: str) -> str | None:
    """Run vbagent idea to extract key concepts.
    
    Args:
        full_content: Combined problem + solution LaTeX
    """
    try:
        return generate_idea_latex(full_content)
    except Exception as e:
        click.echo(f"  ⚠️  Idea extraction failed: {e}")
    return None


def run_vbagent_alternate(problem: str, solution: str) -> str | None:
    """Run vbagent alternate to get alternative solution."""
    try:
        return generate_alternate(problem, solution)
    except Exception as e:
        click.echo(f"  ⚠️  Alternate generation failed: {e}")
    return None


def parse_scan_results(results: list[ScanResult]) -> tuple[str, str]:
    r"""Parse scan results into problem and solution parts.
    
    Args:
        results: List of ScanResult objects
        
    Returns:
        (problem_latex, solution_latex) tuple
        problem_latex includes \item (will be replaced with lambda style)
    """
    # Combine all latex from results
    all_latex = "\n\n".join(r.latex for r in results if r.latex)
    
    problem = ""
    solution = ""
    
    # Split by solution environment
    if r"\begin{solution}" in all_latex:
        parts = all_latex.split(r"\begin{solution}", 1)
        problem = parts[0].strip()
        
        # Get solution content
        remaining = r"\begin{solution}" + parts[1]
        solutions = []
        while r"\begin{solution}" in remaining:
            start = remaining.find(r"\begin{solution}") + len(r"\begin{solution}")
            end = remaining.find(r"\end{solution}")
            if end > start:
                sol = remaining[start:end].strip()
                if sol:
                    solutions.append(sol)
                remaining = remaining[end + len(r"\end{solution}"):]
            else:
                break
        
        if solutions:
            solution = "\n\n".join(solutions)
    else:
        # No solution found, all is problem
        problem = all_latex.strip()
    
    return problem, solution


def create_post_from_image(
    image_paths: list[str],
    include_idea: bool = True,
    include_alternate: bool = False,
    include_code: str | None = None,
    folder_name: str | None = None,
    question_type: str | None = None,
) -> Path:
    """Create a complete post from physics problem image(s).
    
    Args:
        image_paths: List of paths to physics problem images (problem, solution, etc.)
        include_idea: Whether to include key idea slide
        include_alternate: Whether to include alternate solution
        include_code: Language for code slide (rust, python, swift, None)
        folder_name: Override folder name
        question_type: Question type to skip classification (subjective, mcq_sc, etc.)
        
    Returns:
        Path to created post folder
    """
    click.echo(f"\n🔍 Scanning {len(image_paths)} image(s) with vbagent...")
    qtype = question_type or "subjective"
    click.echo(f"  Using type: {qtype}")
    
    # Scan images
    if len(image_paths) == 1:
        results = [run_vbagent_scan(image_paths[0], qtype)]
    else:
        results = run_vbagent_scan_multiple(image_paths, qtype)
    
    # Parse results
    problem, solution = parse_scan_results(results)
    
    if not problem:
        raise click.ClickException("Could not extract problem from image(s)")
    
    # Create folder first
    today = date.today().strftime("%Y_%m_%d")
    name = folder_name if folder_name else f"{today}_physics_problem"
    
    posts_dir = get_posts_dir()
    post_path = posts_dir / name
    
    if post_path.exists():
        i = 1
        while (posts_dir / f"{name}_{i}").exists():
            i += 1
        post_path = posts_dir / f"{name}_{i}"
    
    post_path.mkdir(parents=True)
    (post_path / "images").mkdir()
    
    # Track component files for main.tex
    components = []
    
    # Save problem.tex - raw content with \item replaced by lambda style
    click.echo("📝 Creating problem.tex...")
    problem_content = replace_item_with_lambda(problem)
    (post_path / "problem.tex").write_text(problem_content)
    components.append("problem")
    
    # Check if problem references a diagram and generate it
    if has_diagram_reference(problem_content):
        click.echo("🎨 Generating TikZ diagram (referenced in problem)...")
        try:
            # Check if source image has a diagram
            has_diagram = any(kw in problem.lower() for kw in ["diagram", "figure", "shown", "given", "cylindrical", "piston"])
            tikz_code = generate_tikz(
                problem=problem,
                solution=solution,
                image_path=image_paths[0] if image_paths else None,
                has_diagram=has_diagram,
            )
            if tikz_code:
                (post_path / "diagram.tex").write_text(tikz_code)
                components.append("diagram")
                click.echo("  ✓ Created diagram.tex")
        except Exception as e:
            click.echo(f"  ⚠️  Diagram generation failed: {e}")
    
    # Save solution.tex - raw solution env content
    if solution:
        click.echo("✅ Creating solution.tex...")
        solution_content = create_solution_slide(solution)
        (post_path / "solution.tex").write_text(solution_content)
        components.append("solution")
    
    # Save idea.tex (optional)
    if include_idea:
        click.echo("💡 Extracting key idea...")
        # Combine all latex for idea extraction
        full_latex = "\n\n".join(r.latex for r in results if r.latex)
        idea = run_vbagent_idea(full_latex)
        if idea:
            # Extract content from idea environment if present
            if r"\begin{idea}" in idea:
                idea_content = idea.split(r"\begin{idea}")[1].split(r"\end{idea}")[0].strip()
            else:
                idea_content = idea
            idea_slide = create_idea_slide(idea_content)
            (post_path / "idea.tex").write_text(idea_slide)
            components.append("idea")
    
    # Save alternate.tex (optional)
    if include_alternate and solution:
        click.echo("🔄 Generating alternate solution...")
        alternate = run_vbagent_alternate(problem, solution)
        if alternate:
            # Extract content from alternatesolution environment if present
            if r"\begin{alternatesolution}" in alternate:
                alt_content = alternate.split(r"\begin{alternatesolution}")[1].split(r"\end{alternatesolution}")[0].strip()
            else:
                alt_content = alternate
            alt_slide = create_solution_slide(alt_content)
            (post_path / "alternate.tex").write_text(alt_slide)
            components.append("alternate")
    
    # Save datamodel code file (optional) - no separate tex file
    if include_code:
        click.echo(f"💻 Generating {include_code} data model...")
        try:
            code = generate_datamodel(
                problem=problem,
                language=include_code,
                solution=solution,
            )
            if code:
                ext = get_code_file_extension(include_code)
                (post_path / f"datamodel.{ext}").write_text(code)
                components.append(include_code)
                click.echo(f"  ✓ Saved datamodel.{ext}")
        except Exception as e:
            click.echo(f"  ⚠️  Code generation failed: {e}")
    
    # Assemble main.tex with \input statements
    click.echo("📄 Assembling main.tex...")
    latex_content = assemble_modular_document(components, post_path=str(post_path))
    (post_path / "main.tex").write_text(latex_content)
    
    # Generate captions
    click.echo("✍️  Generating captions...")
    topic = problem[:50] + "..." if len(problem) > 50 else problem
    captions_output = generate_captions(topic=topic, difficulty="intermediate")
    captions = {
        "facebook": captions_output.facebook,
        "instagram": captions_output.instagram,
        "linkedin": captions_output.linkedin,
        "x": captions_output.x,
        "youtube": captions_output.youtube,
    }
    
    # Write post.yaml
    yaml_content = {
        "title": topic,
        "date": today,
        "captions": captions,
        "source_images": [str(p) for p in image_paths],
        "components": components,
    }
    with open(post_path / "post.yaml", "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)
    
    return post_path


@click.command(name="from-image")
@click.argument("image_paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--idea/--no-idea", default=True, help="Include key idea slide")
@click.option("--alternate", "-a", is_flag=True, help="Include alternate solution")
@click.option("--code", "-c", type=click.Choice(["rust", "python", "swift", "c", "zig", "go"]), help="Include code slide")
@click.option("--name", "-n", help="Override folder name")
@click.option("--render", "-r", is_flag=True, help="Render to images after generation")
@click.option("--type", "-t", "question_type", 
              type=click.Choice(["subjective", "mcq_sc", "mcq_mc", "assertion_reason", "passage", "match"]),
              help="Question type (skips classification, faster)")
def from_image(image_paths: tuple[str, ...], idea: bool, alternate: bool, code: str | None, 
               name: str | None, render: bool, question_type: str | None) -> None:
    """Generate social media post from physics problem image(s).
    
    Uses vbagent to:
    1. Scan and extract LaTeX from image(s)
    2. Extract key ideas
    3. Generate alternate solutions
    4. Create code data models
    
    You can provide multiple images (e.g., problem image + solution image).
    Use --type to skip classification and speed up scanning.
    
    Example:
        vbsocial from-image problem.png
        vbsocial from-image problem.png solution.png -t subjective
        vbsocial from-image problem.png solution.png --type subjective --code rust -r
    """
    click.echo(f"\n🚀 Generating post from {len(image_paths)} image(s)")
    click.echo("=" * 50)
    
    try:
        post_path = create_post_from_image(
            image_paths=list(image_paths),
            include_idea=idea,
            include_alternate=alternate,
            include_code=code,
            folder_name=name,
            question_type=question_type,
        )
        
        if render:
            click.echo("\n🖼️  Rendering images...")
            # Compile LaTeX
            subprocess.run(
                ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "main.tex"],
                cwd=post_path,
                capture_output=True,
            )
            
            # Render PDF to PNG
            if (post_path / "main.pdf").exists():
                from .render import render_pdf_to_pngs
                render_pdf_to_pngs(
                    pdf_path=post_path / "main.pdf",
                    output_dir=post_path / "images",
                    dpi=300,
                )
            else:
                click.echo("  ⚠️  PDF not created, check LaTeX errors")
        
        click.echo("\n" + "=" * 50)
        click.echo("✅ Post generated successfully!")
        click.echo(f"\n📍 Location: {post_path}")
        
    except Exception as e:
        raise click.ClickException(str(e))
