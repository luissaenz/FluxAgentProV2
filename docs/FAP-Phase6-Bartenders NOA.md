# Fase 6 — Bartenders NOA (con mock connector)

> **Definición cerrada.** Basada en el backend de Fases 1–5 ya implementado.
> Todo el código propuesto es consistente con los patterns existentes.

---

## Visión del sistema

Bartenders NOA es una empresa de barras móviles en Tucumán que opera en las 4 provincias
del NOA (Tucumán, Salta, Jujuy, Catamarca). Este sistema automatiza el 95% de su operación:
desde capturar una consulta hasta auditar la rentabilidad post-evento.

Fase 6 implementa los 11 agentes usando **Supabase como mock del Google Sheets connector**.
Los agentes nunca llaman directamente a Supabase ni a Google Sheets — siempre usan
`DataConnector.read()` / `DataConnector.write()`. En Fase 7, se reemplaza la implementación
del conector por Google Sheets API real sin tocar ningún agente.

### Criterio de éxito

Demo completa del flujo preventa en el Dashboard:
consulta → escandallo → 3 opciones de precio → HITL aprobación → reserva → asignación de bartenders.
Más: alerta climática disparando compra de emergencia (HITL) y auditoría post-evento.

---

## 01 — El patrón DataConnector

### Por qué existe

Los agentes necesitan leer y escribir datos del negocio (precios, inventario, bartenders)
que en producción viven en Google Sheets. En Fase 6, esos datos viven en Supabase bajo
RLS de la org `bartenders-noa`. El conector es la única capa que cambia entre fases.

### Interfaz (nunca cambia)

```python
# src/connectors/base_connector.py

from abc import ABC, abstractmethod
from typing import Any

class BaseDataConnector(ABC):
    """Interfaz que todos los conectores deben implementar.
    Los agentes solo conocen esta interfaz — nunca la implementación."""

    @abstractmethod
    def read(self, table: str, filters: dict = None) -> list[dict]:
        """Leer registros de una tabla/planilla."""
        pass

    @abstractmethod
    def write(self, table: str, data: dict) -> dict:
        """Insertar un registro nuevo. Retorna el registro creado."""
        pass

    @abstractmethod
    def update(self, table: str, record_id: str, data: dict) -> dict:
        """Actualizar un registro existente por su ID primario."""
        pass

    @abstractmethod
    def get_config(self, table: str, filters: dict = None) -> list[dict]:
        """Leer tablas de configuración (solo lectura, sin RLS de evento)."""
        pass
```

### Implementación Fase 6 — SupabaseMockConnector

```python
# src/connectors/supabase_connector.py

from src.connectors.base_connector import BaseDataConnector
from src.db.session import get_tenant_client

class SupabaseMockConnector(BaseDataConnector):
    """
    Fase 6: Lee y escribe en Supabase bajo RLS de la org.
    Fase 7: Reemplazar por GoogleSheetsConnector sin cambiar agentes.
    """

    def __init__(self, org_id: str, user_id: str):
        self.org_id = org_id
        self.user_id = user_id

    def read(self, table: str, filters: dict = None) -> list[dict]:
        with get_tenant_client(self.org_id, self.user_id) as db:
            query = db.table(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            return query.execute().data

    def write(self, table: str, data: dict) -> dict:
        with get_tenant_client(self.org_id, self.user_id) as db:
            # Inyectar org_id automáticamente en tablas operativas
            if table not in ("config_consumo_pax", "config_margenes",
                             "equipamiento_amortizacion"):
                data["org_id"] = self.org_id
            return db.table(table).insert(data).execute().data[0]

    def update(self, table: str, record_id: str, data: dict) -> dict:
        with get_tenant_client(self.org_id, self.user_id) as db:
            pk = self._get_pk(table)
            return db.table(table).update(data).eq(pk, record_id).execute().data[0]

    def get_config(self, table: str, filters: dict = None) -> list[dict]:
        """Tablas de config sin org_id — usan service client."""
        from src.db.session import get_service_client
        db = get_service_client()
        query = db.table(table).select("*")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute().data

    def _get_pk(self, table: str) -> str:
        PKS = {
            "eventos": "evento_id",
            "cotizaciones": "cotizacion_id",
            "inventario": "item_id",
            "ordenes_compra": "orden_id",
            "auditorias": "auditoria_id",
            "bartenders_disponibles": "bartender_id",
            "precios_bebidas": "producto_id",
        }
        return PKS.get(table, "id")
```

### Implementación Fase 7 — GoogleSheetsConnector (referencia)

```python
# src/connectors/google_sheets_connector.py  ← Fase 7

class GoogleSheetsConnector(BaseDataConnector):
    """Fase 7: reemplaza SupabaseMockConnector. Agentes no cambian."""

    def __init__(self, credentials_json: str, spreadsheet_ids: dict):
        self.service = build('sheets', 'v4', credentials=...)
        self.sheet_ids = spreadsheet_ids  # {"eventos": "1BxiM...", ...}

    def read(self, table: str, filters: dict = None) -> list[dict]:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_ids[table],
            range="Datos"
        ).execute()
        # Convertir lista de listas a lista de dicts usando primera fila como headers
        rows = result.get("values", [])
        headers = rows[1]  # fila 2 = headers (fila 1 = título)
        return [dict(zip(headers, row)) for row in rows[2:]]

    # write() y update() usan sheets.values().update() / append()
```

---

## 02 — Stack tecnológico

| Componente | Tecnología | Estado |
|---|---|---|
| Backend Python | FastAPI + CrewAI Flows | existente (Fases 1–4) |
| Base de datos | Supabase (PostgreSQL) | existente |
| Dashboard | Next.js 14 + Realtime | existente (Fase 5) |
| DataConnector | `SupabaseMockConnector` | ⭐ NUEVO Fase 6 |
| Agentes (11) | CrewAI Agent + Crew | ⭐ NUEVO Fase 6 |
| Flows (4) | CrewAI Flow + BaseFlow | ⭐ NUEVO Fase 6 |
| SQL tablas negocio | 11 tablas + RLS | ⭐ NUEVO Fase 6 |
| Seed data | Datos reales de planillas | ⭐ NUEVO Fase 6 |
| APScheduler | Jobs background (Agente 11) | ⭐ NUEVO Fase 6 |

