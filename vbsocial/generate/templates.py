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


def has_diagram_reference(content: str) -> bool:
    """Check if content references a diagram file."""
    return r"\input{diagram}" in content or r"\include{diagram}" in content


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


def split_code_into_blocks(code: str, language: str) -> list[str]:
    """Split code into logical blocks that shouldn't be broken across pages.
    
    Each block = doc comments + struct/impl/function
    Comments stay attached to their code.
    
    Returns list of code blocks.
    """
    import re
    
    lines = code.split('\n')
    blocks = []
    current_block_lines = []
    brace_depth = 0
    in_code_block = False  # True when we're inside a struct/impl/fn
    
    # Patterns for code block starts (not comments)
    block_start_patterns = {
        "rust": r'^(pub\s+)?(struct|impl|enum|fn|trait|mod|type|use)\s+',
        "python": r'^(class|def|@)',
        "swift": r'^(public\s+|private\s+)?(struct|class|extension|func|enum|protocol|import)\s+',
        "c": r'^(struct|typedef|static\s+|extern\s+|#include|double|int|void|float)\s*',
        "go": r'^(type|func|package|import)\s+',
        "zig": r'^(pub\s+)?(const|fn|struct)\s+',
    }
    
    pattern = block_start_patterns.get(language, r'^(struct|class|fn|func|def)\s+')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines at the start
        if not current_block_lines and not stripped:
            continue
        
        # Check if this line starts actual code (not a comment)
        is_code_start = bool(re.match(pattern, stripped))
        
        # If we hit a new code block start and we're not inside braces
        if is_code_start and brace_depth == 0 and in_code_block:
            # Save previous block
            block_text = '\n'.join(current_block_lines).strip()
            if block_text:
                blocks.append(block_text)
            current_block_lines = []
            in_code_block = False
        
        # Add line to current block
        current_block_lines.append(line)
        
        # Track if we're in a code block
        if is_code_start:
            in_code_block = True
        
        # Track brace depth
        if language in ("rust", "swift", "c", "go", "zig"):
            brace_depth += line.count('{') - line.count('}')
            # When braces close, we've finished a block
            if brace_depth == 0 and in_code_block and '{' in ''.join(current_block_lines):
                block_text = '\n'.join(current_block_lines).strip()
                if block_text:
                    blocks.append(block_text)
                current_block_lines = []
                in_code_block = False
    
    # Don't forget the last block
    if current_block_lines:
        block_text = '\n'.join(current_block_lines).strip()
        if block_text:
            blocks.append(block_text)
    
    # If no blocks found, return the whole code as one block
    if not blocks:
        return [code.strip()]
    
    return blocks


def create_code_tex_content(code: str, language: str) -> str:
    """Create LaTeX content for code with smart page breaks.
    
    Splits code into logical blocks and wraps each in \\vbox{}
    so page breaks happen between blocks, not inside them.
    """
    blocks = split_code_into_blocks(code, language)
    
    tex_parts = []
    for block in blocks:
        # Wrap each block in vbox to prevent internal page breaks
        tex_parts.append(r"\vbox{")
        tex_parts.append(r"\begin{minted}{" + language + "}")
        tex_parts.append(block)
        tex_parts.append(r"\end{minted}")
        tex_parts.append(r"}")
        tex_parts.append("")  # Empty line between blocks
    
    return "\n".join(tex_parts)


