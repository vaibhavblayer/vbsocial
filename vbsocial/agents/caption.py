"""Caption generation agent for social media platforms.

Two-part caption system:
1. Physics caption - from problem, solution, idea (storytelling)
2. Code caption - from datamodel, functions (thinking in code)

Combined must fit within platform limits.
"""

from pydantic import BaseModel, Field

from .config import get_agent_config
from .debug import log_agent_call, log_agent_result


# Character limits per platform
CHAR_LIMITS = {
    "instagram": 2200,
    "facebook": 2000,
    "linkedin": 3000,
    "x": 280,
    "youtube": 5000,
}


class CaptionOutput(BaseModel):
    """Structured output for platform-specific captions."""
    instagram: str = Field(description="Instagram caption")
    facebook: str = Field(description="Facebook caption")
    linkedin: str = Field(description="LinkedIn caption")
    x: str = Field(description="X/Twitter caption")
    youtube: str = Field(description="YouTube community post")


class CodeCaptionOutput(BaseModel):
    """Code-focused caption additions."""
    instagram: str = Field(description="Code angle for Instagram ~300 chars")
    facebook: str = Field(description="Code angle for Facebook ~400 chars")
    linkedin: str = Field(description="Code angle for LinkedIn ~500 chars")
    x: str = Field(description="Code teaser for X ~50 chars")
    youtube: str = Field(description="Code deep-dive for YouTube ~800 chars")


PHYSICS_CAPTION_PROMPT = """You are a physics educator creating engaging social media content.

Transform physics problems into accessible, storytelling content.

## CRITICAL FORMATTING RULES
1. NO backslashes in output - write plain text
2. NO markdown code blocks (no triple backticks)
3. NO LaTeX syntax - convert all math to plain English
4. Write equations in words: "H equals k times A times deltaT divided by L"
5. Use simple ASCII only - no special characters
6. DO NOT ask questions like "Want me to draw..." or "Should I explain..."
7. DO NOT offer to do anything - just deliver the content
8. NO hashtags in physics section - they go at the very end after code section

## Content Style
- Tell a STORY, not a lecture
- Start with a relatable hook or question TO THE READER
- Explain the "why" before the "how"
- Use analogies (heat flow like water, resistance like traffic)
- End with a thought-provoking statement, NOT an offer to do more

## EXAMPLE INSTAGRAM OUTPUT (physics part only, ~1600 chars):

Ever wondered why some walls feel cold even when the room is warm? It comes down to how heat flows through layered materials.

Picture a two-layer slab: the left face sits at temperature T2, the right at T1, with T2 greater than T1. Layer one has conductivity K and thickness x. Layer two conducts twice as well at 2K but is four times thicker at 4x.

Here is the key insight: in steady state, the same heat must pass through both layers. Think of it like water flowing through two pipes in series. The flow rate is identical in both pipes, but each pipe creates its own pressure drop.

To find the interface temperature, set the heat flow through layer one equal to layer two. Heat through layer one is K times A times the temperature drop divided by x. Heat through layer two is 2K times A times its temperature drop divided by 4x.

Solving gives the interface temperature as two T2 plus T1, all divided by three. The total heat flow becomes K times A times T2 minus T1 divided by x, multiplied by one third.

The factor f equals one third. Even though layer two conducts better, its greater thickness makes it contribute significant resistance.

## EXAMPLE FACEBOOK OUTPUT (~1400 chars):

How heat navigates a two-material sandwich

When heat flows through stacked materials, each layer acts like a resistor in series. The layer with higher resistance dominates the temperature drop.

Consider two layers: the first has conductivity K and thickness x, the second has conductivity 2K and thickness 4x. The outer faces are at T2 and T1.

In steady state, heat flow is constant through both layers. Setting up the flux equations and solving for the interface temperature gives T equals two T2 plus T1 divided by three.

The total heat flow works out to K times A times T2 minus T1 divided by x, multiplied by one third. So f equals one third.

The takeaway: higher conductivity does not guarantee lower resistance. Thickness matters equally. This principle guides insulation design, heat sink engineering, and thermal management in electronics.

## Platform Guidelines (leave room for code section)
- Instagram: ~1600 chars, conversational, NO hashtags
- Facebook: ~1400 chars, article style, end with insight
- LinkedIn: ~2200 chars, professional, NO hashtags
- X: ~220 chars, one key insight, 1 hashtag max
- YouTube: ~3500 chars, detailed, invite engagement
"""


CODE_CAPTION_PROMPT = """You are a developer educator explaining how physics maps to code.

Create SHORT additions focusing on the coding/modeling aspect.

## CRITICAL RULES
1. NO backslashes, NO markdown, NO code blocks
2. Plain text only - describe the modeling approach
3. Focus on: how physics concepts become data structures
4. Point readers to the SLIDES to see actual code
5. Keep it SHORT - these are additions to existing captions
6. For Instagram: END with hashtags (5-8 relevant ones)

## EXAMPLE INSTAGRAM CODE SECTION (~400 chars):

Thinking in code: I modeled each material as a ThermalLayer struct holding conductivity and thickness. The CompositeSlab groups layers and computes total thermal resistance. Two key functions: interface_temperature finds where layers meet, and steady_heat_flow returns the flux. Swipe through the slides to see Rust and Swift implementations.

#Physics #Coding #Rust #Swift #STEM #ThermalEngineering #Programming

## EXAMPLE FACEBOOK CODE SECTION (~500 chars):

The code angle: Each physical layer becomes a ThermalLayer type with conductivity and thickness fields. CompositeSlab wraps the layers and exposes methods for thermal analysis. The interface_temperature function solves for the boundary temperature by balancing heat flux. The steady_heat_flow function returns total heat transfer rate. This separation keeps physics logic clean and testable. Check the slides for complete Rust and Swift implementations you can run yourself.

## EXAMPLE LINKEDIN CODE SECTION (~600 chars):

From physics to code: The problem naturally maps to a layered data model. Each material becomes a ThermalLayer struct encapsulating conductivity and thickness. A CompositeSlab aggregates layers and provides thermal analysis methods. The interface_temperature function computes boundary conditions by enforcing flux continuity. The steady_heat_flow function returns the heat transfer rate through the composite. This modeling approach isolates physical parameters, enables unit testing, and scales to multi-layer systems. Implementation in Rust and Swift available in the slides.

#ThermalEngineering #Physics #SoftwareEngineering

## Platform targets
- Instagram: ~400 chars, end with 5-8 hashtags
- Facebook: ~500 chars, explain modeling
- LinkedIn: ~600 chars, professional, 2-3 hashtags at end
- X: ~50 chars, tiny hook
- YouTube: ~1000 chars, detailed walkthrough
"""


