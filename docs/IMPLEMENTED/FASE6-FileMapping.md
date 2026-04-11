# Fase 6 — Mapping de Archivos por ZIP

> Correspondencia entre los ZIPs entregados y los archivos de la especificación técnica.
> Cada ZIP corresponde a una capa de arquitectura del sistema.

---

## Capa 1. Los SQL.zip

Migraciones SQL que deben ejecutarse en Supabase **en este orden exacto**.

| Archivo en ZIP | Ruta en proyecto | Ejecutar en |
|---|---|---|
| `009_bartenders_config.sql` | `sql/009_bartenders_config.sql` | Supabase SQL Editor |
| `010_bartenders_operativo.sql` | `sql/010_bartenders_operativo.sql` | Supabase SQL Editor |
| `011_bartenders_rls.sql` | `sql/011_bartenders_rls.sql` | Supabase SQL Editor |
| `012_bartenders_seed_config.sql` | `sql/012_bartenders_seed_config.sql` | Supabase SQL Editor |
| `013_bartenders_rpc_inventario.sql` | `sql/013_bartenders_rpc_inventario.sql` | Supabase SQL Editor |
| `seed_bartenders_noa.py` | `scripts/seed_bartenders_noa.py` | Terminal (Python) |

### Orden de ejecución obligatorio

```
1. 009_bartenders_config.sql       → crea config_consumo_pax, config_margenes,
                                     config_climatico, equipamiento_amortizacion
2. 010_bartenders_operativo.sql    → crea las 8 tablas operativas con org_id,
                                     índices, trigger updated_at
3. 011_bartenders_rls.sql          → activa RLS en las 8 tablas operativas
4. 012_bartenders_seed_config.sql  → inserta datos de config (sin org_id):
                                     3 tipos de menú, 3 márgenes, 12 factores
                                     climáticos, 4 ítems de equipamiento
5. 013_bartenders_rpc_inventario.sql → crea RPCs atómicas reserve/release
6. seed_bartenders_noa.py          → insertar DESPUÉS de crear la org en FAP:
                                     python scripts/seed_bartenders_noa.py
                                     --org-name "Bartenders NOA"
```

### Qué contiene cada SQL

| Archivo | Tablas / Objetos creados |
|---|---|
| `009` | `config_consumo_pax`, `config_margenes`, `config_climatico`, `equipamiento_amortizacion` |
| `010` | `bartenders_disponibles`, `precios_bebidas`, `inventario`, `eventos`, `cotizaciones`, `ordenes_compra`, `auditorias`, `historial_precios` + índices + trigger |
| `011` | 8 políticas RLS (una por tabla operativa) |
| `012` | 3 filas en `config_consumo_pax`, 3 en `config_margenes`, 12 en `config_climatico`, 4 en `equipamiento_amortizacion` |
| `013` | Funciones `reserve_inventory_item()` y `release_inventory_item()` con `FOR UPDATE` |
| `seed_bartenders_noa.py` | 12 bartenders, 7 bebidas, 9 items de inventario, datos demo EVT-2026-001 |

---

## Capa 2. Conector (abstracción).zip

La única capa que cambia entre Fase 6 (Supabase) y Fase 7 (Google Sheets).
Los agentes nunca importan estas clases directamente — reciben el conector por inyección.

| Archivo en ZIP | Ruta en proyecto | Qué es |
|---|---|---|
| `base_connector.py` | `src/connectors/base_connector.py` | Interfaz abstracta |
| `supabase_connector.py` | `src/connectors/supabase_connector.py` | Implementación Fase 6 |
| `test_supabase_connector.py` | `tests/unit/test_supabase_connector.py` | 18 tests unitarios |

### Métodos de la interfaz

