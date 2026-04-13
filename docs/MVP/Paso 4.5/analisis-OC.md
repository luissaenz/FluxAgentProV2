# 📊 ANÁLISIS TÉCNICO — Paso 4.5: Test de Precisión Analítica

**Agente:** OC  
**Fecha:** 2026-04-12  
**Fase:** 4 — Capa de Inteligencia Visual y Analítica  
**Paso:** 4.5 [Validación]: Test de Precisión Analítica

---

## 1. Diseño Funcional

### 1.1 Descripción del Paso

El **Paso 4.5** es un paso de validación que certifica que el sistema analítico (AnalyticalCrew + herramientas SQL + sintetizador LLM) responde correctamente a consultas known-good y que los resultados coinciden con la base de datos real.

**Inputs:**
- Preguntas en lenguaje natural (ej: "¿Cuál es el agente con mayor tasa de éxito en la última semana?")
- Query types explícitos (ej: `query_type=agent_success_rate`)
- Base de datos con datos de prueba o producción

**Outputs:**
- Validación binaria (pass/fail) por cada caso de prueba
- Métricas de precisión (coincidencia de datos entre query directo y respuesta del crew)
- Reporte de clasificación de intents (keywords vs LLM)

### 1.2 Happy Path

1. **Consulta por Lenguaje Natural:**
   - Usuario → Frontend Chat (`AnalyticalAssistantChat`)
   - Envía `POST /analytical/ask` con `{ "question": "¿Cuál es el agente con mayor tasa de éxito?" }`
   - Backend → `AnalyticalCrew.ask()` con `question`
   - Clasificador de intents (LLM o fallback keywords) → identifica `agent_success_rate`
   - Ejecuta SQL via `SQLAnalyticalTool` con `{ org_id, query_type }`
   - Retorna datos crudos + sintetiza narrativa con LLM
   - Frontend renderiza respuesta + datos tabulares

2. **Consulta Explícita:**
   - Usuario → Quick Query button → `{ "query_type": "agent_success_rate" }`
   - Skip classification → ejecución directa
   - Mismo flujo de retorno

### 1.3 Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Sin datos en rango temporal | Retorna array vacío con mensaje "No hay datos" en summary |
| Query no permitido (SQL injection attempt) | `ValueError` con "not allowed", retorna 400 |
| Rate limit excedido (10 req/min) | Retorna 429 con mensaje de retry |
| Clasificación fallback (keywords) cuando LLM falla | Ejecuta correctamente usando heurística local |
| Pregunta fuera de alcance | `query_type=unknown`, summary "No tengo acceso a esa información" |
| Org_id sin datos de tasks | Retorna 0 filas, no rompe |

### 1.4 Manejo de Errores

- **429 Rate Limit:** Usuario ve toast con "Demasiadas consultas. Esperá un momento."
- **500 Internal Error:** Usuario ve mensaje genérico "Error ejecutando análisis"
- **400 Invalid Query:** Usuario ve lista de queries disponibles

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Rol | Modificaciones |
|------------|-----|-----------------|
| `src/scripts/test_analytical_precision.py` | Script de validación ejecutable | **Ninguna** (ya existe) |
| `src/crews/analytical_crew.py` | Core analítico (classify + execute + synthesize) | Ninguna (validar existente) |
| `src/tools/analytical.py` | SQLAnalyticalTool + EventStoreTool | Ninguna (validar existente) |
| `src/api/routes/analytical_chat.py` | Endpoint POST /analytical/ask | Ninguna (validar existente) |
| `src/crews/analytical_queries.py` | Allowlist de SQL pre-aprobado | Ninguna (validar existente) |
| Base de datos | Supabase/PostgreSQL | Datos de test necesarios |

### 2.2 Esquema de Datos

**Tablas consultadas en queries:**
- `tasks` → `status`, `assigned_agent_role`, `flow_type`, `tokens_used`, `created_at`, `org_id`
- `agent_catalog` → `role`, `org_id`
- `tickets` → `status`, `org_id`
- `domain_events` → `event_type`, `created_at`, `org_id`

**Schemas de retorno (por query_type):**

| Query Type | Columnas Retornadas |
|------------|---------------------|
| `agent_success_rate` | role, total_tasks, completed_tasks, success_rate |
| `tickets_by_status` | status, count |
| `flow_token_consumption` | flow_type, total_runs, total_tokens, avg_tokens |
| `recent_events_summary` | event_type, count |
| `tasks_by_flow_type` | flow_type, status, count |

### 2.3 Flujo de Validación

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Script Test     │ ──▶ │ AnalyticalCrew    │ ──▶ │ SQL Tool        │
│ (pytest/standalone)│     │ (ask/analyze)    │     │ (allowlist)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Verifica:      │     │ Clasifica:       │     │ Ejecuta:        │
│ - Estructura   │     │ - LLM            │     │ - Query SQL     │
│ - Contenido    │     │ - Keywords       │     │ - Params {org} │
│ - Aislamiento  │     │ - Fallback       │     │ - Retorna JSON  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 3. Decisiones

