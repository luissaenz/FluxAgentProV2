-- Migration 0028: Roadmap Features (Phase II)
-- Adds versioning to bundles and soft deletes.

-- 1. Add version and is_active to bundle_imports
ALTER TABLE bundle_imports ADD COLUMN IF NOT EXISTS version TEXT DEFAULT '1.0.0';
ALTER TABLE bundle_imports ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 2. Add is_active to skill_catalog (agents/workflows already have it or are linked to bundles)
ALTER TABLE skill_catalog ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 3. Update import_bundle_atomic to handle the new version field
-- SUPUESTO: We redefine the RPC to include the version in the insertion.
-- Actually, we can just update the existing one or create a v2.
-- For simplicity in this roadmap step, we'll just update the table and the ImportService (already done).

-- 4. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bundle_imports_org_version ON bundle_imports(org_id, version);
CREATE INDEX IF NOT EXISTS idx_skill_catalog_active ON skill_catalog(org_id, is_active);

-- 4. Update RPC to handle version
CREATE OR REPLACE FUNCTION import_bundle_atomic(p_org_id UUID, p_payload JSONB)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_bundle_id UUID;
    v_agent JSONB;
    v_flow JSONB;
    v_skill_name TEXT;
    v_skill_code TEXT;
    v_result JSONB;
BEGIN
    -- 1. Registrar el bundle import (Auditoría) con versión (Roadmap T15.2)
    INSERT INTO bundle_imports (org_id, bundle_name, bundle_hash, status, version, is_active)
    VALUES (
        p_org_id, 
        p_payload->>'bundle_name', 
        p_payload->>'bundle_hash', 
        'committed',
        COALESCE(p_payload->>'version', '1.0.0'),
        TRUE
    )
    RETURNING id INTO v_bundle_id;

    -- 2. Upsert Agents
    IF p_payload ? 'agents' THEN
        FOR v_agent IN SELECT * FROM jsonb_array_elements(p_payload->'agents') LOOP
            INSERT INTO agent_catalog (org_id, role, soul_json, allowed_tools, max_iter, bundle_id, is_active)
            VALUES (
                p_org_id, 
                v_agent->>'role', 
                v_agent,
                COALESCE((SELECT ARRAY(SELECT jsonb_array_elements_text(v_agent->'allowed_tools'))), '{}'),
                COALESCE((v_agent->>'max_iter')::INTEGER, 5),
                v_bundle_id,
                TRUE
            )
            ON CONFLICT (org_id, role) DO UPDATE SET
                soul_json = EXCLUDED.soul_json,
                allowed_tools = EXCLUDED.allowed_tools,
                max_iter = EXCLUDED.max_iter,
                bundle_id = EXCLUDED.bundle_id,
                is_active = TRUE,
                updated_at = now();
        END LOOP;
    END IF;

    -- 3. Upsert Flows (Workflow Templates)
    IF p_payload ? 'flows' THEN
        FOR v_flow IN SELECT * FROM jsonb_array_elements(p_payload->'flows') LOOP
            INSERT INTO workflow_templates (org_id, name, flow_type, definition, bundle_id, status)
            VALUES (
                p_org_id,
                COALESCE(v_flow->>'name', v_flow->>'flow_type'),
                v_flow->>'flow_type',
                COALESCE(v_flow->'definition', '{}'::JSONB),
                v_bundle_id,
                'active'
            )
            ON CONFLICT (org_id, flow_type) DO UPDATE SET
                name = EXCLUDED.name,
                definition = EXCLUDED.definition,
                bundle_id = EXCLUDED.bundle_id,
                status = EXCLUDED.status,
                updated_at = now();
        END LOOP;
    END IF;

    -- 4. Upsert Skills
    IF p_payload ? 'skills' THEN
        FOR v_skill_name, v_skill_code IN SELECT * FROM jsonb_each_text(p_payload->'skills') LOOP
            INSERT INTO skill_catalog (org_id, bundle_id, name, code_source, is_active)
            VALUES (
                p_org_id, 
                v_bundle_id, 
                v_skill_name, 
                v_skill_code,
                TRUE
            )
            ON CONFLICT (org_id, name) DO UPDATE SET
                code_source = EXCLUDED.code_source,
                bundle_id = EXCLUDED.bundle_id,
                is_active = TRUE;
        END LOOP;
    END IF;

    v_result := jsonb_build_object(
        'status', 'success', 
        'bundle_id', v_bundle_id,
        'agents_count', jsonb_array_length(COALESCE(p_payload->'agents', '[]'::JSONB)),
        'flows_count', jsonb_array_length(COALESCE(p_payload->'flows', '[]'::JSONB)),
        'skills_count', (SELECT count(*) FROM jsonb_object_keys(COALESCE(p_payload->'skills', '{}'::JSONB)))
    );

    RETURN v_result;

EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Atomic import failed: %', SQLERRM;
END;
$$;

COMMENT ON COLUMN bundle_imports.version IS 'Semantic version of the bundle (SemVer).';
COMMENT ON COLUMN bundle_imports.is_active IS 'Soft delete flag for the entire bundle.';
