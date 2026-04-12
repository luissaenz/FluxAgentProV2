-- supabase/migrations/023_add_get_server_time.sql
-- Paso 3.5: Añadir función RPC para sincronización de reloj en pruebas de latencia.

CREATE OR REPLACE FUNCTION public.get_server_time()
RETURNS timestamptz
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT NOW();
$$;

-- Otorgar permisos para ejecución (necesario para service_role y authenticated si es el caso)
GRANT EXECUTE ON FUNCTION public.get_server_time() TO service_role;
GRANT EXECUTE ON FUNCTION public.get_server_time() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_server_time() TO anon;
