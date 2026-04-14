# 🏛️ ANÁLISIS FINAL: PASO 2.1 - MIGRACIÓN AGENT_METADATA (DB)

## 1. Resumen Ejecutivo
Este paso inicia la **Fase 2 (Agent Panel 2.0)** encargándose de la capa de persistencia para la identidad de los agentes. Se creará la tabla `agent_metadata`, la cual servirá como el repositorio de la personalidad (SOUL) y la narrativa amigable que el usuario verá en el nuevo panel de agentes. 

El objetivo es separar la configuración técnica de ejecución (ubicada en `agent_catalog`) del contenido enriquecido y de presentación, permitiendo una personalización profunda por organización sin alterar el motor de inferencia.

## 2. Diseño Funcional Consolidado
- **Propósito**: Permitir que cada organización defina cómo se presenta y "se comporta" (narrativamente) cada rol de agente.
- **Flujo de Uso**:
    1. El sistema consulta `agent_metadata` al cargar el detalle de un agente.
    2. Si existe metadata específica, se utiliza para renderizar la "Personality Card" (Paso 2.3).
    3. Si no existe, el sistema cae de forma segura (graceful degradation) hacia los datos técnicos de `agent_catalog`.
- **Edge Cases MVP**:
    - **Roles duplicados**: La restricción de unicidad garantiza que no haya conflicto de personalidad para un mismo rol de agente en una organización.
    - **Navegación**: El esquema admite la inclusión de un `avatar_url` para mejorar la estética premium del panel.

## 3. Diseño Técnico Definitivo
- **Esquema de Tabla (`agent_metadata`)**:
    - `id`: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
    - `org_id`: `UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE`
    - `agent_role`: `TEXT NOT NULL` (Matches logic with `agent_catalog.role`).
    - `display_name`: `TEXT` (Nombre legible para humanos, ej: "Asistente de Revisión").
    - `soul_narrative`: `TEXT` (Descripción profunda del SOUL en prosa).
    - `avatar_url`: `TEXT` (Link a imagen del agente).
    - `created_at`: `TIMESTAMPTZ DEFAULT now()`
    - `updated_at`: `TIMESTAMPTZ DEFAULT now()`
- **Restricciones de Integridad**:
    - `UNIQUE(org_id, agent_role)`: Clave compuesta para evitar colisiones de personalidad.
- **Seguridad y Aislamiento**:
    - Se habilita **RLS** absoluto.
    - Política de aislamiento: `USING (org_id::text = current_setting('app.org_id', TRUE))`.
- **Optimización**:
    - Índice B-Tree en `(org_id, agent_role)` para acelerar los JOINs en el endpoint de detalle de agentes.

## 4. Decisiones
- **Vinculación por Rol vs ID**: Se confirma el uso de `agent_role` (text) + `org_id` como identificador. Esto permite que si una organización elimina y vuelve a crear a su agente "Analista", la personalidad narrativa asociada persista automáticamente.
- **Uso de JSONB vs Columnas Planas**: Se opta por columnas planas (`soul_narrative`, `display_name`) en lugar de un objeto JSON para facilitar búsquedas futuras y asegurar tipado fuerte en el backend.
- **Triggers**: Se incluirá el trigger estándar `update_timestamp` para mantener la coherencia de auditoría.

## 5. Criterios de Aceptación MVP ✅
1. **Migración Exitosa**: El archivo `020_agent_metadata.sql` se ejecuta sin errores en Supabase. [ ]
2. **Estructura de Tabla**: La tabla contiene las columnas `org_id`, `agent_role`, `soul_narrative` y `display_name`. [ ]
3. **Aislamiento Multitenant**: Un `SELECT` desde una sesión con `app.org_id = 'A'` NO debe devolver registros de la organización 'B'. [ ]
4. **Constraint de Unicidad**: Intentar insertar un segundo "analyst" en la misma organización falla con error de duplicado. [ ]
5. **Índice de Rendimiento**: Existe un índice que cubra la búsqueda por `org_id` y `agent_role`. [ ]

## 6. Plan de Implementación
1. **Tarea 1**: Crear archivo `supabase/migrations/020_agent_metadata.sql` (Baja).
2. **Tarea 2**: Configurar políticas RLS y triggers de auditoría (Baja).
3. **Tarea 3**: Ejecutar migración y verificar creación mediante `\d agent_metadata` o consola (Media).
4. **Tarea 4**: Insertar registros de prueba (Seed) para agentes "Generic" y "Flow Analyst" (Baja).

## 7. Riesgos y Mitigaciones
- **Conflictos de Naming**: Que el `agent_role` en la metadata no coincida exactamente con el del catálogo.
    - *Mitigación*: El JOIN en el Paso 2.2 debe ser insensible a mayúsculas/minúsculas y manejar espacios en blanco.
- **Riesgo de Permisos**: Que el cliente anon no pueda leer la metadata por políticas RLS restrictivas.
    - *Mitigación*: Verificar que la política incluya permiso de `SELECT` para el rol `authenticated`.

## 8. Testing Mínimo Viable
- Intentar insertar datos para una organización inexistente (debe fallar por FK).
- Consultar metadata sin configurar `app.org_id` (debe devolver 0 filas).
- Verificar que el JOIN en SQL manual funciona: `SELECT * FROM agent_catalog ac LEFT JOIN agent_metadata am ON ac.role = am.agent_role AND ac.org_id = am.org_id`.

## 9. 🔮 Roadmap (NO implementar ahora)
- **Internacionalización**: Soportar `soul_narrative_en`, `soul_narrative_es`.
- **Avatar Generator**: Integración con DALL-E para generar el avatar basado en una semilla física del SOUL.
- **Tool Overrides**: Permitir cambiar la descripción de las herramientas específicamente para un agente en esta tabla.
