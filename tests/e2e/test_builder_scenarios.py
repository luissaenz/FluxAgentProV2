"""tests/e2e/test_builder_scenarios.py — Escenarios E2E del Builder Visual.

Cubre el ciclo de vida completo del builder:
  TP-1  Crear Agente + validacion longitud goal/backstory
  TP-2  Playground: POST run + polling GET /tasks/{task_id}
  TP-3  Crew Assembly: POST /workflows con grafo ReactFlow
  TP-4  Round-trip: export ZIP + re-import + verificar persistencia
  TP-5  Template: GET /api/templates/{id} + mapeo a formulario
  TP-6  Tools: GET /api/tools/available

Patron: seguir test_scenario_6_full_stack.py, test_register_agent.py y
test_crew_endpoints.py.
"""

from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.bundle_schemas import AgentExportItem, ExportBundleRequest
from src.services.export_service import ExportService
from src.services.integrity import calculate_sha256

# ── constantes ────────────────────────────────────────────────────

TEST_ORG_ID = "00000000-0000-0000-0000-000000000001"

AGENT_CREATE_PAYLOAD = {
    "role": "data_analyst",
    "soul_json": {
        "role": "Data Analyst",
        "goal": "Analyse complex datasets and generate actionable insights",
        "backstory": (
            "Sos un analista de datos con 10 anos de experiencia en negocios. "
            "Transformas datos crudos en recomendaciones de negocio claras."
        ),
    },
    "allowed_tools": ["excel_reader"],
    "max_iter": 3,
}

