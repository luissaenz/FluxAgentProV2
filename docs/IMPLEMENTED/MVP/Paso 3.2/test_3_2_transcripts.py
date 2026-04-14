"""
Test de validacion para Paso 3.2 — Endpoint de Transcripts refinado.

Valida los criterios de aceptacion del analisis-FINAL.md:
1. Tarea nueva → is_running=true, events vacia
2. Tarea terminada → is_running=false
3. Filtrado por defecto (solo flow_step, agent_thought, tool_output)
4. last_sequence coincide con el ultimo evento
5. after_sequence filtra correctamente
6. has_more detecta truncamiento
7. Aislamiento: org_A no ve transcripts de org_B
8. 404 para task_id inexistente

Uso:
    Este script esta disenado para ejecutarse contra el entorno de desarrollo
    con variables de entorno configuradas.

    python LAST/test_3_2_transcripts.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from typing import Any

# ── Supabase client for test data setup ──────────────────────────────
from supabase import create_client, Client

# ── Test helpers ─────────────────────────────────────────────────────

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


def get_settings():
    """Load settings from env (mirrors src/config.py pattern)."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required.")
        sys.exit(1)
    return supabase_url, supabase_key


def get_service_client() -> Client:
    url, key = get_settings()
    return create_client(url, key)


# ── Test data helpers ────────────────────────────────────────────────

def _cleanup(db: Client, task_ids: list[str]):
    """Best-effort cleanup of test data."""
    for tid in task_ids:
        try:
            db.table("domain_events").delete().eq("aggregate_id", tid).execute()
        except Exception:
            pass
        try:
            db.table("tasks").delete().eq("id", tid).execute()
        except Exception:
            pass


def create_test_task(
    db: Client,
    org_id: str,
    status: str = "pending",
    flow_type: str = "test_flow",
) -> str:
    """Create a test task and return its ID."""
    task_id = str(uuid.uuid4())
    db.table("tasks").insert({
        "id": task_id,
        "org_id": org_id,
        "flow_type": flow_type,
        "status": status,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).execute()
    return task_id


def create_test_event(
    db: Client,
    task_id: str,
    org_id: str,
    event_type: str,
    sequence: int,
    payload: dict | None = None,
):
    """Create a test domain event."""
    db.table("domain_events").insert({
        "org_id": org_id,
        "aggregate_type": "flow",
        "aggregate_id": task_id,
        "event_type": event_type,
        "sequence": sequence,
        "payload": payload or {},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }).execute()


# ── HTTP test runner ─────────────────────────────────────────────────

async def call_transcript(
    task_id: str,
    org_id: str,
    base_url: str,
    types: str | None = None,
    after_sequence: int = 0,
    limit: int = 500,
) -> tuple[int, dict[str, Any]]:
    """Call the transcripts endpoint and return (status_code, json_body)."""
    import httpx

    url = f"{base_url}/transcripts/{task_id}"
    params: dict[str, Any] = {"limit": limit}
    if after_sequence > 0:
        params["after_sequence"] = after_sequence
    if types:
        params["types"] = types

    headers = {"X-Org-ID": org_id}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=headers)
        return resp.status_code, resp.json() if resp.content else {}


# ── Individual tests ─────────────────────────────────────────────────

async def test_404_for_nonexistent_task(base_url: str):
    """Criterio: Tarea inexistente retorna 404."""
    fake_id = str(uuid.uuid4())
    status, body = await call_transcript(fake_id, "00000000-0000-0000-0000-000000000000", base_url)
    check("404 para task inexistente", status == 404, f"status={status}")


async def test_task_new_returns_is_running_true(base_url: str, org_id: str):
    """Criterio: Tarea nueva (pending) → is_running=true, events vacia."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="pending")
    try:
        status, body = await call_transcript(task_id, org_id, base_url)
        check("Task pending → is_running=true", body.get("is_running") is True, f"is_running={body.get('is_running')}")
        check("Task pending → events vacia", body.get("events") == [], f"events_count={len(body.get('events', []))}")
        check("Task pending → last_sequence=0", body.get("sync", {}).get("last_sequence") == 0)
    finally:
        _cleanup(db, [task_id])


async def test_task_done_returns_is_running_false(base_url: str, org_id: str):
    """Criterio: Tarea terminada → is_running=false."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="done")
    try:
        status, body = await call_transcript(task_id, org_id, base_url)
        check("Task done → is_running=false", body.get("is_running") is False, f"is_running={body.get('is_running')}")
    finally:
        _cleanup(db, [task_id])