---

## 03 — Base de datos

### Tablas de configuración (sin org_id — globales por instalación)

```sql
-- sql/009_bartenders_config.sql

-- Config de consumo por tipo de menú
CREATE TABLE config_consumo_pax (
    tipo_menu                  TEXT PRIMARY KEY,  -- basico | estandar | premium
    coctel_por_persona         INTEGER NOT NULL,
    ml_espiritoso_por_coctel   INTEGER NOT NULL,
    hielo_kg_por_persona       NUMERIC(4,2) NOT NULL,
    agua_litros_por_persona    NUMERIC(4,2) NOT NULL,
    garnish_ars_por_persona    INTEGER NOT NULL,
    desechables_ars_por_persona INTEGER NOT NULL,
    mix_gin_pct                INTEGER NOT NULL,
    mix_whisky_pct             INTEGER NOT NULL,
    mix_ron_pct                INTEGER NOT NULL,
    mix_vodka_pct              INTEGER NOT NULL,
    mix_tequila_pct            INTEGER NOT NULL
);

-- Config de márgenes de venta
CREATE TABLE config_margenes (
    opcion       TEXT PRIMARY KEY,  -- basica | recomendada | premium
    margen_pct   INTEGER NOT NULL,
    descripcion  TEXT
);

-- Factor climático por mes (NOA)
CREATE TABLE config_climatico (
    mes          INTEGER PRIMARY KEY,  -- 1-12
    factor_pct   INTEGER NOT NULL,
    razon        TEXT NOT NULL
);

-- Amortización de equipamiento (por instalación, no por org)
CREATE TABLE equipamiento_amortizacion (
    item_id                 TEXT PRIMARY KEY,
    descripcion             TEXT NOT NULL,
    costo_compra_ars        INTEGER NOT NULL,
    vida_util_eventos       INTEGER NOT NULL,
    amortizacion_por_evento NUMERIC(10,2) NOT NULL,
    fecha_compra            DATE,
    eventos_usados          INTEGER DEFAULT 0,
    estado                  TEXT DEFAULT 'activo'
);
```

### Tablas operativas (con org_id + RLS)

```sql
-- sql/010_bartenders_operativo.sql

-- Maestro de bartenders de la empresa
CREATE TABLE bartenders_disponibles (
    bartender_id          TEXT PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations(id),
    nombre                TEXT NOT NULL,
    telefono              TEXT,
    especialidad          TEXT NOT NULL CHECK (especialidad IN ('premium', 'clasica')),
    es_head_bartender     BOOLEAN DEFAULT FALSE,
    tarifa_hora_ars       INTEGER NOT NULL,
    eventos_realizados    INTEGER DEFAULT 0,
    calificacion          NUMERIC(3,1) DEFAULT 5.0,
    disponible            BOOLEAN DEFAULT TRUE,
    fecha_proxima_reserva DATE,
    created_at            TIMESTAMPTZ DEFAULT now()
);

-- Precios de bebidas (actualizados por Agente 11)
CREATE TABLE precios_bebidas (
    producto_id           TEXT PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations(id),
    nombre                TEXT NOT NULL,
    categoria             TEXT NOT NULL,  -- gin | whisky | ron | vodka | tequila
    presentacion_ml       INTEGER NOT NULL,
    precio_ars            INTEGER NOT NULL,
    precio_por_coctel     INTEGER NOT NULL,
    proveedor             TEXT,
    fuente                TEXT,
    fecha_actualizacion   DATE DEFAULT CURRENT_DATE,
    es_oferta             BOOLEAN DEFAULT FALSE,
    precio_base_referencia INTEGER
);

-- Inventario de stock físico
CREATE TABLE inventario (
    item_id              TEXT PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations(id),
    nombre               TEXT NOT NULL,
    categoria            TEXT NOT NULL,
    stock_actual         INTEGER NOT NULL DEFAULT 0,
    stock_reservado      INTEGER NOT NULL DEFAULT 0,
    stock_disponible     INTEGER GENERATED ALWAYS AS (stock_actual - stock_reservado) STORED,
    unidad               TEXT NOT NULL,
    stock_minimo         INTEGER NOT NULL DEFAULT 0,
    ultima_actualizacion DATE DEFAULT CURRENT_DATE
);

-- Registro de eventos (tabla principal del negocio)
CREATE TABLE eventos (
    evento_id            TEXT PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations(id),
    fecha_evento         DATE NOT NULL,
    provincia            TEXT NOT NULL CHECK (provincia IN ('Tucuman','Salta','Jujuy','Catamarca')),
    localidad            TEXT NOT NULL,
    tipo_evento          TEXT NOT NULL,
    pax                  INTEGER NOT NULL CHECK (pax BETWEEN 10 AND 500),
    duracion_horas       INTEGER NOT NULL,
    tipo_menu            TEXT NOT NULL CHECK (tipo_menu IN ('basico','estandar','premium')),
    restricciones        TEXT,
    status               TEXT NOT NULL DEFAULT 'nuevo'
                             CHECK (status IN ('nuevo','cotizado','confirmado',
                                               'coordinado','ejecutado','cerrado','cancelado')),
    escandallo_id        TEXT,
    cotizacion_id        TEXT,
    feedback             TEXT,
    rating               INTEGER CHECK (rating BETWEEN 1 AND 5),
    proxima_contacto     DATE,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

-- Cotizaciones generadas por Agente 4
CREATE TABLE cotizaciones (
    cotizacion_id         TEXT PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations(id),
    evento_id             TEXT NOT NULL REFERENCES eventos(evento_id),
    escandallo_total      BIGINT NOT NULL,
    opcion_basica         BIGINT NOT NULL,
    opcion_recomendada    BIGINT NOT NULL,
    opcion_premium        BIGINT NOT NULL,
    factor_climatico      INTEGER NOT NULL DEFAULT 0,
    fecha_generacion      DATE DEFAULT CURRENT_DATE,
    opcion_elegida        TEXT CHECK (opcion_elegida IN ('basica','recomendada','premium')),
    status                TEXT DEFAULT 'generada'
                              CHECK (status IN ('generada','enviada','aceptada','rechazada','vencida'))
);

-- Órdenes de compra (Agente 7)
CREATE TABLE ordenes_compra (
    orden_id             TEXT PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations(id),
    evento_id            TEXT REFERENCES eventos(evento_id),
    fecha_generacion     DATE DEFAULT CURRENT_DATE,
    motivo               TEXT NOT NULL
                             CHECK (motivo IN ('alerta_climatica','faltante_stock','programada')),
    proveedor            TEXT,
    items                JSONB NOT NULL DEFAULT '[]',
    total_ars            BIGINT NOT NULL,
    status               TEXT DEFAULT 'pendiente'
                             CHECK (status IN ('pendiente','aprobada','rechazada','entregada')),
    fecha_entrega        DATE
);

-- Auditorías post-evento (Agente 9)
CREATE TABLE auditorias (
    auditoria_id         TEXT PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations(id),
    evento_id            TEXT NOT NULL REFERENCES eventos(evento_id),
    precio_cobrado       BIGINT NOT NULL,
    costo_real           BIGINT NOT NULL,
    ganancia_neta        BIGINT GENERATED ALWAYS AS (precio_cobrado - costo_real) STORED,
    margen_pct           NUMERIC(5,2),
    mermas               BIGINT DEFAULT 0,
    desvio_climatico     TEXT,
    compras_emergencia   BIGINT DEFAULT 0,
    leccion              TEXT,
    fecha_cierre         DATE DEFAULT CURRENT_DATE
);

-- Historial de precios (Agente 11 en background)
CREATE TABLE historial_precios (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID NOT NULL REFERENCES organizations(id),
    fecha                DATE DEFAULT CURRENT_DATE,
    producto_id          TEXT NOT NULL,
    precio_ars           INTEGER NOT NULL,
    fuente               TEXT,
    variacion_pct        NUMERIC(5,2)
);
```

