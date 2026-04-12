# Análisis Técnico — Paso 3.1: Habilitar Supabase Realtime para `domain_events`

## 1. Diseño Funcional

### Problema que Resuelve
La tabla `domain_events` ya existe y almacena eventos de dominio correctamente, pero **no está publicada en la suscripción `supabase_realtime` de Supabase**. Sin esta habilitación, las suscripciones del frontend (`useRealtimeDashboard.ts`, `useFlowTranscript.ts`) **no reciben eventos en tiempo real** — dependen de que Supabase tenga la publicación configurada a nivel de base de datos, no solo la suscripción del cliente.

El paso 3.1 cierra esta brecha: la infraestructura de realtime debe activarse en la capa de Postgres para que los eventos INSERT/UPDATE en `domain_events` fluyan hacia los clientes suscritos.

### Happy Path
1. Se ejecuta una migración SQL que añade `domain_events` a la publicación `supabase_realtime`.
2. Supabase detecta la publicación y comienza a emitir cambios vía WebSockets.
3. Los hooks del frontend (`useRealtimeDashboard`, `useFlowTranscript`) ya configurados reciben los payloads sin cambios adicionales en el cliente.
4. Se valida que un INSERT manual en `domain_events` llega al frontend en < 1 segundo.

### Edge Cases Relevantes para MVP
- **Publicación ya existe pero la tabla no está incluida:** El `ALTER PUBLICATION` debe ser idempotente (`ADD TABLE IF NOT EXISTS` no existe en Postgres, hay que envolver en `DO $$ ... $$` o verificar antes).
- **Publicación no existe:** Hay que crearla si no fue creada previamente (algunos proyectos Supabase no la generan automáticamente).
- **Replica Identity:** La tabla ya tiene `REPLICA IDENTITY FULL` (seteado en migration 008), lo cual es correcto para que los cambios incluyan el row completo.

### Manejo de Errores
- Si la migración falla porque la publicación ya contiene la tabla, debe ser un no-op silencioso (idempotente).
- Si Supabase tiene deshabilitado Realtime a nivel de proyecto, la migración SQL se ejecuta correctamente pero el streaming no funcionará — esto se detecta en validación, no en la migración.

---

## 2. Diseño Técnico

### Componente Nuevo: Migración SQL `022_enable_realtime_domain_events.sql`

La migración debe:

1. **Verificar si la publicación `supabase_realtime` existe.**
2. **Si existe:** Añadir `domain_events` a la publicación.
3. **Si no existe:** Crear la publicación con `domain_events` incluida.
4. **Verificar `REPLICA IDENTITY`:** Confirmar que `domain_events` tiene `REPLICA IDENTITY FULL` (ya lo tiene por migration 008, pero agregar un `ALTER` idempotente como safety net).
5. **Verificación de configuración de proyecto:** Agregar un `COMMENT` documentando que Realtime debe estar habilitado en el Dashboard de Supabase → Database → Replication.

### Schema SQL Propuesto

```sql
-- Migration 022: Enable Supabase Realtime for domain_events
-- Purpose: Add domain_events to supabase_realtime publication for live streaming

-- 1. Ensure REPLICA IDENTITY FULL (idempotent)
ALTER TABLE domain_events REPLICA IDENTITY FULL;

-- 2. Add domain_events to supabase_realtime publication
--    Handle both cases: publication exists or doesn't

DO $$
BEGIN
    -- Check if publication exists
    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        -- Check if table is already in publication
        IF NOT EXISTS (
            SELECT 1 FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public'
              AND tablename = 'domain_events'
        ) THEN
            ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
        END IF;
    ELSE
        -- Create publication with domain_events
        CREATE PUBLICATION supabase_realtime
            FOR TABLE domain_events;
    END IF;
END $$;

-- 3. Document the requirement
COMMENT ON TABLE domain_events IS 'Event sourcing table. MUST be in supabase_realtime publication for live transcript streaming.';
```

### Interfaces (Inputs/Outputs)
- **Input:** Ninguno — la migración se ejecuta contra la base de datos directamente.
- **Output:** La tabla `domain_events` queda publicada en `supabase_realtime`, permitiendo que los clientes suscritos reciban eventos `INSERT`, `UPDATE`, `DELETE`.

### Coherencia con `estado-fase.md`
- El estado actual indica: *"Realtime (Fase 3): Estructura de `domain_events` existe, pero la publicación en `supabase_realtime` y la suscripción desde el frontend están pendientes."*
- Este análisis aborda exactamente esa deuda técnica.
- Los hooks del frontend (`useRealtimeDashboard.ts`, `useFlowTranscript.ts`) ya tienen la lógica de suscripción implementada — **no requieren cambios**. Solo necesitan que la publicación esté activa.

### Tablas Adicionales a Considerar
El hook `useRealtimeDashboard.ts` también se suscribe a:
- `tasks` — Debe estar en `supabase_realtime` para que el dashboard refresque estados.
- `pending_approvals` — Debe estar en `supabase_realtime` para notificaciones de aprobación.

