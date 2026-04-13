# 🏛️ ANÁLISIS TÉCNICO DEFINITIVO (UNIFICADO) — Paso 4.3: AnalyticalCrew

## 1. Resumen Ejecutivo
El **AnalyticalCrew** es el corazón de la "Capa de Inteligencia Visual y Analítica" de LUMIS. Su propósito es actuar como un puente inteligente entre las preguntas en lenguaje natural del usuario y el vasto historial de datos almacenado en Supabase (tareas, tickets) y el `EventStore` (eventos de dominio).

Este componente evoluciona desde un prototipo de coincidencia de palabras clave (keyword matching) hacia un **agente analítico de CrewAI** capaz de clasificar intenciones, ejecutar consultas seguras pre-validadas y sintetizar respuestas narrativas con insights accionables. Se integra directamente con el dashboard de analítica para proporcionar visibilidad proactiva sobre la salud y eficiencia de la organización.

---

## 2. Diseño Funcional Consolidado

### 2.1 Happy Path Detallado
1. **Entrada de Usuario:** Un operador administrativo pregunta: *"¿Cuál es mi agente más eficiente esta semana?"*.
2. **Clasificación de Intención (LLM):** El `AnalyticalCrew` utiliza el modelo configurado para mapear la pregunta al intent `agent_success_rate`, extrayendo parámetros temporales si aplica.
3. **Selección de Herramienta:** El agente decide utilizar la herramienta `SQLAnalyticalTool`.
4. **Ejecución Segura:** La herramienta recupera la consulta SQL del allowlist, inyecta el `org_id` del tenant actual y ejecuta la consulta a través del `get_tenant_client`.
5. **Enriquecimiento Opcional:** Si la pregunta requiere contexto temporal histórico profundo, se consulta el `EventStoreExplorerTool`.
6. **Síntesis Narrativa (LLM):** Con los datos recuperados (ej: tabla de agentes y tasas de éxito), el agente genera una respuesta en Markdown: *"El agente mas eficiente es **ArchitectRole** con un **94%** de éxito en 45 tareas..."*.
7. **Respuesta Estructurada:** El sistema retorna el resumen narrativo, los datos crudos (para gráficas) y metadata de ejecución.

### 2.2 Edge Cases y Manejo de Errores
- **Pregunta fuera de alcance:** El agente responde educadamente que no tiene acceso a esos datos y sugiere las métricas disponibles (agente, tickets, tokens, eventos).
- **Datos insuficientes:** Si la consulta retorna 0 filas, el LLM informa que no hay actividad en el rango solicitado en lugar de mostrar una tabla vacía.
- **Error de Base de Datos:** Se captura la excepción y se informa al usuario de un "Fallo temporal en la recuperación de métricas", registrando el error técnico internamente.

---

## 3. Diseño Técnico Definitivo

### 3.1 Arquitectura de Componentes
Se implementará un patrón de **Agente con Herramientas** siguiendo la arquitectura del sistema:

- **Crew:** `AnalyticalCrew` (refactorización de `src/crews/analytical_crew.py`).
- **Agent:** `AnalyticalAnalyst` (Single-agent per Rule R1).
- **Herramientas (Tools):**
    - `SQLAnalyticalTool`: Ejecutor de consultas del `ALLOWED_ANALYTICAL_QUERIES`. Recibe `query_type` y `params`.
    - `EventStoreTool`: Consultor del EventStore para análisis de eventos de dominio.

### 3.2 Contratos y APIs
**Endpoint:** `POST /analytical/ask` (Sin cambios en firma, upgrade interno).
- **Request:** `{ "question": str, "query_type": Optional[str] }`
- **Response:**
```json
{
  "question": "Pregunta original",
  "query_type": "intent_identificado",
  "data": [ ... rows ... ],
  "summary": "Resumen narrativo generado por LLM",
  "metadata": {
    "tokens_used": 1200,
    "row_count": 5
  }
}
```