### RLS para todas las tablas operativas

```sql
-- sql/011_bartenders_rls.sql

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'bartenders_disponibles', 'precios_bebidas', 'inventario',
        'eventos', 'cotizaciones', 'ordenes_compra',
        'auditorias', 'historial_precios'
    ] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I
             FOR ALL USING (org_id::text = current_setting(''app.org_id'', TRUE))',
            t
        );
    END LOOP;
END $$;
```

### Seed data (datos reales de las planillas)

```sql
-- sql/012_bartenders_seed.sql
-- Ejecutar después de crear la org bartenders-noa

-- Config consumo (sin org_id)
INSERT INTO config_consumo_pax VALUES
  ('basico',   4, 45, 0.50, 0.50,  700, 400, 50, 20, 15, 10, 5),
  ('estandar', 5, 50, 0.67, 0.75, 1200, 600, 50, 20, 15, 10, 5),
  ('premium',  6, 55, 0.80, 1.00, 2000, 800, 50, 20, 15, 10, 5)
ON CONFLICT DO NOTHING;

-- Config márgenes
INSERT INTO config_margenes VALUES
  ('basica',      40, 'Corporativos ajustados'),
  ('recomendada', 45, 'Estándar (recomendado)'),
  ('premium',     50, 'Bodas / galas')
ON CONFLICT DO NOTHING;

-- Factor climático NOA
INSERT INTO config_climatico VALUES
  (1, 20, 'Enero: calor extremo'),   (2, 20, 'Febrero: lluvia/calor'),
  (3, 12, 'Marzo: fin lluvia'),       (4, 12, 'Abril: variable'),
  (5,  5, 'Mayo: invierno seco'),     (6,  5, 'Junio: invierno'),
  (7,  5, 'Julio: invierno'),         (8,  5, 'Agosto: invierno'),
  (9,  8, 'Septiembre: primavera'),  (10,  8, 'Octubre: primavera'),
  (11, 20, 'Noviembre: pre-verano'), (12, 20, 'Diciembre: verano')
ON CONFLICT DO NOTHING;

-- Equipamiento
INSERT INTO equipamiento_amortizacion VALUES
  ('BARRA-001',    'Barra móvil plegable',   500000, 200, 2500,   '2025-01-15', 12, 'activo'),
  ('CRISTAL-001',  'Set 200 copas',           200000, 150, 1333,   '2025-02-01',  8, 'activo'),
  ('HELADERA-001', 'Heladera portátil 100L',  300000, 180, 1667,   '2025-01-10', 10, 'activo'),
  ('EQUIPOS-001',  'Cocteleras y jiggers',    150000, 200,  750,   '2025-01-05', 15, 'activo')
ON CONFLICT DO NOTHING;

-- Las tablas con org_id se insertan vía script Python post-creación de org
-- Ver: scripts/seed_bartenders_noa.py
```

---

## 04 — Estructura del proyecto

