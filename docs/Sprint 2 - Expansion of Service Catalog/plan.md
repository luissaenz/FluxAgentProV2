# Expansion of Service Catalog (TIPO C) — Integration of ~226 Tools

Scale the service catalog by parsing and transforming tool definitions from `prompt1.txt` through `prompt4.txt` into the required schema for `service_catalog_seed.json`, followed by a complete database import.

## Goals
- Integrate ~240 potential tool definitions across 4 regional and category-specific files.
- Ensure all tools match the TIPO C nested schema.
- Validate and import into Supabase under the `service_role` policy.

## Proposed Changes

### 1.0 Data Transformation Script (NEW)

#### [NEW] [expand_catalog.py](file:///d:/Develop/Personal/FluxAgentPro-v2/scripts/expand_catalog.py)
Create a specialized script to:
- Extract JSON arrays from text files (prompt1.txt to prompt4.txt).
- Transform flat JSON structure to nested TIPO C schema.
- **Mapping Logic**:
  - `tool_id` -> `id`
  - `provider` (string) -> `provider` (object) with inferred `id`, `category`, and `auth_type`.
  - `auth.type` -> `provider.auth_type`.
  - `execution.url` base part -> `provider.base_url`.
  - Generate `required_secrets` (e.g., `[provider_id]_api_key`).
- Deduplicate tools by ID (prioritizing newer prompt files or maintaining existing seed tools).
- Update [service_catalog_seed.json](file:///d:/Develop/Personal/FluxAgentPro-v2/data/service_catalog_seed.json).

### 1.1 Service Catalog Seed Update

#### [MODIFY] [service_catalog_seed.json](file:///d:/Develop/Personal/FluxAgentPro-v2/data/service_catalog_seed.json)
Update with the expanded toolset.

### 1.2 Database Import

#### [EXECUTE] [import_service_catalog.py](file:///d:/Develop/Personal/FluxAgentPro-v2/scripts/import_service_catalog.py)
Run the existing import script to:
- Upsert ~30+ providers into `service_catalog`.
- Upsert ~226+ tools into `service_tools`.
- Verify integrity (count, RLS, schemas).

## Verification Plan

### Automated Tests
- **Pre-import**: Run `expand_catalog.py` and verify JSON validity and tool count (~226).
- **Import**: Run `python -m scripts.import_service_catalog` and check for "✅ Import completed successfully!".
- **Database**: Execute SQL query to verify final tool count in Supabase.

### Manual Verification
- Check specific tools (e.g., MercadoPago, AFIP, QuickBooks) in the database via Supabase dashboard or API endpoint `/tools/active`.
