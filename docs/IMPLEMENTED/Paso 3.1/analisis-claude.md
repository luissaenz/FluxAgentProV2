# Analisis Tecnico — Paso 3.1: Habilitar Supabase Realtime para domain_events

## 1. Diseno Funcional

### 1.1 Comprension del Paso

| Aspecto | Detalle |
|--------|---------|
| **Problema** | La tabla `domain_events` existe y tiene RLS configurado, pero no esta incluida en la publicacion `supabase_realtime`. Los clientes frontend no pueden suscribirse a eventos en tiempo real. |
| **Input** | Tabla `domain_events` con estructura completa, indices y RLS habilitado. |
| **Output** | La tabla `domain_events` pertenece a la publicacion `supabase_realtime`, habilitando suscripcion desde clientes. |
| **Rol en Fase** | Prerrequisito infrastructural. Sin este paso, los pasos 3.2-3.5 no pueden funcionar. Es el gate de entrada a la fase de realtime. |

### 1.2 Happy Path

1. Ejecutar `ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;`
2. Verificar en Supabase Dashboard (Database > Replication) que la tabla aparece como "Realtime enabled"
3. Verificar con consulta SQL: `SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';`
4. Un cliente autenticado establece conexion de streaming y recibe INSERT en tiempo real
5. RLS aplica automaticamente en tiempo real (org_id filtering)

### 1.3 Edge Cases

| Caso | Manejo |
|------|--------|
| Tabla no tiene `REPLICA IDENTITY` configurado | Realtime no funcionara. El script de migracion 008_org_members.sql line 71 configuro `REPLICA IDENTITY FULL` globalmente. Si se creo una tabla posterior sin esto, se require `ALTER TABLE domain_events REPLICA IDENTITY FULL;` |
| Cliente sin auth intenta subscribe | Supabase Realtime filtra por RLS. El cliente sin token no recibe nada. Silencioso. |
| Alta frecuencia de eventos (flooding) | Frontend debe manejar throttling/debounce. Backend no implementa rate control. |
| Cliente se reconecta durante ejecucion activa | Cliente obtiene snapshot inicial (Paso 3.2) y luego subscribe. El gap se recupera via snapshot. |

### 1.4 Manejo de Errores

| Escenario | Que ve el usuario/cliente |
|----------|---------------------------|
| Fallo al agregar tabla a publicacion | Error SQL returned by Supabase. Requiere intervencion manual en Supabase Dashboard. |
| Tabla no aparece en pg_publication_tables | Verificar: (1) Nombre exacto de tabla, (2) Permisos de superuser en Supabase. |
| Cliente no recibe eventos | Verificar: (1) Auth token valido, (2) Tabla habilitada en Supabase, (3) RLS permite acceso al org_id. |

---

## 2. Diseno Tecnico

### 2.1 Componente/Nuevo

**SQL Script de habilitacion (migracion):**

```sql
-- Habilitar domain_events en la publicacion supabase_realtime
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
```

**Script de verificacion posterior:**

```sql
-- Verificar que domain_events esta en la publicacion
SELECT 
    schemaname, 
    tablename 
FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime' 
AND tablename = 'domain_events';
```

### 2.2 Verificaciones Previas (Estado Actual)

| Verificacion | Estado | Archivo/Linea |
|-------------|--------|---------------|
| Tabla `domain_events` existe | ✅ EXISTS | migration 001:87 |
| RLS habilitada | ✅ ON | migration 001:117 |
| Policy `domain_events_org_access` | ✅ EXISTS | migration 001:118 |
| `REPLICA IDENTITY FULL` | ⚠️ CONFIGURED EN 008 | migration 008:71 (global) |
| `correlation_id` existe en tabla | ✅ EXISTS | migration 021:7 |
| Indice `idx_domain_events_correlation` | ✅ EXISTS | migration 021:11 |
| Indices existentes | ✅ CONFIGURED | idx_domain_events_aggregate, idx_domain_events_org |

### 2.3 Extensiones de Modelo de Datos