```
src/
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py          # ⭐ Interfaz abstracta
│   └── supabase_connector.py      # ⭐ Implementación Fase 6
│
├── flows/
│   ├── bartenders/
│   │   ├── __init__.py
│   │   ├── preventa_flow.py       # ⭐ Agentes 1→2→3→4 (consulta → cotización)
│   │   ├── reserva_flow.py        # ⭐ Agentes 3→7→8 (reserva + staffing)
│   │   ├── alerta_flow.py         # ⭐ Agentes 5→7 (alerta climática → compra)
│   │   └── cierre_flow.py         # ⭐ Agentes 9→10 (auditoría + feedback)
│
├── crews/
│   ├── bartenders/
│   │   ├── requerimientos_crew.py  # ⭐ Agente 1
│   │   ├── meteorologico_crew.py   # ⭐ Agente 2
│   │   ├── calculador_crew.py      # ⭐ Agente 3
│   │   ├── presupuestador_crew.py  # ⭐ Agente 4
│   │   ├── monitor_clima_crew.py   # ⭐ Agente 5
│   │   ├── inventario_crew.py      # ⭐ Agente 6
│   │   ├── compras_crew.py         # ⭐ Agente 7
│   │   ├── staffing_crew.py        # ⭐ Agente 8
│   │   ├── auditoria_crew.py       # ⭐ Agente 9
│   │   ├── feedback_crew.py        # ⭐ Agente 10
│   │   └── monitor_precios_crew.py # ⭐ Agente 11
│
├── tools/
│   ├── bartenders/
│   │   ├── escandallo_tool.py     # ⭐ Cálculo de 4 bloques
│   │   ├── clima_tool.py          # ⭐ Factor climático (mock: lee config_climatico)
│   │   ├── inventario_tool.py     # ⭐ Reservar/liberar stock
│   │   └── logistica_tool.py      # ⭐ Calcular km y costos NOA
│
├── scheduler/
│   └── bartenders_jobs.py         # ⭐ APScheduler para Agente 11
│
└── api/
    └── routes/
        └── bartenders.py          # ⭐ POST /bartenders/consulta, etc.

sql/
├── 009_bartenders_config.sql      # ⭐ Tablas config (sin org_id)
├── 010_bartenders_operativo.sql   # ⭐ Tablas negocio (con org_id)
├── 011_bartenders_rls.sql         # ⭐ RLS masivo
└── 012_bartenders_seed.sql        # ⭐ Datos reales de planillas

scripts/
└── seed_bartenders_noa.py         # ⭐ Inserta datos con org_id real
```

---

## 05 — Los 4 Flows de Bartenders NOA

### Flow 1: PreventaFlow (Agentes 1 → 2 → 3 → 4)

**Trigger:** `POST /webhooks/{org_id}/bartenders_preventa`

**Input:**
```json
{
  "fecha_evento": "2026-07-20",
  "provincia": "Tucuman",
  "localidad": "San Miguel",
  "tipo_evento": "boda",
  "pax": 150,
  "duracion_horas": 5,
  "tipo_menu": "premium",
  "restricciones": ""
}
```

**Secuencia:**
```
listen_inicio()
    │
    ├── Agente 1: validate_event_input()
    │   → Valida fecha, PAX, provincia
    │   → Crea registro en eventos (status: "nuevo")
    │   → Genera evento_id
    │
    ├── Agente 2: analyze_climate_risk()
    │   → Lee config_climatico para el mes del evento
    │   → Retorna factor_climatico_pct
    │
    ├── Agente 3: calculate_escandallo()
    │   → BLOQUE 1: productos (config_consumo_pax × precios_bebidas)
    │   → BLOQUE 2: equipamiento (equipamiento_amortizacion)
    │   → BLOQUE 3: personal (CEILING(PAX/40) × tarifas)
    │   → BLOQUE 4: logística (Tucumán fijo o km × 600 ARS)
    │   → Aplica factor climático + mermas 5% + imprevistos 3%
    │   → Guarda escandallo en estado del flow
    │
    └── Agente 4: generate_quote()
        → Calcula 3 opciones (40% / 45% / 50% margen)
        → Escribe en cotizaciones
        → Actualiza eventos.status = "cotizado"
        → Retorna cotizacion_id
```

**HITL:** Ninguno — el escandallo y las cotizaciones son automáticos.

**Output en Kanban:** Task `bartenders_preventa` → `completed` con las 3 opciones.

---

### Flow 2: ReservaFlow (Agentes 3 → 7 → 8)

**Trigger:** `POST /webhooks/{org_id}/bartenders_reserva`

**Input:**
```json
{
  "evento_id": "EVT-2026-002",
  "cotizacion_id": "COT-2026-002",
  "opcion_elegida": "recomendada"
}
```

**Secuencia:**
```
listen_inicio()
    │
    ├── Agente 6: reserve_inventory()
    │   → Lee inventario para el evento
    │   → SI stock suficiente: reserva (resta stock_actual, suma stock_reservado)
    │   → SI stock insuficiente: → request_approval("compra_emergencia_stock")
    │                              HITL: Jefe aprueba orden de compra
    │
    ├── Agente 8: assign_staffing()
    │   → CEILING(PAX/40) bartenders necesarios
    │   → Head si PAX > 100
    │   → Filtra bartenders_disponibles por disponible=TRUE y especialidad
    │   → SI no hay suficientes: → request_approval("sin_personal_suficiente")
    │                               HITL: Jefe decide qué hacer
    │   → Marca bartenders como no disponibles
    │   → Genera hoja de ruta (texto con instrucciones)
    │
    └── Actualiza eventos.status = "confirmado"
```

**HITL obligatorio:** Ninguno automático, pero puede dispararse si falta stock o personal.

---

### Flow 3: AlertaClimaFlow (Agentes 5 → 7)

**Trigger:** Scheduler — corre automáticamente 7 días antes de cada evento confirmado.

**Secuencia:**
```
listen_inicio()
    │
    ├── Agente 5: check_real_forecast()
    │   → Lee el pronóstico mock (en Fase 6: dato hardcodeado configurable)
    │   → Compara con config_climatico del mes
    │   → SI desviación > 10%: emite ALERTA_ROJA
    │   → SI stock OK: continúa sin acción
    │
    └── SI ALERTA_ROJA:
        Agente 7: create_emergency_order()
        → Calcula items adicionales (+ hielo, + agua según desvío)
        → Crea orden en ordenes_compra (status: "pendiente")
        → request_approval("compra_emergencia_clima")
           HITL OBLIGATORIO: Jefe aprueba/rechaza compra de emergencia
           Payload visible: {items, total_ars, motivo, desvio_detectado}
```

**HITL obligatorio:** Siempre — ninguna compra de emergencia es autónoma.

