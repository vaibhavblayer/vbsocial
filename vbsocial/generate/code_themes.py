"""Pygments code themes for minted.

Categorized into light and dark themes with easy selection.
"""

# Light themes - good for light backgrounds
LIGHT_THEMES = {
    "xcode": "xcode",  # Default - clean, Apple style
    "friendly": "friendly",
    "colorful": "colorful",
    "autumn": "autumn",
    "tango": "tango",
    "perldoc": "perldoc",
    "borland": "borland",
    "pastie": "pastie",
    "trac": "trac",
    "default": "default",
    "emacs": "emacs",
    "vs": "vs",
    "igor": "igor",
    "paraiso-light": "paraiso-light",
    "lovelace": "lovelace",
    "algol": "algol",
    "algol_nu": "algol_nu",
    "arduino": "arduino",
    "rainbow_dash": "rainbow_dash",
    "bw": "bw",  # Black and white
}

# Dark themes - good for dark backgrounds
DARK_THEMES = {
    "one-dark": "one-dark",
    "monokai": "monokai",
    "dracula": "dracula",
    "gruvbox-dark": "gruvbox-dark",
    "nord": "nord",
    "native": "native",
    "fruity": "fruity",
    "vim": "vim",
    "murphy": "murphy",
    "rrt": "rrt",
    "paraiso-dark": "paraiso-dark",
    "solarized-dark": "solarized-dark",
    "zenburn": "zenburn",
    "material": "material",
    "inkpot": "inkpot",
    "github-dark": "github-dark",
    "stata-dark": "stata-dark",
    "lightbulb": "lightbulb",
}

# All themes combined
ALL_THEMES = {**LIGHT_THEMES, **DARK_THEMES}

# Default theme
DEFAULT_THEME = "xcode"


def get_theme(name_or_number: str | int) -> str:
    """Get theme name from string name or number.
    
    Args:
        name_or_number: Theme name (e.g., "xcode") or number (e.g., 1, "1")
        
    Returns:
        Theme name for minted
        
    Examples:
        get_theme("xcode") -> "xcode"
        get_theme(1) -> "xcode"
        get_theme("5") -> "tango"
    """
    # If it's a number or numeric string, use indexed lookup
    try:
        idx = int(name_or_number)
        theme_list = list(ALL_THEMES.keys())
        if 1 <= idx <= len(theme_list):
            return ALL_THEMES[theme_list[idx - 1]]
        else:
            raise ValueError(f"Theme number must be between 1 and {len(theme_list)}")
    except (ValueError, TypeError):
        pass
    
    # Otherwise treat as theme name
    name = str(name_or_number).lower()
    if name in ALL_THEMES:
        return ALL_THEMES[name]
    
    # Fallback to default
    return DEFAULT_THEME


def is_dark_theme(theme: str) -> bool:
    """Check if theme is dark."""
    return theme in DARK_THEMES.values()


def list_themes() -> str:
    """Return formatted list of all themes."""
    lines = ["Available Code Themes:", ""]
    
    lines.append("LIGHT THEMES (for light backgrounds):")
    for i, name in enumerate(LIGHT_THEMES.keys(), 1):
        marker = " (default)" if name == DEFAULT_THEME else ""
        lines.append(f"  {i:2d}. {name}{marker}")
    
    lines.append("")
    lines.append("DARK THEMES (for dark backgrounds):")
    start = len(LIGHT_THEMES) + 1
    for i, name in enumerate(DARK_THEMES.keys(), start):
        lines.append(f"  {i:2d}. {name}")
    
    lines.append("")
    lines.append("Usage:")
    lines.append("  vbsocial assemble . --code-theme xcode")
    lines.append("  vbsocial assemble . --code-theme 5")
    
    return "\n".join(lines)