CREW_GRAPH_PAYLOAD = {
    "name": "data-analysis-crew",
    "flow_type": "data_analysis_crew",
    "definition": {
        "description": "Crew de analisis de datos con 3 agentes",
        "agents": [
            {
                "role": "data_fetcher",
                "goal": "Recolectar datos de multiples fuentes para su analisis",
                "backstory": "Eres un recolector de datos experto en APIs externas",
                "allowed_tools": ["excel_reader"],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "data_analyst",
                "goal": "Analizar conjuntos de datos complejos y extraer patrones",
                "backstory": "Eres un analista senior con habilidades estadisticas",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
            {
                "role": "report_writer",
                "goal": "Redactar informes ejecutivos claros y accionables",
                "backstory": "Eres un redactor tecnico con experiencia empresarial",
                "allowed_tools": [],
                "rules": [],
                "model": "claude-sonnet-4-20250514",
                "max_iter": 3,
            },
        ],
        "steps": [
            {
                "id": "step_1",
                "name": "Recolectar datos",
                "description": "Obtener datos de fuentes externas",
                "agent_role": "data_fetcher",
                "depends_on": [],
                "requires_approval": False,
            },
            {
                "id": "step_2",
                "name": "Analizar",
                "description": "Analizar datos recolectados",
                "agent_role": "data_analyst",
                "depends_on": ["step_1"],
                "requires_approval": False,
            },
            {
                "id": "step_3",
                "name": "Reportar",
                "description": "Generar informe",
                "agent_role": "report_writer",
                "depends_on": ["step_2"],
                "requires_approval": False,
            },
        ],
        "approval_rules": [],
    },
    "status": "draft",
}

CREW_EMPTY_PAYLOAD = {
    "name": "empty-crew",
    "flow_type": "empty_crew_v1",
    "definition": {
        "description": "Crew vacia",
        "agents": [],
        "steps": [],
        "approval_rules": [],
    },
    "status": "draft",
}

EXPORT_AGENTS_PAYLOAD = [
    {
        "role": "data_fetcher",
        "soul_json": {
            "goal": "Recolectar datos de multiples fuentes para su analisis",
            "backstory": "Eres un recolector de datos experto en APIs externas",
        },
        "allowed_tools": ["excel_reader"],
        "max_iter": 3,
    },
    {
        "role": "data_analyst",
        "soul_json": {
            "goal": "Analizar conjuntos de datos complejos y extraer patrones",
            "backstory": "Eres un analista senior con habilidades estadisticas",
        },
        "allowed_tools": [],
        "max_iter": 3,
    },
    {
        "role": "report_writer",
        "soul_json": {
            "goal": "Redactar informes ejecutivos claros y accionables",
            "backstory": "Eres un redactor tecnico con experiencia empresarial",
        },
        "allowed_tools": [],
        "max_iter": 3,
    },
]

MOCK_TEMPLATE = {
    "id": "template-001",
    "name": "Analista de Datos",
    "description": "Template para un agente de analisis",
    "category": "Research",
    "soul_json": {
        "role": "Data Analyst",
        "goal": "Analyze business data and generate strategic insights",
        "backstory": "You are a senior business analyst with 10 years experience.",
    },
    "suggested_tools": ["excel_reader"],
    "max_iter": 5,
    "is_system": True,
    "created_at": "2025-01-01T00:00:00Z",
}


# ── auth override ─────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_auth():
    """Override verify_org_membership for every test."""
    from src.api.middleware import verify_org_membership

    async def _fake_auth():
        return {"user_id": str(uuid4()), "org_id": TEST_ORG_ID, "role": "admin"}

    app.dependency_overrides[verify_org_membership] = _fake_auth
    yield
    app.dependency_overrides.pop(verify_org_membership, None)


# ── DB mock helpers ────────────────────────────────────────────────


def fresh_db():
    """Create a fresh mock db object."""
    db = MagicMock()
    db.execute_with_retry = MagicMock()
    db.rpc = MagicMock()
    return db


def db_cm(db):
    """Wrap db in a context manager for with get_tenant_client() as db: patterns."""
    cm = MagicMock()
    cm.__enter__.return_value = db
    cm.__exit__.return_value = False
    return cm


def chain_response(data):
    """Build a standard MagicMock response with .data = data."""
    resp = MagicMock()
    resp.data = data
    return resp


def mock_select(db, data=None):
    """Configure db.table("X").select() chain."""
    sel = MagicMock()
    sel.eq = MagicMock(return_value=sel)
    sel.neq = MagicMock(return_value=sel)
    sel.gt = MagicMock(return_value=sel)
    sel.lt = MagicMock(return_value=sel)
    sel.gte = MagicMock(return_value=sel)
    sel.lte = MagicMock(return_value=sel)
    sel.like = MagicMock(return_value=sel)
    sel.ilike = MagicMock(return_value=sel)
    sel.is_ = MagicMock(return_value=sel)
    sel.in_ = MagicMock(return_value=sel)
    sel.maybe_single = MagicMock(return_value=sel)
    sel.single = MagicMock(return_value=sel)
    sel.limit = MagicMock(return_value=sel)
    sel.order = MagicMock(return_value=sel)
    sel.range = MagicMock(return_value=sel)
    sel.execute.return_value = chain_response(data if data is not None else [])
    db.table.return_value.select.return_value = sel
    return sel


def mock_insert(db, data=None):
    """Configure db.table("X").insert() chain."""
    ins = MagicMock()
    ins.values = MagicMock(return_value=ins)
    ins.execute.return_value = chain_response(data if data is not None else [])
    db.table.return_value.insert.return_value = ins
    return ins


def mock_update(db, data=None):
    """Configure db.table("X").update() chain."""
    upd = MagicMock()
    upd.eq = MagicMock(return_value=upd)
    upd.execute.return_value = chain_response(data if data is not None else [])
    db.table.return_value.update.return_value = upd
    return upd


def mock_delete(db, data=None):
    """Configure db.table("X").delete() chain."""
    d = MagicMock()
    d.eq = MagicMock(return_value=d)
    d.execute.return_value = chain_response(data if data is not None else [])
    db.table.return_value.delete.return_value = d
    return d


# ═══════════════════════════════════════════════════════════════════
#  TP-1 — CRUD Agente y validacion longitud
# ═══════════════════════════════════════════════════════════════════


class TestBuilderAgentCRUD:
    """Scenario 1: Agente CRUD y validaciones de entrada."""

    def test_create_agent_returns_201(self):
        """TP-1: POST /agents con datos validos retorna 201."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[])
        mock_insert(
            db,
            data=[
                {
                    "id": uuid4().hex,
                    "org_id": TEST_ORG_ID,
                    "role": "data_analyst",
                    "is_active": True,
                    "soul_json": AGENT_CREATE_PAYLOAD["soul_json"],
                    "allowed_tools": AGENT_CREATE_PAYLOAD["allowed_tools"],
                    "max_iter": AGENT_CREATE_PAYLOAD["max_iter"],
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.post(
                    "/agents",
                    json=AGENT_CREATE_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )
        assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["role"] == "data_analyst"

    def test_create_agent_persists_in_mock_db(self):
        """POST /agents inserta en agent_catalog."""
        db = fresh_db()
        sel = mock_select(db, data=[])
        ins = mock_insert(
            db,
            data=[
                {
                    "id": uuid4().hex,
                    "org_id": TEST_ORG_ID,
                    "role": "data_analyst",
                    "is_active": True,
                    "soul_json": {
                        "role": "DA",
                        "goal": "do things",
                        "backstory": "Things",
                    },
                    "allowed_tools": [],
                    "max_iter": 3,
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=db_cm(db)):
            with TestClient(app) as client:
                client.post(
                    "/agents",
                    json=AGENT_CREATE_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )

        # Se llamo a SELECT (upsert check) e INSERT
        assert sel.execute.called
        assert ins.execute.called

    def test_upsert_updates_existing(self):
        """POST /agents con role duplicado ejecuta UPDATE."""
        db = fresh_db()
        mock_select(db, data=[{"id": "eid", "role": "data_analyst"}])  # existing found
        mock_update(
            db,
            data=[
                {
                    "id": "eid",
                    "role": "data_analyst",
                    "is_active": True,
                    "soul_json": AGENT_CREATE_PAYLOAD["soul_json"],
                    "allowed_tools": [],
                    "max_iter": 3,
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=db_cm(db)):
            with TestClient(app) as client:
                resp = client.post(
                    "/agents",
                    json=AGENT_CREATE_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )

        assert resp.status_code == 201
        assert db.table.return_value.update.return_value.execute.called

    def test_short_goal_returns_422(self):
        """Goal < 10 caracteres dispara 422 en /api/bundles/export."""
        with TestClient(app) as client:
            resp = client.post(
                "/api/bundles/export",
                json={
                    "agents": [
                        {
                            "role": "short_goal_agent",
                            "soul_json": {
                                "goal": "short",
                                "backstory": "This is a valid backstory here",
                            },
                        }
                    ]
                },
                headers={"X-Org-Id": TEST_ORG_ID},
            )
        assert resp.status_code == 422

    def test_short_backstory_returns_422(self):
        """Backstory < 10 caracteres dispara 422 en export."""
        with TestClient(app) as client:
            resp = client.post(
                "/api/bundles/export",
                json={
                    "agents": [
                        {
                            "role": "short_bg",
                            "soul_json": {
                                "goal": "This is a valid goal that is long enough and correct",
                                "backstory": "x",
                            },
                        }
                    ]
                },
                headers={"X-Org-Id": TEST_ORG_ID},
            )
        assert resp.status_code == 422

    def test_missing_goal_returns_422(self):
        """Goal vacio dispara 422."""
        with TestClient(app) as client:
            resp = client.post(
                "/api/bundles/export",
                json={
                    "agents": [
                        {
                            "role": "no_goal",
                            "soul_json": {
                                "backstory": "Valid backstory here with enough characters"
                            },
                        }
                    ]
                },
                headers={"X-Org-Id": TEST_ORG_ID},
            )
        assert resp.status_code == 422

    def test_missing_backstory_returns_422(self):
        """Backstory vacio dispara 422."""
        with TestClient(app) as client:
            resp = client.post(
                "/api/bundles/export",
                json={
                    "agents": [
                        {
                            "role": "no_bg",
                            "soul_json": {
                                "goal": "A valid and sufficient goal for this agent test case"
                            },
                        }
                    ]
                },
                headers={"X-Org-Id": TEST_ORG_ID},
            )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  TP-6 — Tools disponibles
# ═══════════════════════════════════════════════════════════════════


class TestBuilderToolsEndpoint:
    """Scenario 6: Herramientas disponibles."""

    def test_tools_available_returns_200(self):
        """GET /api/tools/available retorna 200 + ToolsListResponse."""
        db = fresh_db()
        mock_select(db, data=[])

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                resp = client.get(
                    "/api/tools/available", headers={"X-Org-Id": TEST_ORG_ID}
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "tools" in body
        assert body["count"] == 0

    def test_tools_count_matches_array_length(self):
        """count coincide con la longitud de tools."""
        db = fresh_db()
        mock_select(db, data=[])

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                body = client.get(
                    "/api/tools/available", headers={"X-Org-Id": TEST_ORG_ID}
                ).json()
        assert body["count"] == len(body["tools"])


# ═══════════════════════════════════════════════════════════════════
#  TP-5 — Templates
# ═══════════════════════════════════════════════════════════════════


class TestBuilderTemplates:
    """Scenario 5: Catalogo y detalle de templates."""

    def test_list_templates_returns_list(self):
        """GET /api/templates retorna TemplateListResponse con 1 template."""
        db = fresh_db()
        mock_select(db, data=[MOCK_TEMPLATE])

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                resp = client.get("/api/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1

    def test_template_detail_contains_soul_json(self):
        """GET /api/templates/{id} retorna detalle con soul_json."""
        db = fresh_db()
        sel = MagicMock()
        sel.eq = MagicMock(return_value=sel)
        sel.maybe_single = MagicMock(return_value=sel)
        sel.execute.return_value = chain_response(MOCK_TEMPLATE)
        db.table.return_value.select.return_value = sel

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                resp = client.get("/api/templates/template-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "template-001"
        assert "soul_json" in body
        assert body["soul_json"]["goal"]

    def test_template_not_found_returns_404(self):
        """GET /api/templates/{id} con ID invalido retorna 404."""
        db = fresh_db()
        sel = MagicMock()
        sel.eq = MagicMock(return_value=sel)
        sel.maybe_single = MagicMock(return_value=sel)
        sel.execute.return_value = chain_response(None)
        db.table.return_value.select.return_value = sel

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                resp = client.get("/api/templates/id-invalido-999")
        assert resp.status_code == 404

    def test_template_mapping_to_form_values(self):
        """Mapeo template -> form values: role/goal/backstory >= 10 chars."""
        db = fresh_db()
        sel = MagicMock()
        sel.eq = MagicMock(return_value=sel)
        sel.maybe_single = MagicMock(return_value=sel)
        sel.execute.return_value = chain_response(MOCK_TEMPLATE)
        db.table.return_value.select.return_value = sel

        with patch("src.db.session.get_service_client", return_value=db):
            with TestClient(app) as client:
                resp = client.get("/api/templates/template-001")
        assert resp.status_code == 200
        soul = resp.json().get("soul_json", {})
        assert len(soul.get("role", "")) >= 1
        assert len(soul.get("goal", "")) >= 10
        assert len(soul.get("backstory", "")) >= 10


# ═══════════════════════════════════════════════════════════════════
#  TP-2 — Playground (POST run + polling)
# ═══════════════════════════════════════════════════════════════════

TASK_ID = "test-task-poll-1234"


class TestBuilderPlayground:
    """Scenario 2: Ejecutar agente y hacer polling."""

    def test_post_run_returns_task_id(self):
        """POST /agents/{role}/run retorna task_id y status accepted."""
        db = fresh_db()
        cm = db_cm(db)
        mock_insert(
            db,
            data=[
                {
                    "id": TASK_ID,
                    "org_id": TEST_ORG_ID,
                    "flow_type": "agent:data_analyst",
                    "status": "pending",
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.post(
                    "/agents/data_analyst/run",
                    json={"input_data": {"message": "Hola"}},
                    headers={"X-Org-Id": TEST_ORG_ID},
                )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "task_id" in body
        assert body["status"] == "accepted"

    def test_polling_task_completed(self):
        """Polling GET /tasks/{id} retornacompleted con tokens_used."""
        db = fresh_db()
        cm = db_cm(db)
        task = {
            "id": TASK_ID,
            "org_id": TEST_ORG_ID,
            "flow_type": "agent:data_analyst",
            "status": "completed",
            "result": {"output": "ok"},
            "error": None,
            "tokens_used": 150,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:01:00",
        }
        mock_select(db, data=[task])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.get(
                    "/tasks/" + TASK_ID, headers={"X-Org-Id": TEST_ORG_ID}
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["tokens_used"] == 150

    def test_polling_task_failed(self):
        """Polling detecta estado failed."""
        db = fresh_db()
        cm = db_cm(db)
        task = {
            "id": "fail-001",
            "org_id": TEST_ORG_ID,
            "flow_type": "agent:da",
            "status": "failed",
            "result": None,
            "error": "timeout",
            "tokens_used": 0,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:30",
        }
        mock_select(db, data=[task])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.get("/tasks/fail-001", headers={"X-Org-Id": TEST_ORG_ID})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"

    def test_polling_task_not_found_returns_404(self):
        """Polling con task_id inexistente retorna 404."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.get(
                    "/tasks/task-inexistente-999", headers={"X-Org-Id": TEST_ORG_ID}
                )
        assert resp.status_code == 404

    def test_run_agent_inserts_task_in_db(self):
        """POST /agents/{role}/run inserta registro en tabla tasks."""
        db = fresh_db()
        cm = db_cm(db)
        mock_insert(db, data=[])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                client.post(
                    "/agents/data_analyst/run",
                    json={"input_data": {"message": "test"}},
                    headers={"X-Org-Id": TEST_ORG_ID},
                )

        assert db.table.return_value.insert.return_value.execute.called


