# Análisis Técnico — Paso 4.1: Metadata de Escalamiento en el Registry

## 1. Diseño Funcional

### Problema que resuelve
El sistema actualmente tiene flows registrados pero sin capacidad de modelar **jerarquías de procesos de negocio**. No existe forma de expresar que un flow de "Venta" debe completarse antes que uno de "Facturación", ni de agrupar flows por categoría funcional (ventas, logística, finanzas, etc.).

### Happy path
1. Un flow se registra con `@register_flow("nombre", depends_on=["flow_previo"], category="categoria")`.
2. El registry almacena la metadata junto a la clase del flow.
3. La API expone `GET /flows/hierarchy` que retorna el grafo completo de dependencias y agrupación por categorías.
4. Un consumidor (frontend u otro servicio) puede consumir esta metadata para:
   - Renderizar un árbol visual de dependencias.
   - Validar que un flow no se ejecute si sus dependencias no están completas.
   - Filtrar flows por categoría.

### Edge cases relevantes para MVP
- **Dependencia no existente:** Un flow declara `depends_on=["flow_inexistente"]`. Actualmente el registry NO valida esto. Debe detectarse y reportarse.
- **Dependencias circulares:** A y B se dependen mutuamente. El registry debe detectar y rechazar el registro.
- **Dynamic flows sin metadata:** `DynamicWorkflow.register()` inyecta directamente en `_flows` sin pasar por `register()`, por lo que los dynamic flows NO tienen metadata. Deben recibir valores por defecto (`depends_on=[]`, `category=None`).
- **Flow sin categoría explícita:** Debe agruparse bajo "sin_categoria" (ya implementado en `get_flows_by_category()`).

### Manejo de errores
- Si un flow depende de otro inexistente → **LOG warning** al momento del registro + el endpoint `/hierarchy` incluye un campo `invalid_dependencies: bool` por nodo.
- Si hay ciclo → **LOG warning** al momento del registro + endpoint marca el ciclo.
- **El registro NO debe fallar** silenciosamente: el flow se registra igual (compatibilidad), pero la metadata queda marcada como inválida.

---

## 2. Diseño Técnico

### Componentes nuevos o modificaciones

#### 2.1 `FlowRegistry` (`src/flows/registry.py`)

**Métodos existentes que requieren modificación:**

| Método | Cambio |
|--------|--------|
| `register()` | Ya acepta `depends_on` y `category`. **Agregar validación** de existencia de dependencias al registrar. |
| `get_metadata()` | Ya funcional. Sin cambios. |
| `get_hierarchy()` | Ya funcional. **Agregar campo `valid_dependencies: bool`** por nodo. |
| `get_flows_by_category()` | Ya funcional. Sin cambios. |

**Método nuevo:**

```
validate_dependencies() -> Dict[str, List[str]]
```
- Recorre todos los flows registrados.
- Para cada flow, verifica que cada item en `depends_on` exista en `_flows`.
- Retorna `{flow_name: [dependencias_invalidas]}` para flows con deps inválidas.

```
detect_cycles() -> List[List[str]]
```
- Implementa DFS para detectar ciclos en el grafo de dependencias.
- Retorna lista de ciclos encontrados (cada ciclo es una lista de flow names).

#### 2.2 `DynamicWorkflow.register()` (`src/flows/dynamic_flow.py`)

**Modificación:** Después de inyectar en `_flows`, también debe inyectar en `_metadata`:

```python
flow_registry._metadata[flow_type.lower()] = {
    "depends_on": definition.get("depends_on", []),
    "category": definition.get("category"),
}
```

Esto requiere que el `definition` dict desde la DB incluya opcionalmente estos campos. Si no los tiene, se usan defaults.

#### 2.3 API Endpoints (`src/api/routes/flows.py`)

**Modificación en `GET /flows/hierarchy`:**

Agregar al response un campo `validation`:
```python
{
    "hierarchy": {...},
    "categories": {...},
    "validation": {
        "invalid_dependencies": {"flow_a": ["dep_x", "dep_y"]},
        "cycles": [["flow_b", "flow_c", "flow_b"]]
    }
}
```