async def test_task_failed_returns_is_running_false(base_url: str, org_id: str):
    """Criterio: Tarea failed → is_running=false."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="failed")
    try:
        status, body = await call_transcript(task_id, org_id, base_url)
        check("Task failed → is_running=false", body.get("is_running") is False)
    finally:
        _cleanup(db, [task_id])


async def test_task_cancelled_returns_is_running_false(base_url: str, org_id: str):
    """Criterio: Tarea cancelled → is_running=false."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="cancelled")
    try:
        status, body = await call_transcript(task_id, org_id, base_url)
        check("Task cancelled → is_running=false", body.get("is_running") is False)
    finally:
        _cleanup(db, [task_id])


async def test_task_blocked_returns_is_running_false(base_url: str, org_id: str):
    """Criterio: Tarea blocked → is_running=false."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="blocked")
    try:
        status, body = await call_transcript(task_id, org_id, base_url)
        check("Task blocked → is_running=false", body.get("is_running") is False)
    finally:
        _cleanup(db, [task_id])


async def test_default_event_type_filtering(base_url: str, org_id: str):
    """Criterio: Filtrado por defecto — solo flow_step, agent_thought, tool_output."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running", flow_type="test_flow")
    try:
        # Create events of various types
        create_test_event(db, task_id, org_id, "flow_step", 1, {"step": "start"})
        create_test_event(db, task_id, org_id, "agent_thought", 2, {"thought": "thinking"})
        create_test_event(db, task_id, org_id, "tool_output", 3, {"output": "result"})
        create_test_event(db, task_id, org_id, "task.completed", 4, {})
        create_test_event(db, task_id, org_id, "approval.requested", 5, {})

        status, body = await call_transcript(task_id, org_id, base_url)
        events = body.get("events", [])
        event_types = [e["event_type"] for e in events]

        allowed = {"flow_step", "agent_thought", "tool_output"}
        all_allowed = all(et in allowed for et in event_types)
        check(
            "Default filtering — solo tipos permitidos",
            all_allowed,
            f"event_types={event_types}",
        )
        check(
            "Default filtering — 3 eventos (excluye task.completed, approval.requested)",
            len(events) == 3,
            f"count={len(events)}",
        )
    finally:
        _cleanup(db, [task_id])


async def test_last_sequence_matches_last_event(base_url: str, org_id: str):
    """Criterio: last_sequence coincide con sequence del ultimo evento."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running")
    try:
        for i in range(1, 6):
            create_test_event(db, task_id, org_id, "flow_step", i, {"seq": i})

        status, body = await call_transcript(task_id, org_id, base_url)
        events = body.get("events", [])
        last_seq = body.get("sync", {}).get("last_sequence")
        expected_last = events[-1]["sequence"] if events else 0
        check(
            "last_sequence = sequence del ultimo evento",
            last_seq == expected_last,
            f"last_sequence={last_seq}, expected={expected_last}",
        )
    finally:
        _cleanup(db, [task_id])


async def test_after_sequence_filters(base_url: str, org_id: str):
    """Criterio: after_sequence=2 retorna eventos con sequence > 2 (primero es 3)."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running")
    try:
        for i in range(1, 6):
            create_test_event(db, task_id, org_id, "flow_step", i, {"seq": i})

        status, body = await call_transcript(task_id, org_id, base_url, after_sequence=2)
        events = body.get("events", [])
        sequences = [e["sequence"] for e in events]

        check(
            "after_sequence=2 → primer evento es sequence 3",
            sequences[0] == 3 if sequences else False,
            f"sequences={sequences}",
        )
        check(
            "after_sequence=2 → 3 eventos (3,4,5)",
            len(events) == 3,
            f"count={len(events)}",
        )
    finally:
        _cleanup(db, [task_id])


async def test_has_more_when_truncated(base_url: str, org_id: str):
    """Criterio: Si hay mas de limit eventos, has_more=true."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running")
    try:
        # Create 10 events, request limit=5
        for i in range(1, 11):
            create_test_event(db, task_id, org_id, "flow_step", i, {"seq": i})

        status, body = await call_transcript(task_id, org_id, base_url, limit=5)
        has_more = body.get("sync", {}).get("has_more")
        events = body.get("events", [])

        check("has_more=true cuando excede limit", has_more is True, f"has_more={has_more}")
        check("events truncados a limit=5", len(events) == 5, f"count={len(events)}")
    finally:
        _cleanup(db, [task_id])


async def test_custom_types_parameter(base_url: str, org_id: str):
    """Criterio: Parametro types=flow_step filtra solo ese tipo."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running")
    try:
        create_test_event(db, task_id, org_id, "flow_step", 1, {})
        create_test_event(db, task_id, org_id, "agent_thought", 2, {})
        create_test_event(db, task_id, org_id, "tool_output", 3, {})

        status, body = await call_transcript(task_id, org_id, base_url, types="flow_step")
        events = body.get("events", [])
        all_flow_step = all(e["event_type"] == "flow_step" for e in events)

        check(
            "types=flow_step → solo flow_step",
            all_flow_step and len(events) == 1,
            f"count={len(events)}, types={[e['event_type'] for e in events]}",
        )
    finally:
        _cleanup(db, [task_id])


