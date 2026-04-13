# Análisis Técnico — Paso 4.3: Implementar `AnalyticalCrew` (Backend)

## 1. Diseño Funcional

### 1.1 Problema que Resuelve
El sistema actual tiene 5 consultas pre-validadas que funcionan como "vistas parametrizadas": devuelven datos crudos pero **no procesan consultas complejas en lenguaje natural**. El gap entre lo implementado y lo que define el criterio de aceptación de Fase 4 es:

> *"El chat analítico debe poder responder preguntas complejas sobre el Event Store usando lenguaje natural."*

Actualmente el endpoint `/analytical/ask`:
- Hace keyword matching rudimentario para inferir `query_type`
- Si la pregunta no matchea keywords conocidas, retorna `query_type="unknown"` → HTTP 400
- No hay LLM involucrado en la interpretación de la pregunta
- No hay composición de múltiples consultas (ej: "compara el consumo de tokens del flow de ventas con el de logística y dime cuál es más eficiente")

### 1.2 Happy Path
1. Usuario envía pregunta en lenguaje natural: *"¿Cuál fue el flow con mejor margen de éxito en marzo comparado con abril?"*
2. El `AnalyticalCrew` usa un LLM agente para:
   a. **Clasificar el intent**: identificar qué datos necesita la pregunta
   b. **Seleccionar consultas**: mapear el intent a una o más consultas del allowlist, o componer una nueva consulta segura
   c. **Ejecutar**: correr las consultas contra Supabase con RLS
   d. **Sintetizar**: el LLM genera una respuesta narrativa basada en los datos
3. El endpoint retorna `{ question, query_type, data, summary, metadata }` donde `summary` es generado por el LLM, no por templates hardcodeados.

### 1.3 Edge Cases (MVP)
| Edge Case | Comportamiento Esperado |
|-----------|------------------------|
| Pregunta fuera de dominio ("¿quién ganó el mundial?") | LLM identifica que no es analítica → retorna mensaje amigable: "No puedo responder esa pregunta con los datos disponibles" |
| Pregunta que requiere datos no disponibles en el allowlist | LLM identifica gap → sugiere consultas disponibles más cercanas |
| Pregunta ambigua ("¿cómo van las cosas?") | LLM pide aclaración: retorna respuesta con opciones de consultas disponibles |
| Query retorna 0 filas | LLM genera explicación contextual: "No hay datos para el período solicitado" en vez de lista vacía |
| Timeout de Supabase (>10s) | Error 504 con mensaje: "La consulta excede el tiempo límite. Intentá con un período más corto." |

### 1.4 Manejo de Errores (UI/UX del endpoint)
- **400 Bad Request**: `{"message": "...", "available_queries": [...], "hint": "..."}` — ya implementado, mantener
- **500 Internal Error**: `{"message": "Error interno ejecutando el análisis", "request_id": "..."}` — agregar request_id para trazabilidad
- **429 Too Many Requests**: Rate limiter a nivel de endpoint (máx 10 consultas/min por org) — proteger contra abuso de LLM calls
- **504 Gateway Timeout**: Consultas que exceden 15s

---

## 2. Diseño Técnico

### 2.1 Componentes Actuales vs Necesarios

| Componente | Estado Actual | Acción Requerida |
|------------|--------------|-----------------|
| `AnalyticalCrew` class | ✅ Existe con 5 queries + ejecución via Supabase client | **Modificar**: agregar capa de LLM para intent classification y síntesis |
| `ALLOWED_ANALYTICAL_QUERIES` | ✅ 5 queries hardcodeados | **Mantener**: el allowlist es correcto para MVP |
| `_execute_safe_query()` | ✅ Ejecuta queries via Supabase client con agregación Python | **Mantener**: funciona para MVP |
| `_infer_query_type()` | ⚠️ Keyword matching en `analytical_chat.py` | **Reemplazar**: usar LLM para clasificación de intents |
| `_generate_summary()` | ⚠️ Templates hardcodeados en `analytical_chat.py` | **Reemplazar**: usar LLM para síntesis narrativa |
| `query_events()` | ✅ Acceso directo al EventStore | **Mantener**: ya permite análisis ad-hoc |
| Herramientas SQL como CrewAI tools | ❌ No existe | **Crear**: `SafeQueryTool` como CrewAI tool para que el agente analítico las use |
| Herramienta EventStore como CrewAI tool | ❌ No existe | **Crear**: `EventStoreQueryTool` como CrewAI tool |
| Rate limiter en endpoint | ❌ No existe | **Crear**: decorador o middleware simple |