**Modificación en `GET /flows/available`:**

Ya incluye `depends_on` y `category`. Agregar campo `has_valid_dependencies: bool`.

#### 2.4 Modelos de datos (Pydantic en `flows.py`)

Agregar nuevos modelos:

```python
class FlowValidationResponse(BaseModel):
    invalid_dependencies: Dict[str, List[str]]
    cycles: List[List[str]]

class FlowHierarchyResponse(BaseModel):
    hierarchy: Dict[str, FlowHierarchyNode]
    categories: Dict[str, List[str]]
    validation: FlowValidationResponse
```

### Integraciones existentes

- **Coherencia con `estado-fase.md`:** El estado actual documenta contratos de `GET /transcripts/{task_id}` y Realtime. Este paso NO toca esos contratos. Es independiente de la Fase 3.
- **`WorkflowDefinition` (`workflow_definition.py`):** Ya tiene validación de ciclos a nivel de steps dentro de un workflow. La nueva validación de ciclos en el registry opera a nivel de **flows**, no de steps. Son complementarios.

---

## 3. Decisiones

### D1: Validación de dependencias al registro vs. bajo demanda
**Decisión:** Validar **al momento del registro** (decorator) pero NO rechazar el registro si las deps son inválidas. Solo loguear warning y marcar la metadata como inválida.

**Justificación:** Rechazar el registro rompería el startup de la app si un flow depende de otro que aún no se importó (orden de importación). La validación lazy permite que todos los flows se carguen y luego se valida en bloque.

### D2: Los dynamic flows pueden tener metadata desde la DB
**Decisión:** Extender `DynamicWorkflow.register()` para leer `depends_on` y `category` del `definition` dict si están presentes.

**Justificación:** Los flows dinámicos son flows de pleno derecho y deben poder participar en la jerarquía. La definición en la tabla `workflow_templates` debe permitir estos campos opcionales.

### D3: La validación de ciclos se ejecuta en startup, no en cada request
**Decisión:** `detect_cycles()` y `validate_dependencies()` se llaman una vez en el startup de FastAPI y el resultado se cachea hasta el próximo re-registro.

**Justificación:** El grafo de dependencias es estático en runtime. No tiene sentido recalcularlo en cada request al endpoint `/hierarchy`.

### D4: No se agrega runtime enforcement de dependencias en este paso
**Decisión:** El enforcement (bloqueo de ejecución si deps no completadas) queda para un paso futuro. Este paso solo modela y expone la metadata.

**Justificación:** El MVP de la capa visual no necesita bloquear ejecución. Solo necesita mostrar la jerarquía. Agregar enforcement ahora aumenta la superficie de cambio y requiere estado de ejecución cruzado entre flows.

---

## 4. Criterios de Aceptación

- [ ] `FlowRegistry.register()` almacena `depends_on` y `category` en `_metadata` para cada flow.
- [ ] `FlowRegistry.validate_dependencies()` retorna un dict con flows que tienen dependencias inexistentes.
- [ ] `FlowRegistry.detect_cycles()` retorna una lista de ciclos detectados en el grafo.
- [ ] `DynamicWorkflow.register()` también registra metadata en `_metadata` (con defaults si no se proveen).
- [ ] `GET /flows/hierarchy` retorna `validation` con `invalid_dependencies` y `cycles`.
- [ ] `GET /flows/available` retorna `has_valid_dependencies: bool` por flow.
- [ ] Un flow con `depends_on=["inexistente"]` se registra correctamente pero aparece en `invalid_dependencies`.
- [ ] Un ciclo A→B→A es detectado y reportado por `detect_cycles()`.
- [ ] Los tests existentes del registry siguen pasando sin modificaciones.
- [ ] No se rompe la ejecución manual de flows existentes vía `POST /flows/{flow_type}/run`.

---

## 5. Riesgos