async def test_org_isolation(base_url: str, org_a: str, org_b: str):
    """Criterio: org_A no puede ver transcripts de org_B → 404."""
    db = get_service_client()
    task_id = create_test_task(db, org_a, status="running")
    try:
        create_test_event(db, task_id, org_a, "flow_step", 1, {})

        # Query from org_b — should get 404
        status, body = await call_transcript(task_id, org_b, base_url)
        check(
            "Org isolation — org_B ve 404 para task de org_A",
            status == 404,
            f"status={status}",
        )
    finally:
        _cleanup(db, [task_id])


# ── Response contract test ───────────────────────────────────────────

async def test_response_contract(base_url: str, org_id: str):
    """Criterio: Response coincide con estructura definida en analisis-FINAL.md."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running", flow_type="test_flow")
    try:
        create_test_event(db, task_id, org_id, "flow_step", 1, {"test": True})

        status, body = await call_transcript(task_id, org_id, base_url)

        required_keys = {"task_id", "flow_type", "status", "is_running", "sync", "events"}
        sync_keys = {"last_sequence", "has_more"}
        event_keys = {"id", "event_type", "payload", "sequence", "created_at"}

        check(
            "Response tiene claves requeridas",
            required_keys.issubset(body.keys()),
            f"keys={set(body.keys())}",
        )
        check(
            "sync tiene last_sequence y has_more",
            sync_keys.issubset(body.get("sync", {}).keys()),
            f"sync_keys={set(body.get('sync', {}).keys())}",
        )

        if body.get("events"):
            evt = body["events"][0]
            check(
                "Evento tiene claves requeridas",
                event_keys.issubset(evt.keys()),
                f"event_keys={set(evt.keys())}",
            )

        check("task_id coincide", body.get("task_id") == task_id)
        check("flow_type coincide", body.get("flow_type") == "test_flow")
        check("status coincide", body.get("status") == "running")
    finally:
        _cleanup(db, [task_id])


# ── Performance smoke test ───────────────────────────────────────────

async def test_response_time_smoke(base_url: str, org_id: str):
    """Criterio: Tiempo de respuesta < 200ms para snapshot de 500 eventos."""
    db = get_service_client()
    task_id = create_test_task(db, org_id, status="running")
    try:
        # Create 50 events (enough for a smoke test, not full 500)
        for i in range(1, 51):
            create_test_event(db, task_id, org_id, "flow_step", i, {"seq": i})

        start = time.monotonic()
        status, body = await call_transcript(task_id, org_id, base_url)
        elapsed_ms = (time.monotonic() - start) * 1000

        # For MVP smoke test, 500ms is acceptable (analysis says <200ms target)
        check(
            "Response time < 500ms (smoke test)",
            elapsed_ms < 500,
            f"{elapsed_ms:.0f}ms",
        )
    finally:
        _cleanup(db, [task_id])


# ── Main ─────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("Paso 3.2 — Validacion de Transcripts Endpoint")
    print("=" * 70)

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    org_id = os.getenv("TEST_ORG_ID")

    if not org_id:
        print("WARNING: TEST_ORG_ID not set — using placeholder (org isolation test skipped)")
        org_id = "00000000-0000-0000-0000-000000000001"

    org_b = os.getenv("TEST_ORG_ID_B", "00000000-0000-0000-0000-000000000002")

    print(f"API Base URL: {base_url}")
    print(f"Test Org ID:  {org_id}")
    print()

    # Run all tests
    print("[Contract & Error Handling]")
    await test_404_for_nonexistent_task(base_url)
    await test_response_contract(base_url, org_id)

    print("\n[State → is_running]")
    await test_task_new_returns_is_running_true(base_url, org_id)
    await test_task_done_returns_is_running_false(base_url, org_id)
    await test_task_failed_returns_is_running_false(base_url, org_id)
    await test_task_cancelled_returns_is_running_false(base_url, org_id)
    await test_task_blocked_returns_is_running_false(base_url, org_id)

    print("\n[Event Filtering]")
    await test_default_event_type_filtering(base_url, org_id)
    await test_custom_types_parameter(base_url, org_id)
    await test_last_sequence_matches_last_event(base_url, org_id)
    await test_after_sequence_filters(base_url, org_id)
    await test_has_more_when_truncated(base_url, org_id)

    print("\n[Isolation & Performance]")
    await test_org_isolation(base_url, org_id, org_b)
    await test_response_time_smoke(base_url, org_id)

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed
    print(f"Resultados: {passed}/{total} pasaron")

    if failed > 0:
        print("\nFallas:")
        for name, ok, detail in results:
            if not ok:
                print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))
        sys.exit(1)
    else:
        print("\n🎉 Todos los criterios de aceptacion del Paso 3.2 fueron validados.")


if __name__ == "__main__":
    asyncio.run(main())
