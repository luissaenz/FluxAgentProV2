# 📋 ANÁLISIS TÉCNICO — Paso 2.5: Verificación de Aislamiento Multi-tenant para SOUL

## 1. Diseño Funcional

### 1.1 Objetivo del Paso
Confirmar que el sistema de identidad de agentes (SOUL) respeta el aislamiento multi-tenant: el Agente A en la Org 1 no debe poder acceder a la metadata de personalidad del Agente A en la Org 2.

### 1.2 Happy Path de Validación
1. Usuario autenticado de **Org 1** solicita `GET /agents/{id}/detail`
2. Header `X-Org-ID: org_1` es extraído por middleware `require_org_id`
3. `get_tenant_client("org_1")` ejecuta RPC `set_config('app.org_id', 'org_1')`
4. Consulta a `agent_catalog` filtra por `org_id = 'org_1' AND id = agent_id`
5. LEFT JOIN con `agent_metadata` filtra por `org_id = 'org_1' AND agent_role = role`
6. **Resultado:** Solo retorna metadata de Org 1, nunca de Org 2

### 1.3 Edge Cases
- **Org sin metadata:** Si Org 1 no tiene entrada en `agent_metadata`, retorna `null` en `soul_narrative` (fallback OK)
- **Agente no existe:** Retorna 404 (comportamiento esperado)
- **Org diferente:** Si header es `X-Org-ID: org_2`, la query retornará metadata de Org 2, nunca la de Org 1

### 1.4 Manejo de Errores
- Si el header falta → 400 "X-Org-ID header is required"
- Si el token es inválido → 401/403 según corresponda
- Si la tabla no existe → Warning en logs, retorna sin metadata (fallback)

---

## 2. Diseño Técnico

### 2.1 Componentes Involucrados

| Componente | Rol | Archivo |
|------------|-----|---------|
| `require_org_id` | Extrae y valida `X-Org-ID` header | `src/api/middleware.py:103` |
| `get_tenant_client` | Context manager que setea `app.org_id` via RPC | `src/db/session.py:175` |
| `TenantClient` | Ejecuta `set_config('app.org_id', org_id)` antes de consultas | `src/db/session.py:112-140` |
| `agent_metadata` RLS | Política `agent_metadata_tenant_isolation` filtra por `current_setting('app.org_id')` | `supabase/migrations/020_agent_metadata.sql:32-37` |
| `GET /agents/{id}/detail` | Endpoint que combina agent_catalog + metadata con aislamiento | `src/api/routes/agents.py:13-126` |

### 2.2 Flujo de Aislamiento (detalle técnico)

```
HTTP Request
    │
    ▼
require_org_id (middleware) ──► extrae X-Org-ID
    │
    ▼
get_tenant_client(org_id) ──► set_config('app.org_id', 'org_1')
    │
    ▼
TenantClient.execute() ──► antes de cada query: set_config RPC
    │
    ▼
db.table("agent_metadata").eq("org_id", org_id) ──► RLS filtra por app.org_id
```

### 2.3 Modelo de Datos
- **Tabla:** `agent_metadata`
- **Clave única:** `(org_id, agent_role)` — impide duplicados por organización
- **RLS:** Política activa con过滤 por `app.org_id` setting

---

## 3. Decisiones

| Decisión | Justificación |
|----------|----------------|
| **RLS con `current_setting('app.org_id')`** en vez de filtrado manual | El patrón RPC/set_config es consistente con otras tablas del sistema (tasks, tickets, flows). No requiere código de filtrado manual en cada query. |
| **Fallback de metadata null** en vez de error | Si la metadata falla, el endpoint sigue funcionando retornando `display_name` desde `agent_role`. El SOUL es enhancement, no requisito crítico. |
| **LEFT JOIN en vez de INNER JOIN** | Permite mostrar el agente aunque no tenga metadata aún. La ausencia de SOUL no bloquea la operación del agente. |

---

## 4. Criterios de Aceptación

- [ ] **Aislamiento confirmado:** Consultar `agent_metadata` con `X-Org-ID: org_1` retorna solo registros de org_1
- [ ] **Aislamiento confirmado:** Consultar con `X-Org-ID: org_2` retorna solo registros de org_2
- [ ] **Fallback operativo:** Agente sin metadata retorna `soul_narrative: null` (no rompe UI)
- [ ] **Logs de error:** Si RLS falla por configuración, se registra warning en logs
- [ ] **Integridad referencial:** `agent_catalog` + `agent_metadata` linkage funciona por `agent_role` (no por ID)

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **org_id mal configurado en cliente** | Baja | Alta | El middleware valida que header no esté vacío |
| **RLS deshabilitada manualmente en Supabase** | Muy Baja | Crítica | Política existe y está habilitada; verificar en cada migration |
| **Race condition en set_config** | Baja | Media | Cada request es independiente; no hay estado compartido |

---

## 6. Plan

### Tarea 6.1: Verificación Manual de Aislamiento
**Complejidad:** Baja  
**Dependencias:** Ninguna (solo requiere acceso a dashboard y 2 organizaciones)

Pasos:
1. Autenticarse como usuario de Org 1
2. Navegar a detalle de agente (cualquiera)
3. Observar que `soul_narrative` corresponde a Org 1
4. Cerrar sesión, autenticarse como usuario de Org 2
5. Navegar al mismo agente (mismo `agent_role`)
6. Observar que `soul_narrative` es diferente (el de Org 2)

### Tarea 6.2: Verificación Programática (opcional, no MVP)
**Complejidad:** Media  
**Dependencias:** Tarea 6.1

Scripts de test:
```python
# Pseudocódigo de verificación
with get_tenant_client("org_1") as db:
    result = db.table("agent_metadata").select("soul_narrative").execute()
    # Deben ser solo registros de org_1

with get_tenant_client("org_2") as db:
    result = db.table("agent_metadata").select("soul_narrative").execute()
    # Deben ser solo registros de org_2, distintos de org_1
```

---

## 🔮 Roadmap (NO implementar ahora)

- **Audit logs de acceso a metadata:** Registrar quién consultó qué agente y cuándo (requiere tabla de auditoría)
- **Metadata edit desde UI:** Permitir a admins de org editar `soul_narrative` desde el dashboard (requiere endpoint PUT + form UI)
- **Plantillas de SOUL:** Predefinir narratives por dominio/industry para rápida configuración
- **Migración de metadata entre organizaciones:** Herramienta para clonar template de personality a nueva org