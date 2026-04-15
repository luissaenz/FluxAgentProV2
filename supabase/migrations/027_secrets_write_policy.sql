-- =============================================================
-- Migration 027: Secrets Write Policy
-- Permitir INSERT/UPDATE en secrets para service_role
-- Requerido por IntegrationResolver (Paso 1)
-- =============================================================

-- IMPORTANTE: secrets ya tiene ENABLE ROW LEVEL SECURITY desde migración 002.
-- La política existente solo permitía SELECT para service_role.

CREATE POLICY "service_role_write_secrets" ON secrets
  FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_role_update_secrets" ON secrets
  FOR UPDATE USING (auth.role() = 'service_role');

-- NOTA: Se usa service_role para evitar exponer secretos a través de RLS de cliente anon.