Estas tablas **no están en el alcance de este paso**, pero se debe verificar como parte de la validación. Si no están publicadas, se creará la migración correspondiente en un paso posterior.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|----------|---------------|
| D1 | **Usar `DO $$ ... $$` para idempotencia** en vez de `ALTER PUBLICATION` directo | Evita errores en re-ejecución de migraciones. Supabase no tiene `IF NOT EXISTS` para `ALTER PUBLICATION ADD TABLE`. |
| D2 | **No modificar hooks del frontend** | Ya están correctamente implementados con `supabase.channel().on().subscribe()`. El problema es de infraestructura DB, no de cliente. |
| D3 | **Incluir `REPLICA IDENTITY FULL` como safety net** idempotente | Ya fue seteado en migration 008, pero garantizarlo aquí evita debug innecesario si alguien lo cambió. |
| D4 | **No añadir `tasks` ni `pending_approvals` en esta migración** | El paso 3.1 es específicamente para `domain_events` (transcripts). Añadir otras tablas mezclaría alcances. Se puede crear issue separado. |
| D5 | **No crear script de validación automatizado (tipo `test_3_1_*.py`)** | La validación de Realtime es inherentemente E2E (requiere frontend + WebSocket). Se valida en paso 3.5 (Test de Latencia). |

---

## 4. Criterios de Aceptación

- [ ] La migración `022_enable_realtime_domain_events.sql` existe en `supabase/migrations/`.
- [ ] La migración es **idempotente** — se puede ejecutar múltiples veces sin error.
- [ ] Tras ejecutarla, `domain_events` aparece en `pg_publication_tables` para `supabase_realtime`.
- [ ] `domain_events` tiene `REPLICA IDENTITY FULL` verificado.
- [ ] Un INSERT manual en `domain_events` dispara un evento que es recibido por un cliente suscrito vía `@supabase/supabase-js`.
- [ ] No se modificó ningún hook del frontend (solo infraestructura DB).
- [ ] La migración no altera datos existentes — solo cambia configuración de publicación.

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **R1: Realtime deshabilitado a nivel de proyecto Supabase** | La migración funciona pero no hay streaming | Verificar en Supabase Dashboard → Database → Replication que Realtime esté enabled. Documentar en `estado-fase.md`. |
| **R2: Límite de conexiones WebSocket de Supabase** | En producción con muchos usuarios concurrentes, se puede saturar el plan gratuito | Para MVP es aceptable. Si se escala, migrar a canal compartido con filtrado por `org_id` en el backend. |
| **R3: Fuga de datos entre tenants si el filter del cliente falla** | Un cliente mal configurado podría recibir eventos de otras orgs | Los filtros `org_id=eq.{orgId}` en los hooks ya previenen esto. Verificar en paso 3.5. |
| **R4: Publicación con nombre diferente** | Algunos proyectos Supabase usan `supabase_realtime`, otros `realtime` | El bloque `DO $$` verifica por nombre exacto. Si el nombre difiere, la migración creará una nueva publicación — esto es intencional y se loguea. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Crear archivo `supabase/migrations/022_enable_realtime_domain_events.sql` con el SQL idempotente descrito | Baja | Ninguna |
| 2 | Ejecutar migración local contra instancia Supabase (CLI o Dashboard) | Baja | Tarea 1 |
| 3 | Verificar con query SQL que `domain_events` está en `pg_publication_tables` | Baja | Tarea 2 |
| 4 | Ejecutar migración segunda vez para confirmar idempotencia | Baja | Tarea 3 |
| 5 | Actualizar `docs/estado-fase.md` marcando paso 3.1 como completado | Baja | Tarea 4 |

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 (secuencial, sin paralelismo).

**Estimación total:** Baja complejidad — ~15 minutos de implementación + validación.

---

## 🔮 Roadmap (NO implementar ahora)

- **Publicaciones por tabla separada:** En lugar de una sola publicación `supabase_realtime` con todas las tablas, crear publicaciones específicas por dominio (`realtime_transcripts`, `realtime_tasks`) para permitir suscripciones selectivas y reducir tráfico innecesario.
- **Filtrado de columnas en Realtime:** Supabase soporta configurar qué columnas se incluyen en los eventos. Para MVP enviamos el row completo, pero en producción se podría optimizar excluyendo payloads grandes.
- **Migración para `tasks` y `pending_approvals`:** Si se confirma que estas tablas tampoco están en `supabase_realtime`, crear migraciones dedicadas (fuera del alcance de este paso).
- **Validación automatizada E2E:** Crear un script Python que: (a) inserte un evento, (b) abra un cliente WebSocket, (c) mida latencia, (d) limpie datos. Esto sería parte del paso 3.5.
- **Fallback polling:** Si Realtime falla en producción, los hooks deberían tener un fallback de polling cada N segundos para garantizar resiliencia. No crítico para MVP.
