"""Add components to an existing post directory."""

from pathlib import Path

import click
import yaml

from ..agents.datamodel import generate_datamodel
from ..agents.tikz import generate_tikz
from ..agents.debug import debug_enabled, log_debug
from .templates import (
    create_idea_slide,
    create_solution_slide,
    get_code_file_extension,
    assemble_modular_document,
    has_diagram_reference,
    replace_item_with_lambda,
)


def read_problem_solution(post_path: Path) -> tuple[str, str]:
    """Read problem and solution from existing tex files."""
    problem = ""
    solution = ""
    
    problem_file = post_path / "problem.tex"
    solution_file = post_path / "solution.tex"
    
    if problem_file.exists():
        problem = problem_file.read_text()
    
    if solution_file.exists():
        solution = solution_file.read_text()
    
    return problem, solution


def update_main_tex(post_path: Path, components: list[str]) -> None:
    """Update main.tex with new components."""
    latex_content = assemble_modular_document(components, post_path=str(post_path))
    (post_path / "main.tex").write_text(latex_content)


def update_post_yaml(post_path: Path, components: list[str]) -> None:
    """Update post.yaml with new components list."""
    yaml_path = post_path / "post.yaml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    config["components"] = components
    
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def get_existing_components(post_path: Path) -> list[str]:
    """Get list of existing component files."""
    components = []
    
    if (post_path / "problem.tex").exists():
        components.append("problem")
    if (post_path / "solution.tex").exists():
        components.append("solution")
    if (post_path / "idea.tex").exists():
        components.append("idea")
    if (post_path / "alternate.tex").exists():
        components.append("alternate")
    if (post_path / "diagram.tex").exists():
        components.append("diagram")
    
    # Check for datamodel files (no separate code_*.tex anymore)
    for lang, ext in [("rust", "rs"), ("python", "py"), ("swift", "swift"), ("c", "c"), ("zig", "zig"), ("go", "go")]:
        if (post_path / f"datamodel.{ext}").exists():
            components.append(lang)
    
    return components


