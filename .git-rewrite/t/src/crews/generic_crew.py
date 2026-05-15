"""GenericCrew — Factory for the Phase-1 demo crew.

In production this would load agent definitions from an agent_catalog;
for Phase 1 it creates a minimal single-agent crew that processes text.

CrewAI is an optional dependency (extra ``[crew]``).  When not installed
the factory raises ``ImportError`` at call time — tests never hit this
because ``_run_crew`` is mocked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from crewai import Crew


def create_generic_crew() -> "Crew":
    """Build a simple text-processing crew for end-to-end validation."""
    from crewai import Agent, Crew, Process, Task
    from ..config import get_settings

    settings = get_settings()
    llm = settings.get_llm()

    agent = Agent(
        role="Text Processor",
        goal="Process and transform text according to user requirements",
        backstory="You are an expert text processor with attention to detail.",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    task = Task(
        description="Process the following text: {text}",
        expected_output="Processed text with transformations applied",
        agent=agent,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
