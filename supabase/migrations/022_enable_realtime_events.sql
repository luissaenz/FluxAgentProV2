-- ============================================================
-- Migration 022: Enable Supabase Realtime for domain_events
-- Purpose: Add domain_events to supabase_realtime publication for live streaming
-- ============================================================

-- 1. Asegurar REPLICA IDENTITY FULL (Esencial para recibir el record completo en el stream)
ALTER TABLE domain_events REPLICA IDENTITY FULL;

-- 2. Añadir domain_events a la publicación de forma segura
DO $$
BEGIN
    -- Verificar si la publicación estándar de Supabase existe
    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        -- Verificar si la tabla ya está en la publicación
        IF NOT EXISTS (
            SELECT 1 FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public'
              AND tablename = 'domain_events'
        ) THEN
            ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
        END IF;
    ELSE
        -- Si por alguna razón no existe, crearla con esta tabla
        CREATE PUBLICATION supabase_realtime FOR TABLE domain_events;
    END IF;
END $$;

-- 3. Documentación técnica en DB
COMMENT ON TABLE domain_events IS 'Tabla de Event Sourcing. Debe estar en supabase_realtime para el streaming de transcripts.';

-- 4. Helper para verificación técnica (Usado por el Validador)
CREATE OR REPLACE FUNCTION debug_realtime_config()
RETURNS TABLE (
    object_name TEXT,
    config_type TEXT,
    config_value TEXT
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- 1. Verificar Publicación
    RETURN QUERY
    SELECT 
        tablename::TEXT as object_name,
        'publication'::TEXT as config_type,
        pubname::TEXT as config_value
    FROM pg_publication_tables
    WHERE tablename = 'domain_events' AND pubname = 'supabase_realtime';

    -- 2. Verificar Replica Identity
    RETURN QUERY
    SELECT 
        relname::TEXT as object_name,
        'replica_identity'::TEXT as config_type,
        CASE relreplident 
            WHEN 'd' THEN 'default'
            WHEN 'n' THEN 'nothing'
            WHEN 'f' THEN 'full'
            WHEN 'i' THEN 'index'
        END::TEXT as config_value
    FROM pg_class
    WHERE relname = 'domain_events' AND relkind = 'r';
END;
$$;

