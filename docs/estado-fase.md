# 🗺️ ESTADO DE FASE: FASE 4 - CAPA DE INTELIGENCIA VISUAL Y ANALÍTICA 🏗️

## 1. Resumen de Fase
- **Objetivo:** Dotar al sistema de herramientas avanzadas de supervisión, modelado de procesos de negocio y diagnóstico basado en IA, permitiendo entender no solo *qué* está pasando, sino *cómo* se conectan los procesos y qué dicen los datos históricos.
- **Fase Anterior:** Fase 3 - Real-time Run Transcripts [FINALIZADA ✅]
- **Pasos de la Fase 4:**
    1. **4.1 [Framework]:** Metadata de Escalamiento en el `registry.py`. [COMPLETADO ✅]
    2. **4.2 [Frontend]:** Implementar `FlowHierarchyView.tsx`. [COMPLETADO ✅]
    3. **4.3 [Backend]:** Implementar `AnalyticalCrew`. [PENDIENTE 🏗️]
    4. **4.4 [Frontend]:** Implementar `AnalyticalAssistantChat.tsx`. [PENDIENTE 🏗️]
    5. **4.5 [Validación]:** Test de Precisión Analítica. [PENDIENTE 🏗️]

## 2. Estado Actual del Proyecto
- **Implementado y Funcional:**
    - **Visualización de Jerarquía (Step 4.2):** Componente `FlowHierarchyView` desplegado en `/workflows`. Agrupa flows por categorías, visualiza dependencias entrada/salida (`depends_on`/`required_by`) y resalta visualmente errores de grafo.
    - **Diagnóstico Premium:** Integración de `HealthBadge` global, resaltado de ciclos con animaciones `pulse` y tooltips descriptivos de fallos de integridad.
    - **Registro Enriquecido (Step 4.1):** El `FlowRegistry` ahora soporta metadatos de jerarquía (`category`) y dependencias (`depends_on`). Implementado algoritmo de detección de ciclos (DFS) y validación de referencias huérfanas.
    - **Validación Automática en Startup:** El servidor ejecuta una validación completa del grafo de procesos durante el `lifespan`, reportando inconsistencias en logs de forma preventiva.
    - **API de Jerarquía:** Endpoint `GET /flows/hierarchy` operativo, entregando un mapa estructurado de procesos agrupados por categoría con estatus de validación integrado.
    - **Fase 3 Completa:** Streaming de eventos en tiempo real (Transcripts) funcional con latencia < 500ms (caliente) y visualización animada en el timeline.

- **Parcialmente Implementado:**
    - **Categorización de Flows de Sistema:** `ArchitectFlow` y `GenericFlow` han sido categorizados, pero se requiere una auditoría continua a medida que se agreguen nuevos flows dinámicos para asegurar que las categorías sigan los estándares de negocio definidos.

## 3. Contratos Técnicos Vigentes
- **Metadata de Registro (`registry.py`):**
    - `category`: String (ej. "ventas", "operaciones", "system"). Por defecto `"sin_categoria"`.
    - `depends_on`: List[str]. Lista de `flow_type` de los que depende este proceso.
- **API Hierarchy (`GET /flows/hierarchy`):**
    - Payload: `{ hierarchy: Dict, categories: Dict, validation: { invalid_dependencies: Dict, cycles: List } }`
- **UI/UX Conventions:**
    - `HealthBadge`: Indicador visual de salud del grafo ("Todo Verde" vs "N Errores").
    - `AnimatePresence`: Uso de Framer Motion para transiciones suaves en expansión de componentes colapsables.

## 4. Decisiones de Arquitectura Tomadas
- **Visibilidad Proactiva de Errores (Paso 4.2):** Las categorías que contienen flows con ciclos o dependencias rotas se abren por defecto al cargar el componente. Razón: Minimizar el tiempo de reacción del operador ante fallos estructurales.
- **Micro-interacciones Premium:** Uso de `framer-motion` para elevar la estética percibida del dashboard, coherente con la identidad visual del proyecto.
- **Code-as-Schema (Paso 4.1):** Las dependencias entre procesos de negocio se definen en el código (decoradores) para facilitar el mantenimiento y la consistencia con la implementación lógica, evitando desincronización con la Base de Datos.
- **Validación Pasiva en Startup:** Se decidió que los errores de integridad del grafo (ciclos/huérfanos) generen warnings en logs y estados de error en la API, pero **NO capturen el arranque del servidor**, permitiendo que procesos no afectados sigan funcionando (Fail-safe).

## 5. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|------|--------|---------------------|-------------------|-------|
| 4.2  | ✅ | `FlowHierarchyView.tsx`, `page.tsx`, `types.ts` | Error Auto-expand / Framer Motion | Visualización diagnóstica aprobada con 100% de cumplimiento. |
| 4.1  | ✅ | `registry.py`, `main.py`, `flows.py`, `architect_flow.py` | Code-as-Schema / DFS Cycle Detection | Jerarquía de procesos validada. Fix crítico de registro de coctel_flows aplicado. |
| 3.5  | ✅ | `test_3_5_latency.py`, `get_server_time.sql` | Certificación de Latencia P95 | Validado tras resolver issues de Cold Start en Supabase. |
| 3.4  | ✅ | `tasks/[id]/page.tsx`, `TranscriptTimeline.tsx` | Tab Navigation / Initial Auto-switch | Integración premium finalizada. |

## 6. Criterios Generales de Aceptación MVP (Fase 4)
- El sistema debe ser capaz de representar visualmente las dependencias entre flows.
- El chat analítico debe poder responder preguntas complejas sobre el Event Store usando lenguaje natural.
- Los errores en el grafo de procesos no deben impedir el funcionamiento del resto del sistema.

---
*Documento actualizado por el protocolo CONTEXTO tras la finalización del Paso 4.2 (Implementación de la visualización de jerarquía).*

