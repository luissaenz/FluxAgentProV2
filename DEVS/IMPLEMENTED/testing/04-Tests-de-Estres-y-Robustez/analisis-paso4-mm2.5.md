# ANÁLISIS — Paso 4: Estrés y Condiciones de Borde
**Agente:** mm2.5

---

## §0 VERIFICACIÓN CONTRA CÓDIGO FUENTE

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | `ToolRegistry.get()` existe | grep `src/tools/registry.py` | ✅ | línea 75 |
| 2 | `MCPPool.get_tools()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 77 |
| 3 | `MCPPool.reset()` existe | grep `src/tools/mcp_pool.py` | ✅ | línea 210 |
| 4 | `sanitize_output()` existe | grep `src/mcp/sanitizer.py` | ✅ | línea 28 |
| 5 | `FlowRegistry.register()` existe | grep `src/flows/registry.py` | ✅ | línea 47 |
| 6 | `WorkflowDefinition` valida flow_type | grep `src/flows/workflow_definition.py` | ✅ | línea 73-83 |
| 7 | `DynamicWorkflow` existe | grep `src/flows/dynamic_flow.py` | ✅ | línea 1+ |
| 8 | Fixture `mock_mcp_pool` en conftest | grep `tests/conftest.py` | ✅ | línea 304-316 |

**Discrepancias:** Ninguna. Código existe y coincide con plan.

---

## 1 ANÁLISIS DE DATOS

### 1.1 Tablas y Schema
N/A — Paso 4 no toca DB. Tests en memoria con mocks.

### 1.2 Integridad Referencial
N/A

### 1.3 RLS Policies
N/A

### 1.4 Índices
N/A

### 1.5 Tipos de Datos
- ✅ `WorkflowDefinition.flow_type` validado por Pydantic (línea 73-83): debe ser snake_case
- ✅ `StepDefinition.approval_threshold` existe pero **NO se usa** en `_run_crew()`. DOCUMENTAR como gap.

---

## 2 ANÁLISIS DE CÓDIGO

### 2.1 Funciones/Clases Creadas

| Función | Firma | Responsabilidad |
|---|---|---|
| `ToolRegistry.get()` | `(name: str, org_id: str=None) → Type` | Lookup de herramientas, 4 estrategias |
| `MCPPool.get_tools()` | `(org_id, server_name, timeout=30, max_retries=3) → list` | Conexión MCP con circuit breaker |
| `MCPPool.reset()` | `() → None` | Reset singleton para tests |
| `sanitize_output()` | `(data: Any) → Any` | Redacta secretos en output |
| `FlowRegistry.register()` | `(name, depends_on, category, description) → decorator` | Registro de flujos con metadatos |
| `WorkflowDefinition` | Pydantic model | Validación de workflows |

### 2.2 Patrones

- ✅ `ToolRegistry` sigue patrón singleton con `_tools: Dict[str, Type]`
- ✅ `MCPPool` usa circuit breaker con `_health` (dict defaultdict)
- ✅ `FlowRegistry` usa `_flows` como dict simple → registro duplicado sobrescribe (S4.4 confirmado)
- ✅ `sanitize_output` recursivo para dict/list

### 2.3 Modularidad

- ✅ `ToolRegistry._load_from_filesystem()`: filesystem fallback condicionado a `fap_strict_mode`
- ✅ `MCPPool.get_tools()`: retry con tenacity + circuit breaker
- ✅ `sanitize_output()`: manejo de tipos primitivos

### 2.4 Imports y Dependencias

```python
# registry.py
from src.config import get_settings  # línea 101

# mcp_pool.py
from ..db.session import get_service_client
from ..db.vault import get_secret_async
from tenacity import retry, stop_after_attempt, wait_exponential

# sanitizer.py
import re
from typing import Any