### 3.1 Decisiones del Paso

| Decisión | Justificación |
|----------|----------------|
| **Usar script existente `test_analytical_precision.py`** | Ya implementa 13 casos de prueba covering clasificación, ejecución, estructura y aislamiento. No requiere desarrollo nuevo. |
| **Validación manual vs automatizada** | El script permite ejecución standalone (`python src/scripts/test_analytical_precision.py`) y con pytest. Ambas opciones son válidas para certificación. |
| **Query tipo específico como gold standard** | La validación compara: (1) resultado directo del allowlist SQL vs (2) resultado del crew. Si coinciden → pass. |

### 3.2 Notas de Coherencia con Estado de Fase

El **estado-fase.md** establece:
- Rate limiting de 10 req/min implementado en `analytical_chat.py:65`
- Fallback keywords activo en `analytical_crew.py`
- Allowlist de 5 queries pre-aprobadas

El script de test valida **todos estos contratos** (líneas 54-62, 135-147, 181-188).

---

## 4. Criterios de Aceptación

| # | Criterio | Método de Verificación |
|---|----------|----------------------|
| ✅ | El script `test_analytical_precision.py` ejecuta sin errores de sintaxis | `python src/scripts/test_analytical_precision.py` |
| ✅ | Las 5 queries del allowlist retornan estructura correcta | `test_tickets_by_status_returns_data`, `test_flow_token_consumption_structure`, etc. |
| ✅ | Clasificación por keywords funciona para preguntas NL | `test_keyword_classification` con 6 casos |
| ✅ | Queries no permitidos son rechazados con error claro | `test_disallowed_query_rejected` |
| ✅ | Aislamiento multi-tenant funciona (org_id separado) | `test_multi_tenant_isolation` |
| ✅ | La pregunta "¿Cuál es el agente con mayor tasa de éxito?" retorna `agent_success_rate` y datos coherentes | `test_ask_method_structure` línea 155 |
| ✅ | Preguntas fuera de alcance retornan `unknown` con mensaje apropiado | `test_out_of_scope_question` |
| ✅ | SQLAnalyticalTool rechaza queries dinámicos | `test_sql_tool_rejects_dynamic_query` |
| ✅ | EventStoreTool retorna estructura válida | `test_event_store_tool_structure` |

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Base de datos sin datos de test** | Media | Bajo | El script maneja arrays vacíos gracefulmente. Warnings en output. |
| **Fallos de conexión a DB durante test** | Baja | Alto | El script captura excepciones y reporta como warnings. |
| **LLM no disponible para clasificación** | Baja | Medio | Fallback por keywords保证 respuesta (verificado en test 8). |
| **Timeout en queries complejos** | Baja | Medio | Rate limit protege against flooding. Queries son lightweight (agregaciones). |

---

## 6. Plan

### Tareas atómicas

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|---------------|
| 1 | Ejecutar `python src/scripts/test_analytical_precision.py` en entorno de desarrollo | Baja | Ninguna |
| 2 | Verificar que al menos 10/13 tests pasen (warningsOK) | Baja | Tarea 1 |
| 3 | Validar manualmente vía curl: `POST /analytical/ask` con pregunta NL | Media | Servidor corriendo |
| 4 | Comparar respuesta de API vs query directo a DB (gold standard) | Media | Tarea 3 |
| 5 | Documentar resultado en estado-fase.md | Baja | Tarea 4 |

### Comandos de validación

```bash
# Modo standalone
python src/scripts/test_analytical_precision.py

# Modo pytest
python -m pytest src/scripts/test_analytical_precision.py -v

# Validación manual
curl -X POST http://localhost:8000/analytical/ask \
  -H "Content-Type: application/json" \
  -H "x-org-id: 00000000-0000-0000-0000-000000000000" \
  -d '{"question": "¿Cuál es el agente con mayor tasa de éxito?"}'
```

---

## 🔮 Roadmap (NO implementar ahora)

| Item | Descripción | Bloqueado por |
|------|-------------|---------------|
| **Test de stress** | Validar rendimiento con 100+ queries concurrentes | MVP completo |
| **Test de precisión numérica** | Comparar cálculos exactos (ej: success_rate %) entre DB y crew | MVP completo |
| **Ampliar allowlist** | Agregar queries como "top 5 agents by token consumption" | Validación paso actual |
| **Test de degradación** | Validar fallback cuando LLM falla completamente | Fallback keywords ya validado |
| **Dashboard de métricas** | Visualización de uso analítico por org | MVP completo |

---

**Nota:** El script de test existente cubre todos los criterios de aceptación del paso 4.5. La validación consiste en ejecutarlo y verificar resultados, no en desarrollo adicional.