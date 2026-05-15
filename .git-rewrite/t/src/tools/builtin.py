"""Built-in tools — example registrations to validate the ToolRegistry pattern."""

from __future__ import annotations

from .registry import register_tool


@register_tool(
    name="noop",
    description="No-op tool used for testing and validation",
    tags=["builtin", "testing"],
)
class NoopTool:
    """Placeholder tool that returns its input unchanged."""

    name: str = "noop"
    description: str = "Returns input unchanged — for testing only."

    def _run(self, text: str) -> str:
        return text
