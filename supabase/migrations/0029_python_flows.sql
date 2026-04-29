-- ============================================================
-- Migration 0029: Python Flows Support
-- ============================================================

-- 1. Extender workflow_templates con campos para código Python
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS code_source TEXT;
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS is_python BOOLEAN DEFAULT FALSE;

-- 2. Actualizar función RPC: import_bundle_atomic
-- Ahora soporta los campos is_python y code_source en el array de flows.
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
    -- 1. Registrar el bundle import (Auditoría)
    INSERT INTO bundle_imports (org_id, bundle_name, bundle_hash, status)
    VALUES (
        p_org_id, 
        p_payload->>'bundle_name', 
        p_payload->>'bundle_hash', 
        'committed'
    )
    RETURNING id INTO v_bundle_id;

    -- 2. Upsert Agents
    IF p_payload ? 'agents' THEN
        FOR v_agent IN SELECT * FROM jsonb_array_elements(p_payload->'agents') LOOP
            INSERT INTO agent_catalog (org_id, role, soul_json, allowed_tools, max_iter, bundle_id)
            VALUES (
                p_org_id, 
                v_agent->>'role', 
                v_agent,
                COALESCE((SELECT ARRAY(SELECT jsonb_array_elements_text(v_agent->'allowed_tools'))), '{}'),
                COALESCE((v_agent->>'max_iter')::INTEGER, 5),
                v_bundle_id
            )
            ON CONFLICT (org_id, role) DO UPDATE SET
                soul_json = EXCLUDED.soul_json,
                allowed_tools = EXCLUDED.allowed_tools,
                max_iter = EXCLUDED.max_iter,
                bundle_id = EXCLUDED.bundle_id,
                updated_at = now();
        END LOOP;
    END IF;

    -- 3. Upsert Flows (Workflow Templates)
    IF p_payload ? 'flows' THEN
        FOR v_flow IN SELECT * FROM jsonb_array_elements(p_payload->'flows') LOOP
            INSERT INTO workflow_templates (org_id, name, flow_type, definition, code_source, is_python, bundle_id, status)
            VALUES (
                p_org_id,
                COALESCE(v_flow->>'name', v_flow->>'flow_type'),
                v_flow->>'flow_type',
                COALESCE(v_flow->'definition', '{}'::JSONB),
                v_flow->>'code_source',
                COALESCE((v_flow->>'is_python')::BOOLEAN, FALSE),
                v_bundle_id,
                'active'
            )
            ON CONFLICT (org_id, flow_type) DO UPDATE SET
                name = EXCLUDED.name,
                definition = EXCLUDED.definition,
                code_source = EXCLUDED.code_source,
                is_python = EXCLUDED.is_python,
                bundle_id = EXCLUDED.bundle_id,
                status = EXCLUDED.status,
                updated_at = now();
        END LOOP;
    END IF;

    -- 4. Upsert Skills
    IF p_payload ? 'skills' THEN
        FOR v_skill_name, v_skill_code IN SELECT * FROM jsonb_each_text(p_payload->'skills') LOOP
            INSERT INTO skill_catalog (org_id, bundle_id, name, code_source)
            VALUES (
                p_org_id, 
                v_bundle_id, 
                v_skill_name, 
                v_skill_code
            )
            ON CONFLICT (org_id, name) DO UPDATE SET
                code_source = EXCLUDED.code_source,
                bundle_id = EXCLUDED.bundle_id;
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
