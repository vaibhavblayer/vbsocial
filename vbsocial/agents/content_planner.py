"""Content planning agent for carousel/multi-slide posts."""

from pydantic import BaseModel, Field

from vbagent.agents.base import create_agent, run_agent_sync

from .config import get_agent_config


class SlideContent(BaseModel):
    """Content for a single slide."""
    
    title: str = Field(description="Slide title/header")
    content: str = Field(description="Main content for the slide")
    has_diagram: bool = Field(description="Whether this slide needs a TikZ diagram")
    diagram_description: str | None = Field(default=None, description="Description of diagram if needed")


class ContentPlan(BaseModel):
    """Structured plan for a multi-slide post."""
    
    topic: str = Field(description="Main topic/title")
    slides: list[SlideContent] = Field(description="List of slides (2-10)")
    difficulty: str = Field(description="Difficulty level: beginner, intermediate, advanced")
    key_concepts: list[str] = Field(description="Key physics concepts covered")
    prerequisites: list[str] = Field(description="Prerequisites for understanding")


CONTENT_PLANNER_PROMPT = """You are an educational content planner for physics social media posts.

Given a topic or idea, create a structured plan for a carousel/multi-slide post.

Guidelines:
- 3-6 slides is optimal for engagement
- First slide: Hook/problem statement
- Middle slides: Solution steps or concept explanation
- Last slide: Key takeaway or call-to-action

For each slide, specify:
- Clear title
- Concise content (will be rendered in LaTeX)
- Whether a diagram is needed
- Diagram description if needed

Keep content:
- Mathematically accurate
- Visually balanced (not too text-heavy)
- Progressive in complexity
- Self-contained but connected

Output a structured plan that can be directly converted to LaTeX slides.
"""


def plan_content(
    idea: str,
    num_slides: int | None = None,
    include_code: bool = False,
    model: str | None = None,
) -> ContentPlan:
    """Plan content structure for a social media post.
    
    Args:
        idea: The topic, problem, or content idea
        num_slides: Optional target number of slides
        include_code: Whether to include programming examples
        model: Override model from config
        
    Returns:
        ContentPlan with structured slide content
    """
    config = get_agent_config("content_planner")
    
    agent = create_agent(
        name="ContentPlannerAgent",
        instructions=CONTENT_PLANNER_PROMPT,
        model=model or config["model"],
        output_type=ContentPlan,
    )
    
    input_text = f"Create a content plan for: {idea}"
    if num_slides:
        input_text += f"\nTarget slides: {num_slides}"
    if include_code:
        input_text += "\nInclude programming/code examples where relevant."
    
    return run_agent_sync(agent, input_text)
