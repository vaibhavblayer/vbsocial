"""TikZ diagram generation for physics problems.

Uses vbagent's tikz agent to:
1. Reproduce diagrams from images exactly
2. Create illustrative diagrams for physics concepts
"""

from pathlib import Path

from .config import get_agent_config
from .debug import log_agent_call, log_agent_result, debug_transform


ILLUSTRATE_PROMPT = """You are a physics diagram specialist. Create a simple, clear TikZ diagram to illustrate a physics concept.

## Rules
1. Keep it SIMPLE - minimal elements
2. Use standard TikZ libraries (arrows, calc, patterns)
3. Label key quantities (forces, velocities, angles)
4. Use consistent style: thick lines, clear labels
5. Output ONLY the tikzpicture environment, no document wrapper

## Style Guidelines
- Vectors: ->, thick, labeled
- Objects: circles or rectangles, filled or outlined
- Axes: dashed, labeled
- Angles: arc with label
- Dimensions: |<->| style

## Output
- Raw TikZ code only (\\begin{tikzpicture}...\\end{tikzpicture})
- NO markdown code blocks
- NO explanations
"""

ILLUSTRATE_USER_TEMPLATE = """Create a simple TikZ diagram to illustrate this physics problem:

## Problem
{problem}

## Solution Context
{solution}

Create a clear, minimal diagram showing the key physical setup.
"""


def generate_tikz_from_image(image_path: str, description: str = "") -> str:
    """Generate TikZ code to reproduce a diagram from an image.
    
    Uses vbagent's tikz agent which has reference context.
    
    Args:
        image_path: Path to image containing diagram
        description: Optional description of what to focus on
        
    Returns:
        TikZ code string
    """
    import time
    from vbagent.agents.tikz import generate_tikz as vbagent_generate_tikz
    
    log_agent_call("TikZFromImage", description, image_path=image_path)
    
    start = time.time()
    result = vbagent_generate_tikz(
        description=description or "Reproduce this physics diagram exactly",
        image_path=image_path,
        search_references=True,
        use_context=True,
    )
    duration_ms = (time.time() - start) * 1000
    
    log_agent_result("TikZFromImage", result, duration_ms)
    return result


def generate_tikz_illustration(problem: str, solution: str = "") -> str:
    """Generate an illustrative TikZ diagram for a physics problem.
    
    Creates a simple diagram even if the problem has no diagram.
    
    Args:
        problem: Physics problem text (LaTeX)
        solution: Solution context (LaTeX)
        
    Returns:
        TikZ code string
    """
    import time
    from vbagent.agents.base import create_agent, run_agent_sync
    from agents.model_settings import ModelSettings, Reasoning
    
    config = get_agent_config("datamodel")  # Use same config as datamodel
    
    settings = ModelSettings(reasoning=Reasoning(effort=config["reasoning"]))
    
    agent = create_agent(
        name="TikZIllustrator",
        instructions=ILLUSTRATE_PROMPT,
        model=config["model"],
        model_settings=settings,
    )
    
    input_text = ILLUSTRATE_USER_TEMPLATE.format(
        problem=problem,
        solution=solution or "(no solution provided)",
    )
    
    log_agent_call("TikZIllustrator", input_text, model=config["model"])
    
    start = time.time()
    result = run_agent_sync(agent, input_text)
    duration_ms = (time.time() - start) * 1000
    
    log_agent_result("TikZIllustrator", result, duration_ms)
    
    # Clean up markdown if present
    if "```tikz" in result:
        result = result.split("```tikz")[1].split("```")[0]
    elif "```latex" in result:
        result = result.split("```latex")[1].split("```")[0]
    elif "```" in result:
        result = result.split("```")[1].split("```")[0]
    
    return result.strip()


def generate_tikz(
    problem: str,
    solution: str = "",
    image_path: str | None = None,
    has_diagram: bool = False,
) -> str:
    """Generate TikZ diagram - either from image or as illustration.
    
    Args:
        problem: Physics problem text
        solution: Solution context
        image_path: Path to image (if has diagram)
        has_diagram: Whether the problem/image has a diagram to reproduce
        
    Returns:
        TikZ code string
    """
    if has_diagram and image_path:
        # Reproduce diagram from image
        return generate_tikz_from_image(image_path, problem[:200])
    else:
        # Create illustrative diagram
        return generate_tikz_illustration(problem, solution)
