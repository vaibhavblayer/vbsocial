"""Content generation pipeline for social media posts."""

# Lazy imports for fast CLI startup
__all__ = ["generate", "from_image"]


def __getattr__(name):
    if name == "generate":
        from .from_idea import generate
        return generate
    elif name == "from_image":
        from .from_image import from_image
        return from_image
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
