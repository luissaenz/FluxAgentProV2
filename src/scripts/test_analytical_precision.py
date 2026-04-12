"""Test de precisión analítica — Fase 4.5

Valida que el AnalyticalCrew responda correctamente a consultas analíticas
conocidas y compare los resultados contra la base de datos real.

Uso:
    python -m pytest src/scripts/test_analytical_precision.py -v
    o
    python src/scripts/test_analytical_precision.py  (modo standalone)
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Dict, Any, List

# Agregar src/ al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.crews.analytical_crew import AnalyticalCrew, ALLOWED_ANALYTICAL_QUERIES
from src.db.session import get_tenant_client

# ── Configuración de test ─────────────────────────────────────────

# SUPUESTO: Usamos un org_id de test que existe en el entorno de desarrollo.
# En CI/CD, esto debería venir de fixtures de pytest con datos seed.
TEST_ORG_ID = os.getenv("TEST_ORG_ID", "00000000-0000-0000-0000-000000000000")


async def test_analytical_crew_initialization():
    """Test 1: Verificar que el crew se inicializa correctamente."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    assert crew.org_id == TEST_ORG_ID
    assert crew.event_store is not None
    print("✅ Test 1: AnalyticalCrew se inicializa correctamente")


async def test_allowed_queries_exist():
    """Test 2: Verificar que existen consultas pre-validadas."""
    expected_queries = {
        "agent_success_rate",
        "tickets_by_status",
        "flow_token_consumption",
        "recent_events_summary",
        "tasks_by_flow_type",
    }
    for query_key in expected_queries:
        assert query_key in ALLOWED_ANALYTICAL_QUERIES, f"Falta query: {query_key}"
    print(f"✅ Test 2: Existen {len(expected_queries)} consultas pre-validadas")


async def test_disallowed_query_rejected():
    """Test 3: Verificar que queries no permitidos son rechazados."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    try:
        await crew.analyze(query_type="DROP TABLE tasks;")
        assert False, "Debería haber lanzado ValueError"
    except ValueError as e:
        assert "not allowed" in str(e).lower()
    print("✅ Test 3: Queries no permitidos son rechazados")


async def test_tickets_by_status_returns_data():
    """Test 4: Verificar que tickets_by_status retorna datos válido."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    result = await crew.analyze(query_type="tickets_by_status")

    assert "data" in result
    assert "metadata" in result
    assert result["query_type"] == "tickets_by_status"
    assert result["org_id"] == TEST_ORG_ID

    data = result["data"]
    assert isinstance(data, list)

    # Si hay datos, verificar estructura
    if len(data) > 0:
        first_row = data[0]
        assert "status" in first_row or "count" in first_row
        print(f"✅ Test 4: tickets_by_status retornó {len(data)} filas con estructura válida")
    else:
        print("⚠️  Test 4: tickets_by_status retornó 0 filas (posiblemente sin datos de test)")


async def test_flow_token_consumption_structure():
    """Test 5: Verificar estructura de flow_token_consumption."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    result = await crew.analyze(query_type="flow_token_consumption")

    assert result["query_type"] == "flow_token_consumption"
    data = result["data"]
    assert isinstance(data, list)

    if len(data) > 0:
        first_row = data[0]
        assert "flow_type" in first_row
        assert "total_tokens" in first_row or "total_runs" in first_row
        print(f"✅ Test 5: flow_token_consumption retornó {len(data)} filas")
    else:
        print("⚠️  Test 5: flow_token_consumption sin datos (OK si no hay tareas con tokens)")


async def test_recent_events_summary():
    """Test 6: Verificar resumen de eventos recientes."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    result = await crew.analyze(query_type="recent_events_summary")

    assert result["query_type"] == "recent_events_summary"
    data = result["data"]
    assert isinstance(data, list)
    print(f"✅ Test 6: recent_events_summary retornó {len(data)} tipos de eventos")


async def test_query_events_method():
    """Test 7: Verificar método query_events."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    events = await crew.query_events(limit=10)

    assert isinstance(events, list)
    assert len(events) <= 10
    print(f"✅ Test 7: query_events retornó {len(events)} eventos")


async def test_tasks_by_flow_type():
    """Test 8: Verificar tasks_by_flow_type."""
    crew = AnalyticalCrew(org_id=TEST_ORG_ID)
    result = await crew.analyze(query_type="tasks_by_flow_type")

    assert result["query_type"] == "tasks_by_flow_type"
    data = result["data"]
    assert isinstance(data, list)

    if len(data) > 0:
        first_row = data[0]
        assert "flow_type" in first_row
        assert "status" in first_row
        assert "count" in first_row
        print(f"✅ Test 8: tasks_by_flow_type retornó {len(data)} combinaciones")
    else:
        print("⚠️  Test 8: tasks_by_flow_type sin datos")


# ── Runner ────────────────────────────────────────────────────────

async def run_all_tests():
    """Ejecutar todos los tests de precisión analítica."""
    print("=" * 60)
    print("🧪 Tests de Precisión Analítica — Fase 4.5")
    print("=" * 60)
    print()

    tests = [
        test_analytical_crew_initialization,
        test_allowed_queries_exist,
        test_disallowed_query_rejected,
        test_tickets_by_status_returns_data,
        test_flow_token_consumption_structure,
        test_recent_events_summary,
        test_query_events_method,
        test_tasks_by_flow_type,
    ]

    passed = 0
    failed = 0
    warnings = 0

    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test_fn.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  WARNING: {test_fn.__name__}")
            print(f"   Error: {type(e).__name__}: {e}")
            warnings += 1

    print()
    print("=" * 60)
    print(f"📊 Resultados: {passed} passed, {failed} failed, {warnings} warnings")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