### 2.2 Arquitectura Propuesta

```
POST /analytical/ask
    │
    ▼
┌─────────────────────────────────┐
│  AnalyticalChatEndpoint         │  (analytical_chat.py)
│  - Valida request                │
│  - Crea AnalyticalCrew           │
│  - Llama crew.query(question)    │
│  - Retorna respuesta             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  AnalyticalCrew.query(question) │  (analytical_crew.py — NUEVO método principal)
│                                 │
│  1. IntentClassifier (LLM)      │
│     → Determina query_types     │
│     → Extrae parámetros         │
│                                 │
│  2. QueryExecutor               │
│     → Ejecuta 1+ consultas      │
│     → Combina resultados        │
│                                 │
│  3. ResponseSynthesizer (LLM)   │
│     → Genera resumen narrativo  │
│     → Contextualiza datos       │
│                                 │
│  Retorna: {query_type, data,    │
│            summary, metadata}   │
└────────────┬────────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
┌──────────┐  ┌──────────────┐
│SafeQuery │  │EventStore    │
│Tool      │  │QueryTool     │
└──────────┘  └──────────────┘
```

### 2.3 Interfaces

#### Nuevo método principal: `AnalyticalCrew.query()`
```python
async def query(self, question: str) -> Dict[str, Any]:
    """Procesar pregunta en lenguaje natural.
    
    Args:
        question: Pregunta del usuario
        
    Returns:
        {
            "question": str,           # Pregunta original
            "intent": str,             # Intent clasificado
            "query_types": [str],      # Consultas ejecutadas
            "data": List[Dict],        # Resultados combinados
            "summary": str,            # Respuesta narrativa del LLM
            "metadata": {
                "execution_time_ms": int,
                "queries_executed": int,
                "tokens_used": int,
            }
        }
    """
```

#### Herramienta CrewAI: `SafeQueryTool`
```python
class SafeQueryTool(OrgBaseTool):
    """Ejecuta consultas pre-validadas del allowlist analítico.
    
    El agente analítico usa esta herramienta para ejecutar
    consultas SQL seguras contra la base de datos.
    """
    name: str = "execute_analytical_query"
    description: str = "Ejecuta una consulta analítica pre-validada. 
        Queries disponibles: agent_success_rate, tickets_by_status, 
        flow_token_consumption, recent_events_summary, tasks_by_flow_type"
    
    async def _run(self, query_type: str, params: dict = None) -> str:
        # Delega a AnalyticalCrew._execute_safe_query
        ...
```

#### Herramienta CrewAI: `EventStoreQueryTool`
```python
class EventStoreQueryTool(OrgBaseTool):
    """Consulta el EventStore para análisis temporal.
    
    Permite al agente analítico buscar eventos por tipo,
    agregado o rango de tiempo.
    """
    name: str = "query_event_store"
    description: str = "Consulta eventos de dominio para análisis 
        temporal. Parámetros: event_type, aggregate_type, limit"
    
    async def _run(self, event_type: str = None, 
                   aggregate_type: str = None, 
                   limit: int = 100) -> str:
        # Delega a AnalyticalCrew.query_events
        ...
```

### 2.4 Modelo de Datos — Sin Cambios
No se requieren nuevas tablas ni columnas. Todo el schema existente soporta la funcionalidad:
- `tasks` → métricas de ejecución
- `domain_events` → análisis temporal
- `tickets` → estado de work items
- `agent_catalog` → metadata de agentes

