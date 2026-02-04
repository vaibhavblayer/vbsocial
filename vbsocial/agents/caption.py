"""Caption generation agent for social media platforms."""

from pydantic import BaseModel, Field

from vbagent.agents.base import create_agent, run_agent_sync
from agents.model_settings import ModelSettings, Reasoning

from .config import get_agent_config


class CaptionOutput(BaseModel):
    """Structured output for platform-specific captions."""
    
    facebook: str = Field(description="Facebook caption - can be longer, professional tone")
    instagram: str = Field(description="Instagram caption with hashtags, engaging tone")
    linkedin: str = Field(description="LinkedIn caption - professional, educational focus")
    x: str = Field(description="X/Twitter caption - concise, under 280 chars")
    youtube: str = Field(description="YouTube community post caption")


CAPTION_PROMPT = """You are a social media content specialist for educational physics content.

Given a physics topic/problem and optional context, generate engaging captions for each platform.

Guidelines per platform:

**Facebook**: 
- Professional but approachable
- Can be 2-3 paragraphs
- Include a question to encourage engagement
- No hashtags needed

**Instagram**:
- Start with a hook (emoji or question)
- Educational but fun tone
- End with 5-10 relevant hashtags
- Use line breaks for readability

**LinkedIn**:
- Professional, educational focus
- Highlight learning value
- Good for career/skill development angle
- 1-2 relevant hashtags max

**X (Twitter)**:
- MUST be under 280 characters
- Punchy, direct
- Can include 1-2 hashtags
- Use thread hook if complex topic

**YouTube**:
- Community post style
- Can ask for video topic suggestions
- Encourage comments/discussion

Always:
- Match the physics difficulty level
- Be accurate with physics terminology
- Make it accessible to students
"""


def generate_captions(
    topic: str,
    content_summary: str | None = None,
    difficulty: str = "intermediate",
    model: str | None = None,
) -> CaptionOutput:
    """Generate platform-specific captions for a physics topic.
    
    Args:
        topic: The physics topic or problem title
        content_summary: Optional summary of the content/solution
        difficulty: Difficulty level (beginner, intermediate, advanced)
        model: Override model from config
        
    Returns:
        CaptionOutput with captions for each platform
    """
    config = get_agent_config("caption")
    
    settings = ModelSettings(reasoning=Reasoning(effort=config["reasoning"]))
    
    agent = create_agent(
        name="CaptionAgent",
        instructions=CAPTION_PROMPT,
        model=model or config["model"],
        model_settings=settings,
        output_type=CaptionOutput,
    )
    
    input_text = f"""
Topic: {topic}
Difficulty: {difficulty}
"""
    if content_summary:
        input_text += f"\nContent Summary:\n{content_summary}"
    
    return run_agent_sync(agent, input_text)
