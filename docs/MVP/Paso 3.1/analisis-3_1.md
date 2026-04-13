# 🔬 ANÁLISIS TÉCNICO — Paso 3.1: Habilitar Supabase Realtime para domain_events

## 1. Diseño Funcional

### 1.1 Comprensión del Paso

| Aspecto | Detalle |
|--------|---------|
| **Problema** | Los clientes frontend no pueden recibir eventos en tiempo real. La tabla `domain_events` existe pero no está incluida en la publicación de Supabase Realtime. |
| **Input** | Tabla `domain_events` existente con estructura completa y RLS configurada. |
| **Output** | La tabla `domain_events` queda incluida en la publicación `supabase_realtime`, permitiendo suscripción desde clientes. |
| **Rol en Fase** | Habilita la infraestructura de streaming necesaria para los pasos 3.2-3.5. Es prerequisito técnico. |

### 1.2 Happy Path

1. Se ejecuta ALTER PUBLICATION para agregar `domain_events` a `supabase_realtime`
2. Se verifica que Supabase Console muestra la tabla como "Realtime enabled"
3. Un cliente de test puede conectarse y recibir inserts en tiempo real
4. Los filtros RLS se aplican correctamente en tiempo real (solo eventos del tenant autenticado)

### 1.3 Edge Cases

| Caso | Manejo |
|------|--------|
| Cliente sin auth intenta subscribe | Supabase Realtime ignora silenciosamente eventos fuera del tenant. El cliente simplemente no recibe eventos. |
| Tabla tiene RLS pero REPLICA IDENTITY no está configurado | PREEXISTENTE: La migración 008 ya configuró `REPLICA IDENTITY FULL`. No action needed. |
| Alta frecuencia de eventos ( flooding ) | El frontend debe manejar throttling. El backend no implementa control de rate. |
| Cliente se reconecta durante ejecución activa | El cliente debe obtener snapshot inicial (3.2) + luego subscribe. El gap se recupera vía snapshot. |

### 1.4 Manejo de Errores

| Escenario |Qué ve el usuario / cliente |
|----------|------------------------|
| Fallo al agregar tabla a publicación | Error SQL returned by Supabase. No es recoverable programáticamente. Requiere intervención manual en Supabase Dashboard. |
| Cliente no recibe eventos | Verificar: (1) Auth token válido, (2) Tabla habilitada en Supabase, (3) RLS permite acceso al org_id. |

---

## 2. Diseño Técnico

### 2.1 Componente/Nuevo

**SQL Script de habilitación:**

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;
```

### 2.2 Verificaciones Previas Requeridas

| Verificación | Estado | Notas |
|-------------|--------|-------|
| Tabla existe | ✅ EXISTS | Definida en migration 001_set_config_rpc.sql:87 |
| RLS habilitada | ✅ ON | Policy `tenant_select_domain_events` existe (migration 002 y 010) |
| REPLICA IDENTITY FULL | ✅ CONFIGURED | Seteado en migration 008_org_members.sql:71 |
| correlation_id existe | ✅ EXISTS | Agregado en migration 021 |
| Índices existentes | ✅ CONFIGURED | idx_domain_events_aggregate, idx_domain_events_org, idx_domain_events_correlation |

### 2.3 Extensiones de Modelo de Datos

**NINGUNA.** La estructura actual soporta realtime sin modificaciones.

### 2.4 Integraciones

| Componente | Tipo | Descripción |
|-----------|------|-------------|
| Supabase Realtime | Publicación DB | Habilitación de tabla en `supabase_realtime` publication |
| Frontend Clients | Suscriptor |will subscribe vía `@supabase/supabase-js` client |

---

## 3. Decisiones

| Decisión | Justificación |
|---------|----------------|
| Usar `ALTER PUBLICATION` en lugar de Dashboard | Approach declarativo, versionable y replicable en nuevos ambientes. |
| Habilitar realtime a nivel de tabla, no columna | Los eventos completos son necesarios para reconstruir transcript. No hay datos sensibles adicionales en payload. |
| No modificar RLS existente | Las policies vigentes (`tenant_select_domain_events`) aplican automáticamente a realtime. No requiere cambio. |

---

## 4. Criterios de Aceptación

- [ ] El comando `ALTER PUBLICATION supabase_realtime ADD TABLE domain_events;` ejecuta sin error
- [ ] La tabla aparece habilitada en Supabase Dashboard (Settings > API > Table supabase_realtime toggle)
- [ ] Un cliente autenticado puede establecer conexión de streaming
- [ ] Un INSERT en `domain_events` es recibido por el cliente en < 1 segundo
- [ ] Los eventos filtrados por `org_id` son los únicos recibidos (verificación de RLS applied)

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|-------|--------------|---------|------------|
| RLS bloquea realtime silently | Baja | Alta | Verificar con cliente autenticado en step 3.3 antes de cerrar. Ya existe policy, solo verificar que aplica. |
| Fallback a polling si realtime no funciona | Media | Baja | Step 3.5 incluye test de latencia. Si falla, se implementa fallback en 3.3. |

---

## 6. Plan

### Tareas Atómicas

| # | Tarea | Complejidad | Dependencia |
|---|-------|-------------|-----------|
| 1 | Ejecutar script SQL de habilitación | Baja | Ninguna |
| 2 | Verificar habilitación en Supabase Dashboard | Baja | 1 |
| 3 | Test de suscripción con cliente autenticado | Media | 2 |

### Estimación

- **Complejidad:** Baja (1 comando SQL + verificación)
- **Esfuerzo:** 15-30 minutos
- **Bloqueador:** No. Solo requiere acceso a Supabase.

---

## 🔮 Roadmap (NO implementar en MVP)

| Item | Razón para postergar |
|------|---------------------|
| Habilitar realtime en otras tablas (tasks, snapshots) | No requerido hasta Fase 4+. Por ahora solo domain_events es necesario para transcripts. |
| Custom filtering server-side | Supabase realtime filtra por RLS. Suficiente para MVP. |
| WebSocket multiplexing | Un canal por execution es suficiente para MVP. |
| Event retention policies | Configurable en Supabase. Por ahora usar defaults. |

---

*Documento generado por proceso de análisis técnico. Paso 3.1 — Habilitar Supabase Realtime.*