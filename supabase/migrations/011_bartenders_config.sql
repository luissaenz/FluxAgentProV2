-- ============================================================
-- Migration 009: Bartenders NOA — Tablas de Configuración
-- Tablas globales sin org_id. Son de la instalación, no del tenant.
-- Ejecutar ANTES de 010_bartenders_operativo.sql
-- ============================================================

-- -----------------------------------------------------------
-- 1. Consumo estimado por tipo de menú y persona
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_consumo_pax (
    tipo_menu                   TEXT PRIMARY KEY
                                    CHECK (tipo_menu IN ('basico','estandar','premium')),
    coctel_por_persona          INTEGER      NOT NULL,
    ml_espiritoso_por_coctel    INTEGER      NOT NULL,
    hielo_kg_por_persona        NUMERIC(4,2) NOT NULL,
    agua_litros_por_persona     NUMERIC(4,2) NOT NULL,
    garnish_ars_por_persona     INTEGER      NOT NULL,
    desechables_ars_por_persona INTEGER      NOT NULL,
    mix_gin_pct                 INTEGER      NOT NULL DEFAULT 0,
    mix_whisky_pct              INTEGER      NOT NULL DEFAULT 0,
    mix_ron_pct                 INTEGER      NOT NULL DEFAULT 0,
    mix_vodka_pct               INTEGER      NOT NULL DEFAULT 0,
    mix_tequila_pct             INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT pct_suma_100 CHECK (
        mix_gin_pct + mix_whisky_pct + mix_ron_pct +
        mix_vodka_pct + mix_tequila_pct = 100
    )
);

-- -----------------------------------------------------------
-- 2. Márgenes de venta por opción
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_margenes (
    opcion       TEXT PRIMARY KEY
                     CHECK (opcion IN ('basica','recomendada','premium')),
    margen_pct   INTEGER NOT NULL CHECK (margen_pct BETWEEN 1 AND 99),
    descripcion  TEXT
);

-- -----------------------------------------------------------
-- 3. Factor climático histórico NOA por mes
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_climatico (
    mes         INTEGER PRIMARY KEY CHECK (mes BETWEEN 1 AND 12),
    factor_pct  INTEGER NOT NULL    CHECK (factor_pct >= 0),
    razon       TEXT    NOT NULL
);

-- -----------------------------------------------------------
-- 4. Equipamiento y amortización
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipamiento_amortizacion (
    item_id                 TEXT PRIMARY KEY,
    descripcion             TEXT         NOT NULL,
    costo_compra_ars        BIGINT       NOT NULL,
    vida_util_eventos       INTEGER      NOT NULL,
    amortizacion_por_evento NUMERIC(10,2) NOT NULL,
    fecha_compra            DATE,
    eventos_usados          INTEGER      NOT NULL DEFAULT 0,
    estado                  TEXT         NOT NULL DEFAULT 'activo'
                                CHECK (estado IN ('activo','baja','reparacion'))
);