| Riesgo | Estrategia de mitigación |
|--------|------------------------|
| **Orden de importación:** Un flow se registra antes que su dependencia, causando falso positivo en `validate_dependencies()`. | Ejecutar `validate_dependencies()` después de que todos los módulos estén importados (post-startup hook). |
| **Dynamic flows con definición incompleta:** La tabla `workflow_templates` no tiene columna para `depends_on` o `category`. | Usar `definition.get()` con defaults. Si la columna no existe, la metadata será `None/[]` y el flow aparecerá sin categoría. |
| **Performance en graphs grandes:** DFS para ciclos puede ser lento si hay cientos de flows. | El MVP tiene ~16 flows. El DFS es O(V+E), trivial para este tamaño. Optimizar solo si se supera el umbral de 100 flows. |
| **Breaking change en API response:** Agregar `validation` al response de `/hierarchy` puede romper clientes que no lo esperan. | Es un campo **adicional**, no modifica los existentes. Los clientes que ignoran campos desconocidos no se ven afectados. |

---

## 6. Plan

### Tareas atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Agregar `validate_dependencies()` a `FlowRegistry` | Baja | — |
| 2 | Agregar `detect_cycles()` a `FlowRegistry` | Media | — |
| 3 | Modificar `get_hierarchy()` para incluir campo `valid_dependencies` | Baja | 1, 2 |
| 4 | Modificar `DynamicWorkflow.register()` para registrar metadata en `_metadata` | Baja | — |
| 5 | Agregar modelo Pydantic `FlowValidationResponse` | Baja | — |
| 6 | Modificar `GET /flows/hierarchy` para incluir `validation` en response | Baja | 1, 2, 5 |
| 7 | Modificar `GET /flows/available` para incluir `has_valid_dependencies` | Baja | 1 |
| 8 | Agregar tests unitarios para `validate_dependencies()` (deps inválidas) | Media | 1 |
| 9 | Agregar tests unitarios para `detect_cycles()` (ciclo directo, indirecto, sin ciclo) | Media | 2 |
| 10 | Agregar tests de integración para endpoints modificados | Media | 6, 7 |
| 11 | Verificar que tests existentes siguen pasando | Baja | 1-10 |

### Orden recomendado

```
1, 2 → 3, 4, 5 → 6, 7 → 8, 9 → 10 → 11
```

Las tareas 1 y 2 son independientes y pueden hacerse en paralelo. Luego 3, 4, 5 dependen de 1 y 2. Los endpoints (6, 7) dependen de las validaciones. Los tests (8, 9) dependen de las implementaciones.

---

## 🔮 Roadmap (NO implementar ahora)

### Runtime enforcement de dependencias
- Bloquear `POST /flows/{flow_type}/run` si las dependencias no tienen una task completada recientemente.
- Requiere un estado de "última ejecución exitosa" por flow.
- Puede implementarse con una tabla `flow_executions` que trackee `flow_type`, `task_id`, `status`, `completed_at`.

### Trigger automático de flows dependientes
- Cuando un flow se completa, verificar si hay flows que lo tienen como dependencia y dispararlos automáticamente.
- Requiere un mecanismo de "post-completion hooks" en el `BaseFlow.execute()`.

### Categorías jerárquicas
- Actualmente `category` es un string plano. Podría ser un path como `ventas/cotizaciones` para permitir agrupamiento multinivel.

### Validación de dependencias en el decorador
- Si se resuelve el problema de orden de importación (ej. con lazy imports o un registro en dos fases), se puede validar al momento del decorador y rechazar flows con deps inválidas.

### Visualización de grafo de dependencias en el frontend
- El endpoint `/hierarchy` ya retorna la data. El paso 4.2 (`FlowHierarchyView.tsx`) consumirá esta data para renderizar el árbol.
- Este análisis asume que el formato de response es suficiente para esa visualización.

### Metadata adicional por flow
- `version`: Semver del flow para tracking de cambios.
- `timeout`: Timeout máximo de ejecución por flow.
- `retry_policy`: Configuración de reintentos por flow.
