"""Social media AI agents for content generation."""

# Lazy imports for fast CLI startup
__all__ = ["generate_captions", "CaptionOutput", "plan_content", "ContentPlan"]


def __getattr__(name):
    if name == "generate_captions" or name == "CaptionOutput":
        from .caption import generate_captions, CaptionOutput
        return generate_captions if name == "generate_captions" else CaptionOutput
    elif name == "plan_content" or name == "ContentPlan":
        from .content_planner import plan_content, ContentPlan
        return plan_content if name == "plan_content" else ContentPlan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
