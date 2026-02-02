"""Shared CLI utilities."""

import click


class LazyGroup(click.Group):
    """A Click group that lazily loads subcommands for faster startup.
    
    Usage:
        @click.group(
            cls=LazyGroup,
            lazy_subcommands={
                "cmd_name": "module.path:attribute",
            },
        )
        def my_group():
            pass
    """
    
    def __init__(self, *args, lazy_subcommands: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._lazy_subcommands = lazy_subcommands or {}
    
    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy
    
    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_command(cmd_name)
        return super().get_command(ctx, cmd_name)
    
    def _load_command(self, cmd_name: str) -> click.Command:
        import importlib
        
        spec = self._lazy_subcommands[cmd_name]
        if ":" in spec:
            module_path, attr = spec.rsplit(":", 1)
        else:
            # Default to cmd_name as attribute
            module_path = spec
            attr = cmd_name
        
        module = importlib.import_module(module_path)
        return getattr(module, attr)
