"""LaTeX templates for social media posts."""

# Main template with minted support for code highlighting (pdflatex compatible)
MAIN_TEMPLATE = r"""\documentclass[border=0pt]{{standalone}}
\usepackage[paperwidth=5in, paperheight=5in, margin=0.25in]{{geometry}}
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

% Custom environments
\newenvironment{{solution}}{{\par\textbf{{Solution:}}\par}}{{}}
\newenvironment{{idea}}{{\par\textbf{{Key Idea:}}\par}}{{}}
\newenvironment{{alternatesolution}}{{\par\textbf{{Alternate Approach:}}\par}}{{}}

\begin{{document}}

{content}

\end{{document}}
"""

# Main template that uses \input for separate component files
# Uses post.sty package
MAIN_TEMPLATE_MODULAR = r"""\documentclass{{article}}
\usepackage{{post}}

\begin{{document}}

\posttitle{{{title}}}

\begin{{enumerate}}
{enum_inputs}
\end{{enumerate}}

{code_section}

\end{{document}}
"""

# Slide template for carousel posts - raw content only
SLIDE_TEMPLATE = r"""{content}
"""

# Question slide - raw content, \item will be replaced with lambda style
QUESTION_SLIDE = r"""{question}
{diagram}
"""

# Solution slide - raw solution env
SOLUTION_SLIDE = r"""\begin{{solution}}
{solution}
\end{{solution}}
"""

# Idea slide - raw idea env
IDEA_SLIDE = r"""\begin{{idea}}
{idea}
\end{{idea}}
"""

# Code slide with minted (Pygments) - one-dark theme, matte background
CODE_SLIDE_TEMPLATE = r"""\begin{{minted}}[
    bgcolor=codebg,
    fontsize=\small,
    breaklines=true,
    style=one-dark,
]{{{language}}}
{code}
\end{{minted}}
"""

# Standalone code file template - raw minted, no overlay
CODE_FILE_TEMPLATE = r"""\inputminted[bgcolor=codebg,fontsize=\small,breaklines=true,style=one-dark]{{{language}}}{{datamodel.{ext}}}
"""

# Rust data model template
RUST_DATAMODEL_TEMPLATE = r"""/// {description}
#[derive(Debug, Clone)]
pub struct {struct_name} {{
{fields}
}}

impl {struct_name} {{
{methods}
}}
"""

# Python data model template  
PYTHON_DATAMODEL_TEMPLATE = r'''"""
{description}
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class {class_name}:
    """{docstring}"""
{fields}

{methods}
'''

# Swift data model template
SWIFT_DATAMODEL_TEMPLATE = r"""/// {description}
struct {struct_name} {{
{fields}
}}

extension {struct_name} {{
{methods}
}}
"""


def replace_item_with_lambda(content: str) -> str:
    """Replace \\item with \\item[$\\lambda.$] in content."""
    return content.replace(r"\item", r"\item[$\lambda.$]")


def create_code_slide(code: str, language: str) -> str:
    """Create raw minted code block."""
    return CODE_SLIDE_TEMPLATE.format(
        language=language,
        code=code,
    ).strip()


def create_code_slide_from_file(language: str) -> str:
    """Create raw \\inputminted for external code file."""
    ext = {
        "rust": "rs",
        "python": "py",
        "swift": "swift",
        "cpp": "cpp",
    }.get(language, language)
    
    return CODE_FILE_TEMPLATE.format(language=language, ext=ext)


def get_code_file_extension(language: str) -> str:
    """Get file extension for a language."""
    return {
        "rust": "rs",
        "python": "py",
        "swift": "swift",
        "c": "c",
        "zig": "zig",
        "go": "go",
        "cpp": "cpp",
    }.get(language, language)


def create_question_slide(question: str, diagram: str = "") -> str:
    """Create raw question content with lambda marker."""
    return QUESTION_SLIDE.format(
        question=question,
        diagram=diagram if diagram else "",
    ).strip()


def create_solution_slide(solution: str) -> str:
    """Create raw solution content."""
    if r"\begin{solution}" in solution:
        return solution.strip()
    return SOLUTION_SLIDE.format(solution=solution).strip()


def create_idea_slide(idea: str) -> str:
    """Create raw idea content for idea.tex.
    
    Note: If idea already contains \\begin{idea}, return as-is.
    """
    if r"\begin{idea}" in idea:
        return idea.strip()
    return IDEA_SLIDE.format(idea=idea).strip()


def assemble_document(slides: list[str]) -> str:
    """Assemble slides into a complete document."""
    content = "\n\n\\pagebreak\n\n".join(slides)
    return MAIN_TEMPLATE.format(content=content)


def assemble_modular_document(components: list[str], title: str = "PHYSICS") -> str:
    r"""Assemble document using \input for component files.
    
    Structure:
    - problem, idea, solution, alternate go inside \begin{enumerate}
    - code languages get \inputminted directly in main.tex
    
    Args:
        components: List of component names (e.g., ['problem', 'solution', 'idea', 'rust'])
        title: Title for \posttitle (default: PHYSICS)
    """
    enum_parts = []
    code_langs = []
    
    for comp in components:
        if comp in ("rust", "python", "swift", "c", "zig", "go", "cpp"):
            code_langs.append(comp)
        elif comp.startswith("code_"):
            # Handle old format code_rust -> rust
            code_langs.append(comp.replace("code_", ""))
        elif comp == "diagram":
            # Diagram goes in enumerate section
            enum_parts.append(comp)
        else:
            enum_parts.append(comp)
    
    # Build enum inputs
    enum_inputs = "\n".join(f"\\input{{{comp}}}" for comp in enum_parts)
    
    # Build code section - \inputminted directly
    code_lines = []
    for lang in code_langs:
        ext = get_code_file_extension(lang)
        code_lines.append(r"\pagebreak")
        code_lines.append(r"{\pagecolor{bg}")
        code_lines.append(r"\begin{center}\textsc{\color{codetitle}Data Model: " + lang.title() + r"}\end{center}")
        code_lines.append(f"\\inputminted{{{lang}}}{{datamodel.{ext}}}")
        code_lines.append(r"}")
    
    code_section = "\n".join(code_lines)
    
    return MAIN_TEMPLATE_MODULAR.format(
        title=title,
        enum_inputs=enum_inputs,
        code_section=code_section,
    )