**Por qué es el showcase de la demo:** El Jefe ve en el Dashboard una card ámbar
"ALERTA ROJA — Ola de calor +8°C. Compra emergencia ARS 220.000" y decide aprobar o rechazar.

---

### Flow 4: CierreFlow (Agentes 9 → 10)

**Trigger:** `POST /webhooks/{org_id}/bartenders_cierre`

**Input:**
```json
{
  "evento_id": "EVT-2026-002",
  "costo_real": 4200000,
  "mermas": 150000,
  "compras_emergencia": 220000,
  "desvio_climatico": "+8C vs historico"
}
```

**Secuencia:**
```
listen_inicio()
    │
    ├── Agente 9: audit_event()
    │   → Lee cotizacion (precio_cobrado)
    │   → Calcula ganancia_neta y margen_pct real
    │   → SI margen < 10%: → request_approval("margen_critico")
    │                         HITL: Jefe revisa antes de cerrar
    │   → Escribe en auditorias
    │   → Extrae lección aprendida (texto generado por LLM)
    │
    └── Agente 10: feedback_and_retention()
        → Genera texto de email de seguimiento
        → Calcula fecha proxima_contacto (mismo mes, año siguiente)
        → Actualiza eventos con rating, feedback, proxima_contacto
        → status = "cerrado"
```

---

## 06 — Los 11 agentes — SOUL, SKILL, SECURITY

### Agente 1 — Requerimientos ("El Interrogador")

```python
# src/crews/bartenders/requerimientos_crew.py

SOUL = """
Sos el primer punto de contacto de Bartenders NOA.
Tu trabajo es capturar los datos del evento con precisión quirúrgica.
Sos meticuloso, detallista y no avanzás si los datos son ambiguos.

REGLAS RÍGIDAS:
- NUNCA asumas una provincia si no está especificada
- NUNCA aceptes PAX fuera del rango 10-500
- NUNCA aceptes fechas en el pasado
- Si falta cualquier dato obligatorio: solicitarlo antes de continuar
"""

def create_requerimientos_crew(connector: BaseDataConnector) -> Crew:
    agent = Agent(
        role="Analista de Requerimientos de Eventos",
        goal="Capturar y validar todos los datos necesarios para cotizar un evento",
        backstory=SOUL,
        tools=[ValidateEventTool(connector), CreateEventTool(connector)],
        allow_delegation=False,
        max_iter=3
    )
    task = Task(
        description="""
        Validar y registrar el evento con estos datos: {input_data}
        1. Validar fecha (no pasado), PAX (10-500), provincia (NOA)
        2. Crear registro en eventos con status "nuevo"
        3. Retornar evento_id generado
        """,
        expected_output="JSON con evento_id y confirmación de datos validados",
        agent=agent,
        output_pydantic=EventoCreado
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
```

### Agente 2 — Meteorológico Histórico ("El Analista")

```python
SOUL = """
Sos el analista climático de Bartenders NOA.
Consultás datos históricos de NOA para calcular el riesgo estacional.
Sos frío, objetivo y basás todo en datos — nunca en intuición.

REGLAS RÍGIDAS:
- El factor climático viene EXCLUSIVAMENTE de config_climatico
- NUNCA inventés un factor — si no encontrás el mes, usá 10% como default
- Tu output siempre incluye la razón del factor (transparencia)
"""

# Tool: lee config_climatico por número de mes
# Output: { factor_climatico_pct: 20, razon: "Enero NOA: calor extremo" }
```

### Agente 3 — Calculador ("El Ingeniero")

```python
SOUL = """
Sos el ingeniero financiero de Bartenders NOA.
Calculás escandallos de 4 bloques con precisión matemática.
Cada número tiene una fuente — nunca estimás sin respaldo en tablas.

REGLAS RÍGIDAS:
- NUNCA redondees a favor del cliente — siempre CEILING en bartenders
- El ratio PAX/bartenders es 40 (no 50 ni 30)
- Las mermas son SIEMPRE 5% — no negociable
- Los imprevistos son SIEMPRE 3% — no negociable
- El factor climático se aplica SOLO sobre Bloques 1 y 2
"""

# Bloque 1: connector.get_config("config_consumo_pax") + connector.read("precios_bebidas")
# Bloque 2: connector.get_config("equipamiento_amortizacion")
# Bloque 3: connector.read("bartenders_disponibles", {"disponible": True})
# Bloque 4: EscandalloTool.calcular_logistica(provincia, localidad)
```

### Agente 4 — Presupuestador ("El Vendedor")

```python
SOUL = """
Sos el comercial de Bartenders NOA.
Convertís el escandallo técnico en 3 propuestas de precio para el cliente.
Sos transparente con los números pero estratégico en cómo los presentás.

REGLAS RÍGIDAS:
- Las 3 opciones usan márgenes EXACTOS de config_margenes: 40% / 45% / 50%
- La fórmula es precio = escandallo / (1 - margen)
- NUNCA modifiques los márgenes por presión del cliente
- La opción "recomendada" es SIEMPRE la del 45%
"""
```

### Agente 5 — Monitor Climático ("El Vigía")

```python
SOUL = """
Sos el sistema de alerta temprana de Bartenders NOA.
Comparás el pronóstico real con el histórico presupuestado.
Sos conservador: preferís una falsa alarma a un evento sin stock.

REGLAS RÍGIDAS:
- El umbral de ALERTA ROJA es > 10% de desvío (no > 15% ni > 20%)
- En Fase 6: el pronóstico real viene de MockClimaData (configurable por evento)
- NUNCA cancelés ni modificés una compra ya aprobada
"""

# En Fase 6: MockClimaData devuelve temperatura configurable
# En Fase 7: llama a API de SMN (Servicio Meteorológico Nacional)
```

### Agentes 6, 7, 8, 9, 10, 11

