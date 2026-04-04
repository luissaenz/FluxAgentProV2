-- ============================================================
-- Migration 012: Bartenders NOA — Seed de Configuración
-- Datos reales extraídos de las planillas Excel originales.
-- Tablas sin org_id: se insertan una sola vez por instalación.
-- Ejecutar DESPUÉS de 011_bartenders_rls.sql
-- ============================================================

-- -----------------------------------------------------------
-- config_consumo_pax
-- Fuente: config_consumo_pax.xlsx [Datos]
-- -----------------------------------------------------------
INSERT INTO config_consumo_pax (
    tipo_menu, coctel_por_persona, ml_espiritoso_por_coctel,
    hielo_kg_por_persona, agua_litros_por_persona,
    garnish_ars_por_persona, desechables_ars_por_persona,
    mix_gin_pct, mix_whisky_pct, mix_ron_pct, mix_vodka_pct, mix_tequila_pct
) VALUES
    ('basico',   4, 45, 0.50, 0.50,  700, 400, 50, 20, 15, 10, 5),
    ('estandar', 5, 50, 0.67, 0.75, 1200, 600, 50, 20, 15, 10, 5),
    ('premium',  6, 55, 0.80, 1.00, 2000, 800, 50, 20, 15, 10, 5)
ON CONFLICT (tipo_menu) DO NOTHING;

-- -----------------------------------------------------------
-- config_margenes
-- Fuente: config_margenes.xlsx [Margenes]
-- -----------------------------------------------------------
INSERT INTO config_margenes (opcion, margen_pct, descripcion) VALUES
    ('basica',      40, 'Corporativos ajustados'),
    ('recomendada', 45, 'Estándar (recomendado)'),
    ('premium',     50, 'Bodas / galas')
ON CONFLICT (opcion) DO NOTHING;

-- -----------------------------------------------------------
-- config_climatico
-- Fuente: config_margenes.xlsx [Climatico]
-- -----------------------------------------------------------
INSERT INTO config_climatico (mes, factor_pct, razon) VALUES
    ( 1, 20, 'Enero: calor extremo NOA'),
    ( 2, 20, 'Febrero: lluvia y calor'),
    ( 3, 12, 'Marzo: fin de lluvias, variable'),
    ( 4, 12, 'Abril: transición, variable'),
    ( 5,  5, 'Mayo: invierno seco, bajo consumo'),
    ( 6,  5, 'Junio: invierno'),
    ( 7,  5, 'Julio: invierno'),
    ( 8,  5, 'Agosto: invierno'),
    ( 9,  8, 'Septiembre: primavera, transición'),
    (10,  8, 'Octubre: primavera'),
    (11, 20, 'Noviembre: pre-verano'),
    (12, 20, 'Diciembre: verano')
ON CONFLICT (mes) DO NOTHING;

-- -----------------------------------------------------------
-- equipamiento_amortizacion
-- Fuente: equipamiento_amortizacion.xlsx [Datos]
-- -----------------------------------------------------------
INSERT INTO equipamiento_amortizacion (
    item_id, descripcion, costo_compra_ars, vida_util_eventos,
    amortizacion_por_evento, fecha_compra, eventos_usados, estado
) VALUES
    ('BARRA-001',     'Barra móvil plegable',    500000, 200, 2500.00, '2025-01-15', 12, 'activo'),
    ('CRISTALERIA-001','Set 200 copas',           200000, 150, 1333.00, '2025-02-01',  8, 'activo'),
    ('HELADERA-001',  'Heladera portátil 100L',  300000, 180, 1667.00, '2025-01-10', 10, 'activo'),
    ('EQUIPOS-001',   'Cocteleras y jiggers',    150000, 200,  750.00, '2025-01-05', 15, 'activo')
ON CONFLICT (item_id) DO NOTHING;
