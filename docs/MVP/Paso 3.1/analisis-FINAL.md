# 🏛️ ANÁLISIS TÉCNICO FINAL — Paso 3.1: Habilitar Supabase Realtime para domain_events

## 1. Resumen Ejecutivo
Este paso consiste en habilitar la infraestructura de streaming en tiempo real para la tabla `domain_events`. Actualmente, aunque el sistema captura correctamente los eventos de ejecución de los agentes, el frontend no puede visualizarlos al instante porque la tabla no está incluida en la publicación de replicación de Supabase.

La implementación habilitará `Supabase Realtime` específicamente para esta tabla, permitiendo que el dashboard y los paneles de control reciban "transcripts" (pensamientos, acciones y resultados de herramientas) con una latencia mínima (< 1s), sentando las bases para la transparencia total de la Fase 3.

## 2. Diseño Funcional Consolidado

### Happy Path
1. El backend inserta un registro en la tabla `domain_events` con un `correlation_id` (formato `ticket-{id}`).
2. La base de datos, configurada con `REPLICA IDENTITY FULL`, captura el cambio completo.
3. Supabase Realtime publica el evento vía WebSockets a los clientes suscritos.
4. El frontend recibe el payload y actualiza la UI del transcript en tiempo real.

### Edge Cases (MVP)
- **Desconexión y Reconexión:** El cliente puede perder eventos durante micro-cortes. El diseño asume que el Paso 3.2 (Snapshot Inicial) recuperará el historial completo al cargar el componente, y el Realtime cubrirá los eventos nuevos.
- **Inundación de Eventos (Flooding):** Durante ejecuciones de agentes muy "pensativos", el volumen de eventos puede ser alto. Se habilitará la tabla completa ya que el filtrado se realiza por RLS y por el cliente (vía `correlation_id`).

### Manejo de Errores
- **Fallo de Suscripción:** Si el cliente no puede conectar, se mostrará un aviso de "Conexión en tiempo real perdida" y el usuario podrá refrescar manualmente (fallback temporal).
- **Fallo de Migración:** El script se diseñará para ser idempotente, evitando bloqueos en el pipeline de CI/CD o ejecuciones manuales repetidas.

## 3. Diseño Técnico Definitivo

### Configuración de Replicación (SQL)
Se creará una migración que asegure la presencia de la tabla en la publicación de Supabase. El enfoque es **idempotente** para evitar errores si la publicación ya existe o si la tabla ya fue agregada.

```sql
-- Migration 022: Enable Supabase Realtime for domain_events
-- Purpose: Add domain_events to supabase_realtime publication for live streaming

-- 1. Asegurar REPLICA IDENTITY FULL (Esencial para recibir el record completo en el stream)
ALTER TABLE domain_events REPLICA IDENTITY FULL;

-- 2. Añadir domain_events a la publicación de forma segura
DO $$
BEGIN
    -- Verificar si la publicación estándar de Supabase existe
    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        -- Verificar si la tabla ya está en la publicación
        IF NOT EXISTS (
            SELECT 1 FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public'
              AND tablename = 'domain_events'
        ) THEN
            ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
        END IF;
    ELSE
        -- Si por alguna razón no existe, crearla con esta tabla
        CREATE PUBLICATION supabase_realtime FOR TABLE domain_events;
    END IF;
END $$;

-- 3. Documentación técnica en DB
COMMENT ON TABLE domain_events IS 'Tabla de Event Sourcing. Debe estar en supabase_realtime para el streaming de transcripts.';
```

### Seguridad y Aislamiento
- **RLS (Row Level Security):** Supabase Realtime respeta automáticamente las políticas RLS. No se requieren cambios en las políticas actuales de `domain_events` ya que filtran por `org_id`.
- **Contrato de Filtro:** El frontend **DEBE** suscribirse utilizando el canal `realtime:public:domain_events` y aplicar un filtro por `correlation_id` para evitar tráfico innecesario en el cliente.

## 4. Decisiones Tecnológicas

| Componente | Decisión | Justificación |
|------------|----------|---------------|
| **Publicación** | `supabase_realtime` | Se utiliza el canal estándar por defecto del ecosistema Supabase para mayor compatibilidad con las herramientas del Dashboard. |
| **Identity** | `REPLICA IDENTITY FULL` | Garantiza que el suscriptor reciba todos los campos del evento, no solo la PK. Crucial para mostrar el `payload` del transcript. |
| **Migración** | SQL Idempotente (PL/pgSQL) | Evita fallos en ambientes donde la tabla ya esté habilitada parcialmente o donde la publicación tenga nombres distintos. |

## 5. Criterios de Aceptación MVP ✅

### Funcionales
- [ ] Un usuario autenticado recibe notificaciones de nuevos eventos en `domain_events` sin refrescar la página.
- [ ] La latencia entre la inserción en DB y la recepción en el cliente es inferior a 1 segundo.

### Técnicos
- [ ] La tabla `domain_events` aparece en la consulta: `SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';`.
- [ ] La tabla tiene configurado `REPLICA IDENTITY` como `FULL`.
- [ ] No existen errores en los logs de Supabase Realtime al realizar suscripciones.

### Robustez
- [ ] **Aislamiento Multi-tenant:** Un cliente de la Org A **no** recibe eventos de la Org B (Validado por RLS).
- [ ] El script de migración puede ejecutarse 2 veces seguidas sin lanzar errores de "exists".

## 6. Plan de Implementación

| # | Tarea | Descripción | Complejidad |
|---|-------|-------------|-------------|
| 1 | **Migración SQL** | Crear y ejecutar `supabase/migrations/022_enable_realtime_events.sql`. | Baja |
| 2 | **Verificación DB** | Validar presencia en `pg_publication_tables`. | Baja |
| 3 | **Script de Test** | Crear `LAST/test_3_1_realtime.py` para validar streaming y RLS. | Media |
| 4 | **Dashboard Sync** | Verificar visualmente el toggle en Supabase Dashboard. | Baja |

## 7. Riesgos y Mitigaciones

- **Riesgo:** Supabase Realtime está deshabilitado globalmente en las settings del proyecto.
    - **Mitigación:** Paso 4 del plan incluye verificación visual obligatoria en la consola.
- **Riesgo:** El volumen de eventos degrada el rendimiento del socket.
    - **Mitigación:** Solo se habilitan eventos de dominio (no logs de debug técnicos).

## 8. Testing Mínimo Viable
1. **Prueba de Replicación:** `INSERT INTO domain_events` manual y verificar recepción en un cliente local (`supabase-py` o terminal).
2. **Prueba de Seguridad:** Crear evento con `org_id` de un segundo tenant y verificar que el cliente del primer tenant **no** lo recibe.

## 9. 🔮 Roadmap (No implementar ahora)
- **Publicaciones Dedicadas:** En el futuro, crear una publicación `realtime_transcripts` separada para optimizar el canal.
- **Broadcast sin persistencia:** Para logs de depuración (pensamientos internos "raw" que no necesiten guardarse permanentemente).
- **Throttling en Cliente:** Si el volumen crece, implementar buffers en el frontend para evitar saturar el thread de UI.