# registry.py (flows)
from typing import Any, Callable, Dict, List, Optional, Type
import re
from src.flows.dynamic_flow import DynamicWorkflow
from src.db.session import get_tenant_client
from src.services.security_guard import SecurityGuard
```

### 2.5 Calidad

- ✅ `sanitize_output`: try/except wrapper con fallback seguro
- ✅ `MCPPool._is_circuit_open`: lógica simple, verificable
- ⚠️ `WorkflowDefinition` no usa `approval_threshold` — campo morto

---

## 3 ANÁLISIS DE BACKEND

### 3.1 Endpoints
N/A — Paso 4 no toca API routes.

### 3.2 Middleware
N/A

### 3.3 Flujos de Datos
N/A

### 3.4 Contratos
N/A

### 3.5 Error Handling

| Escenario | Comportamiento Actual |
|---|---|
| `ToolRegistry.get()` tool no existe | ValueError con lista de tools disponibles |
| `MCPPool.get_tools()` circuit open | MCPConnectionError con mensaje de retry |
| `sanitize_output()` falla | Retorna "[ERROR: output no pudo ser procesado]" |
| `FlowRegistry.get()` flow no existe | ValueError |

---

## 4 ANÁLISIS DE FULLSTACK + DX

### 4.1 Flujo Completo
N/A — tests puros.

### 4.2 Coherencia
✅ Todo código existe y es testeable.

### 4.3 Gaps

| Gap | Detalle |
|---|---|
| G1 | `StepDefinition.approval_threshold` existe en schema pero NO se usa en `DynamicWorkflow._run_crew()`. Campo morto |

### 4.4 DX & Tooling

**Herramienta Propuesta:** Test Runner Paralelo
- **Qué automatiza:** Ejecución de tests de stress en paralelo real, no sequential
- **Tipo:** Script pytest
- **Cómo se usa:** `pytest tests/stress/ -n auto`
- **Impacto:** Tests S4.2 (50 workflows concurrentes) ejecutan vs CPU cores, no serial
- **Prioridad:** Media — beneficios limitada para 7 tests

---

## 5 CRITERIOS DE ACEPTACIÓN

| Criterio | Verificable |
|---|---|
| ✅ S4.1: `resolve_tools` 500 tools completa <2s | ✅ |
| ✅ S4.2: 50 `DynamicWorkflow` concurrentes sin deadlock | ✅ |
| ✅ S4.3: `MCPPool.reset()` 100x sin error | ✅ |
| ✅ S4.4: flow_type duplicado sobrescribe sin error | ✅ |
| ✅ S4.5: sanitize 10MB completa <5s | ✅ |
| ✅ S4.6: org_id="" no crashea | ✅ |
| ✅ S4.7: JSON 20 niveles sin stack overflow | ✅ |

---

## 6 RIESGOS

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| R1: Memory leak en S4.1 (500 tools) | Media | Lista masiva en memoria | Monitorear `tracemalloc` en test |
| R2: S4.2 timeout en CI | Baja | 50 workflows concurrentes | Añadir `pytest.mark.timeout(60)` |
| R3: Campo `approval_threshold` muerto | Media | Plan no usa campo existente | Ignorar o eliminar campo |

---

## 7 PLAN DE IMPLEMENTACIÓN

| # | Tarea | Etapa(s) | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|
| 0 | Crear tests/stress/ | FULLSTACK/DX | Baja | 0.5h | Ninguna | → verificar: `ls tests/stress/` existe |
| 1 | S4.1: resolve_tools 500 tools | CODE | Media | 1h | Tarea 0 | → verificar: `pytest tests/stress/test_concurrency.py::test_resolve_500_tools` pasa |
| 2 | S4.2: 50 workflows concurrentes | CODE | Media | 1.5h | Tarea 0 | → verificar: `pytest tests/stress/test_concurrency.py::test_50_workflows` pasa |
| 3 | S4.3: MCPPool.reset() 100x | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_concurrency.py::test_pool_reset_100x` pasa |
| 4 | S4.4: flow_type duplicado | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_edge_cases.py::test_duplicate_flow_type` pasa |
| 5 | S4.5: sanitize 10MB | CODE | Media | 1h | Tarea 0 | → verificar: `pytest tests/stress/test_edge_cases.py::test_sanitize_10mb` pasa |
| 6 | S4.6: org_id vacío | CODE | Baja | 0.5h | Tarea 0 | → verificar: `pytest tests/stress/test_edge_cases.py::test_empty_org_id` pasa |
| 7 | S4.7: JSON 20 niveles | CODE | Media | 1h | Tarea 0 | → verificar: `pytest tests/stress/test_edge_cases.py::test_json_deep` pasa |

**Tiempo total estimado:** 6.5 horas

---

## 8 ROADMAP

- R1: Considerar eliminar campo `approval_threshold` de `StepDefinition` — no usado
- R2: Añadir `pytest-xdist` para ejecución paralela real de S4.2
- R3: Documentar que S4.4 ("segundo registro sobrescribe") es comportamiento esperado, no bug

---

## 9 VERIFICACIÓN FINAL

| Métrica | Mínimo |
|---|---|
| Elementos verificados (§0) | 8 ≥ 8 ✅ |
| Discrepancias detectadas | 0 |
| Secciones completadas | 8/8 ✅ |
| Criterios de aceptación | 7/7 ✅ |
| Riesgos identificados | 3 ≥ 3 ✅ |
| Tareas en plan | 7 ≥ 4 ✅ |
| Verificación inline por tarea | 7/7 ✅ |
| DX/Tooling propuesta | 1 ✅ |