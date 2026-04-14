"""Import Service Catalog seed data into Supabase.

Reads data/service_catalog_seed.json, extracts unique providers into
service_catalog, and inserts all tools into service_tools.

Requires env vars: SUPABASE_URL, SUPABASE_SERVICE_KEY

Usage:
    python -m scripts.import_service_catalog
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from supabase import create_client, Client


def load_seed_data() -> list[dict]:
    """Load and validate the seed JSON file."""
    seed_path = Path(__file__).parent.parent / "data" / "service_catalog_seed.json"
    if not seed_path.exists():
        print(f"ERROR: Seed file not found at {seed_path}")
        sys.exit(1)

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tools = data.get("tools", [])
    if not tools:
        print("ERROR: No tools found in seed file")
        sys.exit(1)

    print(f"Loaded {len(tools)} tools from seed file")
    return tools


def fix_required_schema(schema: dict) -> dict:
    """Fix JSON Schema: ensure 'required' is an array at the top level.

    Some generators output 'required: true' inside properties instead of
    an array of required field names at the schema level. This function
    corrects that pattern.
    """
    if not isinstance(schema, dict):
        return schema

    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])

    # If required is a boolean (invalid), convert based on properties
    if isinstance(required_fields, bool):
        if required_fields:
            required_fields = list(properties.keys())
        else:
            required_fields = []
        schema["required"] = required_fields

    # Check for 'required: true' inside individual properties and move to top level
    collected_required = list(required_fields) if isinstance(required_fields, list) else []
    for prop_name, prop_def in properties.items():
        if isinstance(prop_def, dict) and prop_def.pop("required", None) is True:
            if prop_name not in collected_required:
                collected_required.append(prop_name)

    schema["required"] = collected_required
    return schema


def extract_providers(tools: list[dict]) -> dict[str, dict]:
    """Extract unique providers from tools list."""
    providers: dict[str, dict] = {}
    for tool in tools:
        provider = tool.get("provider", {})
        provider_id = provider.get("id")
        if provider_id and provider_id not in providers:
            providers[provider_id] = {
                "id": provider_id,
                "name": provider.get("name", provider_id),
                "category": provider.get("category", "other"),
                "auth_type": provider.get("auth_type", "api_key"),
                "base_url": provider.get("base_url", ""),
                "health_check_url": provider.get("health_check_url"),
                "docs_url": provider.get("docs_url"),
                "required_secrets": provider.get("required_secrets", []),
            }
    return providers


def extract_tools(tools: list[dict]) -> list[dict]:
    """Extract tool definitions from seed data, fixing schemas."""
    tool_records = []
    for tool in tools:
        input_schema = fix_required_schema(tool.get("input_schema", {}))
        output_schema = tool.get("output_schema", {})
        execution = tool.get("execution", {})
        tool_profile = tool.get("tool_profile", {})

        # Validate tool_profile has required fields
        for field in ("description", "risk_level", "requires_approval"):
            if field not in tool_profile:
                print(f"  WARNING: Tool {tool['id']} missing tool_profile.{field}")
                if field == "description":
                    tool_profile["description"] = tool.get("name", "")
                elif field == "risk_level":
                    tool_profile["risk_level"] = "low"
                elif field == "requires_approval":
                    tool_profile["requires_approval"] = False

        # 🚨 VALIDATION: HTTPS Mandatory (Sprint 5)
        exec_url = execution.get("url", "")
        if exec_url and not exec_url.startswith("https://"):
            raise ValueError(f"CRITICAL: Tool {tool['id']} uses insecure protocol in {exec_url}. HTTPS mandatory.")

        tool_records.append({
            "id": tool["id"],
            "service_id": tool["provider"]["id"],
            "name": tool.get("name", tool["id"]),
            "version": tool.get("version", "1.0.0"),
            "input_schema": input_schema,
            "output_schema": output_schema,
            "execution": execution,
            "tool_profile": tool_profile,
        })

    return tool_records


def import_to_supabase(
    db: Client,
    providers: dict[str, dict],
    tool_records: list[dict],
) -> None:
    """Insert providers and tools into Supabase."""

    # 1. Insert providers into service_catalog
    provider_list = list(providers.values())
    print(f"\nImporting {len(provider_list)} providers into service_catalog...")
    for provider in provider_list:
        db.table("service_catalog").upsert(provider, on_conflict="id").execute()
    print(f"  OK: {len(provider_list)} providers upserted")

    # 2. Insert tools into service_tools
    print(f"\nImporting {len(tool_records)} tools into service_tools...")
    for tool in tool_records:
        db.table("service_tools").upsert(tool, on_conflict="id").execute()
    print(f"  OK: {len(tool_records)} tools upserted")


def verify_integrity(db: Client, expected_tools: int) -> bool:
    """Verify data integrity after import."""
    print("\n--- Verification ---")
    success = True

    # Count providers
    result = db.table("service_catalog").select("id", count="exact").execute()
    provider_count = result.count if result.count is not None else len(result.data)
    print(f"Providers: {provider_count} (expected: at least 15)")
    if provider_count < 15:
        print("  FAIL: fewer than 15 providers")
        success = False
    else:
        print("  OK")

    # Count tools
    result = db.table("service_tools").select("id", count="exact").execute()
    tool_count = result.count if result.count is not None else len(result.data)
    print(f"Tools: {tool_count} (expected: {expected_tools})")
    if tool_count != expected_tools:
        print(f"  FAIL: expected {expected_tools}, got {tool_count}")
        success = False
    else:
        print("  OK")

    # Check orphans (tools without valid service_id)
    orphans = (
        db.rpc("", {})  # Fallback: check via select
    )
    # Use a direct query approach for orphan check
    all_tools = db.table("service_tools").select("id, service_id").execute()
    all_providers = db.table("service_catalog").select("id").execute()
    provider_ids = {p["id"] for p in all_providers.data}
    orphan_tools = [t for t in all_tools.data if t["service_id"] not in provider_ids]
    print(f"Orphan tools: {len(orphan_tools)} (expected: 0)")
    if orphan_tools:
        print(f"  FAIL: orphan tools found: {[t['id'] for t in orphan_tools]}")
        success = False
    else:
        print("  OK")

    # Check tool_profile completeness
    all_tools_full = db.table("service_tools").select("id, tool_profile").execute()
    incomplete = []
    required_profile_fields = {"description", "risk_level", "requires_approval"}
    for tool in all_tools_full.data:
        profile = tool.get("tool_profile", {})
        missing = required_profile_fields - set(profile.keys())
        if missing:
            incomplete.append({"id": tool["id"], "missing": list(missing)})

    print(f"Incomplete tool_profiles: {len(incomplete)} (expected: 0)")
    if incomplete:
        print(f"  FAIL: {incomplete}")
        success = False
    else:
        print("  OK")

    return success


def main() -> None:
    """Main entry point."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")
        sys.exit(1)

    db = create_client(supabase_url, supabase_key)

    # Load and process seed data
    tools = load_seed_data()
    providers = extract_providers(tools)
    tool_records = extract_tools(tools)

    print(f"\nExtracted {len(providers)} unique providers:")
    for pid, p in providers.items():
        print(f"  - {pid}: {p['name']} ({p['category']})")

    # Import
    import_to_supabase(db, providers, tool_records)

    # Verify
    ok = verify_integrity(db, len(tool_records))

    if ok:
        print("\nSUCCESS: Service catalog import complete.")
    else:
        print("\nFAIL: Import completed with errors — review above")
        sys.exit(1)


if __name__ == "__main__":
    main()