| Método | Tablas que acepta | Descripción |
|---|---|---|
| `read(table, filters)` | Operativas | Lectura con RLS de tenant |
| `write(table, data)` | Operativas | Insert. Inyecta `org_id` automático |
| `update(table, pk, data)` | Operativas | Update por PK. RLS garantiza tenant |
| `get_config(table, filters)` | Configuración | Lectura sin RLS (service_role) |
| `read_one(table, filters)` | Operativas | Helper: primer resultado o None |
| `get_config_one(table, filters)` | Configuración | Helper: primer resultado o None |
| `reserve_stock(item_id, cantidad)` | `inventario` vía RPC | Atómico con FOR UPDATE |
| `release_stock(item_id, cantidad)` | `inventario` vía RPC | Libera reserva |

### Tablas operativas vs tablas de configuración

```
OPERATIVAS (usar read/write/update):
    bartenders_disponibles, precios_bebidas, inventario,
    eventos, cotizaciones, ordenes_compra,
    auditorias, historial_precios

CONFIGURACIÓN (usar get_config):
    config_consumo_pax, config_margenes,
    config_climatico, equipamiento_amortizacion
```

### Qué cambia en Fase 7

Solo se reemplaza `supabase_connector.py` por `google_sheets_connector.py`.
`base_connector.py` no cambia. Los agentes no cambian.

---

## Capa 3. Tools.zip

Herramientas deterministas: mismos inputs → mismo output. Sin LLM en los cálculos.

| Archivo en ZIP | Ruta en proyecto | Tools que contiene |
|---|---|---|
| `escandallo_tool.py` | `src/tools/bartenders/escandallo_tool.py` | `EscandalloTool` |
| `clima_tool.py` | `src/tools/bartenders/clima_tool.py` | `FactorClimaticoTool`, `PronosticoRealTool` |
| `inventario_tool.py` | `src/tools/bartenders/inventario_tool.py` | `CalcularStockNecesarioTool`, `ReservarStockTool`, `LiberarStockTool` |
| `test_bartenders_tools.py` | `tests/unit/test_bartenders_tools.py` | 28 tests unitarios |

### Detalle de cada tool

| Tool (nombre CrewAI) | Usada por | HITL | Descripción |
|---|---|---|---|
| `calcular_escandallo` | Agente 3 | No | Cálculo de 4 bloques + ajustes |
| `obtener_factor_climatico` | Agente 2 | No | Factor histórico de `config_climatico` |
| `verificar_pronostico_real` | Agente 5 | No — pero puede disparar HITL en el flow | Pronóstico mock vs histórico |
| `calcular_stock_necesario` | Agente 6 | No | Cantidades con buffer 10% |
| `reservar_stock_evento` | Agente 6 | Condicional | Reserva atómica vía RPC |
| `liberar_stock_evento` | — (cancelación) | No | Libera reservas |

### Fórmula del escandallo (resumen)

```
B1 = bebidas_alc + bebidas_no_alc + hielo + garnish + desechables
B2 = Σ amortizacion_por_evento (equipamiento activo)  → ARS 6.250 fijo
B3 = (n_bartenders × 35.000 + head × 50.000 + asistente × 28.000) × horas_totales
     horas_totales = duracion_horas + 3   ← setup/cierre siempre
B4 = 51.000 (Tucumán) | km×2×600+5.000 (interprovincial)

Subtotal      = B1 + B2 + B3 + B4
Ajuste clima  = (B1 + B2) × factor_climatico_pct / 100
Base ajustada = Subtotal + Ajuste clima
Mermas        = Base ajustada × 0.05
Imprevistos   = Base ajustada × 0.03
Escandallo    = Base ajustada + Mermas + Imprevistos
```

---

## Capa 4. Los crews.zip

Un crew por agente. La lógica determinista está en funciones `_privadas`,
separada del LLM (Agent + Task). Los tests cubren solo las funciones `_privadas`.

| Archivo en ZIP | Ruta en proyecto | Agentes |
|---|---|---|
| `preventa_crews.py` | `src/crews/bartenders/preventa_crews.py` | A1, A2, A3, A4 |
| `reserva_crews.py` | `src/crews/bartenders/reserva_crews.py` | A5, A6, A7, A8 |
| `cierre_crews.py` | `src/crews/bartenders/cierre_crews.py` | A9, A10, A11 |
| `test_bartenders_crews.py` | `tests/unit/test_bartenders_crews.py` | 24 tests unitarios |

