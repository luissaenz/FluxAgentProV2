"""tests/e2e/test_register_agent.py — Paso 2: Registrar agente via bundle import.

Crea bundle con agente presupuestador + excel_reader tool,
importa via API, verifica agente registrado en agent_catalog.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.integrity import calculate_sha256

AGENT_DEF = {
    "role": "presupuestador",
    "goal": "Generar presupuestos detallados para eventos usando datos de inventario y precios",
    "backstory": (
        "Sos un experto en cotización de eventos con más de 10 años de experiencia. "
        "Usás datos reales de precios, consumos por PAX, y márgenes para calcular "
        "presupuestos precisos. Trabajás con eventos sociales en Tucumán y el NOA. "
        "Siempre respondés en formato JSON estructurado con desglose detallado."
    ),
    "allowed_tools": ["excel_reader"],
    "rules": [],
    "model": "groq/llama-3.3-70b-versatile",
    "max_iter": 3,
}


@pytest.fixture
def api_client():
    return TestClient(app)


def _make_bundle(tmp_path: Path) -> bytes:
    """Create a valid bundle ZIP with presupuestador agent."""
    buf = io.BytesIO()
    agent_str = json.dumps(AGENT_DEF, indent=2)

    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("agents/presupuestador.json", agent_str)
        manifest = {
            "version": "2.0",
            "bundle_info": {
                "name": "presupuesto-bundle",
                "description": "Bundle con agente presupuestador + excel_reader",
            },
            "hashes": {
                "agents/presupuestador.json": calculate_sha256(agent_str.encode("utf-8")),
            },
        }
        z.writestr("manifest.json", json.dumps(manifest))

    return buf.getvalue()


class TestRegisterAgent:
    """Paso 2: Registrar agente presupuestador en el sistema."""

    def test_bundle_import_returns_201(self, api_client, mock_tenant_client, tmp_path):
        """Bundle import via API retorna HTTP 201."""
        zip_bytes = _make_bundle(tmp_path)

        mock_tenant_client.rpc.return_value.execute.return_value.data = {
            "status": "success",
            "bundle_id": "presupuesto-bundle-123",
            "agents_count": 1,
            "flows_count": 0,
            "skills_count": 0,
        }

        response = api_client.post(
            "/api/bundles/import",
            files={"file": ("presupuesto.zip", zip_bytes, "application/zip")},
            headers={"X-Org-Id": "test-org"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["agents_count"] == 1

    def test_agent_definition_valid(self):
        """Agent definition tiene estructura correcta."""
        assert AGENT_DEF["role"] == "presupuestador"
        assert "excel_reader" in AGENT_DEF["allowed_tools"]
        assert AGENT_DEF["model"].startswith("groq/")

    def test_bundle_hash_integrity(self, tmp_path):
        """Hashes en manifest coinciden con contenido."""
        zip_bytes = _make_bundle(tmp_path)
        zip_file = tmp_path / "presupuesto.zip"
        zip_file.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_file) as z:
            manifest = json.loads(z.read("manifest.json"))
            for path, expected_hash in manifest["hashes"].items():
                content = z.read(path)
                actual = calculate_sha256(content)
                assert actual == expected_hash, f"Hash mismatch for {path}"

    def test_excel_reader_tool_registered(self):
        """excel_reader tool está disponible en el registry."""
        from src.tools.registry import tool_registry

        tool_cls = tool_registry.get("excel_reader", org_id="test")
        assert tool_cls is not None

    def test_agent_can_use_excel_reader(self, mock_service_client, mock_tenant_client):
        """Agente con excel_reader tool puede cargar config."""
        org_id = str(uuid4())
        agent_config = {**AGENT_DEF, "org_id": org_id,
                        "soul_json": {
                            "role": AGENT_DEF["role"],
                            "goal": AGENT_DEF["goal"],
                            "backstory": AGENT_DEF["backstory"],
                        }}

        # Configure the existing agent_catalog chain from mock_service_client
        catalog = mock_service_client.table("agent_catalog")
        catalog.select.return_value = catalog
        catalog.eq.return_value = catalog
        catalog.maybe_single.return_value = catalog
        mock_resp = MagicMock()
        mock_resp.data = agent_config
        catalog.execute.return_value = mock_resp

        from src.crews.base_crew import BaseCrew
        crew = BaseCrew(org_id=org_id, role="presupuestador")
        config = crew._load_agent_config()

        assert config["role"] == "presupuestador"
        assert "excel_reader" in config["allowed_tools"]
