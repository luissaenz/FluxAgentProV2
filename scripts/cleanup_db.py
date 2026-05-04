"""Cleanup DB: wipe ALL org data, drop bartenders, reseed service catalog.

Usage:  python scripts/cleanup_db.py
Requires: .env with SUPABASE_URL + SUPABASE_SERVICE_KEY
Strategy: DELETE by org_id + PK ranges (PostgREST safety check bypass)
"""

import json
import logging
import sys
from pathlib import Path

from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

ORG_KEEP = "6877612f-3768-44bf-b6e3-b2d1453c3de9"
SEED_FILE = Path("data/service_catalog_seed.json")
MIN_UUID = "00000000-0000-0000-0000-000000000000"
MAX_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"

# Tables with org_id column — delete per-org
ORG_SCOPED = [
    # No FK dependencies
    "org_service_integrations",
    "secrets",
    "org_mcp_servers",
    "memory_vectors",
    "flow_presentations",
    "tickets",
    "agent_metadata",
    "domain_events",
    # workflow_templates FK → bundle_imports: delete BEFORE parent
    "workflow_templates",
    # skill_catalog → bundle_imports: child first
    "skill_catalog",
    # agent_catalog → bundle_imports: child first
    "agent_catalog",
    "bundle_imports",
    # snapshots → tasks, pending_approvals → tasks: children before parent
    "snapshots",
    "pending_approvals",
    "tasks",
    # conversations → parent of conversation_messages: delete last
    "conversations",
]

BARTENDERS_ORG = [
    "historial_precios",
    "auditorias",
    "ordenes_compra",
    "cotizaciones",
    "eventos",
    "inventario",
    "precios_bebidas",
    "bartenders_disponibles",
]

# Bartenders global config — no org_id, need PK-based filter
# Format: (tablename, pk_column, min_val)
BARTENDERS_GLOBAL = [
    ("config_consumo_pax", "tipo_menu", "!"),
    ("config_margenes", "opcion", "!"),
    ("config_climatico", "mes", 0),
    ("equipamiento_amortizacion", "item_id", "!"),
]


def load_env():
    env_file = Path(".env")
    if not env_file.exists():
        log.error(".env not found.")
        sys.exit(1)
    env = {}
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    url = env.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        log.error("SUPABASE_URL or SUPABASE_SERVICE_KEY missing from .env")
        sys.exit(1)
    return url, key


def get_client(url, key):
    return create_client(url, key)


def delete_org_data(sb, table: str, org_ids: list[str]) -> None:
    """Delete rows from *table* for given org_id list."""
    for oid in org_ids:
        try:
            sb.table(table).delete(returning="minimal").eq("org_id", oid).execute()
        except Exception as e:
            log.warning(f"  ? {table} org={oid[:12]}: {e}")


def delete_pk_range(sb, table: str, pk: str, min_val) -> None:
    """Delete all rows using PK range filter (PostgREST safety bypass)."""
    try:
        if isinstance(min_val, int):
            sb.table(table).delete(returning="minimal").gte(pk, min_val).execute()
        else:
            sb.table(table).delete(returning="minimal").gte(pk, min_val).lte(pk, "zzzzzzzzzzzz").execute()
        return True
    except Exception as e:
        log.warning(f"  ? {table} PK={pk}: {e}")
        return False


