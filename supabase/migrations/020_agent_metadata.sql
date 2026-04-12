-- ============================================================
-- Migration 020: Agent Metadata (Phase 2 - Agent Panel 2.0)
--   Stores personality (SOUL) and UI metadata for agents.
-- ============================================================

-- Function to handle updated_at if not globally defined
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. Create table with consistent 'public.' prefix
CREATE TABLE IF NOT EXISTS public.agent_metadata (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    agent_role    TEXT NOT NULL,
    display_name  TEXT,
    soul_narrative TEXT,
    avatar_url    TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, agent_role)
);

-- 2. RLS with service_role bypass
ALTER TABLE public.agent_metadata ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_metadata_tenant_isolation" ON public.agent_metadata;
CREATE POLICY "agent_metadata_tenant_isolation" ON public.agent_metadata
    FOR ALL USING (
        (auth.role() = 'service_role') 
        OR 
        (org_id::text = current_setting('app.org_id', TRUE))
    );

-- 3. Optimization: Better naming for the index
CREATE INDEX IF NOT EXISTS idx_agent_metadata_org_role 
    ON public.agent_metadata(org_id, agent_role);

-- 4. Audit Trigger using the locally defined function
DROP TRIGGER IF EXISTS tr_agent_metadata_updated_at ON public.agent_metadata;
CREATE TRIGGER tr_agent_metadata_updated_at
    BEFORE UPDATE ON public.agent_metadata
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 5. Seed Data: Initialize metadata for existing agents in catalog
-- This ensures that existing agents have a starting point for their "SOUL".
INSERT INTO public.agent_metadata (org_id, agent_role, display_name, soul_narrative)
SELECT 
    org_id, 
    role as agent_role,
    CASE 
        WHEN role = 'analyst' THEN 'Analista de Sistemas'
        WHEN role = 'processor' THEN 'Procesador de Datos'
        WHEN role = 'reviewer' THEN 'Control de Calidad (Reviewer)'
        ELSE INITCAP(role)
    END as display_name,
    CASE 
        WHEN role = 'analyst' THEN 'Experto en descomponer problemas complejos en tareas accionables. Su enfoque es la precisión y la estructura.'
        WHEN role = 'processor' THEN 'Focalizado en la ejecución eficiente y el cumplimiento de protocolos técnicos sin desviaciones.'
        WHEN role = 'reviewer' THEN 'Crítico y perfeccionista. Su misión es asegurar que nada se escape antes del feedback final.'
        ELSE 'Agente especializado en flujo de trabajo operativo.'
    END as soul_narrative
FROM public.agent_catalog
ON CONFLICT (org_id, agent_role) DO NOTHING;

-- 6. Documentation
COMMENT ON TABLE public.agent_metadata IS 'Identity and personality data (SOUL) for agents per organization.';
COMMENT ON COLUMN public.agent_metadata.agent_role IS 'Logical link to agent_catalog.role';
COMMENT ON COLUMN public.agent_metadata.soul_narrative IS 'Human-readable personality description for Agent Panel 2.0';
