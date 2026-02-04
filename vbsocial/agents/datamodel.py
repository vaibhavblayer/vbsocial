"""Data model generation agents for physics problems.

Generates code representations of physics problems in various languages.
Teaches students how to model physics concepts in programming.
"""

from vbagent.agents.base import create_agent, run_agent_sync
from agents.model_settings import ModelSettings, Reasoning

from .config import get_agent_config


# ============================================================================
# SYSTEM PROMPTS - Language specific
# ============================================================================

BASE_RULES = """## Rules
1. NO main function, NO instance creation, NO tests
2. Doc comments: 1-2 short lines explaining the physics concept
3. NO special characters in comments (no subscripts, no unicode, no math symbols)
4. Keep it minimal - avoid unnecessary abstractions
5. Use consistent naming across languages

## Comment Style
- Plain English only, no special chars like p₀ or γ
- Write "pressure_0" not "p₀", write "gamma" not "γ"
- One or two short lines max per block
- Explain what the struct/function represents

## Output
- Raw code only
- NO markdown code blocks
- NO explanations
"""

RUST_PROMPT = f"""You are a Rust architect. Generate a concise data model for physics problems.

{BASE_RULES}

## Rust Specific
- ONLY struct, impl, enum, trait
- Use f64 for quantities
- Use (f64, f64) or [f64; 2] for vectors
"""

PYTHON_PROMPT = f"""You are a Python developer. Generate a concise data model for physics problems.

{BASE_RULES}

## Python Specific
- ONLY dataclass definitions with methods
- Use float for quantities
- Use tuple[float, float] for vectors
"""

SWIFT_PROMPT = f"""You are a Swift developer. Generate a concise data model for physics problems.

{BASE_RULES}

## Swift Specific
- ONLY struct, extension, enum, protocol
- Use Double for quantities
"""

C_PROMPT = f"""You are a C developer. Generate a concise data model for physics problems.

{BASE_RULES}

## C Specific
- ONLY struct, typedef, function definitions
- Use double for quantities
- Use struct for vectors
- Include function implementations (not just declarations)
"""

ZIG_PROMPT = f"""You are a Zig developer. Generate a concise data model for physics problems.

{BASE_RULES}

## Zig Specific
- ONLY struct, const, fn
- Use f64 for quantities
- Use [2]f64 for vectors
"""

GO_PROMPT = f"""You are a Go developer. Generate a concise data model for physics problems.

{BASE_RULES}

## Go Specific
- ONLY struct, type, func
- Use float64 for quantities
- Use [2]float64 for vectors
"""


# ============================================================================
# USER TEMPLATES
# ============================================================================

USER_TEMPLATE = """Generate a minimal {language} data model for this physics problem:

## Problem
{problem}

## Solution Context
{solution}

Keep it brief - only essential types and methods.
"""

USER_TEMPLATE_WITH_REFERENCE = """Generate a minimal {language} data model for this physics problem.

## Problem
{problem}

## Solution Context
{solution}

## Reference Code ({ref_language})
Use the SAME variable names, function names, and structure as this reference:

```{ref_language}
{reference_code}
```

Keep naming consistent with the reference.
"""


# ============================================================================
# LANGUAGE CONFIG
# ============================================================================

LANGUAGE_CONFIG = {
    "rust": {"prompt": RUST_PROMPT, "ext": "rs", "block": "rust"},
    "python": {"prompt": PYTHON_PROMPT, "ext": "py", "block": "python"},
    "swift": {"prompt": SWIFT_PROMPT, "ext": "swift", "block": "swift"},
    "c": {"prompt": C_PROMPT, "ext": "c", "block": "c"},
    "zig": {"prompt": ZIG_PROMPT, "ext": "zig", "block": "zig"},
    "go": {"prompt": GO_PROMPT, "ext": "go", "block": "go"},
}


# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def clean_code_output(result: str, language: str) -> str:
    """Clean up markdown code blocks from output."""
    block = LANGUAGE_CONFIG.get(language, {}).get("block", language)
    
    if f"```{block}" in result:
        result = result.split(f"```{block}")[1].split("```")[0]
    elif "```" in result:
        result = result.split("```")[1].split("```")[0]
    
    return result.strip()


def generate_datamodel(
    problem: str,
    language: str,
    solution: str = "",
    reference_code: str | None = None,
    reference_language: str | None = None,
    model: str | None = None,
) -> str:
    """Generate data model for a physics problem.
    
    Args:
        problem: The physics problem (LaTeX)
        language: Target language (rust, python, swift, c, zig, go)
        solution: Solution context (LaTeX) - helps model understand the physics
        reference_code: Existing code in another language for consistency
        reference_language: Language of reference code
        model: Override model from config
        
    Returns:
        Generated code as a string
    """
    if language not in LANGUAGE_CONFIG:
        raise ValueError(f"Unsupported language: {language}. Use: {list(LANGUAGE_CONFIG.keys())}")
    
    config = get_agent_config("datamodel")
    lang_config = LANGUAGE_CONFIG[language]
    
    settings = ModelSettings(reasoning=Reasoning(effort=config["reasoning"]))
    
    agent = create_agent(
        name=f"{language.title()}DataModelAgent",
        instructions=lang_config["prompt"],
        model=model or config["model"],
        model_settings=settings,
    )
    
    # Build input with or without reference
    if reference_code and reference_language:
        input_text = USER_TEMPLATE_WITH_REFERENCE.format(
            language=language.title(),
            problem=problem,
            solution=solution or "(no solution provided)",
            ref_language=reference_language,
            reference_code=reference_code,
        )
    else:
        input_text = USER_TEMPLATE.format(
            language=language.title(),
            problem=problem,
            solution=solution or "(no solution provided)",
        )
    
    result = run_agent_sync(agent, input_text)
    return clean_code_output(result, language)


def get_code_file_extension(language: str) -> str:
    """Get file extension for a language."""
    return LANGUAGE_CONFIG.get(language, {}).get("ext", language)


def get_supported_languages() -> list[str]:
    """Get list of supported languages."""
    return list(LANGUAGE_CONFIG.keys())