**NINGUNA.** La estructura actual soporta realtime sin modificaciones de esquema.

### 2.4 Integraciones

| Componente | Tipo | Descripcion |
|-----------|------|-------------|
| Supabase Realtime | Publicacion DB | Habilitacion de tabla en `supabase_realtime` publication |
| Supabase Dashboard | Verificacion | GUI para verificar habilitacion |
| Frontend Clients | Suscriptor | Suscripcion via `@supabase/supabase-js` client (Paso 3.3) |

---

## 3. Decisiones

| Decision | Justificacion |
|---------|----------------|
| Usar `ALTER PUBLICATION` declarativo | Approach versionable y replicable en nuevos ambientes. Preferido sobre click-in-Dashboard. |
| Habilitar realtime a nivel de tabla completa | Los eventos completos son necesarios para reconstruir transcript. No hay datos sensibles adicionales en columnas. |
| No modificar RLS existente | Las policies vigentes (`domain_events_org_access`) aplican automaticamente a realtime. No requiere cambio. |
| No crear publicacion nueva | Se reutiliza `supabase_realtime` existente siguiendo convenciones Supabase. |

---

## 4. Criterios de Aceptacion

- [ ] El comando `ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;` ejecuta sin error
- [ ] La consulta `SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';` muestra `domain_events` en la columna `tablename`
- [ ] La tabla aparece habilitada en Supabase Dashboard (Settings > API > Database > Replication)
- [ ] Un cliente autenticado puede establecer conexion de streaming a `realtime:public:domain_events`
- [ ] Un INSERT en `domain_events` es recibido por el cliente suscriptor en < 1 segundo
- [ ] Los eventos filtrados por `org_id` son los unicos recibidos por el cliente (verificacion de RLS aplicada en realtime)

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigacion |
|-------|--------------|---------|------------|
| `REPLICA IDENTITY` no configurado para domain_events | Baja | Alta | Verificar con `ALTER TABLE domain_events REPLICA IDENTITY FULL;` si el script falla. |
| RLS bloquea realtime silently | Baja | Alta | Verificar con cliente autenticado en Paso 3.3 antes de cerrar. Policy existente, solo verificar que aplica. |
| Fallback a polling si realtime no funciona | Media | Baja | Paso 3.5 incluye test de latencia. Si falla, se implementa polling fallback en componente frontend. |
| Supabase no tiene realtime habilitado en proyecto | Baja | Alta | Verificar en Supabase Dashboard > Settings > Database > Replication. Si no existe, crear publicacion manualmente. |

---

## 6. Plan

### Tareas Atomicas

| # | Tarea | Complejidad | Dependencia |
|---|-------|-------------|-----------|
| 1 | Ejecutar script SQL de habilitacion | Baja | Ninguna |
| 2 | Verificar con consulta `pg_publication_tables` | Baja | 1 |
| 3 | Verificar habilitacion en Supabase Dashboard | Baja | 1 |
| 4 | Ejecutar test delatencia 3.5 para validar extremo a extremo | Media | 1, 2, 3 |

### Estimacion

- **Complejidad:** Baja (1 comando SQL + verificacion)
- **Esfuerzo:** 15-30 minutos
- **Bloqueador:** No. Solo requiere acceso a Supabase con permisos de publicacion.

---

## Seccion Final: Roadmap (NO implementar ahora)

| Item | Razon para postergar |
|------|---------------------|
| Habilitar realtime en otras tablas (tasks, snapshots) | No requerido hasta Fase 4+. Solo domain_events es necesario para transcripts en MVP. |
| Custom filtering server-side | Supabase realtime filtra por RLS. Suficiente para MVP. |
| WebSocket multiplexing | Un canal por execution es suficiente para MVP. |
| Event retention policies | Configurable en Supabase. Por ahora usar defaults. |
| Publicacion dedicada para domain_events | `supabase_realtime` es suficiente para MVP. Separar despues si hay conflictos de throughput. |

---

*Documento generado por proceso de analisis tecnico. Paso 3.1 — Habilitar Supabase Realtime.*
*Idioma: Espanol.*
