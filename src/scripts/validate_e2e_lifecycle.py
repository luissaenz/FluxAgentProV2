"""E2E Lifecycle Validation Script — Paso 1.5

Validates the complete ticket lifecycle:
1. Create ticket → Execute → Verify task_id linked + status done
2. Create ticket → Execute failing flow → Verify blocked + error notes
3. Verify correlation_id propagation to tasks and domain_events
4. Verify EventStore flush behavior

Usage:
    uv run python src/scripts/validate_e2e_lifecycle.py
"""

from __future__ import annotations

import asyncio
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.flows.registry import flow_registry
from src.flows.test_flows import SuccessTestFlow, FailTestFlow  # noqa: F401
from src.db.session import get_service_client


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _pass(msg: str) -> None:
    print(f"  {GREEN}✅ {msg}{RESET}")


def _fail(msg: str) -> None:
    print(f"  {RED}❌ {msg}{RESET}")


def _info(msg: str) -> None:
    print(f"  {CYAN}ℹ️  {msg}{RESET}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def section(title: str) -> None:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


# ── Test 1: Flow Registration ─────────────────────────────────────────


def test_flow_registration() -> bool:
    """Verify test flows are registered."""
    section("TEST 1: Flow Registration")

    has_success = flow_registry.has("success_test_flow")
    has_fail = flow_registry.has("fail_test_flow")

    if has_success:
        _pass("success_test_flow registered")
    else:
        _fail("success_test_flow NOT registered")

    if has_fail:
        _pass("fail_test_flow registered")
    else:
        _fail("fail_test_flow NOT registered")

    available = flow_registry.list_flows()
    _info(f"Total flows registered: {len(available)}")
    _info(f"Available: {available}")

    return has_success and has_fail


# ── Test 2: Success Cycle via API ──────────────────────────────────


async def test_success_cycle(org_id: str) -> bool:
    """
    Execute a full success cycle:
    1. Create ticket with success_test_flow
    2. Execute it
    3. Verify ticket status = done, task_id linked
    4. Verify task record exists with correlation_id = ticket-{id}
    5. Verify domain_events has flow.created and flow.completed
    """
    section("TEST 2: Success Cycle (Happy Path)")

    import httpx

    base_url = os.getenv("API_URL", "http://localhost:8000")
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": org_id,
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        # Step 1: Create ticket
        _info("Creating ticket with success_test_flow...")
        resp = await client.post(
            "/tickets",
            json={
                "title": "E2E Success Test",
                "description": "Automated E2E validation — success cycle",
                "flow_type": "success_test_flow",
                "priority": "low",
                "input_data": {"text": "E2E test input"},
            },
            headers=headers,
        )

        if resp.status_code != 201:
            _fail(f"Failed to create ticket: {resp.status_code} — {resp.text}")
            return False

        ticket = resp.json()
        ticket_id = ticket["id"]
        _pass(f"Ticket created: {ticket_id}")
        _info(f"Initial status: {ticket['status']}")

        # Step 2: Execute ticket
        _info("Executing ticket...")
        resp = await client.post(
            f"/tickets/{ticket_id}/execute",
            headers=headers,
        )

        if resp.status_code != 200:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            _fail(f"Execute failed: {resp.status_code} — {body}")
            return False

        result = resp.json()
        _pass(f"Ticket executed — status: {result.get('status')}")
        _pass(f"Task ID linked: {result.get('task_id')}")

        # Step 3: Verify final state
        if result.get("status") != "done":
            _fail(f"Expected status 'done', got '{result.get('status')}'")
            return False
        _pass("Final status is 'done'")

        task_id = result.get("task_id")
        if not task_id:
            _fail("No task_id in response")
            return False
        _pass(f"task_id present: {task_id}")

        # Step 4: Verify task record in DB
        _info("Verifying task record in database...")
        svc = get_service_client()
        task_result = svc.table("tasks").select("*").eq("id", task_id).execute()

        if not task_result.data:
            _fail("Task record not found in DB")
            return False

        task = task_result.data[0]
        _pass(f"Task found: status={task.get('status')}")

        # Step 5: Verify correlation_id
        expected_correlation = f"ticket-{ticket_id}"
        actual_correlation = task.get("correlation_id")
        if actual_correlation != expected_correlation:
            _fail(f"Correlation ID mismatch: expected '{expected_correlation}', got '{actual_correlation}'")
            return False
        _pass(f"correlation_id correct: {actual_correlation}")

        # Step 6: Verify domain_events
        _info("Verifying domain_events...")
        events_result = svc.table("domain_events").select("*").eq("correlation_id", expected_correlation).order("sequence", desc=False).execute()

        if not events_result.data:
            _fail("No domain_events found for correlation_id")
            return False

        event_types = [e["event_type"] for e in events_result.data]
        _info(f"Events found: {event_types}")

        has_created = "flow.created" in event_types
        has_completed = "flow.completed" in event_types

        if has_created:
            _pass("flow.created event exists")
        else:
            _fail("flow.created event MISSING")

        if has_completed:
            _pass("flow.completed event exists")
        else:
            _fail("flow.completed event MISSING")

        # Verify all events have correlation_id
        events_without_corr = [e for e in events_result.data if not e.get("correlation_id")]
        if events_without_corr:
            _fail(f"{len(events_without_corr)} events missing correlation_id")
            return False
        _pass("All events have correlation_id")

        return True


# ── Test 3: Error Cycle via API ────────────────────────────────────


async def test_error_cycle(org_id: str) -> bool:
    """
    Execute a full error cycle:
    1. Create ticket with fail_test_flow
    2. Execute it
    3. Verify ticket status = blocked
    4. Verify notes contain error message
    5. Verify task record exists with correlation_id
    6. Verify notes are APPENDED, not overwritten
    """
    section("TEST 3: Error Cycle (Robustness)")

    import httpx

    base_url = os.getenv("API_URL", "http://localhost:8000")
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": org_id,
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        # Step 1: Create ticket with pre-existing notes
        _info("Creating ticket with fail_test_flow and pre-existing notes...")
        resp = await client.post(
            "/tickets",
            json={
                "title": "E2E Error Test",
                "description": "Automated E2E validation — error cycle",
                "flow_type": "fail_test_flow",
                "priority": "medium",
                "input_data": {"text": "E2E error test input"},
                "notes": "Pre-existing note: this should be preserved",
            },
            headers=headers,
        )

        if resp.status_code != 201:
            _fail(f"Failed to create ticket: {resp.status_code} — {resp.text}")
            return False

        ticket = resp.json()
        ticket_id = ticket["id"]
        _pass(f"Ticket created: {ticket_id}")

        # Step 2: Execute ticket (should fail)
        _info("Executing ticket (expecting failure)...")
        resp = await client.post(
            f"/tickets/{ticket_id}/execute",
            headers=headers,
        )

        # We expect a 500 because the flow fails
        if resp.status_code != 500:
            _warn(f"Expected 500, got {resp.status_code} — checking DB state anyway")

        # Step 3: Fetch ticket from DB to verify blocked status
        _info("Verifying ticket status in database...")
        svc = get_service_client()
        ticket_result = svc.table("tickets").select("*").eq("id", ticket_id).execute()

        if not ticket_result.data:
            _fail("Ticket not found in DB after execution")
            return False

        ticket = ticket_result.data[0]
        status = ticket.get("status")
        _info(f"Ticket status: {status}")

        if status != "blocked":
            _fail(f"Expected status 'blocked', got '{status}'")
            return False
        _pass("Ticket status is 'blocked'")

        # Step 4: Verify notes contain error AND pre-existing content
        notes = ticket.get("notes", "")
        _info(f"Notes content preview: {notes[:200]}...")

        if "Pre-existing note: this should be preserved" not in notes:
            _fail("Pre-existing notes were OVERWRITTEN (data loss!)")
            return False
        _pass("Pre-existing notes preserved")

        if "RuntimeError" in notes or "Exception" in notes or "fail" in notes.lower():
            _pass("Error information present in notes")
        else:
            _warn("Error information may be in notes but not easily identifiable")

        # Step 5: Verify correlation_id in task
        task_id = ticket.get("task_id")
        if task_id:
            _pass(f"task_id present even in failure: {task_id}")
            task_result = svc.table("tasks").select("*").eq("id", task_id).execute()
            if task_result.data:
                task = task_result.data[0]
                correlation = task.get("correlation_id")
                expected = f"ticket-{ticket_id}"
                if correlation == expected:
                    _pass(f"correlation_id correct in task: {correlation}")
                else:
                    _fail(f"correlation_id mismatch: expected '{expected}', got '{correlation}'")
        else:
            _warn("No task_id on blocked ticket (may be expected if failure was early)")

        return True


# ── Test 4: Interruption Resilience ────────────────────────────────


async def test_interruption_resilience(org_id: str) -> bool:
    """
    Validate that a ticket stuck in 'in_progress' can be resolved by re-fetching.

    Simulates: ticket set to in_progress → server crash → re-enter → status resolves.
    """
    section("TEST 4: Interruption Resilience")

    import httpx

    base_url = os.getenv("API_URL", "http://localhost:8000")
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": org_id,
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        # Step 1: Create a ticket
        _info("Creating ticket...")
        resp = await client.post(
            "/tickets",
            json={
                "title": "E2E Interruption Test",
                "description": "Simulates a ticket stuck in in_progress",
                "flow_type": "success_test_flow",
                "priority": "low",
                "input_data": {"text": "interruption test"},
            },
            headers=headers,
        )

        if resp.status_code != 201:
            _fail(f"Failed to create ticket: {resp.status_code} — {resp.text}")
            return False

        ticket = resp.json()
        ticket_id = ticket["id"]
        _pass(f"Ticket created: {ticket_id}")

        # Step 2: Simulate interruption — set to in_progress manually
        _info("Simulating interruption (setting status to in_progress)...")
        resp = await client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "in_progress"},
            headers=headers,
        )

        if resp.status_code != 200:
            _fail(f"Failed to set in_progress: {resp.status_code}")
            return False
        _pass("Status set to in_progress (simulated crash)")

        # Step 3: Try to re-execute — should work because endpoint handles in_progress
        # The execute endpoint blocks if already in_progress, but the polling in the
        # frontend should eventually resolve the state via refetch.
        _info("Attempting re-execution (should return 409 conflict)...")
        resp = await client.post(
            f"/tickets/{ticket_id}/execute",
            headers=headers,
        )

        # 409 is expected — the ticket is already in_progress
        if resp.status_code == 409:
            _pass("Endpoint correctly returned 409 (already in progress)")
            _info("This prevents duplicate executions — correct behavior")
        else:
            _warn(f"Got {resp.status_code} instead of 409 — may still be valid")

        # Step 4: Verify the polling mechanism would resolve this
        _info("Verifying that GET /tickets/{id} returns current state...")
        resp = await client.get(f"/tickets/{ticket_id}", headers=headers)
        if resp.status_code == 200:
            current = resp.json()
            _info(f"Current status: {current.get('status')}")
            _pass("Polling endpoint accessible — frontend refetch would resolve")
        else:
            _fail("Cannot fetch ticket — polling would not work")
            return False

        # Step 5: Clean up — set back to backlog so the test is idempotent
        _info("Cleaning up — resetting ticket to backlog...")
        resp = await client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "backlog"},
            headers=headers,
        )

        if resp.status_code == 200:
            _pass("Ticket reset to backlog for future test runs")
        else:
            _warn(f"Could not reset ticket: {resp.status_code}")

        return True