### Los 11 agentes — referencia rápida

| # | Nombre | Archivo | SOUL en una línea | max_iter |
|---|---|---|---|---|
| A1 | Requerimientos | `preventa_crews.py` | Captura datos con precisión quirúrgica | 3 |
| A2 | Meteorológico Histórico | `preventa_crews.py` | Calcula factor climático desde tabla histórica | 3 |
| A3 | Calculador | `preventa_crews.py` | Escandallo matemático, cada número tiene fuente | 2 |
| A4 | Presupuestador | `preventa_crews.py` | 3 opciones con márgenes exactos 40/45/50% | 3 |
| A5 | Monitor Climático Real | `reserva_crews.py` | Alerta si desvío real > 10% vs histórico | 2 |
| A6 | Inventario | `reserva_crews.py` | Reserva stock físico, nunca más de lo disponible | 3 |
| A7 | Compras | `reserva_crews.py` | Genera orden pendiente — NUNCA compra sin HITL | 3 |
| A8 | Staffing | `reserva_crews.py` | Asigna equipo óptimo por calificación y especialidad | 3 |
| A9 | Auditoría | `cierre_crews.py` | Calcula rentabilidad real y extrae lección | 3 |
| A10 | Feedback | `cierre_crews.py` | Cierra relación con cliente, próximo contacto año+1 | 3 |
| A11 | Monitor Precios | `cierre_crews.py` | Actualiza precios semanalmente (mock en Fase 6) | 2 |

### Reglas invariantes de todos los agentes

```python
allow_delegation = False   # nunca delegan a otro agente
max_iter ≤ 3               # A3 y A11 usan max_iter=2 (cálculo determinista)
output_pydantic = <Model>  # salida tipada y validada en todos
```

### Funciones deterministas por archivo (testeable sin LLM)

**`preventa_crews.py`:**
- `_registrar_evento(connector, data)` → escribe evento en DB
- `_calcular_opciones(escandallo)` → `{basica, recomendada, premium}`
- `_guardar_cotizacion(connector, ...)` → escribe cotización, actualiza evento

**`reserva_crews.py`:**
- `_calcular_items_orden(connector, motivo, items)` → aplica factores de emergencia
- `_seleccionar_bartenders(connector, pax, tipo_menu)` → ordena y selecciona
- `_generar_hoja_de_ruta(asignados, ...)` → texto de instrucciones
- `_guardar_orden(connector, ...)` → escribe orden con status="pendiente"

**`cierre_crews.py`:**
- `_guardar_auditoria(connector, ...)` → escribe auditoría en DB
- `_actualizar_precios(connector)` → actualiza precios desde mock

---

## Capa 5. Los flows.zip

Los flows orquestan los crews con `@start` / `@listen`.
Heredan de `BaseFlow` (Fase 1) — usan `request_approval()`, `FlowSuspendedException`, `EventStore`.

| Archivo en ZIP | Ruta en proyecto | Flow | HITL |
|---|---|---|---|
| `preventa_flow.py` | `src/flows/bartenders/preventa_flow.py` | PreventaFlow | ❌ Ninguno |
| `reserva_flow.py` | `src/flows/bartenders/reserva_flow.py` | ReservaFlow | ⚠️ Condicional |
| `alerta_flow.py` | `src/flows/bartenders/alerta_flow.py` | AlertaClimaFlow | ✅ Siempre |
| `cierre_flow.py` | `src/flows/bartenders/cierre_flow.py` | CierreFlow | ⚠️ Condicional |
| `test_bartenders_flows.py` | `tests/integration/test_bartenders_flows.py` | Todos | 16 tests |

### Secuencias de cada flow

**PreventaFlow** (sin HITL):
```
cargar_input → A1_requerimientos → A2_clima → A3_escandallo → A4_cotizacion → COMPLETED
```

**ReservaFlow** (HITL si falta stock):
```
cargar_evento → A6_inventario ──────────────────────────────→ A8_staffing → COMPLETED
                     └─ SI falta stock → request_approval → SUSPENDIDO
                                              └─ aprobado  → A8_staffing → COMPLETED
                                              └─ rechazado → evento="cotizado" → COMPLETED
```