```python
# Agente 6 — Inventario ("El Guardián")
SOUL_6 = """
Controlás el stock físico. Reservás items para eventos confirmados.
REGLA: NUNCA reservés más de lo disponible. Si falta: alerta inmediata.
"""

# Agente 7 — Compras ("El Negociador")
SOUL_7 = """
Generás órdenes de compra cuando hay alertas de clima o faltante de stock.
REGLA ABSOLUTA: NUNCA comprás sin aprobación del Jefe. Toda compra pasa por HITL.
"""

# Agente 8 — Staffing ("El Organizador")
SOUL_8 = """
Asignás el equipo correcto para cada evento según PAX, especialidad y rating.
REGLA: Head bartender obligatorio si PAX > 100. Ratio máximo 1 bartender cada 40 PAX.
"""

# Agente 9 — Auditoría ("El Contador")
SOUL_9 = """
Auditás la rentabilidad real post-evento. Extraés lecciones para el futuro.
REGLA: Si margen real < 10%, el cierre requiere revisión del Jefe (HITL).
"""

# Agente 10 — Feedback ("El Embajador")
SOUL_10 = """
Gestionás la relación post-evento. Encuesta, retención, próximo contacto.
REGLA: Siempre programar proxima_contacto = mismo mes del año siguiente.
"""

# Agente 11 — Monitor de Precios ("El Cazador")
SOUL_11 = """
Monitoreás precios de bebidas en NOA. Actualizás precios_bebidas semanalmente.
REGLA: En Fase 6, datos vienen de MockPreciosData. En Fase 7, scraping real.
REGLA: Si precio baja > 15% vs base: marcar es_oferta = TRUE.
"""
```

---

## 07 — EscandalloTool (herramienta crítica del Agente 3)

```python
# src/tools/bartenders/escandallo_tool.py

from crewai_tools import BaseTool
from math import ceil
from src.connectors.base_connector import BaseDataConnector

DISTANCIAS_KM = {
    "Salta": 300,
    "Jujuy": 350,
    "Catamarca": 280,
    "Tucuman": 0
}

class EscandalloTool(BaseTool):
    name: str = "calcular_escandallo"
    description: str = "Calcula el escandallo completo de 4 bloques para un evento"

    connector: BaseDataConnector

    def _run(self, evento_id: str, pax: int, duracion_horas: int,
             tipo_menu: str, provincia: str, factor_climatico_pct: int) -> dict:

        # Leer configs
        consumo = {r["tipo_menu"]: r for r in
                   self.connector.get_config("config_consumo_pax")}[tipo_menu]
        precios = {r["producto_id"]: r for r in
                   self.connector.read("precios_bebidas")}
        equipamiento = self.connector.get_config("equipamiento_amortizacion")
        bartenders = self.connector.read("bartenders_disponibles",
                                         {"disponible": "true"})

        # BLOQUE 1: Productos
        cocteles_totales = pax * int(consumo["coctel_por_persona"])
        ml_total = cocteles_totales * int(consumo["ml_espiritoso_por_coctel"])

        mix = {
            "gin":     int(consumo["mix_gin_pct"]) / 100,
            "whisky":  int(consumo["mix_whisky_pct"]) / 100,
            "ron":     int(consumo["mix_ron_pct"]) / 100,
            "vodka":   int(consumo["mix_vodka_pct"]) / 100,
            "tequila": int(consumo["mix_tequila_pct"]) / 100,
        }

        # Precio promedio ponderado por categoría
        precio_promedio = {}
        for cat in mix:
            prods = [p for p in precios.values() if p["categoria"] == cat]
            if prods:
                precio_promedio[cat] = sum(
                    int(p["precio_ars"]) / int(p["presentacion_ml"])
                    for p in prods) / len(prods)
            else:
                precio_promedio[cat] = 0

        bebidas_alc = sum(
            ml_total * mix[cat] * precio_promedio[cat]
            for cat in mix
        )
        bebidas_no_alc = pax * float(consumo["agua_litros_por_persona"]) * 400
        hielo = pax * float(consumo["hielo_kg_por_persona"]) * 750
        garnish = pax * int(consumo["garnish_ars_por_persona"])
        desechables = pax * int(consumo["desechables_ars_por_persona"])
        bloque1 = bebidas_alc + bebidas_no_alc + hielo + garnish + desechables

        # BLOQUE 2: Equipamiento
        bloque2 = sum(float(e["amortizacion_por_evento"]) for e in equipamiento)

        # BLOQUE 3: Personal
        n_bartenders = ceil(pax / 40)
        necesita_head = pax > 100
        necesita_asistente = duracion_horas > 6
        horas_totales = duracion_horas + 3  # setup/cierre fijo

        tarifa_regular = 35000
        tarifa_head = 50000
        tarifa_asistente = 28000

        costo_personal = n_bartenders * tarifa_regular * horas_totales
        if necesita_head:
            costo_personal += tarifa_head * horas_totales
        if necesita_asistente:
            costo_personal += tarifa_asistente * horas_totales
        bloque3 = costo_personal

        # BLOQUE 4: Logística
        if provincia == "Tucuman":
            bloque4 = 17000 * 3  # mínimo 3 horas
        else:
            km = DISTANCIAS_KM.get(provincia, 300)
            bloque4 = (km * 2 * 600) + 5000  # ida+vuelta + peajes

        subtotal = bloque1 + bloque2 + bloque3 + bloque4
        ajuste_climatico = (bloque1 + bloque2) * factor_climatico_pct / 100
        base_ajustada = subtotal + ajuste_climatico
        mermas = base_ajustada * 0.05
        imprevistos = base_ajustada * 0.03

        escandallo_final = round(base_ajustada + mermas + imprevistos)

        return {
            "evento_id": evento_id,
            "bloque1_productos": round(bloque1),
            "bloque2_equipamiento": round(bloque2),
            "bloque3_personal": round(bloque3),
            "bloque4_logistica": round(bloque4),
            "subtotal": round(subtotal),
            "ajuste_climatico": round(ajuste_climatico),
            "mermas": round(mermas),
            "imprevistos": round(imprevistos),
            "escandallo_final": escandallo_final,
            "bartenders_necesarios": n_bartenders,
            "factor_climatico_aplicado": factor_climatico_pct
        }
```

