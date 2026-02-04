"""CLI command for generating data models from physics problems."""

import click

from ..agents.datamodel import generate_datamodel


@click.command(name="datamodel")
@click.argument("problem", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read problem from file")
@click.option("--language", "-l", type=click.Choice(["rust", "python", "swift"]), 
              default="rust", help="Target language")
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
def datamodel(problem: str | None, file: str | None, language: str, output: str | None) -> None:
    """Generate a data model from a physics problem.
    
    Generates struct/class definitions that model the physics problem
    in the specified programming language. Useful for teaching students
    how to think about physics problems in code.
    
    Examples:
        vbsocial datamodel "projectile motion with initial velocity v0 at angle theta"
        vbsocial datamodel -f problem.tex -l python
        vbsocial datamodel "simple harmonic oscillator" -l rust -o oscillator.rs
    """
    if not problem and not file:
        raise click.ClickException("Provide a problem description or use --file")
    
    if file:
        with open(file) as f:
            problem = f.read()
    
    click.echo(f"🔧 Generating {language} data model...")
    
    try:
        code = generate_datamodel(problem, language)
        
        if output:
            with open(output, "w") as f:
                f.write(code)
            click.echo(f"✓ Written to {output}")
        else:
            click.echo("\n" + "=" * 50)
            click.echo(code)
            click.echo("=" * 50)
            
    except Exception as e:
        raise click.ClickException(f"Generation failed: {e}")
