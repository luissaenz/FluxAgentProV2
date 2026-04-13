# 🏛️ ANÁLISIS TÉCNICO FINAL: PASO 4.5 - TEST DE PRECISIÓN ANALÍTICA

## 1. Resumen Ejecutivo
El **Paso 4.5** constituye el hito de certificación de la Capa de Inteligencia del sistema LUMIS. Su objetivo no es solo validar que los componentes técnicos (AnalyticalCrew, SQLTools) funcionen aisladamente, sino garantizar la **veracidad y precisión** de las respuestas entregadas al usuario final.

En este paso, someteremos al sistema a un proceso de validación cruzada: compararemos las respuestas narrativas y los datos estructurados devueltos por la IA contra cálculos deterministas realizados directamente sobre la base de datos (Ground Truth). El éxito de este paso certifica que el sistema es confiable para la toma de decisiones de negocio en el dashboard.

## 2. Diseño Funcional Consolidado

### Happy Path (Confirmación de Veracidad)
1. **Pregunta Objetivo:** El usuario pregunta: "¿Cuál es el agente con mayor tasa de éxito en la última semana?".
2. **Detección de Intención:** El `AnalyticalCrew` mapea correctamente la pregunta a la query `agent_success_rate` (vía LLM o fallback de keywords).
3. **Cálculo Determinista:** El sistema ejecuta el SQL pre-aprobado filtrando por la `org_id` activa.
4. **Síntesis Narrativa:** El LLM genera un resumen que menciona explícitamente al agente líder y su porcentaje (Ej: "El agente 'Manager' lidera con un 92%").
5. **Certificación:** El validador verifica que el porcentaje mencionado en el summary coincide con el valor numérico en el JSON de datos y que este a su vez coincide con la realidad de las tablas `tasks`.

### Edge Cases (MVP)
- **Empate Técnico:** Si dos agentes tienen la misma tasa de éxito, el sistema debe mencionarlos a ambos o indicar el criterio de desempate (Ej: mayor número de tareas totales).
- **Datos Insuficientes:** Ante una base de datos vacía o sin eventos en los últimos 7 días, el sistema debe responder "No hay datos suficientes..." en lugar de inventar porcentajes (Hallucination Control).
- **Aislamiento Multi-tenant:** Una consulta de la Org A **jamás** debe incluir datos o nombres de agentes de la Org B.

### Manejo de Errores
- **Falla de LLM:** Si el proveedor de LLM está caído, el sistema debe usar el **fallback de keywords** para identificar la query y entregar la respuesta basada en datos, informando que el resumen narrativo es "simplificado por razones técnicas".
- **Rate Limit:** Si se exceden las 10 req/min, el usuario recibe un código 429 con un mensaje narrativo de "Alta demanda analítica, por favor espera un momento".

## 3. Diseño Técnico Definitivo

### Arquitectura de Validación
La validación se realizará mediante una combinación de ejecución automatizada y verificación cruzada de datos:

1.  **Suite de Pruebas Estructurales:** Uso del script `src/scripts/test_analytical_precision.py` (existente) para validar 13 criterios de seguridad, aislamiento y contratos de API.
2.  **Prueba de Precisión Numérica (NUEVA):** Ejecución de una consulta controlada ("Golden Question") tras una carga de datos conocida (Seeding).

### Contratos y APIs
- **Endpoint:** `POST /analytical/ask` (respetando los contratos de Fase 4).
- **Input:** `{"question": str, "query_type_hint": Optional[str]}`
- **Output:** `{ "question": str, "query_type": str, "data": List, "summary": str, "metadata": { "tokens_used": int, "row_count": int } }`

### Modelos de Datos involucrados (Solo Lectura)
- `tasks`: Para cálculo de `success_rate` y `token_consumption`.
- `agent_catalog`: Para identificación de roles y metadata.
- `domain_events`: Para resúmenes de actividad reciente.