**AlertaClimaFlow** (HITL siempre si hay alerta):
```
cargar_evento → A5_pronostico → evaluar_alerta ──────────────────────────────→ COMPLETED
                                      └─ SI alerta → A7_orden → request_approval → SUSPENDIDO
                                                                    └─ aprobado  → orden="aprobada" → COMPLETED
                                                                    └─ rechazado → orden="rechazada" → COMPLETED
```

**CierreFlow** (HITL si margen < 10%):
```
cargar_datos → A9_auditoria ────────────────────────────────→ A10_feedback → COMPLETED
                    └─ SI margen_critico → request_approval → SUSPENDIDO
                                              └─ aprobado  → A10_feedback → COMPLETED
                                              └─ rechazado → evento="ejecutado" → COMPLETED
```

### Estados Pydantic por flow

| Flow | State class | Campos propios destacados |
|---|---|---|
| PreventaFlow | `PreventaState` | `evento_id`, `factor_climatico_pct`, `escandallo_final`, `escandallo_desglose`, `cotizacion_id`, `opcion_basica/recomendada/premium` |
| ReservaFlow | `ReservaState` | `opcion_elegida`, `stock_reservado`, `items_a_comprar`, `bartenders_ids`, `hoja_de_ruta` |
| AlertaClimaFlow | `AlertaState` | `alerta_roja`, `desvio_pct`, `temp_historica`, `temp_pronosticada`, `orden_id`, `total_compra` |
| CierreFlow | `CierreState` | `costo_real`, `mermas`, `compras_emergencia`, `precio_cobrado`, `ganancia_neta`, `margen_pct`, `margen_critico`, `auditoria_id` |

---

## Capa 6. API routes y APScheduler.zip

El punto de entrada externo del sistema. Todo lo demás corre en background.

| Archivo en ZIP | Ruta en proyecto | Descripción |
|---|---|---|
| `bartenders_routes.py` | `src/api/routes/bartenders.py` | 4 endpoints POST → 202 |
| `bartenders_jobs.py` | `src/scheduler/bartenders_jobs.py` | 2 jobs automáticos |
| `registry_wiring.py` | `src/flows/bartenders/registry_wiring.py` | Registro + diff de `main.py` |
| `test_bartenders_routes.py` | `tests/unit/test_bartenders_routes.py` | 14 tests |

### Los 4 endpoints

| Endpoint | Flow que dispara | Input requerido | HITL posible |
|---|---|---|---|
| `POST /bartenders/preventa` | PreventaFlow | `fecha_evento`, `provincia`, `pax`, `duracion_horas`, `tipo_menu`, `localidad`, `tipo_evento` | No |
| `POST /bartenders/reserva` | ReservaFlow | `evento_id`, `cotizacion_id`, `opcion_elegida` | Sí (falta stock) |
| `POST /bartenders/alerta` | AlertaClimaFlow | `evento_id` | Sí (desvío > 10%) |
| `POST /bartenders/cierre` | CierreFlow | `evento_id`, `costo_real` | Sí (margen < 10%) |

Todos responden **202 Accepted** inmediatamente:
```json
{
  "task_id":   "...",
  "status":    "pending",
  "flow_type": "bartenders_preventa",
  "mensaje":   "..."
}
```
El cliente hace polling con `GET /tasks/{task_id}` (endpoint existente de Fases 1–4).

### Los 2 jobs del scheduler

| Job | Cron | Qué hace |
|---|---|---|
| `check_upcoming_events_climate` | Diario 8:00 AM | Busca eventos con `status="confirmado"` en 7 días → dispara AlertaClimaFlow |
| `update_prices_all_orgs` | Lunes 7:00 AM | Ejecuta Agente 11 para todas las orgs con bartenders |

### Diff de `main.py` (3 pasos)