### 2.5 Coherencia con `estado-fase.md`
- **Contrato API**: El endpoint `POST /analytical/ask` mantiene su firma actual (`AnalyticalAskRequest` → `AnalyticalAskResponse`). Internamente cambia la implementación, no el contrato.
- **RLS**: Todas las consultas siguen usando `get_tenant_client(org_id, user_id)` — sin cambios en seguridad.
- **Allowlist**: Se mantiene el patrón de consultas pre-validadas. No se introduce SQL dinámico.

---

## 3. Decisiones

### D1: LLM para intent classification en vez de keyword matching
**Justificación**: El keyword matching actual (`_infer_query_type`) falla con preguntas que no contienen keywords exactas. Un LLM puede entender semántica ("¿qué agente performa mejor?" → `agent_success_rate`). 
**Alternativa rechazada**: Fine-tuning de clasificador — overkill para MVP con 5 queries.
**Riesgo mitigado**: Se usa el mismo LLM configurado en `settings.get_llm()`, costo marginal por consulta (~100 tokens input + ~50 output).

### D2: Un solo agente CrewAI con 2 herramientas en vez de crew multi-agente
**Justificación**: La tarea analítica es secuencial (clasificar → ejecutar → sintetizar), no paralelizable. Un crew multi-agente agregaría latencia innecesaria.
**Coherencia**: Sigue Rule R1 (flow es orquestador, agente es ejecutor) y Rule R2 (`allow_delegation=False`).

### D3: No introducir SQL dinámico — mantener allowlist estricto
**Justificación**: Seguridad ante todo. El allowlist previene inyección SQL y asegura que solo consultas probadas se ejecuten. Para queries fuera del allowlist, el LLM debe informar que no están disponibles y sugerir alternativas.
**Roadmap**: En Fase 5+ se podría agregar un "query builder" seguro con validación de schema.

### D4: `_generate_summary` migrar de templates a LLM synthesis
**Justificación**: Los templates actuales son frágiles y no escalan. Si mañana se agregan 20 queries más, mantener 20 templates es insostenible. Un LLM puede generar resúmenes coherentes para cualquier combinación de datos.
**Prompt del sintetizador**: Se le pasa la pregunta original + los datos retornados + instrucciones de formato.

### D5: Rate limiter simple a nivel de endpoint (no Redis-based)
**Justificación**: Para MVP, un dict en memoria `{org_id: [(timestamp, count)]}` con ventana de 1 minuto es suficiente. No introducir Redis/Redis-compatible hasta que el volumen lo requiera.
**Límite**: 10 consultas/min por org.

---

## 4. Criterios de Aceptación

- [ ] El endpoint `POST /analytical/ask` acepta preguntas en lenguaje natural y retorna una respuesta coherente **sin requerir `query_type` explícito**
- [ ] La clasificación de intent funciona correctamente para las 5 consultas del allowlist (precisión > 80% en tests)
- [ ] Cuando una pregunta no mapea a ninguna consulta del allowlist, el sistema retorna un mensaje explicativo con las consultas disponibles
- [ ] El resumen (`summary`) es generado por un LLM, no por templates hardcodeados
- [ ] El `AnalyticalCrew` expone un método `query(question)` que encapsula todo el pipeline (clasificación → ejecución → síntesis)
- [ ] Las herramientas `SafeQueryTool` y `EventStoreQueryTool` existen y son usables por un agente CrewAI
- [ ] El rate limiter rechaza requests con HTTP 429 cuando se exceden 10 consultas/min por org
- [ ] Todos los métodos asíncronos del crew (`analyze`, `query`, `_execute_safe_query`, etc.) son awaitables y no bloquean el event loop
- [ ] Las consultas respetan RLS — un org no puede ver datos de otro org (verificable via test con tenant client)
- [ ] El endpoint `GET /analytical/queries` sigue funcionando y muestra las 5 consultas con sus descripciones
- [ ] Los errores de Supabase se manejan con HTTP 500 + log estructurado (no stack trace expuesto al cliente)
- [ ] El `AnalyticalCrew` no depende de que exista un registro en `agent_catalog` (no es un crew estándar, no necesita agente DB)

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **LLM malinterpreta la pregunta** y ejecuta la consulta incorrecta | Alto | Incluir en el prompt del clasificador la lista de queries disponibles con descripciones claras. Agregar un "confidence score" — si es < 0.7, pedir aclaración. |
| **Latencia del LLM** suma >3s al tiempo de respuesta | Medio | Usar modelo rápido (gpt-4o-mini o equivalente). Timeout de 10s en la clasificación. Si timeout, fallback a keyword matching existente. |
| **Supabase query lenta** en organizaciones con muchos datos | Medio | Agregar `limit` implícito de 1000 filas en todas las consultas. Si el usuario necesita más, que especifique parámetros de paginación. |
| **Rate limiter en memoria** se pierde en restart del servidor | Bajo | Aceptable para MVP. En producción, migrar a Redis o Supabase-based rate limit. |
| **El LLM genera resumen incorrecto** (alucina datos no presentes) | Alto | En el prompt del sintetizador, instruir explícitamente: "Solo usa los datos proporcionados. Si no hay datos, dilo claramente." Agregar validación post-generación: verificar que números mencionados existan en los datos. |
| **Composición de múltiples queries** falla al combinar resultados | Medio | Para MVP, soportar solo 1 query por pregunta. Composición múltiple queda para roadmap. |