---

## 08 — APScheduler para Agente 11 y AlertaClima

```python
# src/scheduler/bartenders_jobs.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date, timedelta
from src.db.session import get_service_client
from src.flows.registry import FlowRegistry

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=8, minute=0)  # 8 AM todos los días
async def check_upcoming_events_climate():
    """Busca eventos confirmados en 7 días y dispara AlertaClimaFlow."""
    db = get_service_client()
    target_date = date.today() + timedelta(days=7)

    eventos = db.table("eventos") \
        .select("evento_id, org_id, provincia, fecha_evento") \
        .eq("status", "confirmado") \
        .eq("fecha_evento", target_date.isoformat()) \
        .execute().data

    for evento in eventos:
        flow_class = FlowRegistry.get("bartenders_alerta")
        flow = flow_class(org_id=evento["org_id"], user_id="scheduler")
        await flow.execute({"evento_id": evento["evento_id"]})

@scheduler.scheduled_job("cron", day_of_week="mon", hour=7)  # Lunes 7 AM
async def update_prices_all_orgs():
    """Agente 11: actualiza precios para todas las orgs con Bartenders NOA."""
    db = get_service_client()
    orgs = db.table("org_members") \
        .select("org_id") \
        .eq("role", "org_owner") \
        .execute().data

    for org in orgs:
        flow_class = FlowRegistry.get("bartenders_monitor_precios")
        flow = flow_class(org_id=org["org_id"], user_id="scheduler")
        await flow.execute({})

# Integrar en lifespan de FastAPI
# src/api/main.py
from src.scheduler.bartenders_jobs import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

---

## 09 — API Routes de Bartenders NOA

```python
# src/api/routes/bartenders.py

from fastapi import APIRouter, Header, BackgroundTasks
from src.flows.registry import FlowRegistry

router = APIRouter(prefix="/bartenders", tags=["bartenders"])

@router.post("/preventa")
async def iniciar_preventa(
    input_data: PreventaInput,
    background_tasks: BackgroundTasks,
    x_org_id: str = Header(...)
):
    """Inicia el flow preventa: consulta → escandallo → 3 opciones."""
    flow = FlowRegistry.create("bartenders_preventa", org_id=x_org_id)
    background_tasks.add_task(flow.execute, input_data.dict())
    return {"task_id": flow.state.task_id, "status": "pending"}

@router.post("/reserva")
async def confirmar_reserva(input_data: ReservaInput, x_org_id: str = Header(...)):
    """Confirma cotización elegida: reserva stock + asigna bartenders."""
    flow = FlowRegistry.create("bartenders_reserva", org_id=x_org_id)
    background_tasks.add_task(flow.execute, input_data.dict())
    return {"task_id": flow.state.task_id, "status": "pending"}

@router.post("/cierre")
async def cerrar_evento(input_data: CierreInput, x_org_id: str = Header(...)):
    """Cierre post-evento: auditoría + feedback."""
    flow = FlowRegistry.create("bartenders_cierre", org_id=x_org_id)
    background_tasks.add_task(flow.execute, input_data.dict())
    return {"task_id": flow.state.task_id, "status": "pending"}
```

---

## 10 — Flujo demo para el Dashboard (15 minutos)

```
PASO 1 (2 min): Trigger PreventaFlow
  → Disparar desde Dashboard: boda 150 pax, Tucumán, enero, premium
  → Kanban: pending → running
  → 4 agentes encadenados ejecutando (logs visibles en tiempo real)
  → Resultado: 3 opciones de precio en el detalle de la task

PASO 2 (1 min): Mostrar el escandallo
  → Click en task completed → expandir output
  → Ver desglose: Bloque 1 ARS X, Bloque 2 ARS X, factor climático +20%

PASO 3 (2 min): Trigger ReservaFlow con opcion_elegida: recomendada
  → Kanban: nueva task running
  → Agente 6 reserva stock → inventario baja en tiempo real (Dashboard)
  → Agente 8 asigna bartenders → bartenders_disponibles se actualiza

PASO 4 (3 min): ALERTA CLIMÁTICA
  → Trigger manual de AlertaClimaFlow con desvio simulado (+8°C)
  → Kanban: card ámbar "ALERTA ROJA — Compra emergencia ARS 220.000"
  → Ir a Centro de Aprobaciones
  → Ver payload: items, motivo, desvío detectado
  → APROBAR → task reanuda → orden en ordenes_compra

PASO 5 (2 min): RECHAZAR una segunda compra
  → Trigger otra alerta con monto mayor
  → RECHAZAR → task marcada como rejected
  → Log de eventos muestra trail completo

PASO 6 (2 min): CierreFlow
  → Trigger con datos reales del EVT-2026-001
  → Agente 9 calcula margen: 14.3%
  → Agente 10 genera lección: "Enero NOA ola de calor..."
  → auditorias y eventos actualizados

PASO 7 (2 min): Resumen en Dashboard
  → Overview: 3 tasks completed, 1 rejected, ARS 220.000 aprobado
  → Ver inventario actualizado con reservas
  → Ver auditoría con ganancia y lección aprendida
