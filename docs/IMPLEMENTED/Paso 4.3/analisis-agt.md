# 📊 ANÁLISIS TÉCNICO: Paso 4.3 - Implementación de AnalyticalCrew

## 1. Diseño Funcional

### 1.1 Objetivo
Dotar al sistema de una "Capa de Inteligencia Analítica" capaz de responder preguntas complejas sobre el rendimiento, costos y salud de la organización utilizando lenguaje natural, traduciéndolo a consultas estructuradas seguras sobre el `EventStore` y la base de datos relacional.

### 1.2 Happy Path
1. El sistema recibe una pregunta del usuario (ej. "¿Cuál es el agente con mayor tasa de éxito en la última semana?").
2. El `AnalyticalCrew` (Agente Analista) identifica el "intent" de la pregunta contrastándola con su `ALLOWLIST` de consultas analíticas.
3. El agente selecciona la herramienta adecuada (`SQLAnalyticalTool` o `EventStoreTool`).
4. Se ejecuta la consulta inyectando automáticamente el `org_id` del tenant para garantizar el aislamiento de datos.
5. El agente recibe los datos en bruto (JSON) y genera una respuesta narrativa, destacando insights clave (ej. "El agente X es el más eficiente con un 98% de éxito").

### 1.3 Edge Cases y Errores
- **Pregunta Ambigua:** El agente debe responder solicitando aclaración o listando las métricas que sí puede consultar.
- **Sin Datos:** Si la consulta retorna vacío, el resumen debe ser honesto ("No hay actividad registrada en este periodo") en lugar de un error técnico.
- **Timeout en Grandes Volúmenes:** Si la consulta SQL tarda demasiado, se debe capturar el error y sugerir reducir el rango de tiempo (timeframe).

---

## 2. Diseño Técnico

### 2.1 Refactorización de `AnalyticalCrew`
Actualmente el archivo `src/crews/analytical_crew.py` es un "scaffold" con lógica hardcoded. Se propone evolucionarlo hacia un agente de **CrewAI** real:

- **Evolución de Clase:** Heredar de `BaseCrew` pero integrar herramientas específicas de análisis.
- **Herramientas (Tools):**
    - `SQLAnalyticalTool`: Ejecutor de consultas SQL pre-definidas en `ALLOWED_ANALYTICAL_QUERIES`.
    - `EventStoreExplorerTool`: Permite buscar secuencias de eventos específicos (ej. "flows que terminaron en error").
- **Aislamiento Multi-tenant:** Todas las herramientas deben recibir el `org_id` en su constructor y usar el `get_tenant_client`.

### 2.2 Contrato de Salida
El método `analyze()` debe retornar un objeto estructurado para que el Frontend (Paso 4.4) pueda renderizar no solo texto, sino también gráficos:
```json
{
  "summary": "Resumen narrativo generado por LLM",
  "data": [ ... rows ... ],
  "chart_hint": "bar" | "pie" | "table",
  "metadata": {
    "query_executed": "agent_success_rate",
    "timestamp": "2026-04-12T..."
  }
}
```

---

## 3. Decisiones

### 3.1 LLM-Driven Intent Classification (Nueva)
**Decisión:** Usar el LLM para mapear la pregunta del usuario a una de las queries del allowlist, en lugar de Regex/Keywords.
**Justificación:** Permite entender sinónimos (ej. "costo de tokens" vs "gasto de llm") y variaciones gramaticales, elevando la percepción de "Inteligencia" del sistema (WOW factor).

### 3.2 SQL Templates vs SQL Raw
**Decisión:** Mantener el enfoque de `ALLOWED_ANALYTICAL_QUERIES` como templates SQL pre-validados.
**Justificación:** Seguridad absoluta. No se permite que el LLM genere SQL desde cero para evitar inyecciones o lecturas no autorizadas fuera del alcance del tenant.

---

## 4. Criterios de Aceptación

1. [ ] El `AnalyticalCrew` puede clasificar correctamente al menos 5 tipos de preguntas diferentes basadas en las consultas del dashboard.
2. [ ] La respuesta incluye un `summary` narrativo (Markdown) que no parece un log técnico.
3. [ ] Todos los resultados están estrictamente filtrados por el `org_id` del usuario.
4. [ ] El sistema maneja correctamente el caso donde Supabase no permite SQL directos (usando el tenant client o RPCs documentados).
5. [ ] El `EventStore` es consultable para obtener trazabilidad de eventos de dominio de las últimas 24h.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Alucinación Analítica** | Alto | El agente SOLO puede usar los datos retornados por las herramientas; tiene prohibido inventar cifras si la herramienta falla. |
| **Performance SQL** | Medio | Las queries del allowlist deben tener índices adecuados en `tasks` y `domain_events`. |
| **Consumo de Tokens** | Bajo | El análisis analítico es bajo demanda, pero se debe limitar el `max_iter` a 3 para evitar bucles. |

---

## 6. Plan de Implementación

1. **Tarea 1 (Baja):** Definir el `SQLAnalyticalTool` en `src/tools/analytical.py`.
2. **Tarea 2 (Media):** Refactorizar `AnalyticalCrew` para usar `BaseCrew.run_async` con el agente especializado.
3. **Tarea 3 (Media):** Implementar la lógica de "Intent Selection" en el agente para mapear preguntas a `ALLOWED_ANALYTICAL_QUERIES`.
4. **Tarea 4 (Baja):** Actualizar el endpoint `/analytical/ask` para conectar con el nuevo crew analítico.

---

## 🔮 Roadmap (No implementar ahora)
- **Auto-plotting:** Generación dinámica de `chart_configs` para que el frontend dibuje gráficos sin intervención manual.
- **Cross-Org Benchmarking:** (Anónimo) Comparar el rendimiento de la organización contra promedios del mercado.
- **Predicción de Costos:** Análisis predictivo basado en tendencias históricas de tokens.