def _run_caption_agent(prompt: str, input_text: str, output_type, name: str, model: str | None = None):
    """Run a caption agent with given prompt."""
    import time
    from vbagent.agents.base import create_agent, run_agent_sync
    from agents.model_settings import ModelSettings, Reasoning
    
    config = get_agent_config("caption")
    settings = ModelSettings(reasoning=Reasoning(effort=config["reasoning"]))
    
    agent = create_agent(
        name=name,
        instructions=prompt,
        model=model or config["model"],
        model_settings=settings,
        output_type=output_type,
    )
    
    log_agent_call(name, input_text, model=model or config["model"])
    
    start = time.time()
    result = run_agent_sync(agent, input_text)
    duration_ms = (time.time() - start) * 1000
    
    log_agent_result(name, str(result), duration_ms)
    
    return result


def generate_physics_captions(problem: str, solution: str = "", idea: str = "", model: str | None = None) -> CaptionOutput:
    """Generate physics-focused captions (part 1)."""
    input_parts = ["## Physics Problem", problem, ""]
    if solution:
        input_parts.extend(["## Solution", solution, ""])
    if idea:
        input_parts.extend(["## Key Idea", idea, ""])
    
    return _run_caption_agent(
        PHYSICS_CAPTION_PROMPT,
        "\n".join(input_parts),
        CaptionOutput,
        "PhysicsCaptionAgent",
        model,
    )


def generate_code_captions(code_snippets: dict[str, str], model: str | None = None) -> CodeCaptionOutput:
    """Generate code-focused caption additions (part 2)."""
    input_parts = ["## Code Implementations Available", ""]
    for lang, code in code_snippets.items():
        # Include structure info, not full code
        lines = code.split('\n')
        structs = [l.strip() for l in lines if any(kw in l for kw in ['struct ', 'class ', 'fn ', 'func ', 'def ', 'impl '])]
        input_parts.append(f"### {lang.title()}")
        input_parts.append(f"Key elements: {', '.join(structs[:5])}")
        input_parts.append("")
    
    return _run_caption_agent(
        CODE_CAPTION_PROMPT,
        "\n".join(input_parts),
        CodeCaptionOutput,
        "CodeCaptionAgent",
        model,
    )


def combine_captions(physics: CaptionOutput, code: CodeCaptionOutput) -> dict[str, str]:
    """Combine physics and code captions, respecting platform limits."""
    combined = {}
    
    for platform in ["instagram", "facebook", "linkedin", "x", "youtube"]:
        physics_text = getattr(physics, platform)
        code_text = getattr(code, platform)
        limit = CHAR_LIMITS[platform]
        
        # Combine with separator
        if platform == "x":
            # X is too short - just use physics or truncate
            full = physics_text
        else:
            separator = "\n\n---\n\n" if platform in ("facebook", "linkedin", "youtube") else "\n\n"
            full = physics_text + separator + code_text
        
        # Truncate if needed
        if len(full) > limit:
            full = full[:limit-3] + "..."
        
        combined[platform] = full
    
    return combined


def generate_captions_from_post(post_path: str) -> dict[str, str]:
    """Generate combined captions from an existing post directory.
    
    Returns dict with platform -> caption for use in post.yaml
    """
    from pathlib import Path
    
    post_dir = Path(post_path)
    
    # Read physics components
    problem = ""
    solution = ""
    idea = ""
    
    if (post_dir / "problem.tex").exists():
        problem = (post_dir / "problem.tex").read_text()
    if (post_dir / "solution.tex").exists():
        solution = (post_dir / "solution.tex").read_text()
    if (post_dir / "idea.tex").exists():
        idea = (post_dir / "idea.tex").read_text()
    
    # Read code files
    code_snippets = {}
    code_files = [
        ("rust", "datamodel.rs"),
        ("swift", "datamodel.swift"),
        ("python", "datamodel.py"),
        ("c", "datamodel.c"),
    ]
    for lang, filename in code_files:
        filepath = post_dir / filename
        if filepath.exists():
            code_snippets[lang] = filepath.read_text()
    
    # Generate physics captions
    physics_captions = generate_physics_captions(problem, solution, idea)
    
    # Generate code captions if code exists
    if code_snippets:
        code_captions = generate_code_captions(code_snippets)
        return combine_captions(physics_captions, code_captions)
    else:
        # No code - just return physics captions as dict
        return {
            "instagram": physics_captions.instagram,
            "facebook": physics_captions.facebook,
            "linkedin": physics_captions.linkedin,
            "x": physics_captions.x,
            "youtube": physics_captions.youtube,
        }