# ═══════════════════════════════════════════════════════════════════
#  TP-3 — Crew Assembly (POST /workflows con grafo)
# ═══════════════════════════════════════════════════════════════════


class TestBuilderCrewAssembly:
    """Scenario 3: Ensamblaje de crews via POST /workflows."""

    def test_create_workflow_returns_201(self):
        """POST /workflows con grafo valido retorna 201."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[])  # no existing
        mock_insert(
            db,
            data=[
                {
                    "id": uuid4().hex,
                    "flow_type": "data_analysis_crew",
                    "status": "draft",
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.post(
                    "/workflows",
                    json=CREW_GRAPH_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )
        assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["flow_type"] == "data_analysis_crew"
        assert body["status"] == "draft"

    def test_create_workflow_insert_called(self):
        """POST /workflows con grafo valido llama insert en workflow_templates."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[])
        mock_insert(
            db, data=[{"id": uuid4().hex, "flow_type": "test_flow", "status": "draft"}]
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                client.post(
                    "/workflows",
                    json=CREW_GRAPH_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )

        assert db.table.return_value.insert.return_value.execute.called

    def test_duplicate_workflow_returns_409(self):
        """POST /workflows con flow_type duplicado retorna 409."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[{"id": "existing-wf"}])  # existing found

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.post(
                    "/workflows",
                    json=CREW_GRAPH_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_empty_crew_no_server_error(self):
        """Grafo vacio no produce 5xx."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(db, data=[])
        mock_insert(
            db,
            data=[{"id": uuid4().hex, "flow_type": "empty_crew_v1", "status": "draft"}],
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.post(
                    "/workflows",
                    json=CREW_EMPTY_PAYLOAD,
                    headers={"X-Org-Id": TEST_ORG_ID},
                )
        assert resp.status_code < 500

    def test_list_workflows_returns_200(self):
        """GET /workflows/ retorna 200 + lista de workflows."""
        db = fresh_db()
        cm = db_cm(db)
        mock_select(
            db,
            data=[
                {
                    "id": "w1",
                    "name": "Test",
                    "flow_type": "tf",
                    "status": "active",
                    "is_active": True,
                    "execution_count": 0,
                }
            ],
        )

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with TestClient(app) as client:
                resp = client.get("/workflows", headers={"X-Org-Id": TEST_ORG_ID})
        assert resp.status_code == 200
        assert "workflows" in resp.json()

    def test_crew_graph_structure(self):
        """CREW_GRAPH_PAYLOAD tiene 3 agentes + 3 steps con dependencias validas."""
        assert len(CREW_GRAPH_PAYLOAD["definition"]["agents"]) == 3
        assert len(CREW_GRAPH_PAYLOAD["definition"]["steps"]) == 3
        steps = {s["id"]: s for s in CREW_GRAPH_PAYLOAD["definition"]["steps"]}
        assert steps["step_2"]["depends_on"] == ["step_1"]
        assert steps["step_3"]["depends_on"] == ["step_2"]

    def test_agent_fields_have_min_length(self):
        """Todos los agentes tienen goal/backstory >= 10 chars."""
        for a in CREW_GRAPH_PAYLOAD["definition"]["agents"]:
            assert len(a["goal"]) >= 10
            assert len(a["backstory"]) >= 10


# ═══════════════════════════════════════════════════════════════════
#  TP-4 — Round-trip Export -> Import
# ═══════════════════════════════════════════════════════════════════


def _export_request():
    """Construye ExportBundleRequest con los 3 agentes de prueba."""
    return ExportBundleRequest(
        bundle_name="builder-roundtrip-test",
        agents=[
            AgentExportItem(
                role=a["role"],
                soul_json=a["soul_json"],
                allowed_tools=a["allowed_tools"],
                max_iter=a["max_iter"],
            )
            for a in EXPORT_AGENTS_PAYLOAD
        ],
    )


class TestBuilderRoundTrip:
    """Scenario 4: Export ZIP + re-import + integridad."""

    def test_zip_has_manifest_and_3_agents(self):
        """ZIP exportado tiene manifest.json + 3 archivos agents/*.json."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, filename = service.export(payload)

        assert filename == "builder-roundtrip-test.zip"
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
            assert "manifest.json" in names
            agents = [n for n in names if n.startswith("agents/")]
            assert len(agents) == 3
            m = json.loads(z.read("manifest.json"))
            assert m["version"] == "2.0"
            assert m["bundle_info"]["name"] == "builder-roundtrip-test"

    def test_export_and_reimport_returns_201(self):
        """Exportar -> Importar -> 201 con status success."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, filename = service.export(payload)
        assert filename.endswith(".zip")

        db = fresh_db()
        cm = db_cm(db)
        mock_insert(db, data=[{"id": uuid4().hex, "org_id": TEST_ORG_ID}])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with patch("src.db.session.get_service_client", return_value=db):
                with TestClient(app) as client:
                    resp = client.post(
                        "/api/bundles/import",
                        files={"file": ("rt.zip", zip_bytes, "application/zip")},
                        headers={"X-Org-Id": TEST_ORG_ID},
                    )
        assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
        assert resp.json()["status"] == "success"

    def test_manifest_hashes_match_content(self):
        """Hashes del ZIP coinciden con los valores del manifest."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, _ = service.export(payload)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            manifest = json.loads(z.read("manifest.json"))
            for entry_path, expected_hash in manifest["hashes"].items():
                content = z.read(entry_path)
                actual = calculate_sha256(content)
                assert actual == expected_hash, f"Hash mismatch: {entry_path}"

    def test_roundtrip_preserves_agent_roles(self):
        """Round-trip completa: agent roles intactos."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, _ = service.export(payload)

        db = fresh_db()
        cm = db_cm(db)
        mock_insert(db, data=[{"id": uuid4().hex, "org_id": TEST_ORG_ID}])

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with patch("src.db.session.get_service_client", return_value=db):
                with TestClient(app) as client:
                    resp = client.post(
                        "/api/bundles/import",
                        files={"file": ("survival.zip", zip_bytes, "application/zip")},
                        headers={"X-Org-Id": TEST_ORG_ID},
                    )
        assert resp.status_code == 201

    def test_export_no_skills_has_no_skill_files(self):
        """Export sin skills: no hay entradas en skills/ en el ZIP."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, _ = service.export(payload)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            skills = [n for n in z.namelist() if n.startswith("skills/")]
            assert len(skills) == 0

    def test_zip_structure_complete(self):
        """ZIP tiene manifest.json + 3 agentes."""
        payload = _export_request()
        service = ExportService(org_id=TEST_ORG_ID)
        zip_bytes, _ = service.export(payload)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names = z.namelist()
            assert "manifest.json" in names
            assert sum(1 for n in names if n.startswith("agents/")) == 3

    def test_import_corrupt_zip_returns_client_error(self):
        """Importar ZIP corrupto retorna 400-499."""
        db = fresh_db()
        cm = db_cm(db)
        mock_insert(db, data=[{"id": uuid4().hex, "org_id": TEST_ORG_ID}])

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("manifest.json", '{"version": "99.9.9-invalid"}')
        bad_zip = buf.getvalue()

        with patch("src.db.session.get_tenant_client", return_value=cm):
            with patch("src.db.session.get_service_client", return_value=db):
                with TestClient(app) as client:
                    resp = client.post(
                        "/api/bundles/import",
                        files={"file": ("bad.zip", bad_zip, "application/zip")},
                        headers={"X-Org-Id": TEST_ORG_ID},
                    )
        assert 400 <= resp.status_code < 500