def main():
    url, key = load_env()
    sb = get_client(url, key)

    log.info("=" * 50)
    log.info("  DB CLEANUP START")
    log.info("=" * 50)

    # Phase 0: get all orgs + the seed org specifically
    log.info("\n[0/6] Fetching orgs...")
    orgs_resp = sb.table("organizations").select("id").execute()
    all_org_ids = [o["id"] for o in orgs_resp.data]
    wipe_org_ids = [o for o in all_org_ids if o != ORG_KEEP]
    log.info(f"  {len(all_org_ids)} orgs total, wiping data for all {len(all_org_ids)}, keeping {ORG_KEEP[:12]}...")

    # Phase 1: wipe FAP org-scoped tables (ALL orgs, including seed)
    log.info("\n[1/6] Wiping FAP org-scoped tables...")

    # conversation_messages first (no org_id, child of conversations)
    try:
        sb.table("conversation_messages").delete(returning="minimal").gte("id", MIN_UUID).execute()
        log.info("  ✓ conversation_messages")
    except Exception as e:
        log.warning(f"  ? conversation_messages: {e}")

    for t in ORG_SCOPED:
        delete_org_data(sb, t, all_org_ids)
        log.info(f"  ✓ {t}")

    # Phase 2: wipe bartenders org-scoped tables
    log.info("\n[2/6] Wiping bartenders tables...")
    for t in BARTENDERS_ORG:
        delete_org_data(sb, t, all_org_ids)
        log.info(f"  ✓ {t}")

    # Phase 3: wipe bartenders global config tables
    log.info("\n[3/6] Wiping bartenders config tables...")
    for table, pk, min_val in BARTENDERS_GLOBAL:
        success = delete_pk_range(sb, table, pk, min_val)
        if success:
            log.info(f"  ✓ {table}")

    # Phase 4: delete E2E orgs (keep seed)
    log.info("\n[4/6] Deleting E2E test orgs...")
    for oid in wipe_org_ids:
        try:
            sb.table("org_members").delete(returning="minimal").eq("org_id", oid).execute()
        except Exception:
            pass
        try:
            sb.table("organizations").delete(returning="minimal").eq("id", oid).execute()
            log.info(f"  ✓ Deleted org {oid[:12]}...")
        except Exception as e:
            log.warning(f"  ? Could not delete {oid[:12]}...: {e}")

    # Phase 5: reseed service catalog (global tables, no org_id)
    log.info("\n[5/6] Reseeding service catalog...")
    if SEED_FILE.exists():
        data = json.loads(SEED_FILE.read_text())
        tools = data.get("tools", [])
        log.info(f"  → {len(tools)} tools in seed file")

        # Clear existing + re-insert
        try:
            sb.table("service_catalog").delete(returning="minimal").gte("id", "!").execute()
            log.info("  ✓ service_catalog cleared")
        except Exception as e:
            log.warning(f"  ? service_catalog clear: {e}")

        try:
            sb.table("service_tools").delete(returning="minimal").gte("id", "!").execute()
            log.info("  ✓ service_tools cleared")
        except Exception as e:
            log.warning(f"  ? service_tools clear: {e}")

        # Group by provider
        providers = {}
        tool_rows = []
        for tool in tools:
            prov = tool.get("provider", {})
            pid = prov.get("id", "")
            if pid and pid not in providers:
                providers[pid] = {
                    "id": pid,
                    "name": prov.get("name", ""),
                    "category": prov.get("category", ""),
                    "auth_type": prov.get("auth_type", ""),
                    "base_url": prov.get("base_url", ""),
                    "required_secrets": prov.get("required_secrets", []),
                    "auth_scopes": prov.get("auth_scopes", []),
                }
            tool_rows.append({
                "id": tool.get("id", ""),
                "service_id": pid,
                "name": tool.get("name", ""),
                "version": tool.get("version", "1.0.0"),
                "input_schema": tool.get("input_schema", {}),
                "output_schema": tool.get("output_schema", {}),
                "execution": tool.get("execution", {}),
                "tool_profile": tool.get("tool_profile", {}),
            })

        cat_ok = 0
        for entry in providers.values():
            try:
                sb.table("service_catalog").insert(entry).execute()
                cat_ok += 1
            except Exception as e:
                log.warning(f"    ? {entry['id']}: {e}")

        tool_ok = 0
        for row in tool_rows:
            try:
                sb.table("service_tools").insert(row).execute()
                tool_ok += 1
            except Exception as e:
                log.warning(f"    ? {row['id']}: {e}")

        log.info(f"  ✓ service_catalog: {cat_ok}, service_tools: {tool_ok}")

    # Phase 6: print DDL instructions
    log.info("\n[6/6] Finalizing...")
    lines = [
        "=" * 70,
        "  DDL - Run this SQL in Supabase Dashboard > SQL Editor",
        "=" * 70,
        "",
        "-- Drop bartenders RPC functions",
        "DROP FUNCTION IF EXISTS reserve_inventory_item CASCADE;",
        "DROP FUNCTION IF EXISTS release_inventory_item CASCADE;",
        "",
        "-- Drop bartenders tables",
    ]
    bartenders_all = BARTENDERS_ORG + [t[0] for t in BARTENDERS_GLOBAL]
    for t in reversed(bartenders_all):
        lines.append(f"DROP TABLE IF EXISTS {t} CASCADE;")
    lines.extend(["", "=" * 70])
    sys.stdout.write("\n".join(lines) + "\n")

    log.info("\nDone.")


if __name__ == "__main__":
    main()
