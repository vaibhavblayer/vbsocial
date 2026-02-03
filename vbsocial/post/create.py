"""Create post folder structure command."""

import os
from datetime import date
from pathlib import Path

import click
import yaml


LATEX_TEMPLATE = r"""\documentclass[border=0pt]{standalone}
\usepackage[paperwidth=5in, paperheight=5in, margin=0.3in]{geometry}
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{tikz}
\usepackage{fontspec}

% Colors
\definecolor{bg}{HTML}{FFFFFF}
\definecolor{primary}{HTML}{1a1a1a}
\definecolor{accent}{HTML}{3b82f6}

\begin{document}

% Slide 1
\begin{tikzpicture}[remember picture, overlay]
    \fill[bg] (current page.south west) rectangle (current page.north east);
\end{tikzpicture}

\begin{minipage}[c][5in][c]{4.4in}
    \centering
    {\Huge\bfseries\color{primary} Your Title Here}
    
    \vspace{0.5in}
    
    {\large\color{primary} Your content goes here}
\end{minipage}

\newpage

% Slide 2 (add more slides with \newpage)
\begin{tikzpicture}[remember picture, overlay]
    \fill[bg] (current page.south west) rectangle (current page.north east);
\end{tikzpicture}

\begin{minipage}[c][5in][c]{4.4in}
    \centering
    {\Large\color{primary} Slide 2 Content}
\end{minipage}

\end{document}
"""

POST_YAML_TEMPLATE = """title: "{title}"
date: "{date}"

captions:
  facebook: ""
  instagram: ""
  linkedin: ""
  x: ""
  youtube: ""
"""


def get_posts_dir() -> Path:
    """Get the social_posts directory in home."""
    return Path.home() / "social_posts"


@click.command(name="create-post")
@click.argument("topic")
@click.option("--name", "-n", help="Override folder name (default: date_topic)")
def create_post(topic: str, name: str | None) -> None:
    """Create a new post folder structure.
    
    Creates ~/social_posts/YYYY_MM_DD_<topic>/ with:
    - main.tex (LaTeX template)
    - post.yaml (captions for all platforms)
    - images/ (empty folder for rendered PNGs)
    """
    today = date.today().strftime("%Y_%m_%d")
    folder_name = name if name else f"{today}_{topic.replace(' ', '_').lower()}"
    
    posts_dir = get_posts_dir()
    post_path = posts_dir / folder_name
    
    if post_path.exists():
        raise click.ClickException(f"Folder already exists: {post_path}")
    
    # Create directories
    post_path.mkdir(parents=True)
    (post_path / "images").mkdir()
    
    # Create main.tex
    (post_path / "main.tex").write_text(LATEX_TEMPLATE)
    
    # Create post.yaml
    yaml_content = POST_YAML_TEMPLATE.format(title=topic, date=today)
    (post_path / "post.yaml").write_text(yaml_content)
    
    click.echo(f"✓ Created post structure at: {post_path}")
    click.echo(f"  - main.tex (5in × 5in LaTeX template)")
    click.echo(f"  - post.yaml (add your captions)")
    click.echo(f"  - images/ (add rendered PNGs here)")