```python
# PASO 1: Agregar imports
from src.flows.bartenders.registry_wiring import register_bartenders_flows
from src.scheduler.bartenders_jobs import scheduler
from src.api.routes.bartenders import router as bartenders_router

# PASO 2: En lifespan startup (después de recover_orphaned_tasks)
register_bartenders_flows()
scheduler.start()

# PASO 3: En lifespan shutdown
scheduler.shutdown(wait=False)

# PASO 4: Registrar router
app.include_router(bartenders_router)
```

---

## hojas de calculo.zip

Fuente original de todos los datos seed. No se usan en runtime — solo como referencia
y para regenerar el seed si es necesario.

| Archivo en ZIP | Tabla Supabase correspondiente | Usado en |
|---|---|---|
| `config_consumo_pax.xlsx` | `config_consumo_pax` | `012_bartenders_seed_config.sql` |
| `config_margenes.xlsx` | `config_margenes`, `config_climatico` | `012_bartenders_seed_config.sql` |
| `equipamiento_amortizacion.xlsx` | `equipamiento_amortizacion` | `012_bartenders_seed_config.sql` |
| `bartenders_disponibles.xlsx` | `bartenders_disponibles` | `seed_bartenders_noa.py` |
| `precios_bebidas.xlsx` | `precios_bebidas` | `seed_bartenders_noa.py` |
| `inventario.xlsx` | `inventario` | `seed_bartenders_noa.py` |
| `eventos.xlsx` | `eventos` (datos demo) | `seed_bartenders_noa.py` |
| `cotizaciones.xlsx` | `cotizaciones` (datos demo) | `seed_bartenders_noa.py` |
| `ordenes_compra.xlsx` | `ordenes_compra` (datos demo) | `seed_bartenders_noa.py` |
| `auditorias.xlsx` | `auditorias` (datos demo) | `seed_bartenders_noa.py` |
| `historial_precios.xlsx` | `historial_precios` | `seed_bartenders_noa.py` |

### Relación hojas → tablas Supabase

```
hojas de calculo.zip                    Supabase (Fase 6)
─────────────────────────────────────   ──────────────────────────────────
config_consumo_pax.xlsx        →        config_consumo_pax          (sin org_id)
config_margenes.xlsx [Márgenes] →       config_margenes             (sin org_id)
config_margenes.xlsx [Climático] →      config_climatico            (sin org_id)
equipamiento_amortizacion.xlsx →        equipamiento_amortizacion   (sin org_id)
bartenders_disponibles.xlsx   →         bartenders_disponibles      (con org_id)
precios_bebidas.xlsx          →         precios_bebidas             (con org_id)
inventario.xlsx               →         inventario                  (con org_id)
eventos.xlsx                  →         eventos                     (con org_id)
cotizaciones.xlsx             →         cotizaciones                (con org_id)
ordenes_compra.xlsx           →         ordenes_compra              (con org_id)
auditorias.xlsx               →         auditorias                  (con org_id)
historial_precios.xlsx        →         historial_precios           (con org_id)
```

### En Fase 7

Las hojas de cálculo pasarán de ser **fuente de seed** a ser **fuente de verdad en producción**.
Los agentes leerán y escribirán directamente en los Google Sheets reales
a través del `GoogleSheetsConnector` que reemplaza al `SupabaseMockConnector`.
Supabase quedará como caché de lectura sincronizado.

---

## Resumen global

| ZIP | Archivos | Tests | Depende de |
|---|---|---|---|
| Capa 1. Los SQL | 6 | — | — |
| Capa 2. Conector | 3 (incl. tests) | 18 | Capa 1 |
| Capa 3. Tools | 4 (incl. tests) | 28 | Capa 2 |
| Capa 4. Los crews | 4 (incl. tests) | 24 | Capa 3 |
| Capa 5. Los flows | 5 (incl. tests) | 16 | Capa 4 |
| Capa 6. API + Scheduler | 4 (incl. tests) | 14 | Capa 5 |
| hojas de calculo | 11 xlsx | — | (fuente de Capa 1) |
| **Total** | **37 archivos** | **100 tests** | |

---

*FluxAgent Pro — FAP · Fase 6 · Mapping de Archivos v1.0*
*Generado: Abril 2026*
