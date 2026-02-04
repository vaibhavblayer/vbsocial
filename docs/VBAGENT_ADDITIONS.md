# vbsocial AI Content Generation

## Current Implementation

The data model agents are implemented in `vbsocial/agents/datamodel.py` and work with the vbagent package.

### Commands

#### `vbsocial datamodel`
Generate standalone data model code from a physics problem.

```bash
# Generate Rust data model
vbsocial datamodel "projectile motion with initial velocity v0 at angle theta" -l rust

# Generate Python data model from file
vbsocial datamodel -f problem.tex -l python

# Output to file
vbsocial datamodel "simple harmonic oscillator" -l swift -o oscillator.swift
```

#### `vbsocial generate`
Generate complete social media post with optional code slide.

```bash
# Basic generation
vbsocial generate -i "projectile motion basics"

# With Rust code slide
vbsocial generate -i "pursuit problem kinematics" --code rust -r

# With Python code slide and custom name
vbsocial generate -i "Newton's laws" -c python -n "newtons_laws" -r
```

#### `vbsocial from-image`
Generate post from physics problem image using vbagent.

```bash
# Basic scan and generate
vbsocial from-image problem.png

# With alternate solution and Rust code
vbsocial from-image problem.png --alternate --code rust -r
```

### Data Model Agents

Located in `vbsocial/agents/datamodel.py`:

- **RustDataModelAgent**: Generates struct, impl, enum, trait
- **PythonDataModelAgent**: Generates dataclass definitions
- **SwiftDataModelAgent**: Generates struct, extension, enum, protocol

All agents use `gpt-5.1-codex-mini` for code generation.

### Rules for Generated Code

1. NO `fn main()` / `if __name__ == "__main__"`
2. NO instance creation
3. NO test code
4. ONLY data model definitions (struct/class/enum)
5. Include doc comments explaining physics

### LaTeX Integration

Code is rendered using minted (Pygments) in LaTeX:
- Use `pdflatex -shell-escape` for compilation
- Dark theme (monokai) for code slides
- Supports rust, python, swift syntax highlighting

## Future Additions

### Planned Agents (to be added to vbagent)

1. **VoiceoverAgent**: Generate audio narration using OpenAI audio models or local models (Kokoro)
2. **AnimationStorylineAgent**: Plan animation sequences for manim
3. **ScriptWritingAgent**: Generate educational scripts
4. **SimulationAgent**: Generate physics simulations

### Integration Points

- vbagent: scan, idea, alternate commands
- vbpdf: PDF to PNG conversion
- manim: Animation generation (future)
- Pygments: Code syntax highlighting in LaTeX