---

## 6. Plan de Implementación

### Tarea 1: Crear `SafeQueryTool` y `EventStoreQueryTool`
- **Complejidad**: Baja
- **Dependencias**: Ninguna
- **Detalle**:
  - Crear archivo `src/tools/analytical_tools.py`
  - `SafeQueryTool` recibe `query_type` + `params`, delega a lógica de `ALLOWED_ANALYTICAL_QUERIES`
  - `EventStoreQueryTool` recibe filtros, delega a `EventStore` o query directa a `domain_events`
  - Ambas extienden `OrgBaseTool` para tener `org_id` y acceso a secrets si necesario
  - Tests unitarios: cada herramienta retorna datos válidos con org_id correcto

### Tarea 2: Crear `IntentClassifier` con LLM
- **Complejidad**: Media
- **Dependencias**: Tarea 1 (las herramientas deben existir para que el classifier sepa qué puede ejecutar)
- **Detalle**:
  - Clase `IntentClassifier` en `src/crews/analytical_crew.py` (o módulo separado `src/crews/analytical_classifier.py`)
  - Prompt del sistema: lista de queries disponibles con descripción + ejemplo de pregunta para cada una
  - Método `classify(question) -> {query_type: str, confidence: float, extracted_params: dict}`
  - Si confidence < 0.7 → retorna `query_type=None` con mensaje de aclaración
  - Usa `settings.get_llm()` — mismo modelo que el resto del sistema

### Tarea 3: Crear `ResponseSynthesizer` con LLM
- **Complejidad**: Media
- **Dependencias**: Tarea 2
- **Detalle**:
  - Clase `ResponseSynthesizer` en mismo módulo
  - Prompt: pregunta original + datos retornados + instrucción de generar respuesta narrativa
  - Método `synthesize(question, query_type, data) -> str`
  - Instrucción crítica: "Solo usa los datos proporcionados. No inventes números."
  - Manejar caso de datos vacíos con mensaje específico

### Tarea 4: Implementar método `query()` en `AnalyticalCrew`
- **Complejidad**: Media
- **Dependencias**: Tareas 2 y 3
- **Detalle**:
  - `async def query(self, question: str) -> Dict[str, Any]`
  - Pipeline secuencial: classify → execute → synthesize
  - Agregar timing y metadata al resultado
  - Mantener método `analyze()` existente para compatibilidad (uso directo desde código)

### Tarea 5: Refactorizar endpoint `/analytical/ask`
- **Complejidad**: Baja
- **Dependencias**: Tarea 4
- **Detalle**:
  - Cambiar lógica: en vez de `_infer_query_type` + `crew.analyze()`, usar `crew.query(question)`
  - Mantener `_infer_query_type` como fallback si el LLM classifier falla/timeout
  - El `summary` viene del sintetizador, no de `_generate_summary`
  - Eliminar `_generate_summary` del endpoint (ya no se usa)