@click.command(name="add")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--idea", "-i", is_flag=True, help="Add key idea")
@click.option("--alternate", "-a", is_flag=True, help="Add alternate solution")
@click.option("--code", "-c", type=click.Choice(["rust", "python", "swift", "c", "zig", "go"]), help="Add code data model")
@click.option("--tikz", "-t", is_flag=True, help="Add/generate TikZ diagram")
@click.option("--render", "-r", is_flag=True, help="Re-render after adding")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing components")
@click.option("--debug", "-d", is_flag=True, help="Enable debug output")
def add_component(post_path: Path, idea: bool, alternate: bool, code: str | None, tikz: bool, render: bool, force: bool, debug: bool) -> None:
    """Add components to an existing post directory.
    
    Run from within a post directory or provide the path.
    Reads problem.tex and solution.tex to generate new components.
    
    Example:
        cd ~/social_posts/2026_02_04_physics
        vbsocial add --idea
        vbsocial add --alternate
        vbsocial add --code rust
        vbsocial add --tikz
        vbsocial add -i -a -c rust -t -r
        vbsocial add --code rust --force  # regenerate existing
        vbsocial add -c rust -d  # debug mode
    """
    import os
    
    # Enable debug mode if flag is set
    if debug:
        os.environ["VBSOCIAL_DEBUG"] = "1"
        from ..agents.debug import reset_debug_cache
        reset_debug_cache()
    
    if not idea and not alternate and not code and not tikz:
        raise click.ClickException("Specify at least one: --idea, --alternate, --code, or --tikz")
    
    # Check if this is a valid post directory
    if not (post_path / "problem.tex").exists():
        raise click.ClickException(f"Not a valid post directory: {post_path} (no problem.tex)")
    
    click.echo(f"\n📁 Post directory: {post_path}")
    
    if debug_enabled():
        log_debug("add_start", {
            "post_path": str(post_path),
            "idea": idea,
            "alternate": alternate,
            "code": code,
            "tikz": tikz,
        })
    
    # Read existing content
    problem, solution = read_problem_solution(post_path)
    
    if not problem:
        raise click.ClickException("Could not read problem.tex")
    
    # Get existing components
    components = get_existing_components(post_path)
    click.echo(f"  Existing components: {', '.join(components)}")
    
    # Add idea
    if idea:
        if "idea" in components and not force:
            click.echo("  ⚠️  idea.tex already exists, use --force to overwrite")
        elif not solution:
            click.echo("  ⚠️  No solution.tex, cannot generate idea")
        else:
            click.echo("\n💡 Generating key idea...")
            try:
                from vbagent.agents.idea import generate_idea_latex
                # Combine problem and solution for idea extraction
                full_content = problem + "\n\n" + solution
                idea_latex = generate_idea_latex(full_content)
                if idea_latex:
                    idea_slide = create_idea_slide(idea_latex)
                    (post_path / "idea.tex").write_text(idea_slide)
                    if "idea" not in components:
                        components.append("idea")
                    click.echo("  ✓ Created idea.tex")
                else:
                    click.echo("  ⚠️  No ideas extracted")
            except Exception as e:
                click.echo(f"  ❌ Failed: {e}")
    
    # Add alternate
    if alternate:
        if "alternate" in components and not force:
            click.echo("  ⚠️  alternate.tex already exists, use --force to overwrite")
        elif not solution:
            click.echo("  ⚠️  No solution.tex, cannot generate alternate")
        else:
            click.echo("\n🔄 Generating alternate solution...")
            try:
                from vbagent.agents.alternate import generate_alternate
                alt = generate_alternate(problem, solution)
                if alt:
                    alt_slide = create_solution_slide(alt)
                    (post_path / "alternate.tex").write_text(alt_slide)
                    if "alternate" not in components:
                        components.append("alternate")
                    click.echo("  ✓ Created alternate.tex")
                else:
                    click.echo("  ⚠️  No alternate generated")
            except Exception as e:
                click.echo(f"  ❌ Failed: {e}")
    
    # Add tikz diagram
    if tikz:
        tikz_file = post_path / "diagram.tex"
        if tikz_file.exists() and not force:
            click.echo("  ⚠️  diagram.tex already exists, use --force to overwrite")
        else:
            click.echo("\n🎨 Generating TikZ diagram...")
            try:
                # Check if there's a source image with diagram
                import yaml
                yaml_path = post_path / "post.yaml"
                image_path = None
                has_diagram = False
                
                if yaml_path.exists():
                    with open(yaml_path) as f:
                        config = yaml.safe_load(f) or {}
                    source_images = config.get("source_images", [])
                    if source_images:
                        image_path = source_images[0]
                        # Check if problem mentions diagram/figure
                        has_diagram = any(kw in problem.lower() for kw in ["diagram", "figure", "shown", "given"])
                
                tikz_code = generate_tikz(
                    problem=problem,
                    solution=solution,
                    image_path=image_path,
                    has_diagram=has_diagram,
                )
                if tikz_code:
                    tikz_file.write_text(tikz_code)
                    if "diagram" not in components:
                        components.append("diagram")
                    click.echo("  ✓ Created diagram.tex")
                else:
                    click.echo("  ⚠️  No diagram generated")
            except Exception as e:
                click.echo(f"  ❌ Failed: {e}")
    
    # Auto-generate diagram if problem references it but file doesn't exist
    if not tikz and has_diagram_reference(problem) and "diagram" not in components:
        click.echo("\n🎨 Auto-generating TikZ diagram (referenced in problem)...")
        try:
            import yaml
            yaml_path = post_path / "post.yaml"
            image_path = None
            has_diagram = any(kw in problem.lower() for kw in ["diagram", "figure", "shown", "given", "cylindrical", "piston"])
            
            if yaml_path.exists():
                with open(yaml_path) as f:
                    config = yaml.safe_load(f) or {}
                source_images = config.get("source_images", [])
                if source_images:
                    image_path = source_images[0]
            
            tikz_code = generate_tikz(
                problem=problem,
                solution=solution,
                image_path=image_path,
                has_diagram=has_diagram,
            )
            if tikz_code:
                (post_path / "diagram.tex").write_text(tikz_code)
                components.append("diagram")
                click.echo("  ✓ Created diagram.tex")
        except Exception as e:
            click.echo(f"  ⚠️  Diagram generation failed: {e}")
    
    # Add code - just save datamodel.{ext}, no separate tex file
    if code:
        ext = get_code_file_extension(code)
        datamodel_file = post_path / f"datamodel.{ext}"
        if code in components and not force:
            click.echo(f"  ⚠️  datamodel.{ext} already exists, use --force to overwrite")
        else:
            click.echo(f"\n💻 Generating {code} data model...")
            try:
                # Find existing code for reference (consistency)
                reference_code = None
                reference_lang = None
                for lang, lang_ext in [("rust", "rs"), ("python", "py"), ("swift", "swift"), ("c", "c"), ("zig", "zig"), ("go", "go")]:
                    if lang != code:
                        ref_file = post_path / f"datamodel.{lang_ext}"
                        if ref_file.exists():
                            reference_code = ref_file.read_text()
                            reference_lang = lang
                            click.echo(f"  Using {lang} as reference for consistency")
                            break
                
                datamodel = generate_datamodel(
                    problem=problem,
                    language=code,
                    solution=solution,
                    reference_code=reference_code,
                    reference_language=reference_lang,
                )
                if datamodel:
                    datamodel_file.write_text(datamodel)
                    if code not in components:
                        components.append(code)
                    click.echo(f"  ✓ Created datamodel.{ext}")
                else:
                    click.echo("  ⚠️  No code generated")
            except Exception as e:
                click.echo(f"  ❌ Failed: {e}")
    
    # Update main.tex and post.yaml
    click.echo("\n📄 Updating main.tex...")
    update_main_tex(post_path, components)
    update_post_yaml(post_path, components)
    click.echo(f"  Components: {', '.join(components)}")
    
    # Render if requested
    if render:
        click.echo("\n🖼️  Rendering...")
        import subprocess
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
    
    click.echo("\n✅ Done!")


