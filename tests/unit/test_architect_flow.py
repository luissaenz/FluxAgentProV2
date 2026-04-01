"""tests/unit/test_architect_flow.py"""

from unittest.mock import MagicMock, patch

from src.flows.architect_flow import ArchitectFlow, ArchitectState


class TestArchitectFlow:

    def test_validate_input_rejects_empty(self):
        flow = ArchitectFlow(org_id="org-123")
        assert flow.validate_input({}) is False
        assert flow.validate_input({"description": ""}) is False
        assert flow.validate_input({"description": "abc"}) is False
        assert flow.validate_input({"description": "Este es válido"}) is True

    def test_parse_workflow_definition_extracts_json(self):
        flow = ArchitectFlow(org_id="org-123")

        raw = MagicMock()
        raw.raw = (
            '{"name":"Test Workflow","description":"Descripcion suficiente aqui",'
            '"flow_type":"test_flow",'
            '"steps":[{"id":"s1","name":"Paso","description":"Descripcion paso","agent_role":"a1"}],'
            '"agents":[{"role":"a1","goal":"Goal text long enough","backstory":"Backstory long enough"}]}'
        )

        result = flow._parse_workflow_definition(raw)
        assert result.name == "Test Workflow"
        assert result.flow_type == "test_flow"

    def test_parse_workflow_definition_strips_markdown(self):
        flow = ArchitectFlow(org_id="org-123")

        raw = MagicMock()
        raw.raw = (
            '```json\n'
            '{"name":"T Workflow","description":"Descripcion suficiente aqui",'
            '"flow_type":"t_flow",'
            '"steps":[{"id":"s1","name":"Paso","description":"Descripcion paso","agent_role":"a1"}],'
            '"agents":[{"role":"a1","goal":"Goal text long enough","backstory":"Backstory long enough"}]}'
            '\n```'
        )

        result = flow._parse_workflow_definition(raw)
        assert result.name == "T Workflow"

    @patch("src.flows.architect_flow.get_service_client")
    def test_ensure_unique_flow_type_adds_suffix(self, mock_svc):
        """Si el flow_type ya existe, se agrega sufijo del org_id."""
        flow = ArchitectFlow(org_id="org-abc-123")

        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data={"id": "existing"})
        )

        result = flow._ensure_unique_flow_type("existing_flow")
        assert result.startswith("existing_flow_")
        # suffix = org_id sin guiones, primeros 8 chars: "orgabc12"
        assert "orgabc12" in result.replace("-", "")

    @patch("src.flows.architect_flow.get_service_client")
    def test_ensure_unique_flow_type_returns_same_if_new(self, mock_svc):
        """Si el flow_type es nuevo, se retorna sin cambios."""
        flow = ArchitectFlow(org_id="org-123")

        mock_svc.return_value.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data=None)
        )

        result = flow._ensure_unique_flow_type("brand_new_flow")
        assert result == "brand_new_flow"
