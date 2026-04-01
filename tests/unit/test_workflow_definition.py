"""tests/unit/test_workflow_definition.py"""

import pytest
from pydantic import ValidationError

from src.flows.workflow_definition import (
    WorkflowDefinition,
    StepDefinition,
    AgentDefinition,
    ApprovalRule,
)


class TestWorkflowDefinition:
    """WorkflowDefinition valida estructura correcta."""

    def test_valid_minimal_workflow(self):
        wf = WorkflowDefinition(
            name="Test Workflow",
            description="Un workflow de prueba válido con un paso y un agente",
            flow_type="test_workflow",
            steps=[
                StepDefinition(
                    id="step_1",
                    name="Hacer algo",
                    description="El agente hace algo útil",
                    agent_role="worker",
                )
            ],
            agents=[
                AgentDefinition(
                    role="worker",
                    goal="Goal text enough length here",
                    backstory="Backstory text enough length here",
                )
            ],
        )
        assert wf.flow_type == "test_workflow"
        assert len(wf.steps) == 1

    def test_rejects_step_with_unknown_agent_role(self):
        with pytest.raises(ValidationError, match="no existe"):
            WorkflowDefinition(
                name="Test",
                description="Test con paso referencing unknown agent",
                flow_type="test_invalid",
                steps=[
                    StepDefinition(
                        id="step_1",
                        name="Paso uno",
                        description="Descripción del paso",
                        agent_role="inexistente",
                    )
                ],
                agents=[
                    AgentDefinition(
                        role="real",
                        goal="Goal text enough length",
                        backstory="Backstory text enough length",
                    )
                ],
            )

    def test_rejects_invalid_flow_type_format(self):
        with pytest.raises(ValidationError, match="snake_case"):
            WorkflowDefinition(
                name="Test",
                description="Test con flow_type inválido",
                flow_type="Invalid-Flow-Type!",
                steps=[
                    StepDefinition(
                        id="s1",
                        name="Paso",
                        description="Descripción suficiente",
                        agent_role="a1",
                    )
                ],
                agents=[
                    AgentDefinition(
                        role="a1",
                        goal="Goal text enough length",
                        backstory="Backstory text enough length",
                    )
                ],
            )

    def test_rejects_empty_steps(self):
        with pytest.raises(ValidationError):
            WorkflowDefinition(
                name="Test",
                description="Test sin pasos",
                flow_type="empty_test",
                steps=[],
                agents=[
                    AgentDefinition(
                        role="a1",
                        goal="Goal text enough length",
                        backstory="Backstory text enough length",
                    )
                ],
            )

    def test_rejects_circular_dependencies(self):
        with pytest.raises(ValidationError, match="ciclos"):
            WorkflowDefinition(
                name="Test",
                description="Test con dependencias circulares",
                flow_type="circular",
                steps=[
                    StepDefinition(
                        id="step_a",
                        name="Step A",
                        description="Descripción A",
                        agent_role="agent",
                        depends_on=["step_b"],
                    ),
                    StepDefinition(
                        id="step_b",
                        name="Step B",
                        description="Descripción B",
                        agent_role="agent",
                        depends_on=["step_a"],
                    ),
                ],
                agents=[
                    AgentDefinition(
                        role="agent",
                        goal="Goal text long enough",
                        backstory="Backstory text long enough",
                    )
                ],
            )


class TestAgentDefinition:
    """AgentDefinition valida rangos y modelos."""

    def test_max_iter_within_limit(self):
        agent = AgentDefinition(
            role="test",
            goal="Goal text enough length",
            backstory="Backstory text enough length",
            max_iter=5,
        )
        assert agent.max_iter == 5

    def test_rejects_max_iter_too_high(self):
        with pytest.raises(ValidationError):
            AgentDefinition(
                role="test",
                goal="Goal text enough length",
                backstory="Backstory text enough length",
                max_iter=10,
            )

    def test_rejects_unknown_model(self):
        with pytest.raises(ValidationError, match="no permitido"):
            AgentDefinition(
                role="test",
                goal="Goal text enough length",
                backstory="Backstory text enough length",
                model="unknown-model",
            )