### Tarea 6: Implementar Rate Limiter
- **Complejidad**: Baja
- **Dependencias**: Ninguna (puede hacerse en paralelo con Tareas 1-4)
- **Detalle**:
  - Decorador `@rate_limit(max_requests=10, window_seconds=60)` en `src/api/middleware.py`
  - Dict en memoria: `_rate_limits: Dict[str, List[float]]` (org_id → timestamps)
  - Aplicar al endpoint `POST /analytical/ask`
  - Retorna HTTP 429 con `Retry-After` header

### Tarea 7: Tests
- **Complejidad**: Media
- **Dependencias**: Todas las tareas anteriores
- **Detalle**:
  - Test unitario: `IntentClassifier` clasifica correctamente 10 preguntas de ejemplo
  - Test unitario: `ResponseSynthesizer` genera resumen coherente con datos mock
  - Test integración: `AnalyticalCrew.query()` con pregunta real → retorna estructura completa
  - Test endpoint: `POST /analytical/ask` con pregunta NL → 200 con summary
  - Test endpoint: rate limiter → 429 tras 10 requests en 1 minuto
  - Test seguridad: org A no puede ver datos de org B

### Orden Recomendado y Dependencias
```
T1 (SafeQueryTool) ──────────┐
                              ├──→ T4 (query method) ──→ T5 (refactor endpoint) ──→ T7 (tests)
T2 (IntentClassifier) ───────┘                              ↑
                              ──────────────────────────────┘
T3 (ResponseSynthesizer) ────┘

T6 (Rate Limiter) ──────────────────────────────────────→ T5 (applied to endpoint)
```

### Estimación de Complejidad Relativa
| Tarea | Complejidad |
|-------|-------------|
| T1: Herramientas CrewAI | Baja |
| T2: IntentClassifier | Media |
| T3: ResponseSynthesizer | Media |
| T4: Método query() | Media |
| T5: Refactorizar endpoint | Baja |
| T6: Rate Limiter | Baja |
| T7: Tests | Media |

---

## 🔮 Roadmap (NO implementar ahora)

### Composición de Múltiples Queries
- **Qué**: Permitir que una pregunta dispare 2+ consultas y el sintetizador combine resultados ("compara X con Y")
- **Por qué no ahora**: Agrega complejidad significativa al classifier (debe detectar intents compuestos) y al executor (debe parallelizar queries y merge results)
- **Preparación**: El diseño del `query()` retorna `query_types: List[str]` desde ahora, preparado para soportar múltiples en el futuro

### Query Builder Seguro (SQL Dinámico Validado)
- **Qué**: Un parser que convierta preguntas NL en consultas SQL validadas contra un schema allowlist
- **Por qué no ahora**: Requiere un AST parser o LLM con herramientas de validación de schema complejo
- **Preparación**: Mantener el allowlist como base; las RPC functions de Supabase pueden extenderse para queries parametrizadas

### Caché de Respuestas
- **Qué**: Cache de Redis/Supabase para preguntas frecuentes con misma respuesta
- **Por qué no ahora**: MVP no tiene volumen suficiente para justificarlo
- **Preparación**: El `metadata` del resultado incluye `query_type` y `params` — suficiente para construir una cache key en el futuro

### Streaming de Respuesta del LLM
- **Qué**: Server-sent events para el summary del sintetizador (el usuario ve la respuesta generarse en tiempo real)
- **Por qué no ahora**: Agrega complejidad de infraestructura (SSE, connection management)
- **Preparación**: El endpoint actual es síncrono en la respuesta — migrar a streaming es additive

### Análisis Predictivo
- **Qué**: "¿Cuántos tickets预计aremos la semana que viene?" — forecasting basado en datos históricos
- **Por qué no ahora**: Requiere modelos estadísticos o LLM con capacidades numéricas avanzadas
- **Preparación**: El EventStore ya tiene el historial de eventos — los datos existen, solo falta el modelo

### Dashboard Analítico Exportable
- **Qué**: El usuario puede "guardar" una consulta como widget en un dashboard personalizado
- **Por qué no ahora**: Requiere frontend completo de dashboard + persistencia de queries guardadas
- **Preparación**: La estructura `AnalyticalAskResponse` es serializable — puede persistirse como "reporte guardado"
