# Fase 6 — Bartenders NOA (con mock connector)

> **Definición cerrada.** Basada en el backend de Fases 1–5 ya implementado.
> Todo el código es consistente con los patterns existentes de FAP.
> Última revisión: Abril 2026

---

## Tabla de contenidos

1. [Visión y criterio de éxito](#01--visión-y-criterio-de-éxito)
2. [Principio central: el DataConnector](#02--principio-central-el-dataconnector)
3. [Stack tecnológico](#03--stack-tecnológico)
4. [Base de datos — 12 tablas](#04--base-de-datos--12-tablas)
5. [Seed data — datos reales de planillas](#05--seed-data--datos-reales-de-planillas)
6. [Capa 2: BaseDataConnector + SupabaseMockConnector](#06--capa-2-basedataconnector--supabasemockconnector)
7. [Capa 3: Tools (3 herramientas)](#07--capa-3-tools-3-herramientas)
8. [Capa 4: Crews (11 agentes)](#08--capa-4-crews-11-agentes)
9. [Capa 5: Flows (4 orquestadores)](#09--capa-5-flows-4-orquestadores)
10. [Capa 6: API routes + APScheduler](#10--capa-6-api-routes--apscheduler)
11. [HITL: los 3 puntos de aprobación](#11--hitl-los-3-puntos-de-aprobación)
12. [Flujo demo paso a paso](#12--flujo-demo-paso-a-paso)
13. [Transición a Fase 7](#13--transición-a-fase-7)
14. [Orden de implementación](#14--orden-de-implementación)
15. [Criterio de éxito](#15--criterio-de-éxito)
16. [Inventario de archivos](#16--inventario-de-archivos)

---

## 01 — Visión y criterio de éxito

Bartenders NOA es una empresa de barras móviles en Tucumán que opera en las 4 provincias
del NOA (Tucumán, Salta, Jujuy, Catamarca). Fase 6 implementa su sistema agéntico completo
dentro de FAP, usando **Supabase como mock del Google Sheets connector**.

### Por qué Supabase y no dicts hardcodeados

Los datos del negocio (inventario, precios, bartenders) viven en Supabase bajo RLS por org_id.
Esto permite que el Dashboard muestre cambios en tiempo real: cuando el Agente 6 reserva stock,
`inventario.stock_reservado` sube instantáneamente en la pantalla. Con dicts en memoria
eso no sería posible.

### El contrato del conector

Los agentes **nunca** importan Supabase directamente. Siempre llaman al conector:

```python
# El agente siempre hace esto — no cambia entre Fase 6 y Fase 7
data = connector.read("precios_bebidas")
config = connector.get_config("config_climatico", {"mes": 1})
connector.write("eventos", {...})
```

En Fase 7, el único cambio es qué clase se inyecta al crear el Flow:
- Fase 6: `SupabaseMockConnector(org_id, user_id)`
- Fase 7: `GoogleSheetsConnector(credentials_json, spreadsheet_ids)`

### Criterio de éxito

Demo completa de 15 minutos en laptop, sin infraestructura cloud:
- `PreventaFlow` calcula escandallo ~ARS 2.956.716 para boda 150 pax enero Tucumán premium
- `AlertaClimaFlow` dispara ALERTA ROJA por ola de calor (+7°C) → HITL visible en Dashboard
- Jefe aprueba compra → orden_id en DB → task `completed` en Kanban
- `CierreFlow` cierra con margen 14.3% y lección aprendida

---

## 02 — Principio central: el DataConnector

### Interfaz abstracta (`src/connectors/base_connector.py`)

```python
class BaseDataConnector(ABC):

    @abstractmethod
    def read(self, table: str, filters: dict | None = None) -> list[dict]:
        """Tablas operativas con org_id + RLS."""

    @abstractmethod
    def write(self, table: str, data: dict) -> dict:
        """Inserta registro. Inyecta org_id automáticamente."""

    @abstractmethod
    def update(self, table: str, record_id: str, data: dict) -> dict:
        """Actualiza por PK. RLS garantiza que solo modifica registros del tenant."""

    @abstractmethod
    def get_config(self, table: str, filters: dict | None = None) -> list[dict]:
        """Tablas de configuración global sin org_id (service_role)."""

    # Helpers no abstractos:
    def read_one(self, table, filters) -> dict | None   # primer resultado o None
    def get_config_one(self, table, filters) -> dict | None
```

### Separación de tablas

| Tipo | Tablas | org_id | RLS | Método |
|---|---|---|---|---|
| **Configuración** | `config_consumo_pax`, `config_margenes`, `config_climatico`, `equipamiento_amortizacion` | No | No | `get_config()` |
| **Operativas** | `bartenders_disponibles`, `precios_bebidas`, `inventario`, `eventos`, `cotizaciones`, `ordenes_compra`, `auditorias`, `historial_precios` | Sí | Sí | `read()` / `write()` / `update()` |

### Validación de errores de uso

El conector lanza `ValueError` si se confunden los tipos:

```python
connector.read("config_consumo_pax")
# → ValueError: 'config_consumo_pax' es tabla de configuración. Usar get_config()

connector.get_config("eventos")
# → ValueError: 'eventos' no es tabla de configuración reconocida.
```

### RPC atómica de inventario

`reserve_stock()` y `release_stock()` no usan `update()` sino RPCs de Supabase
con `FOR UPDATE` para evitar race conditions cuando dos flows corren en paralelo:

```python
connector.reserve_stock("GIN-001", 5)
# → llama RPC reserve_inventory_item(p_org_id, p_item_id, p_cantidad)
# → PostgreSQL hace SELECT ... FOR UPDATE antes de UPDATE
# → Si stock insuficiente: retorna { "error": "Stock insuficiente..." }
# → Python lanza ValueError con el mensaje
```

### PKs por tabla (usadas en `update()`)

```python
TABLE_PKS = {
    "bartenders_disponibles": "bartender_id",
    "precios_bebidas":         "producto_id",
    "inventario":              "item_id",
    "eventos":                 "evento_id",
    "cotizaciones":            "cotizacion_id",
    "ordenes_compra":          "orden_id",
    "auditorias":              "auditoria_id",
    "historial_precios":       "id",
}
```

---

## 03 — Stack tecnológico

| Componente | Tecnología | Estado |
|---|---|---|
| Backend Python | FastAPI + CrewAI Flows | existente (Fases 1–4) |
| Base de datos | Supabase (PostgreSQL) | existente |
| Dashboard | Next.js 14 + Realtime | existente (Fase 5) |
| DataConnector | `SupabaseMockConnector` | **NUEVO** Fase 6 |
| Agentes (11) | CrewAI Agent + Crew | **NUEVO** Fase 6 |
| Flows (4) | CrewAI Flow + BaseFlow | **NUEVO** Fase 6 |
| SQL tablas negocio | 11 tablas + RLS + 2 RPCs | **NUEVO** Fase 6 |
| APScheduler | `AsyncIOScheduler` | **NUEVO** Fase 6 |
| dateutil | `relativedelta` para proxima_contacto | **NUEVA** dependencia |

---

## 04 — Base de datos — 12 tablas

### Tablas de configuración (sin org_id)

#### `config_consumo_pax`

Consumo estimado por tipo de menú y persona. Constraint suma 100% garantiza
que los porcentajes de mix de espirituosos sumen exactamente 100.

| Columna | Tipo | Descripción |
|---|---|---|
| `tipo_menu` | TEXT PK | `basico` \| `estandar` \| `premium` |
| `coctel_por_persona` | INTEGER | Cócteles por persona durante el evento |
| `ml_espiritoso_por_coctel` | INTEGER | Mililitros de espirituoso por cóctel |
| `hielo_kg_por_persona` | NUMERIC(4,2) | Kilogramos de hielo por persona |
| `agua_litros_por_persona` | NUMERIC(4,2) | Litros de agua por persona |
| `garnish_ars_por_persona` | INTEGER | Costo de garnish en ARS por persona |
| `desechables_ars_por_persona` | INTEGER | Costo de desechables en ARS por persona |
| `mix_gin_pct` | INTEGER | % de gin sobre total de espirituosos |
| `mix_whisky_pct` | INTEGER | % de whisky |
| `mix_ron_pct` | INTEGER | % de ron |
| `mix_vodka_pct` | INTEGER | % de vodka |
| `mix_tequila_pct` | INTEGER | % de tequila |

**Constraint:** `mix_gin + mix_whisky + mix_ron + mix_vodka + mix_tequila = 100`

#### `config_margenes`

| Columna | Tipo | Descripción |
|---|---|---|
| `opcion` | TEXT PK | `basica` \| `recomendada` \| `premium` |
| `margen_pct` | INTEGER | Margen de ganancia (40, 45, 50) |
| `descripcion` | TEXT | Descripción del segmento |

#### `config_climatico`

Factor de ajuste histórico por mes para NOA. El Agente 2 lee esta tabla.

| Mes | Factor % | Razón |
|---|---|---|
| 1 (Enero) | 20 | Calor extremo NOA |
| 2 (Febrero) | 20 | Lluvia y calor |
| 3 (Marzo) | 12 | Fin de lluvias, variable |
| 4 (Abril) | 12 | Transición, variable |
| 5–8 (Invierno) | 5 | Invierno seco, bajo consumo |
| 9–10 (Primavera) | 8 | Primavera, transición |
| 11–12 (Verano) | 20 | Pre-verano / verano |

#### `equipamiento_amortizacion`

Amortización por evento de cada ítem de equipamiento.

| Item | Costo compra | Vida útil | Amort/evento |
|---|---|---|---|
| Barra móvil plegable | ARS 500.000 | 200 eventos | ARS 2.500 |
| Set 200 copas | ARS 200.000 | 150 eventos | ARS 1.333 |
| Heladera portátil 100L | ARS 300.000 | 180 eventos | ARS 1.667 |
| Cocteleras y jiggers | ARS 150.000 | 200 eventos | ARS 750 |

**Total amortización por evento: ARS 6.250**

---

### Tablas operativas (con org_id + RLS)

#### `bartenders_disponibles`

12 bartenders reales cargados desde las planillas Excel originales.

| Columna | Tipo | Descripción |
|---|---|---|
| `bartender_id` | TEXT PK | Ej: `BAR-001` |
| `org_id` | UUID FK | Tenant RLS |
| `nombre` | TEXT | Nombre completo |
| `telefono` | TEXT | Número de contacto |
| `especialidad` | TEXT | `premium` \| `clasica` |
| `es_head_bartender` | BOOLEAN | ¿Puede ser head? |
| `tarifa_hora_ars` | INTEGER | Tarifa por hora en ARS |
| `eventos_realizados` | INTEGER | Experiencia acumulada |
| `calificacion` | NUMERIC(3,1) | Rating 1.0–5.0 |
| `disponible` | BOOLEAN | False si está asignado |
| `fecha_proxima_reserva` | DATE | Próxima fecha disponible |

**Índice:** `(org_id, disponible) WHERE disponible = TRUE` — optimiza la búsqueda del Agente 8.

**Datos seed (12 bartenders):**

| ID | Nombre | Especialidad | Head | Tarifa/h | Cal. |
|---|---|---|---|---|---|
| BAR-001 | Juan Perez | premium | Sí | 50.000 | 4.8 |
| BAR-002 | Maria Garcia | clasica | No | 35.000 | 4.5 |
| BAR-003 | Carlos Lopez | premium | No | 35.000 | 4.7 |
| BAR-004 | Ana Martinez | clasica | No | 35.000 | 4.3 |
| BAR-005 | Roberto Silva | premium | No | 35.000 | 4.9 |
| BAR-006 | Lucia Rodriguez | clasica | No | 35.000 | 4.2 |
| BAR-007 | Martin Gonzalez | premium | No | 35.000 | 4.6 |
| BAR-008 | Sofia Fernandez | clasica | No | 35.000 | 4.4 |
| BAR-009 | Diego Torres | premium | No | 35.000 | 4.8 |
| BAR-010 | Gabriela Lopez | clasica | No | 35.000 | 4.3 |
| BAR-011 | Fernando Ruiz | premium | No | 35.000 | 4.7 |
| BAR-012 | Patricia Alvarez | clasica | No | 35.000 | 4.5 |

#### `precios_bebidas`

Precios actualizados semanalmente por el Agente 11.

| ID | Nombre | Categoría | Presentación | Precio ARS | Por cóctel | Es oferta |
|---|---|---|---|---|---|---|
| GIN-001 | Gordon's Pink | gin | 700ml | 12.000 | 800 | No |
| GIN-002 | Beefeater | gin | 700ml | 28.000 | 1.867 | No |
| WHISKY-001 | Old Smuggler | whisky | 750ml | 7.000 | 467 | No |
| WHISKY-002 | Johnnie Walker Red | whisky | 750ml | 25.000 | 1.667 | No |
| VODKA-001 | Smirnoff | vodka | 700ml | 8.000 | 533 | No |
| RON-001 | Bacardi | ron | 750ml | 18.000 | 1.200 | No |
| TEQUILA-001 | Jose Cuervo | tequila | 750ml | 22.000 | 1.467 | No |

**Nota:** `es_oferta = TRUE` cuando `precio_ars < precio_base_referencia × 0.85` (ahorro > 15%)

#### `inventario`

Stock físico con columna generada `stock_disponible = stock_actual - stock_reservado`.

| ID | Nombre | Stock actual | Stock reservado | Mínimo |
|---|---|---|---|---|
| GIN-001 | Gordon's Pink 700ml | 24 | 12 | 6 |
| WHISKY-001 | Old Smuggler 750ml | 18 | 0 | 4 |
| GIN-002 | Beefeater 700ml | 8 | 0 | 2 |
| WHISKY-002 | Johnnie Walker Red | 6 | 0 | 2 |
| VODKA-001 | Smirnoff 700ml | 12 | 0 | 3 |
| RON-001 | Bacardi 750ml | 10 | 0 | 3 |
| TEQUILA-001 | Jose Cuervo 750ml | 8 | 0 | 2 |
| HIELO-001 | Hielo 2kg | 50 bolsas | 0 | 20 |
| AGUA-001 | Agua mineral 1.5L | 100 botellas | 0 | 30 |

**Constraint:** `stock_reservado <= stock_actual` garantizado en DB.

#### `eventos`

Tabla central del negocio. Ciclo de vida del status:

```
nuevo → cotizado → confirmado → coordinado → ejecutado → cerrado
                                                        → cancelado
```

| Status | Quién lo asigna |
|---|---|
| `nuevo` | Agente 1 al registrar |
| `cotizado` | Agente 4 al generar cotización |
| `confirmado` | Agente 8 al asignar bartenders |
| `coordinado` | Agente 5/7 al aprobar compra de emergencia |
| `ejecutado` | Agente 9 al registrar auditoría |
| `cerrado` | Agente 10 al completar feedback |
| `cancelado` | Manual o por rechazo de reserva |

#### `cotizaciones`

Constraint `opciones_orden` garantiza `basica ≤ recomendada ≤ premium` en DB.

```
cotizacion_id, evento_id, escandallo_total,
opcion_basica, opcion_recomendada, opcion_premium,
factor_climatico, fecha_generacion, opcion_elegida, status
```

#### `ordenes_compra`

Campo `items` es JSONB con estructura:
```json
[
  { "item_id": "GIN-001", "nombre": "Gordon's", "cantidad": 10,
    "precio_unitario": 12000, "subtotal": 120000 }
]
```

Campo `task_id` referencia la task de FAP donde ocurrió el HITL.

#### `auditorias`

`ganancia_neta` es columna generada: `precio_cobrado - costo_real`.
Una sola auditoría por evento (`UNIQUE(evento_id)`).

#### `historial_precios`

Append-only. El Agente 11 inserta aquí antes de actualizar `precios_bebidas`.
Permite ver la evolución de precios en el tiempo.

### RPCs de inventario (`013_bartenders_rpc_inventario.sql`)

Dos funciones con `FOR UPDATE` para operaciones atómicas:

```sql
reserve_inventory_item(p_org_id, p_item_id, p_cantidad) → JSONB
-- Retorna { "ok": true, "stock_disponible_restante": N }
-- o       { "error": "Stock insuficiente..." }

release_inventory_item(p_org_id, p_item_id, p_cantidad) → JSONB
-- Libera reservas al cancelar un evento
```

Solo accesibles por `service_role` — los agentes no las llaman directamente,
van a través de `connector.reserve_stock()` / `connector.release_stock()`.

---

## 05 — Seed data — datos reales de planillas

### Archivos de seed

**`012_bartenders_seed_config.sql`** — tablas sin org_id (ejecutar en SQL Editor):
- `config_consumo_pax`: 3 filas (basico, estandar, premium)
- `config_margenes`: 3 filas (basica 40%, recomendada 45%, premium 50%)
- `config_climatico`: 12 filas (un factor por mes)
- `equipamiento_amortizacion`: 4 ítems

**`scripts/seed_bartenders_noa.py`** — datos con org_id (ejecutar después de crear la org):

```bash
python scripts/seed_bartenders_noa.py --org-name "Bartenders NOA"
# O con UUID directo:
python scripts/seed_bartenders_noa.py --org-id <uuid>

# Para no insertar datos demo (EVT-2026-001):
python scripts/seed_bartenders_noa.py --org-name "Bartenders NOA" --skip-demo
```

El script inserta:
- 12 bartenders en `bartenders_disponibles`
- 7 productos en `precios_bebidas`
- 9 items en `inventario`
- Datos demo: EVT-2026-001 → COT-2026-001 → OC-2026-001 → AUD-2026-001

### Caso de prueba canónico (EVT-2026-001)

| Campo | Valor |
|---|---|
| evento_id | EVT-2026-001 |
| Fecha | 2026-01-15 (enero → factor climático 20%) |
| Provincia | Tucumán (logística fija: ARS 51.000) |
| Pax | 150 (4 bartenders + 1 head) |
| Duración | 5 horas (8 horas totales con setup) |
| Tipo menú | premium (6 cócteles/persona, 55ml/cóctel) |
| Escandallo | ARS 2.956.716 |
| Opción recomendada | ARS 5.376.757 (margen 45%) |

---

## 06 — Capa 2: BaseDataConnector + SupabaseMockConnector

### Tabla de operaciones

| Método | Tabla destino | Usa RLS | Notas |
|---|---|---|---|
| `read(table, filters)` | Operativa | Sí (TenantClient) | Filtros como `{col: val}` |
| `write(table, data)` | Operativa | Sí | Inyecta `org_id` automático |
| `update(table, pk, data)` | Operativa | Sí | PK según `TABLE_PKS` |
| `get_config(table, filters)` | Configuración | No (service_role) | Read-only |
| `read_one(table, filters)` | Operativa | Sí | Helper: primer resultado o None |
| `get_config_one(table, filters)` | Configuración | No | Helper: primer resultado o None |
| `reserve_stock(item_id, cantidad)` | `inventario` vía RPC | No (service_role) | Atómico con FOR UPDATE |
| `release_stock(item_id, cantidad)` | `inventario` vía RPC | No (service_role) | Atómico con FOR UPDATE |

### Transición Fase 6 → Fase 7

Lo único que cambia es la clase concreta inyectada al crear el Flow:

```python
# Fase 6 (actual)
connector = SupabaseMockConnector(org_id=org_id, user_id=user_id)

# Fase 7 (reemplazar solo esta línea)
connector = GoogleSheetsConnector(
    credentials_json = vault.get_secret(org_id, "GOOGLE_SHEETS_CREDENTIALS"),
    spreadsheet_ids  = {
        "eventos":       "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        "precios_bebidas": "...",
        # etc.
    }
)
```

Los 11 agentes, 3 tools y 4 flows no se modifican.

---

## 07 — Capa 3: Tools (3 herramientas)

### EscandalloTool (`calcular_escandallo`)

**Es determinista:** mismos inputs → mismo output. No hay LLM en los cálculos.

#### Fórmula completa

```
BLOQUE 1: Productos
    cocteles_totales = pax × coctel_por_persona
    ml_total         = cocteles_totales × ml_espiritoso_por_coctel
    precio_por_ml    = promedio_ponderado(precios por categoría) / presentacion_ml
    bebidas_alc      = Σ (ml_total × mix_cat_pct × precio_por_ml_cat)
    bebidas_no_alc   = pax × agua_litros_por_persona × 400 ARS/L
    hielo            = pax × hielo_kg_por_persona × 750 ARS/kg
    garnish          = pax × garnish_ars_por_persona
    desechables      = pax × desechables_ars_por_persona
    B1 = bebidas_alc + bebidas_no_alc + hielo + garnish + desechables

BLOQUE 2: Equipamiento
    B2 = Σ amortizacion_por_evento (solo ítems con estado="activo")
       = 2.500 + 1.333 + 1.667 + 750 = 6.250 ARS

BLOQUE 3: Personal
    n_bartenders    = CEILING(pax / 40)
    necesita_head   = pax > 100
    necesita_asist  = duracion_horas > 6
    horas_totales   = duracion_horas + 3   ← setup/cierre fijo
    B3 = n_bartenders × 35.000 × horas_totales
       + (50.000 × horas_totales si necesita_head)
       + (28.000 × horas_totales si necesita_asistente)

BLOQUE 4: Logística
    SI provincia = Tucumán:
        B4 = 17.000 × 3 = 51.000 ARS
    SI provincia ≠ Tucumán:
        km = distancia_km[provincia]
        B4 = km × 2 × 600 + 5.000 ARS
        (Salta: 365.000 | Jujuy: 425.000 | Catamarca: 341.000)

AJUSTES:
    subtotal         = B1 + B2 + B3 + B4
    base_climatica   = B1 + B2  ← el ajuste climático SOLO sobre productos y equipamiento
    ajuste_climatico = base_climatica × factor_climatico_pct / 100
    base_ajustada    = subtotal + ajuste_climatico
    mermas           = base_ajustada × 0.05   ← 5% fijo, no negociable
    imprevistos      = base_ajustada × 0.03   ← 3% fijo, no negociable
    escandallo_final = base_ajustada + mermas + imprevistos
```

#### Verificación con el caso canónico

Boda 150 pax, enero, Tucumán, premium, 5 horas:

| Concepto | Valor |
|---|---|
| B1 Productos | ~ARS 966.000 |
| B2 Equipamiento | ARS 6.250 |
| B3 Personal (4+1 head × 8h) | ARS 1.520.000 |
| B4 Logística Tucumán | ARS 51.000 |
| Subtotal | ARS 2.543.250 |
| Ajuste climático +20% (sobre B1+B2) | ARS 194.450 |
| Mermas 5% | ARS 136.885 |
| Imprevistos 3% | ARS 82.131 |
| **Escandallo final** | **~ARS 2.956.716** |

#### Output del modelo Pydantic

```python
EscandalloOutput(
    evento_id, bloque1_productos, bloque2_equipamiento,
    bloque3_personal, bloque4_logistica, subtotal,
    ajuste_climatico, mermas, imprevistos, escandallo_final,
    bartenders_necesarios, necesita_head, necesita_asistente,
    horas_totales, factor_climatico_aplicado
)
```

---

### FactorClimaticoTool (`obtener_factor_climatico`)

Usada por el **Agente 2** en `PreventaFlow`.

Consulta `config_climatico` por número de mes (1-12).
Si el mes no existe en la tabla: devuelve factor 10% como default conservador.

```python
# Input
mes: int, provincia: str = "Tucuman"

# Output
FactorClimaticoOutput(mes, factor_pct, razon, provincia)
```

---

### PronosticoRealTool (`verificar_pronostico_real`)

Usada por el **Agente 5** en `AlertaClimaFlow`.

Compara temperatura pronosticada vs temperatura histórica del mes.
Umbral de ALERTA ROJA: desvío > 10%.

**Fase 6:** pronóstico viene de `MOCK_FORECAST_OVERRIDE` (dict configurable):
```python
MOCK_FORECAST_OVERRIDE = {
    "EVT-2026-001": 33.0,  # ola de calor → 33°C vs histórico enero 26°C
}
```
Si el evento no está en el dict: usa temperatura histórica + delta 0 (sin desvío).

**Fase 7:** reemplazar `_fetch_real_forecast()` con llamada a API del SMN.

Temperaturas históricas NOA por mes (°C):

| Mes | Temp. histórica |
|---|---|
| Enero | 26.0 |
| Febrero | 25.5 |
| Marzo | 23.0 |
| Abril | 19.0 |
| Mayo | 14.5 |
| Junio | 11.0 |
| Julio | 10.5 |
| Agosto | 13.0 |
| Septiembre | 16.5 |
| Octubre | 20.0 |
| Noviembre | 23.5 |
| Diciembre | 25.0 |

---

### InventarioTool (3 tools separadas)

#### `CalcularStockNecesarioTool` (`calcular_stock_necesario`)

Calcula cantidades necesarias sin modificar el inventario.
Aplica buffer de seguridad del 10%.

Fórmula:
```
botellas_cat = CEILING(ml_categoria / ml_por_botella_cat × 1.10)
bolsas_hielo = CEILING(pax × hielo_kg_persona / 2 × 1.10)
botellas_agua = CEILING(pax × agua_litros_persona / 1.5 × 1.10)
```

#### `ReservarStockTool` (`reservar_stock_evento`)

Reserva los items calculados via `connector.reserve_stock()`.
Nunca falla silenciosamente — siempre reporta éxitos y fallos por separado.

Output:
```python
ReservarStockOutput(
    evento_id,
    reservas_exitosas: list[ReservaResultado],
    reservas_fallidas: list[ReservaResultado],
    alerta_faltante: bool,   # True → Agente 7 debe comprar
    items_a_comprar: list[ItemNecesario]
)
```

#### `LiberarStockTool` (`liberar_stock_evento`)

Libera reservas cuando un evento se cancela.
Usa `connector.release_stock()` — operación inversa a reservar.

---

## 08 — Capa 4: Crews (11 agentes)

### Principio de diseño de los crews

Cada crew tiene una separación clara entre **lógica determinista** (funciones con prefijo `_`)
y **LLM** (Agent + Task). Las funciones `_` se testean sin mockear CrewAI.

```
_registrar_evento()      → escribe en DB directamente
create_requerimientos_crew() → el LLM confirma y formatea el output Pydantic
```

Reglas invariantes de todos los agentes:
- `allow_delegation = False` — nunca delegan a otro agente
- `max_iter ≤ 3` — falla rápido si el LLM no converge (A3 y A11 usan `max_iter=2`)
- `output_pydantic` — salida tipada y validada en todos

---

### Fase 1 — Preventa (`preventa_crews.py`)

#### Agente 1 — Requerimientos

**SOUL:** "Captura datos del evento con precisión quirúrgica. No avanza si datos son ambiguos."

**Reglas rígidas:**
- NUNCA asumir provincia si no está especificada
- NUNCA aceptar PAX fuera de 10–500
- NUNCA aceptar fechas en el pasado
- Provincias válidas: Tucuman, Salta, Jujuy, Catamarca

**Lógica determinista:** `_registrar_evento()` escribe en DB con `status="nuevo"`.
El `evento_id` se genera como `EVT-{año}-{uuid[:4].upper()}`.

---

#### Agente 2 — Meteorológico Histórico

**SOUL:** "Analista climático. Se basa exclusivamente en datos — nunca en intuición."

**Reglas rígidas:**
- Factor climático viene EXCLUSIVAMENTE de `config_climatico`
- Si no encuentra el mes: usar 10% como default
- Siempre incluir la razón del factor

**Lógica:** Lee `config_climatico` por mes, retorna `{factor_pct, razon}`.

---

#### Agente 3 — Calculador

**SOUL:** "Ingeniero financiero. Cada número tiene una fuente."

**Reglas rígidas:**
- Ratio bartenders: 1 cada 40 PAX (CEILING, nunca floor)
- Horas setup/cierre: SIEMPRE +3 horas
- Mermas: SIEMPRE 5%
- Imprevistos: SIEMPRE 3%
- Factor climático: SOLO sobre B1 y B2
- Head: obligatorio si PAX > 100
- Asistente: obligatorio si duración > 6 horas

`max_iter=2` porque el cálculo es determinista.

---

#### Agente 4 — Presupuestador

**SOUL:** "Comercial. Transparente con números, estratégico en presentación."

**Reglas rígidas:**
- Márgenes EXACTOS: 40% / 45% / 50% (de `config_margenes`)
- Fórmula: `precio = escandallo / (1 - margen)`
- NUNCA modificar márgenes por presión del cliente
- Opción "recomendada" = SIEMPRE la del 45%
- NUNCA generar cotización sin persistirla

**Lógica determinista:** `_calcular_opciones()` hace la aritmética. `_guardar_cotizacion()` escribe en DB y actualiza evento a `status="cotizado"`.

Verificación del caso canónico (escandallo 2.956.716):
- Básica: 2.956.716 / 0.60 = **ARS 4.927.860**
- Recomendada: 2.956.716 / 0.55 = **ARS 5.376.757**
- Premium: 2.956.716 / 0.50 = **ARS 5.913.432**

---

### Fase 2 — Reserva y Logística (`reserva_crews.py`)

#### Agente 5 — Monitor Climático Real

**SOUL:** "Sistema de alerta temprana. Conservador: prefiere falsa alarma."

**Reglas rígidas:**
- Umbral ALERTA ROJA: desvío > 10% (no 15%, no 20%)
- Fase 6: pronóstico viene de mock configurable
- NUNCA actuar sobre inventario — solo detectar y reportar

---

#### Agente 6 — Inventario

**SOUL:** "Guardián del stock físico. Nunca reserva más de lo disponible."

**Reglas rígidas:**
- NUNCA reservar más de lo disponible (RPC lo valida atómicamente)
- Si falta algún item: reportar inmediatamente
- NUNCA liberar stock de evento activo sin orden del Jefe

Usa `CalcularStockNecesarioTool` + `ReservarStockTool`.

---

#### Agente 7 — Compras

**SOUL:** "Negociador de compras."

**REGLA ABSOLUTA:**
> NUNCA compras sin aprobación explícita del Jefe (HITL).
> Tu trabajo es GENERAR la orden y esperar — no ejecutarla.
> La orden queda en `status="pendiente"` hasta que el Jefe apruebe.

**Factores de emergencia climática:**
- Hielo: +50% de la cantidad base
- Agua: +30%
- Bebidas: +20%

**Lógica determinista:** `_calcular_items_orden()` aplica factores. `_guardar_orden()` escribe en DB con `status="pendiente"`.

---

#### Agente 8 — Staffing

**SOUL:** "Organizador de equipos. Asigna el mejor equipo para cada evento."

**Reglas rígidas:**
- Ratio: 1 bartender cada 40 PAX (CEILING)
- Head: OBLIGATORIO si PAX > 100
- Priorizar `especialidad="premium"` para menú premium
- Mayor calificación primero
- NUNCA asignar bartender con `disponible=False`
- Marcar asignados como `disponible=False` en DB

**Lógica determinista:** `_seleccionar_bartenders()` ordena por `(especialidad_score, calificacion)` descendente. `_generar_hoja_de_ruta()` produce instrucciones de texto.

---

### Fase 3 — Cierre y Background (`cierre_crews.py`)

#### Agente 9 — Auditoría

**SOUL:** "Contador. Los números no mienten."

**Reglas rígidas:**
- `ganancia_neta = precio_cobrado - costo_real`
- `margen_pct = (ganancia_neta / precio_cobrado) × 100`
- Si `margen_pct < 10%`: `margen_critico = True` → HITL del Jefe
- Lección debe ser accionable (1-2 oraciones)
- NUNCA cerrar evento sin registrar auditoría

---

#### Agente 10 — Feedback y Nurturing

**SOUL:** "Embajador. Cuida la relación post-evento."

**Reglas rígidas:**
- `proxima_contacto` = mismo mes del año siguiente
  (usa `dateutil.relativedelta` para manejar años bisiestos)
- Descuento estándar: 10% para próximo evento
- NUNCA enviar mensaje genérico — personalizar con datos del evento

---

#### Agente 11 — Monitor de Precios (job background)

**SOUL:** "Cazador de ofertas. Actualiza precios semanalmente."

**Reglas rígidas:**
- Fase 6: precios vienen de `MOCK_PRECIOS_ACTUALIZADOS` (dict Python)
- Fase 7: reemplazar con scraping real
- Oferta = precio actual < `precio_base_referencia × 0.85` (ahorro > 15%)
- Alerta de subida = precio actual > `precio_base_referencia × 1.20`
- Siempre registrar en `historial_precios` ANTES de actualizar `precios_bebidas`

`max_iter=2` porque los cálculos son deterministas.

**Mock de precios actualizados (configurable):**
```python
MOCK_PRECIOS_ACTUALIZADOS = {
    "GIN-001":    {"precio_ars": 11_500, "fuente": "Carrefour Tucuman"},
    "GIN-002":    {"precio_ars": 27_500, "fuente": "Mayorista X"},
    "WHISKY-001": {"precio_ars":  6_800, "fuente": "Dia Tucuman"},
    "WHISKY-002": {"precio_ars": 24_000, "fuente": "Mayorista X"},
    "VODKA-001":  {"precio_ars":  7_500, "fuente": "Carrefour Tucuman"},
    "RON-001":    {"precio_ars": 17_000, "fuente": "Mayorista X"},
    "TEQUILA-001":{"precio_ars": 21_000, "fuente": "Mayorista X"},
}
```

---

## 09 — Capa 5: Flows (4 orquestadores)

### PreventaFlow

**Trigger:** `POST /bartenders/preventa`
**HITL:** Ninguno
**Tiempo estimado:** 30–60 segundos

```
cargar_input()
    ↓ @listen
agente_1_requerimientos()  → registra evento en DB → genera evento_id
    ↓ @listen
agente_2_clima()           → lee config_climatico → guarda factor_pct en estado
    ↓ @listen
agente_3_escandallo()      → llama EscandalloTool → guarda escandallo_final en estado
    ↓ @listen
agente_4_cotizacion()      → calcula 3 opciones → escribe en cotizaciones → COMPLETED
```

**Estado (PreventaState):**

| Campo | Tipo | Descripción |
|---|---|---|
| `fecha_evento` | str | Input |
| `provincia` | str | Input |
| `pax` | int | Input |
| `duracion_horas` | int | Input |
| `tipo_menu` | str | Input |
| `evento_id` | str | Generado por A1 |
| `factor_climatico_pct` | int | Calculado por A2 |
| `escandallo_final` | int | Calculado por A3 |
| `escandallo_desglose` | dict | Desglose por bloques de A3 |
| `cotizacion_id` | str | Generado por A4 |
| `opcion_basica/recomendada/premium` | int | Calculado por A4 |

**Validaciones en `validate_input()`:**
- Campos requeridos: `fecha_evento`, `provincia`, `pax`, `duracion_horas`, `tipo_menu`, `localidad`, `tipo_evento`
- `pax` entre 10 y 500
- `provincia` en `{Tucuman, Salta, Jujuy, Catamarca}`
- `tipo_menu` en `{basico, estandar, premium}`

---

### ReservaFlow

**Trigger:** `POST /bartenders/reserva`
**HITL:** Condicional (si falta stock)
**Input:** `evento_id`, `cotizacion_id`, `opcion_elegida`

```
cargar_evento()            → carga datos del evento desde DB
                           → registra opcion_elegida en cotizaciones
    ↓ @listen
agente_6_inventario()      → calcula stock necesario → intenta reservar
    SI alerta_faltante:
        request_approval("compra_emergencia_stock")
        → SUSPENDIDO (espera aprobación)
    SI no:
        ↓ continúa
agente_8_staffing()        → selecciona bartenders → genera hoja de ruta
                           → actualiza disponibilidad
                           → evento.status = "confirmado"
                           → COMPLETED
```

**`_on_approved()`:** Continúa con `agente_8_staffing()`.
**`_on_rejected()`:** Evento vuelve a `status="cotizado"`.

---

### AlertaClimaFlow

**Trigger:** APScheduler (T-7 días) o `POST /bartenders/alerta`
**HITL:** Siempre obligatorio si hay alerta roja
**Input:** `evento_id`

```
cargar_evento()             → valida que evento esté en status "confirmado"/"coordinado"
    ↓ @listen
agente_5_pronostico()       → verifica pronóstico real vs histórico
                            → guarda alerta_roja, desvio_pct en estado
    ↓ @listen
evaluar_alerta()            → router: SI no hay alerta → output_data → COMPLETED
                                     SI hay alerta → continúa
    ↓ @listen (solo si alerta_roja)
agente_7_orden_emergencia() → calcula items con factores de emergencia
                            → crea orden en DB con status="pendiente"
                            → request_approval("compra_emergencia_clima")
                            → SUSPENDIDO (espera aprobación del Jefe)
```

**Payload HITL que ve el Jefe:**
```json
{
  "evento_id":         "EVT-2026-001",
  "orden_id":          "OC-2026-XXX",
  "total_ars":         220000,
  "items":             [...],
  "desvio_pct":        26.9,
  "temp_historica":    26.0,
  "temp_pronosticada": 33.0,
  "tipo":              "compra_emergencia_clima"
}
```

**`_on_approved()`:** `ordenes_compra.status = "aprobada"`, `eventos.status = "coordinado"`.
**`_on_rejected()`:** `ordenes_compra.status = "rechazada"`. El evento sigue confirmado sin stock adicional.

---

### CierreFlow

**Trigger:** `POST /bartenders/cierre`
**HITL:** Condicional (si `margen_pct < 10%`)
**Input:** `evento_id`, `costo_real`, `mermas`, `compras_emergencia`, `desvio_climatico`, `rating` (opcional)

```
cargar_datos()             → carga precio_cobrado desde cotizaciones
                           → calcula ganancia_neta y margen_pct
    ↓ @listen
agente_9_auditoria()       → registra auditoría en DB
                           → evento.status = "ejecutado"
    SI margen_critico (< 10%):
        request_approval("margen_critico")
        → SUSPENDIDO
    SI no:
        ↓ continúa
agente_10_feedback()       → calcula proxima_contacto (mismo mes, año+1)
                           → actualiza eventos con proxima_contacto y rating
                           → evento.status = "cerrado"
                           → COMPLETED
```

**`_on_approved()`:** Ejecuta `_ejecutar_feedback()` — cierra el evento.
**`_on_rejected()`:** Evento queda en `status="ejecutado"` para revisión manual.

---

## 10 — Capa 6: API routes + APScheduler

### Endpoints (`src/api/routes/bartenders.py`)

Todos responden **202 Accepted** con `task_id`. El cliente hace polling con `GET /tasks/{task_id}`.

| Método | Path | Flow | Descripción |
|---|---|---|---|
| POST | `/bartenders/preventa` | PreventaFlow | Cotización automática |
| POST | `/bartenders/reserva` | ReservaFlow | Confirmar + reservar stock |
| POST | `/bartenders/alerta` | AlertaClimaFlow | Trigger manual de alerta |
| POST | `/bartenders/cierre` | CierreFlow | Auditoría post-evento |

Todos usan `Depends(verify_org_access)` — el org_id viene del middleware de auth
y se pasa al `FlowRegistry.create()`.

### APScheduler (`src/scheduler/bartenders_jobs.py`)

**Job 1: `check_upcoming_events_climate`**
- Cron: todos los días a las 8:00 AM (hora Argentina)
- `misfire_grace_time`: 3600 segundos
- Busca eventos con `status="confirmado"` en exactamente 7 días
- Dispara `AlertaClimaFlow` para cada uno
- Un error en un evento no detiene los demás

**Job 2: `update_prices_all_orgs`**
- Cron: todos los lunes a las 7:00 AM
- `misfire_grace_time`: 7200 segundos
- Busca orgs con bartenders en `bartenders_disponibles`
- Ejecuta `_actualizar_precios()` para cada org
- Deduplicar org_ids antes de ejecutar

### Wiring en `main.py`

Tres líneas a agregar (ver `registry_wiring.py` para el diff exacto):

```python
# 1. Imports
from src.flows.bartenders.registry_wiring import register_bartenders_flows
from src.scheduler.bartenders_jobs import scheduler
from src.api.routes.bartenders import router as bartenders_router

# 2. En lifespan startup:
register_bartenders_flows()
scheduler.start()

# 3. En lifespan shutdown:
scheduler.shutdown(wait=False)

# 4. Router:
app.include_router(bartenders_router)
```

### Registro de flows

```python
FlowRegistry.register("bartenders_preventa", PreventaFlow)
FlowRegistry.register("bartenders_reserva",  ReservaFlow)
FlowRegistry.register("bartenders_alerta",   AlertaClimaFlow)
FlowRegistry.register("bartenders_cierre",   CierreFlow)
```

---

## 11 — HITL: los 3 puntos de aprobación

### Resumen

| Flow | HITL | Cuándo | Payload clave |
|---|---|---|---|
| `ReservaFlow` | Condicional | Solo si `alerta_faltante=True` | items faltantes, tipo="compra_emergencia_stock" |
| `AlertaClimaFlow` | **Siempre** si hay alerta | Cuando `desvio_pct > 10%` | total_ars, desvio_pct, temps, items |
| `CierreFlow` | Condicional | Solo si `margen_pct < 10%` | margen_pct, ganancia_neta, precio_cobrado |

### Cómo funciona el HITL en FAP (Fases 1–4)

1. El flow llama `self.request_approval(description, payload)` — método heredado de `BaseFlow`
2. `BaseFlow` lanza `FlowSuspendedException` que corta el DAG de CrewAI
3. FAP crea fila en `pending_approvals` con `status="pending"`
4. FAP crea snapshot del estado del flow en `snapshots`
5. Supabase Realtime notifica el Dashboard → aparece card ámbar en Kanban
6. El Jefe hace click → aprueba o rechaza desde el Dashboard
7. Dashboard llama `POST /approvals/{task_id}` con la decisión
8. FAP restaura el snapshot y llama `flow._on_approved()` o `flow._on_rejected()`
9. El flow continúa desde el punto de reanudación

### Los métodos `_on_approved()` y `_on_rejected()` en cada flow

**ReservaFlow:**
- `_on_approved()`: llama `agente_8_staffing()` directamente
- `_on_rejected()`: evento vuelve a `status="cotizado"`

**AlertaClimaFlow:**
- `_on_approved()`: `ordenes_compra.status="aprobada"`, `eventos.status="coordinado"`
- `_on_rejected()`: `ordenes_compra.status="rechazada"`, evento sigue confirmado

**CierreFlow:**
- `_on_approved()`: llama `_ejecutar_feedback()` → evento se cierra
- `_on_rejected()`: evento queda en `status="ejecutado"` para revisión manual

---

## 12 — Flujo demo paso a paso

### Setup previo (una vez)

```bash
# 1. SQL en Supabase (en orden):
009_bartenders_config.sql
010_bartenders_operativo.sql
011_bartenders_rls.sql
012_bartenders_seed_config.sql
013_bartenders_rpc_inventario.sql

# 2. Crear org en FAP (si no existe)
# 3. Seed con datos reales:
python scripts/seed_bartenders_noa.py --org-name "Bartenders NOA"

# 4. Arrancar servidor:
uvicorn src.api.main:app --reload
```

### Demo (15 minutos)

**Paso 1 (2 min): Cotización automática**

```bash
POST /bartenders/preventa
{
  "fecha_evento": "2026-01-15",
  "provincia": "Tucuman",
  "localidad": "San Miguel de Tucumán",
  "tipo_evento": "boda",
  "pax": 150,
  "duracion_horas": 5,
  "tipo_menu": "premium"
}
# → 202 { task_id: "..." }
```

- Mostrar Kanban: task pasa de `pending` → `running`
- 4 agentes encadenados — logs visibles en tiempo real
- `GET /tasks/{task_id}` → `status: completed`
- Output muestra las 3 opciones de precio

**Paso 2 (1 min): Expandir el escandallo**

Desde el Dashboard, click en la task completada → expandir output:
- B1 productos: ~ARS 966.000
- B2 equipamiento: ARS 6.250
- B3 personal: ARS 1.520.000 (4 bartenders + 1 head × 8h)
- B4 logística: ARS 51.000
- Ajuste climático +20%: ~ARS 194.450
- **Escandallo: ~ARS 2.956.716**
- Recomendada: **ARS 5.376.757**

**Paso 3 (2 min): Confirmar reserva**

```bash
POST /bartenders/reserva
{
  "evento_id": "EVT-2026-001",
  "cotizacion_id": "COT-2026-XXX",
  "opcion_elegida": "recomendada"
}
```

- Mostrar inventario en Dashboard → `stock_reservado` sube en tiempo real
- Bartenders asignados → `disponible=False` en `bartenders_disponibles`

**Paso 4 (3 min): ALERTA ROJA climática**

```bash
POST /bartenders/alerta
{ "evento_id": "EVT-2026-001" }
```

- `MOCK_FORECAST_OVERRIDE["EVT-2026-001"] = 33.0` → desvío +26.9% → ALERTA ROJA
- Kanban: card ámbar "ALERTA ROJA — Compra emergencia ARS 220.000"
- Ir al Centro de Aprobaciones → ver payload completo
- **APROBAR** → task reanuda → `ordenes_compra.status="aprobada"` visible en Dashboard

**Paso 5 (2 min): Rechazar una segunda compra**

- Disparar otra alerta con evento diferente
- **RECHAZAR** → task `rejected` → log muestra trail completo

**Paso 6 (2 min): Cierre y auditoría**

```bash
POST /bartenders/cierre
{
  "evento_id": "EVT-2026-001",
  "costo_real": 4608458,
  "mermas": 250000,
  "compras_emergencia": 220000,
  "desvio_climatico": "+7°C vs histórico enero",
  "rating": 5
}
```

- Agente 9: margen 14.3% > 10% → no hay HITL → auditoría registrada
- Agente 10: próximo contacto = enero 2027
- Evento → `status="cerrado"`

**Paso 7 (2 min): Resumen en Dashboard**

- Overview: tasks completadas, ARS aprobados, margen promedio
- Ver auditoría: ganancia ARS 768.299, lección aprendida
- Ver inventario: cambios de stock reflejados

---

## 13 — Transición a Fase 7

### Qué NO cambia en Fase 7

- Los 11 agentes (crews) — ninguna línea de código
- Las 3 tools — ninguna línea de código
- Los 4 flows — ninguna línea de código
- Las 12 tablas de Supabase — siguen existiendo como caché
- Las RPCs de inventario — siguen siendo atómicas

### Qué cambia en Fase 7

**1. El conector** — una clase Python reemplaza a `SupabaseMockConnector`:

```python
class GoogleSheetsConnector(BaseDataConnector):
    def read(self, table, filters=None):
        rows = sheets_api.spreadsheets().values().get(
            spreadsheetId=self.sheet_ids[table], range="Datos"
        ).execute().get("values", [])
        headers = rows[1]  # fila 2 = headers
        return [dict(zip(headers, row)) for row in rows[2:]]
    # write(), update(), get_config() similarmente
```

**2. `_fetch_real_forecast()` en `PronosticoRealTool`** — una función Python:

```python
def _fetch_real_forecast(self, evento_id, mes):
    # Fase 6: return MOCK_FORECAST_OVERRIDE.get(evento_id, TEMP_HISTORICA_NOA[mes])
    # Fase 7:
    response = requests.get(f"https://api.smn.gob.ar/v1/forecast/{self.provincia}")
    return response.json()["temperatura_max"]
```

**3. `MOCK_PRECIOS_ACTUALIZADOS` en `cierre_crews.py`** — reemplazar con scraping:

```python
def _fetch_precios_mercado():
    # Carrefour, Día, Mayorista X, MercadoLibre
    # Retorna dict { producto_id: { precio_ars, fuente } }
```

**4. Supabase como caché** — sincronización bidireccional:
- Tablas de maestros (bartenders, precios) → sync desde Sheets hacia Supabase
- Tablas operativas (eventos, cotizaciones) → FAP es maestro, Sheets es reflejo

---

## 14 — Orden de implementación

| # | Archivo | Depende de | Tiempo est. |
|---|---|---|---|
| 1 | `009_bartenders_config.sql` | — | 30 min |
| 2 | `010_bartenders_operativo.sql` | 1 | 1 h |
| 3 | `011_bartenders_rls.sql` | 2 | 15 min |
| 4 | `012_bartenders_seed_config.sql` | 1 | 15 min |
| 5 | `013_bartenders_rpc_inventario.sql` | 2 | 30 min |
| 6 | `seed_bartenders_noa.py` | 1–5 + org creada | 30 min |
| 7 | `base_connector.py` | — | 30 min |
| 8 | `supabase_connector.py` | 7 | 1 h |
| 9 | `test_supabase_connector.py` | 8 | 1 h |
| 10 | `escandallo_tool.py` | 8 | 2 h |
| 11 | `clima_tool.py` | 8 | 1 h |
| 12 | `inventario_tool.py` | 8 | 1 h |
| 13 | `test_bartenders_tools.py` | 10–12 | 2 h |
| 14 | `preventa_crews.py` | 10, 11 | 2 h |
| 15 | `reserva_crews.py` | 11, 12 | 3 h |
| 16 | `cierre_crews.py` | 8 | 2 h |
| 17 | `test_bartenders_crews.py` | 14–16 | 2 h |
| 18 | `preventa_flow.py` | 14 | 1 h |
| 19 | `reserva_flow.py` | 15 | 2 h |
| 20 | `alerta_flow.py` | 11, 15 | 2 h |
| 21 | `cierre_flow.py` | 16 | 2 h |
| 22 | `test_bartenders_flows.py` | 18–21 | 2 h |
| 23 | `bartenders_routes.py` | 18–21 | 1 h |
| 24 | `bartenders_jobs.py` | 20, 16 | 1 h |
| 25 | `registry_wiring.py` | 18–21 | 30 min |
| 26 | Aplicar diff a `main.py` | 23–25 | 15 min |
| 27 | Tests end-to-end manuales | todo | 2 h |

**Total estimado: ~35–40 horas**

---

## 15 — Criterio de éxito

### Técnico

- `pytest tests/unit/` pasa sin errores (≥ 100 tests)
- `POST /bartenders/preventa` con datos de EVT-2026-001 produce escandallo entre ARS 2.800.000 y ARS 3.100.000
- `POST /bartenders/alerta` con EVT-2026-001 crea fila en `pending_approvals` visible en Dashboard
- `connector.reserve_stock("GIN-001", 5)` reduce `stock_disponible` en DB
- APScheduler arranca sin bloquear el event loop de FastAPI
- `SupabaseMockConnector.write("config_consumo_pax", {...})` lanza `ValueError`

### Demo

- Demo completa de 15 minutos sin errores en laptop
- Una compra de emergencia se aprueba y otra se rechaza — ambas visibles en Kanban
- El inventario se actualiza en tiempo real al reservar stock
- La auditoría cierra el ciclo con ganancia neta y lección aprendida

### Fuera de scope para Fase 6

- Google Sheets API real (Fase 7)
- Scraping de precios de Carrefour, Día, Mercado Libre (Fase 7)
- API del SMN para pronóstico real (Fase 7)
- Notificaciones WhatsApp/email a bartenders (Fase 7)
- PDFs de cotizaciones y contratos (Fase 7)
- Publicación de Bartenders NOA como template en Marketplace (Fase 7)

---

## 16 — Inventario de archivos

### SQL (6 archivos)

| Archivo | Descripción |
|---|---|
| `sql/009_bartenders_config.sql` | 4 tablas de configuración sin org_id |
| `sql/010_bartenders_operativo.sql` | 8 tablas operativas con org_id, índices y trigger |
| `sql/011_bartenders_rls.sql` | RLS en todas las tablas operativas |
| `sql/012_bartenders_seed_config.sql` | Datos reales: consumo, márgenes, climático, equipamiento |
| `sql/013_bartenders_rpc_inventario.sql` | RPCs atómicas: reserve/release inventory |

### Scripts (1 archivo)

| Archivo | Descripción |
|---|---|
| `scripts/seed_bartenders_noa.py` | Inserta datos operativos con org_id real (12 bartenders, 7 bebidas, 9 items, datos demo) |

### Python — Conector (2 archivos)

| Archivo | Descripción |
|---|---|
| `src/connectors/base_connector.py` | Interfaz abstracta (6 métodos: 4 abstractos + 2 helpers) |
| `src/connectors/supabase_connector.py` | Implementación Fase 6 sobre Supabase |

### Python — Tools (3 archivos)

| Archivo | Tools | Descripción |
|---|---|---|
| `src/tools/bartenders/escandallo_tool.py` | `EscandalloTool` | Cálculo determinista 4 bloques |
| `src/tools/bartenders/clima_tool.py` | `FactorClimaticoTool`, `PronosticoRealTool` | Factor histórico + mock pronóstico real |
| `src/tools/bartenders/inventario_tool.py` | `CalcularStockNecesarioTool`, `ReservarStockTool`, `LiberarStockTool` | Gestión de stock |

### Python — Crews (3 archivos, 11 agentes)

| Archivo | Agentes |
|---|---|
| `src/crews/bartenders/preventa_crews.py` | A1 Requerimientos, A2 Meteorológico, A3 Calculador, A4 Presupuestador |
| `src/crews/bartenders/reserva_crews.py` | A5 Monitor Clima, A6 Inventario, A7 Compras, A8 Staffing |
| `src/crews/bartenders/cierre_crews.py` | A9 Auditoría, A10 Feedback, A11 Monitor Precios |

### Python — Flows (4 archivos)

| Archivo | Flow | HITL |
|---|---|---|
| `src/flows/bartenders/preventa_flow.py` | PreventaFlow (A1→A2→A3→A4) | Ninguno |
| `src/flows/bartenders/reserva_flow.py` | ReservaFlow (A6→A8) | Condicional: falta stock |
| `src/flows/bartenders/alerta_flow.py` | AlertaClimaFlow (A5→A7) | Siempre: toda compra |
| `src/flows/bartenders/cierre_flow.py` | CierreFlow (A9→A10) | Condicional: margen < 10% |

### Python — API + Scheduler + Wiring (3 archivos)

| Archivo | Descripción |
|---|---|
| `src/api/routes/bartenders.py` | 4 endpoints POST (202 + task_id) |
| `src/scheduler/bartenders_jobs.py` | 2 jobs: alerta diaria 8AM + precios lunes 7AM |
| `src/flows/bartenders/registry_wiring.py` | Registro en FlowRegistry + diff de main.py |

### Tests (4 archivos, ~100 tests)

| Archivo | Tests | Qué cubre |
|---|---|---|
| `tests/unit/test_supabase_connector.py` | 18 | read, write, update, get_config, reserve_stock, helpers |
| `tests/unit/test_bartenders_tools.py` | 28 | EscandalloTool (17), ClimaTool (6), InventarioTool (5) |
| `tests/unit/test_bartenders_crews.py` | 24 | Cálculo de opciones, registro, selección bartenders, auditoría, precios |
| `tests/integration/test_bartenders_flows.py` | 16 | validate_input, _on_approved, _on_rejected para los 4 flows |

---

*FluxAgent Pro — FAP · Fase 6 · Bartenders NOA · Especificación v1.0*
*Generado: Abril 2026*
