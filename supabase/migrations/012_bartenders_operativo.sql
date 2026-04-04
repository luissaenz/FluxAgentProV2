-- ============================================================
-- Migration 010: Bartenders NOA — Tablas Operativas
-- Todas las tablas tienen org_id + RLS por tenant.
-- Ejecutar DESPUÉS de 009_bartenders_config.sql
-- ============================================================

-- -----------------------------------------------------------
-- 1. Maestro de bartenders de la empresa
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS bartenders_disponibles (
    bartender_id          TEXT        PRIMARY KEY,
    org_id                UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    nombre                TEXT        NOT NULL,
    telefono              TEXT,
    especialidad          TEXT        NOT NULL
                              CHECK (especialidad IN ('premium','clasica')),
    es_head_bartender     BOOLEAN     NOT NULL DEFAULT FALSE,
    tarifa_hora_ars       INTEGER     NOT NULL CHECK (tarifa_hora_ars > 0),
    eventos_realizados    INTEGER     NOT NULL DEFAULT 0,
    calificacion          NUMERIC(3,1)         DEFAULT 5.0
                              CHECK (calificacion BETWEEN 1.0 AND 5.0),
    disponible            BOOLEAN     NOT NULL DEFAULT TRUE,
    fecha_proxima_reserva DATE,
    created_at            TIMESTAMPTZ          DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bartenders_org_disponible
    ON bartenders_disponibles (org_id, disponible)
    WHERE disponible = TRUE;

-- -----------------------------------------------------------
-- 2. Precios de bebidas (actualizados por Agente 11)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS precios_bebidas (
    producto_id            TEXT        PRIMARY KEY,
    org_id                 UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    nombre                 TEXT        NOT NULL,
    categoria              TEXT        NOT NULL
                               CHECK (categoria IN ('gin','whisky','ron','vodka','tequila','otro')),
    presentacion_ml        INTEGER     NOT NULL CHECK (presentacion_ml > 0),
    precio_ars             INTEGER     NOT NULL CHECK (precio_ars > 0),
    precio_por_coctel      INTEGER     NOT NULL CHECK (precio_por_coctel > 0),
    proveedor              TEXT,
    fuente                 TEXT,
    fecha_actualizacion    DATE                 DEFAULT CURRENT_DATE,
    es_oferta              BOOLEAN     NOT NULL DEFAULT FALSE,
    precio_base_referencia INTEGER
);

CREATE INDEX IF NOT EXISTS idx_precios_org_categoria
    ON precios_bebidas (org_id, categoria);

-- -----------------------------------------------------------
-- 3. Inventario de stock físico
--    stock_disponible es columna generada: actual - reservado
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventario (
    item_id              TEXT         PRIMARY KEY,
    org_id               UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    nombre               TEXT         NOT NULL,
    categoria            TEXT         NOT NULL
                             CHECK (categoria IN ('espiritoso','consumible','equipamiento','otro')),
    stock_actual         INTEGER      NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
    stock_reservado      INTEGER      NOT NULL DEFAULT 0 CHECK (stock_reservado >= 0),
    stock_disponible     INTEGER      GENERATED ALWAYS AS (stock_actual - stock_reservado) STORED,
    unidad               TEXT         NOT NULL,
    stock_minimo         INTEGER      NOT NULL DEFAULT 0,
    ultima_actualizacion DATE                  DEFAULT CURRENT_DATE,
    CONSTRAINT stock_reservado_lte_actual CHECK (stock_reservado <= stock_actual)
);

CREATE INDEX IF NOT EXISTS idx_inventario_org
    ON inventario (org_id);

-- -----------------------------------------------------------
-- 4. Registro de eventos (tabla central del negocio)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS eventos (
    evento_id            TEXT         PRIMARY KEY,
    org_id               UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    fecha_evento         DATE         NOT NULL CHECK (fecha_evento >= CURRENT_DATE - INTERVAL '2 years'),
    provincia            TEXT         NOT NULL
                             CHECK (provincia IN ('Tucuman','Salta','Jujuy','Catamarca')),
    localidad            TEXT         NOT NULL,
    tipo_evento          TEXT         NOT NULL,
    pax                  INTEGER      NOT NULL CHECK (pax BETWEEN 10 AND 500),
    duracion_horas       INTEGER      NOT NULL CHECK (duracion_horas BETWEEN 1 AND 24),
    tipo_menu            TEXT         NOT NULL
                             CHECK (tipo_menu IN ('basico','estandar','premium')),
    restricciones        TEXT,
    status               TEXT         NOT NULL DEFAULT 'nuevo'
                             CHECK (status IN (
                                 'nuevo','cotizado','confirmado',
                                 'coordinado','ejecutado','cerrado','cancelado'
                             )),
    escandallo_id        TEXT,
    cotizacion_id        TEXT,
    feedback             TEXT,
    rating               INTEGER      CHECK (rating BETWEEN 1 AND 5),
    proxima_contacto     DATE,
    created_at           TIMESTAMPTZ           DEFAULT now(),
    updated_at           TIMESTAMPTZ           DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eventos_org_status
    ON eventos (org_id, status);

CREATE INDEX IF NOT EXISTS idx_eventos_org_fecha
    ON eventos (org_id, fecha_evento);

-- Trigger: actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_eventos_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_eventos_updated_at
    BEFORE UPDATE ON eventos
    FOR EACH ROW EXECUTE FUNCTION update_eventos_updated_at();

-- -----------------------------------------------------------
-- 5. Cotizaciones generadas por Agente 4
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS cotizaciones (
    cotizacion_id         TEXT         PRIMARY KEY,
    org_id                UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    evento_id             TEXT         NOT NULL REFERENCES eventos(evento_id),
    escandallo_total      BIGINT       NOT NULL CHECK (escandallo_total > 0),
    opcion_basica         BIGINT       NOT NULL,
    opcion_recomendada    BIGINT       NOT NULL,
    opcion_premium        BIGINT       NOT NULL,
    factor_climatico      INTEGER      NOT NULL DEFAULT 0 CHECK (factor_climatico >= 0),
    fecha_generacion      DATE                  DEFAULT CURRENT_DATE,
    opcion_elegida        TEXT
                              CHECK (opcion_elegida IN ('basica','recomendada','premium')),
    status                TEXT         NOT NULL DEFAULT 'generada'
                              CHECK (status IN ('generada','enviada','aceptada','rechazada','vencida')),
    -- Validación: opciones en orden ascendente
    CONSTRAINT opciones_orden CHECK (
        opcion_basica <= opcion_recomendada AND
        opcion_recomendada <= opcion_premium
    )
);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_org
    ON cotizaciones (org_id);

CREATE INDEX IF NOT EXISTS idx_cotizaciones_evento
    ON cotizaciones (evento_id);

-- -----------------------------------------------------------
-- 6. Órdenes de compra (generadas por Agente 7)
--    items: JSON array de {producto_id, cantidad, precio_unitario}
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ordenes_compra (
    orden_id             TEXT         PRIMARY KEY,
    org_id               UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    evento_id            TEXT         REFERENCES eventos(evento_id),
    fecha_generacion     DATE                  DEFAULT CURRENT_DATE,
    motivo               TEXT         NOT NULL
                             CHECK (motivo IN ('alerta_climatica','faltante_stock','programada')),
    proveedor            TEXT,
    items                JSONB        NOT NULL DEFAULT '[]',
    total_ars            BIGINT       NOT NULL CHECK (total_ars > 0),
    status               TEXT         NOT NULL DEFAULT 'pendiente'
                             CHECK (status IN ('pendiente','aprobada','rechazada','entregada')),
    fecha_entrega        DATE,
    task_id              UUID         REFERENCES tasks(id),  -- link al HITL task de FAP
    created_at           TIMESTAMPTZ           DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ordenes_org_status
    ON ordenes_compra (org_id, status);

-- -----------------------------------------------------------
-- 7. Auditorías post-evento (generadas por Agente 9)
--    ganancia_neta es columna generada
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditorias (
    auditoria_id          TEXT         PRIMARY KEY,
    org_id                UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    evento_id             TEXT         NOT NULL REFERENCES eventos(evento_id),
    precio_cobrado        BIGINT       NOT NULL CHECK (precio_cobrado > 0),
    costo_real            BIGINT       NOT NULL CHECK (costo_real > 0),
    ganancia_neta         BIGINT       GENERATED ALWAYS AS (precio_cobrado - costo_real) STORED,
    margen_pct            NUMERIC(5,2),
    mermas                BIGINT                DEFAULT 0,
    desvio_climatico      TEXT,
    compras_emergencia    BIGINT                DEFAULT 0,
    leccion               TEXT,
    fecha_cierre          DATE                  DEFAULT CURRENT_DATE,
    UNIQUE (evento_id)  -- un evento tiene máximo una auditoría
);

CREATE INDEX IF NOT EXISTS idx_auditorias_org
    ON auditorias (org_id);

-- -----------------------------------------------------------
-- 8. Historial de precios (escrito por Agente 11)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS historial_precios (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    fecha                DATE                  DEFAULT CURRENT_DATE,
    producto_id          TEXT         NOT NULL,
    precio_ars           INTEGER      NOT NULL CHECK (precio_ars > 0),
    fuente               TEXT,
    variacion_pct        NUMERIC(5,2),
    created_at           TIMESTAMPTZ           DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_historial_org_producto
    ON historial_precios (org_id, producto_id, fecha DESC);
