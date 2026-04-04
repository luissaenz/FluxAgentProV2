-- ============================================================
-- Migration 011: Bartenders NOA — Row Level Security
-- Ejecutar DESPUÉS de 010_bartenders_operativo.sql
-- ============================================================

-- -----------------------------------------------------------
-- RLS en tablas operativas (con org_id)
-- Política única: tenant solo ve sus propios datos
-- -----------------------------------------------------------

ALTER TABLE bartenders_disponibles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON bartenders_disponibles
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE precios_bebidas ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON precios_bebidas
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE inventario ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON inventario
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE eventos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON eventos
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE cotizaciones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON cotizaciones
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE ordenes_compra ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON ordenes_compra
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE auditorias ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON auditorias
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

ALTER TABLE historial_precios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON historial_precios
    FOR ALL USING (org_id::text = current_setting('app.org_id', TRUE));

-- -----------------------------------------------------------
-- Las tablas de config NO tienen RLS (son globales)
-- config_consumo_pax, config_margenes, config_climatico,
-- equipamiento_amortizacion → acceso de solo lectura para todos
-- -----------------------------------------------------------

-- Habilitar Supabase Realtime para el Dashboard
-- (ejecutar manualmente en Supabase Dashboard → Database → Replication)
-- ALTER PUBLICATION supabase_realtime ADD TABLE inventario;
-- ALTER PUBLICATION supabase_realtime ADD TABLE bartenders_disponibles;
-- ALTER PUBLICATION supabase_realtime ADD TABLE ordenes_compra;
-- ALTER PUBLICATION supabase_realtime ADD TABLE cotizaciones;