def create_all_code_tex(post_path: str, code_langs: list[str], max_lines_per_page: int = 20) -> str:
    """Create a single code.tex file with all languages.
    
    Each language gets:
    - pagebreak
    - dark background
    - title at TOP (outside vfill)
    - code blocks with smart page breaks (max ~20 lines per page)
    - vertical centering of code with vfill
    
    Args:
        post_path: Path to post directory
        code_langs: List of languages to include
        max_lines_per_page: Max lines before forcing page break (default 20)
    
    Returns the tex content.
    """
    from pathlib import Path
    
    post_dir = Path(post_path)
    tex_parts = []
    
    for lang in code_langs:
        ext = get_code_file_extension(lang)
        datamodel_file = post_dir / f"datamodel.{ext}"
        
        if not datamodel_file.exists():
            continue
        
        code = datamodel_file.read_text()
        blocks = split_code_into_blocks(code, lang)
        
        # Track lines per page
        current_page_lines = 0
        is_first_page = True
        page_blocks = []  # Blocks for current page
        
        def emit_page(blocks_to_emit: list[str], show_title: bool, is_continuation: bool = False):
            """Emit a page with given blocks."""
            nonlocal tex_parts
            
            tex_parts.append(r"\pagebreak")
            tex_parts.append(r"{\pagecolor{bg}")
            
            # Title at TOP (outside vfill)
            title_suffix = " (cont.)" if is_continuation else ""
            tex_parts.append(r"\begin{center}\textsc{\color{codetitle}Data Model: " + lang.title() + title_suffix + r"}\end{center}")
            
            tex_parts.append(r"\vspace*{\fill}")  # Top fill for centering code
            
            # Blocks
            for block in blocks_to_emit:
                tex_parts.append(r"\vbox{")
                tex_parts.append(r"\begin{minted}{" + lang + "}")
                tex_parts.append(block)
                tex_parts.append(r"\end{minted}")
                tex_parts.append(r"}")
            
            tex_parts.append(r"\vspace*{\fill}")  # Bottom fill for centering
            tex_parts.append(r"}")
            tex_parts.append("")
        
        for block in blocks:
            block_lines = len(block.split('\n'))
            
            # Check if adding this block would exceed limit
            if current_page_lines + block_lines > max_lines_per_page and page_blocks:
                # Emit current page and start new one
                emit_page(page_blocks, show_title=is_first_page, is_continuation=not is_first_page)
                is_first_page = False
                page_blocks = []
                current_page_lines = 0
            
            # Add block to current page
            page_blocks.append(block)
            current_page_lines += block_lines
        
        # Emit remaining blocks
        if page_blocks:
            emit_page(page_blocks, show_title=is_first_page, is_continuation=not is_first_page)
    
    return "\n".join(tex_parts)
    
    return "\n".join(tex_parts)


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


def assemble_modular_document(components: list[str], title: str = "PHYSICS", post_path: str | None = None) -> str:
    r"""Assemble document using \input for component files.
    
    Structure:
    - problem, idea, solution, alternate go inside \begin{enumerate}
    - all code languages go into a single code.tex with smart page breaks
    
    Order: problem -> diagram -> idea -> solution -> alternate -> code
    
    Args:
        components: List of component names (e.g., ['problem', 'solution', 'idea', 'rust'])
        title: Title for \posttitle (default: PHYSICS)
        post_path: Path to post directory (for creating code.tex)
    """
    from pathlib import Path
    
    # Define the correct order
    ORDER = ["problem", "diagram", "idea", "solution", "alternate"]
    
    enum_parts = []
    code_langs = []
    
    for comp in components:
        if comp in ("rust", "python", "swift", "c", "zig", "go", "cpp"):
            code_langs.append(comp)
        elif comp.startswith("code_"):
            code_langs.append(comp.replace("code_", ""))
        else:
            enum_parts.append(comp)
    
    # Sort enum_parts by ORDER
    enum_parts_sorted = sorted(enum_parts, key=lambda x: ORDER.index(x) if x in ORDER else 99)
    
    # Build enum inputs
    enum_inputs = "\n".join(f"\\input{{{comp}}}" for comp in enum_parts_sorted)
    
    # Build code section
    code_section = ""
    if code_langs and post_path:
        # Create single code.tex with all languages
        code_tex_content = create_all_code_tex(post_path, code_langs)
        if code_tex_content:
            code_tex_file = Path(post_path) / "code.tex"
            code_tex_file.write_text(code_tex_content)
            code_section = r"\input{code}"
    elif code_langs:
        # Fallback: no post_path, use inputminted directly
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