### 3.3 Aislamiento y Seguridad
- **Multi-tenancy:** El `org_id` se inyecta en el constructor de las herramientas desde el contexto del middleware, asegurando que ninguna consulta SQL pueda leer datos de otros tenants.
- **Allowlist Estricto:** Se prohíbe explícitamente el SQL dinámico generado por LLM. Solo se ejecutan plantillas pre-aprobadas en `ALLOWED_ANALYTICAL_QUERIES`.

---

## 4. Decisiones Tecnológicas

| Decisión | Justificación |
|----------|---------------|
| **Intent Classification via LLM** | Superior al keyword matching; entiende sinónimos y variaciones lingüísticas. |
| **LLM Synthesis** | Reemplaza los templates hardcoded para generar respuestas mucho más humanas y contextualizadas. |
| **SQL Templates (Allowlist)** | Garantiza seguridad contra SQL Injection y simplifica la validación técnica en Supabase. |
| **CrewAI Tool Pattern** | Mantiene consistencia con el resto del backend (Bartenders, ArchitectFlow). |

---

## 5. Criterios de Aceptación MVP ✅

### 5.1 Funcionales
- [ ] El chat analítico responde preguntas naturales sin requerir parámetros técnicos del usuario.
- [ ] La respuesta incluye un resumen en Markdown que destaca los datos más importantes.
- [ ] El sistema identifica correctamente al menos los 5 casos de uso definidos (éxito de agentes, tickets, tokens, eventos, flows).

### 5.2 Técnicos
- [ ] El `AnalyticalCrew` se instancia y ejecuta de forma asíncrona (`run_async`) sin bloquear el servidor.
- [ ] Las herramientas inyectan el `org_id` correctamente en las llamadas al cliente de Supabase.
- [ ] No se utiliza SQL dinámico sensible en ninguna parte del flujo.

### 5.3 Robustez
- [ ] Si el LLM falla o alcanza timeout, el sistema utiliza el `_infer_query_type` (keyword matching) como fallback de emergencia.
- [ ] El rate limiter bloquea intentos de abuso (>10 requests/min por org).

---

## 6. Plan de Implementación

1. **Fase 1 (Herramientas - Complejidad Baja):** Crear `SQLAnalyticalTool` y `EventStoreTool` en un nuevo archivo `src/tools/analytical.py`.
2. **Fase 2 (Agente - Complejidad Media):** Refactorizar `AnalyticalCrew` para heredar de `BaseCrew` y configurar el agente con las nuevas herramientas y el prompt de analista.
3. **Fase 3 (Orquestación - Complejidad Media):** Implementar el pipeline `Intent Classifier -> Tools -> Synthesizer` dentro del método del crew.
4. **Fase 4 (Integración - Complejidad Baja):** Actualizar el endpoint `/analytical/ask` para invocar la nueva lógica.
5. **Fase 5 (Testing - Complejidad Media):** Validar aislamiento multi-tenant y precisión de clasificación.

---

## 7. Riesgos y Mitigaciones

- **Alucinación de Datos:** El LLM podría inventar números si la query retorna vacío. **Mitigación:** Prompt estricto que prohíbe el uso de datos no presentes en el JSON de la herramienta.
- **Latencia:** La doble llamada al LLM (clasificar + sintetizar) puede ser lenta. **Mitigación:** Uso de modelos rápidos (GPT-4o-mini o Claude Haiku) y optimización de prompts.

---

## 8. Testing Mínimo Viable
- **Test 1:** Pregunta NL sobre agentes → Verificar que `query_type` sea `agent_success_rate`.
- **Test 2:** Petición desde Org A → Verificar que los datos NO incluyan IDs o info de Org B.
- **Test 3:** Simulación de fallo de LLM → Verificar que el fallback por keywords retorne datos válidos.

---

## 🔮 Roadmap (No implementar ahora)
- **Auto-Charting:** Inclusión de configuraciones de Recharts en el JSON de respuesta para gráficos automáticos.
- **Exportación:** Botón para descargar los resultados analíticos en CSV.
- **Predicción:** Modelos de forecasting para predecir carga de trabajo basada en eventos históricos.