@click.command(name="fix")
@click.argument("post_path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--diagram", "-d", is_flag=True, help="Generate missing diagram.tex if referenced")
@click.option("--lambda", "-l", "lambda_item", is_flag=True, help="Replace \\item with \\item[$\\lambda.$]")
@click.option("--caption", "-c", is_flag=True, help="Generate captions for all platforms")
@click.option("--all", "-a", "fix_all", is_flag=True, help="Apply all fixes")
@click.option("--render", "-r", is_flag=True, help="Re-render after fixing")
def fix_post(post_path: Path, diagram: bool, lambda_item: bool, caption: bool, fix_all: bool, render: bool) -> None:
    """Fix common issues in existing post files.
    
    Fixes:
    - Diagram: Generate diagram.tex if problem references it
    - Lambda: Replace \\item with \\item[$\\lambda.$]
    - Caption: Generate storytelling captions for all platforms
    
    Example:
        vbsocial fix --diagram
        vbsocial fix --lambda
        vbsocial fix --caption
        vbsocial fix --all -r
    """
    if not diagram and not lambda_item and not caption and not fix_all:
        raise click.ClickException("Specify at least one: --diagram, --lambda, --caption, or --all")
    
    if fix_all:
        diagram = lambda_item = caption = True
    
    if not (post_path / "problem.tex").exists():
        raise click.ClickException(f"Not a valid post directory: {post_path} (no problem.tex)")
    
    click.echo(f"\n🔧 Fixing post: {post_path}")
    
    problem, solution = read_problem_solution(post_path)
    components = get_existing_components(post_path)
    modified = False
    
    # Fix lambda item
    if lambda_item:
        original = problem
        problem = replace_item_with_lambda(problem)
        if problem != original:
            (post_path / "problem.tex").write_text(problem)
            click.echo("  ✓ Replaced \\item with \\item[$\\lambda.$]")
            modified = True
        else:
            click.echo("  - No \\item to replace")
    
    # Generate missing diagram
    if diagram and has_diagram_reference(problem) and "diagram" not in components:
        click.echo("\n🎨 Generating missing diagram.tex...")
        try:
            yaml_path = post_path / "post.yaml"
            image_path = None
            has_diag = any(kw in problem.lower() for kw in ["diagram", "figure", "shown", "given", "cylindrical", "piston"])
            
            if yaml_path.exists():
                with open(yaml_path) as f:
                    config = yaml.safe_load(f) or {}
                source_images = config.get("source_images", [])
                if source_images:
                    image_path = source_images[0]
            
            tikz_code = generate_tikz(
                problem=problem,
                solution=solution,
                image_path=image_path,
                has_diagram=has_diag,
            )
            if tikz_code:
                (post_path / "diagram.tex").write_text(tikz_code)
                components.append("diagram")
                click.echo("  ✓ Created diagram.tex")
                modified = True
        except Exception as e:
            click.echo(f"  ❌ Diagram generation failed: {e}")
    elif diagram:
        if "diagram" in components:
            click.echo("  - diagram.tex already exists")
        elif not has_diagram_reference(problem):
            click.echo("  - No diagram reference in problem")
    
    # Generate captions
    if caption:
        click.echo("\n📝 Generating captions...")
        try:
            from ..agents.caption import generate_captions_from_post, CHAR_LIMITS
            
            captions = generate_captions_from_post(str(post_path))
            
            # Save to post.yaml for post-all command
            yaml_path = post_path / "post.yaml"
            if yaml_path.exists():
                with open(yaml_path) as f:
                    post_config = yaml.safe_load(f) or {}
            else:
                post_config = {}
            
            # Add captions to post.yaml
            post_config["captions"] = captions
            
            # Custom representer for literal block style (cleaner multiline)
            def str_representer(dumper, data):
                if '\n' in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)
            
            yaml.add_representer(str, str_representer)
            
            with open(yaml_path, "w") as f:
                yaml.dump(post_config, f, default_flow_style=False, allow_unicode=True, width=120)
            
            click.echo("  ✓ Saved captions to post.yaml")
            
            # Show preview
            click.echo("\n  📱 Caption previews:")
            for platform, text in captions.items():
                limit = CHAR_LIMITS.get(platform, 1000)
                length = len(text)
                status = "✓" if length <= limit else "⚠️"
                preview = text[:60].replace("\n", " ") + "..." if len(text) > 60 else text.replace("\n", " ")
                click.echo(f"    {status} {platform}: ({length}/{limit}) {preview}")
            
            modified = True
        except Exception as e:
            click.echo(f"  ❌ Caption generation failed: {e}")
    
    # Update main.tex if components changed
    if modified:
        click.echo("\n📄 Updating main.tex...")
        update_main_tex(post_path, components)
        update_post_yaml(post_path, components)
    
    # Render if requested
    if render and modified:
        click.echo("\n🖼️  Rendering...")
        import subprocess
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
    
    click.echo("\n✅ Done!")