```

---

## 11 — Tablas SQL que cambian en Fase 7

Cuando llegue Fase 7 con Google Sheets real, estas tablas dejan de ser la fuente de verdad
del negocio y pasan a ser **caché de lectura**. La única capa que cambia es el conector:

| Tabla Supabase (Fase 6) | Equivalente Google Sheets (Fase 7) | Rol en Fase 7 |
|---|---|---|
| `precios_bebidas` | `precios_bebidas.xlsx` | Caché — sync diario desde Sheets |
| `inventario` | `inventario.xlsx` | Caché — sync en tiempo real |
| `bartenders_disponibles` | `bartenders_disponibles.xlsx` | Caché — sync en tiempo real |
| `config_consumo_pax` | `config_consumo_pax.xlsx` | Caché — sync semanal |
| `config_climatico` | `config_margenes.xlsx Tab Climático` | Caché — sync mensual |
| `eventos` | `eventos.xlsx` | Bidireccional — FAP es maestro |
| `cotizaciones` | `cotizaciones.xlsx` | Bidireccional — FAP es maestro |
| `ordenes_compra` | `ordenes_compra.xlsx` | Bidireccional — FAP es maestro |
| `auditorias` | `auditorias.xlsx` | Bidireccional — FAP es maestro |

---

## 12 — Orden de implementación (dependencias)

| # | Paso | Depende de | Tiempo est. |
|---|---|---|---|
| 1 | SQL: tablas config (009) | — | 1h |
| 2 | SQL: tablas operativas (010) | 1 | 2h |
| 3 | SQL: RLS (011) | 2 | 30m |
| 4 | SQL: seed data (012) | 1, 2 | 1h |
| 5 | Script: seed_bartenders_noa.py | 4 | 1h |
| 6 | `BaseDataConnector` interfaz | — | 30m |
| 7 | `SupabaseMockConnector` | 6 | 1h |
| 8 | `EscandalloTool` | 7 | 2h |
| 9 | `ClimaTool` (mock) | 7 | 1h |
| 10 | `InventarioTool` | 7 | 1h |
| 11 | Crews Agentes 1-4 | 8, 9 | 3h |
| 12 | `PreventaFlow` | 11 | 2h |
| 13 | Crews Agentes 6-8 | 10 | 3h |
| 14 | `ReservaFlow` | 13 | 2h |
| 15 | Crews Agentes 5, 7 | 9, 10 | 2h |
| 16 | `AlertaClimaFlow` | 15 | 2h |
| 17 | Crews Agentes 9-10 | 7 | 2h |
| 18 | `CierreFlow` | 17 | 2h |
| 19 | Crew Agente 11 | 7 | 1h |
| 20 | APScheduler jobs | 16, 19 | 1h |
| 21 | API routes bartenders | 12, 14, 16, 18 | 2h |
| 22 | Registrar flows en FlowRegistry | 12, 14, 16, 18 | 30m |
| 23 | Tests e2e preventa_flow | 12 | 2h |
| 24 | Tests e2e alerta_flow + HITL | 16 | 2h |
| 25 | Demo end-to-end en Dashboard | todo | 2h |

**Total estimado:** ~40 horas de implementación

---

## 13 — Criterio de éxito

### Criterio técnico
- `PreventaFlow` completa en < 60 segundos (4 agentes encadenados)
- Escandallo produce resultado idéntico al ejemplo de la spec (ARS 2.956.716 para boda 150 PAX premium enero Tucumán)
- `AlertaClimaFlow` crea `pending_approval` visible en Dashboard en tiempo real
- `SupabaseMockConnector.read("inventario")` retorna datos reales del seed
- APScheduler corre sin bloquear el event loop de FastAPI

### Criterio demo
- Demo completa de 15 minutos sin errores
- El escandallo muestra los 4 bloques desglosados
- Una compra de emergencia se aprueba y otra se rechaza — ambas visibles en Kanban
- La auditoría cierra el ciclo con ganancia neta y lección aprendida
- El inventario se actualiza visiblemente en el Dashboard cuando se reserva stock

### Fuera de scope para Fase 6
- Google Sheets API real (Fase 7)
- Web scraping de precios (Fase 7)
- SMN API para pronóstico real (Fase 7)
- Notificaciones WhatsApp/email a bartenders (Fase 7)
- Marketplace: publicar Bartenders NOA como template (Fase 7)
- PDFs de cotizaciones y contratos (Fase 7)

---

## 14 — Reglas de implementación

1. **Los agentes nunca importan `supabase` directamente.** Todo pasa por `connector.read()` / `connector.write()`.
2. **El conector se inyecta al crear el Crew, no al crear el agente.** Permite testear con mocks sin tocar el SOUL.
3. **`EscandalloTool` es determinista.** Mismos inputs → mismo output siempre. No hay LLM en el cálculo.
4. **Los flows de Bartenders NOA heredan de `BaseFlow`.** Usan `request_approval()`, `FlowSuspendedException`, `EventStore` — todo igual que cualquier otro flow de FAP.
5. **El APScheduler corre en el mismo proceso que FastAPI.** Sin workers externos en Fase 6. Si hay carga alta, se mueve a Celery en Fase 7.

---

## 15 — Resumen de archivos nuevos en Fase 6

| Archivo | Tipo | Descripción |
|---|---|---|
| `sql/009_bartenders_config.sql` | SQL | Tablas de configuración sin org_id |
| `sql/010_bartenders_operativo.sql` | SQL | 9 tablas de negocio con org_id |
| `sql/011_bartenders_rls.sql` | SQL | RLS masivo para tablas operativas |
| `sql/012_bartenders_seed.sql` | SQL | Datos reales de planillas (config) |
| `scripts/seed_bartenders_noa.py` | Python | Inserta datos con org_id real |
| `src/connectors/base_connector.py` | Python | Interfaz abstracta DataConnector |
| `src/connectors/supabase_connector.py` | Python | Implementación mock con Supabase |
| `src/tools/bartenders/escandallo_tool.py` | Python | Cálculo determinista de 4 bloques |
| `src/tools/bartenders/clima_tool.py` | Python | Factor climático + mock pronóstico |
| `src/tools/bartenders/inventario_tool.py` | Python | Reservar/liberar stock |
| `src/flows/bartenders/preventa_flow.py` | Python | Flow Agentes 1→2→3→4 |
| `src/flows/bartenders/reserva_flow.py` | Python | Flow Agentes 6→8 |
| `src/flows/bartenders/alerta_flow.py` | Python | Flow Agentes 5→7 + HITL |
| `src/flows/bartenders/cierre_flow.py` | Python | Flow Agentes 9→10 |
| `src/crews/bartenders/` (11 archivos) | Python | Un crew por agente |
| `src/scheduler/bartenders_jobs.py` | Python | APScheduler jobs |
| `src/api/routes/bartenders.py` | Python | 3 endpoints + registro en main.py |