## 4. Decisiones Tecnológicas
- **Validación por "Golden Samples"**: Se decide utilizar un dataset controlado (Seed) en lugar de datos ruidosos de producción para la certificación inicial.
- **Fallback Híbrido**: Se ratifica el uso de keywords locales para la clasificación de intenciones ante fallos del LLM, garantizando que la herramienta sea "Always Online".
- **Inyección de `org_id` en Herramientas**: Todas las `AnalyticalTools` heredan de `OrgBaseTool`, obligando al LLM a operar solo sobre datos del tenant actual mediante el filtrado implícito en el schema SQL.

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] El sistema clasifica correctamente preguntas de lenguaje natural hacia los 5 tipos de consulta permitidos.
- [ ] El chat responde a "¿Cuál es el agente con mayor tasa de éxito?" identificando el tipo `agent_success_rate`.
- [ ] Si no hay datos, el summary indica explícitamente la falta de información en lugar de alucinar datos falsos.

### Técnicos
- [ ] Los 13 tests en `test_analytical_precision.py` pasan exitosamente (admite warnings por BD vacía).
- [ ] El tiempo de respuesta total (Classification + Query + Synthesis) es < 8 segundos.
- [ ] La consulta SQL generada/utilizada incluye siempre el filtro `WHERE org_id = ...`.
- [ ] El sistema rechaza intentos de Inyección SQL o consultas fuera del allowlist (Ej: `DROP TABLE`).

### Robustez
- [ ] Al deshabilitar el API Key del LLM, el sistema sigue respondiendo consultas mediante el motor de fallback por keywords.
- [ ] El sistema maneja correctamente el rate limit (10 req/min) devolviendo un error 429 estructurado.

## 6. Plan de Implementación / Validación

1.  **Preparación (Baja):** Ejecutar `src/scripts/seed_dev_data.py` para asegurar que el entorno de test tiene datos vivos de tareas y eventos.
2.  **Validación Estructural (Baja):** Ejecutar `python src/scripts/test_analytical_precision.py` y verificar que no hay fallos críticos (Especialmente tests de aislamiento y seguridad).
3.  **Certificación de Precisión (Media):** 
    - Realizar la pregunta "¿Cuál es el agente con mayor tasa de éxito?" vía curl o UI.
    - Capturar el valor numérico devuelto.
    - Ejecutar la misma query manualmente en Supabase SQL Editor.
    - Comparar resultados: El margen de error debe ser 0.
4.  **Cierre (Baja):** Documentar resultados en `docs/estado-fase.md` y marcar el Paso 4.5 como ✅.

## 7. Riesgos y Mitigaciones
- **Riesgo: Alucinación en el Resumen.** El LLM podría reportar un dato equivocado a pesar de que el JSON adjunto sea correcto.
  - *Mitigación:* Refinar el `system_prompt` del `AnalyticalCrew` para que el "Summary" extraiga los datos estrictamente del bloque "Context Data".
- **Riesgo: Ambigüedad Temporal.** "¿Última semana" interpretado de distintas formas.
  - *Mitigación:* Las queries en el allowlist fijan la ventana a `INTERVAL '7 days'`.

## 8. Testing Mínimo Viable (E2E)
- **Test Case 1:** Pregunta NL → Verificar `query_type` correcto → Verificar coincidencia numérica con DB.
- **Test Case 2:** Intento de consulta prohibida → Verificar rechazo por el `SQLAnalyticalTool`.
- **Test Case 3:** Consulta Multi-tenant → Verificar que un usuario de Org A no ve datos de Org B bajo ninguna circunstancia.

## 9. 🔮 Roadmap (NO implementar ahora)
- **Análisis Predictivo:** Predicción de cuellos de botella basados en tendencias de éxito.
- **Gráficos Dinámicos:** Generación de componentes Chart.js directamente por el asistente analítico.
- **Auditoría de IA:** Registro persistente de la precisión de la IA para entrenamiento futuro del modelo.