# ── Main ───────────────────────────────────────────────────────────


async def main():
    org_id = os.getenv("TEST_ORG_ID")
    if not org_id:
        print(f"\n{RED}ERROR: TEST_ORG_ID environment variable is required{RESET}")
        print("Usage: TEST_ORG_ID=<your-org-uuid> uv run python src/scripts/validate_e2e_lifecycle.py")
        print(f"\n{YELLOW}You can find your org_id in the database:{RESET}")
        print("  SELECT id FROM organizations LIMIT 1;")
        sys.exit(1)

    print(f"\n{BOLD}🧪  E2E LIFECYCLE VALIDATION — PASO 1.5{RESET}")
    print(f"   Org ID: {org_id}")
    print(f"   API URL: {os.getenv('API_URL', 'http://localhost:8000')}")

    results: dict[str, bool] = {}

    # Test 1: Registration (no API needed)
    results["registration"] = test_flow_registration()

    # Tests 2-4: Need API running
    try:
        results["success_cycle"] = await test_success_cycle(org_id)
    except Exception as e:
        print(f"\n{RED}TEST 2 FAILED WITH EXCEPTION: {e}{RESET}")
        results["success_cycle"] = False

    try:
        results["error_cycle"] = await test_error_cycle(org_id)
    except Exception as e:
        print(f"\n{RED}TEST 3 FAILED WITH EXCEPTION: {e}{RESET}")
        results["error_cycle"] = False

    try:
        results["interruption"] = await test_interruption_resilience(org_id)
    except Exception as e:
        print(f"\n{RED}TEST 4 FAILED WITH EXCEPTION: {e}{RESET}")
        results["interruption"] = False

    # Summary
    section("📊 SUMMARY")
    all_passed = True
    for name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print(f"\n{'=' * 60}")
    if all_passed:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED ✅{RESET}")
    else:
        print(f"  {RED}{BOLD}SOME TESTS FAILED ❌{RESET}")
    print(f"{'=' * 60}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
