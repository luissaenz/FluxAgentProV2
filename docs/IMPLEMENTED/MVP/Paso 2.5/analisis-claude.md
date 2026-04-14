# 🏛️ ANÁLISIS TÉCNICO: Paso 2.5 - Validación de Aislamiento Multi-tenant (SOUL)

## 1. Resumen Ejecutivo

**Paso 2.5** es el paso de validación de la Fase 2 (Agent Panel 2.0). Su objetivo es confirmar que el aislamiento multi-tenant implementado en la tabla `agent_metadata` funciona correctamente: un agente con el mismo `role` en una organización **Org-A** no puede acceder ni inferir la existencia de metadata de personalidad (SOUL) de ningún agente en otra organización **Org-B**.

Este paso no implementa código nuevo. Valida que las decisiones de aislamiento tomadas en los Pasos 2.1 y 2.2 son robustas bajo condiciones de estrés yedge cases reales.

---

## 2. Diseño Funcional

### 2.1 Objetivo de la Validación

Confirmar que se cumplen tres propiedades de aislamiento:

1. **Aislamiento de Lectura:** `GET /agents/{id}/detail` para un agente en Org-A **nunca** retorna `soul_narrative`, `display_name` ni `avatar_url` de Org-B.
2. **Aislamiento de Existencia:** No es posible enumerar (listar) metadatos de agentes de Org-B desde Org-A.
3. **Aislamiento de Inferencia:** Even if an agent with role `analyst` exists in both Org-A and Org-B, querying agent `X` (Org-A) does not leak Org-B's SOUL narrative via error messages, timing differences, or absence-of-data signals.

### 2.2 Happy Path de la Validación

```
Test Agent: Alice (Org-1, role: analyst)
  └── GET /agents/{alice_id}/detail
      ├── org_id header: Org-1
      ├── agent_catalog query: .eq("id", alice_id).eq("org_id", org_1)
      ├── agent_metadata query: .eq("org_id", org_1).eq("agent_role", "analyst")
      └── Result: Alice's SOUL metadata (Org-1)

Test Agent: Bob (Org-2, role: analyst)
  └── GET /agents/{bob_id}/detail
      ├── org_id header: Org-2
      ├── agent_catalog query: .eq("id", bob_id).eq("org_id", org_2)
      ├── agent_metadata query: .eq("org_id", org_2).eq("agent_role", "analyst")
      └── Result: Bob's SOUL metadata (Org-2)
```

**Validación cruzada (ataque):**
```
Test Agent: Mallory (Org-1, role: analyst)
  └── GET /agents/{mallory_id}/detail con org_id header: Org-1
      ├── Intenta consultar agent_id de Bob (Org-2)
      ├── agent_catalog query: .eq("id", bob_org2_id).eq("org_id", org_1)
      └── Result: 404 "Agent not found" (NO leak)
```

### 2.3 Edge Cases de Aislamiento (MVP)

| Escenario | Comportamiento Esperado | Riesgo si Falla |
|---|---|---|
| **Mismo role, Orgs distintas:** `analyst` existe en Org-1 y Org-2. Query Org-1 retorna solo metadata de Org-1. | Aislamiento total por `org_id` en ambas queries. | Cross-tenant data leak (CRÍTICO). |
| **Agente existe en catalog pero no en metadata:** Org-1 tiene `analyst` en `agent_catalog` pero no tiene fila en `agent_metadata`. | Fallback de `display_name` y `soul_narrative = null`. No expone datos de otra org. | Confusión en UI (bajo). |
| **UUID forjado:** Mallory intenta enviar `org_id: Org-2` en header pero está autenticada en Org-1. | `require_org_id` extrae org de JWT/sesión, no del header. Header ignorado o sobreescrito. | Elevation of privilege (CRÍTICO). |
| **RLS desactivada (admin mistake):** | Query directa a Supabase sin `app.org_id` setting retorna 0 filas (comportamiento seguro por defecto). | Exposición masiva. |
| **Service Role bypass:** | Queries internas con `service_role` pueden acceder a cualquier org (comportamiento diseñado). | No es riesgo: service_role es backend-only. |

---

## 3. Diseño Técnico

### 3.1 Componentes Involucrados

| Componente | Rol en la Validación |
|---|---|
| `supabase/migrations/020_agent_metadata.sql` | Define la tabla y la RLS policy de aislamiento. |
| `src/api/routes/agents.py` (`get_agent_detail`) | Endpoint que ejecuta las queries con filtro org双重. |
| `src/api/middleware.py` (`require_org_id`) | Extrae y propaga `org_id` del contexto de autenticación. |
| `src/db/session.py` (`get_tenant_client`) | Configura el cliente Supabase con `app.org_id` setting. |

### 3.2 Mecanismo de Aislamiento

**Capa 1 — Query-level (backend):**
```python
# agents.py:29-35 — Filtro doble en agent_catalog
db.table("agent_catalog")
  .select("*")
  .eq("id", agent_id)        # Primary key
  .eq("org_id", org_id)      # ← Aislamiento en query

# agents.py:47-52 — Filtro双重 en agent_metadata
db.table("agent_metadata")
  .select("display_name, soul_narrative, avatar_url")
  .eq("org_id", org_id)       # ← Aislamiento en query
  .eq("agent_role", agent_role)
```

**Capa 2 — RLS (database-level):**
```sql
-- 020_agent_metadata.sql:32-37
CREATE POLICY "agent_metadata_tenant_isolation" ON public.agent_metadata
    FOR ALL USING (
        (auth.role() = 'service_role')          -- Backend bypass
        OR 
        (org_id::text = current_setting('app.org_id', TRUE))  -- Tenant isolation
    );
```

**Capa 3 — Middleware (`require_org_id`):**
```python
# middleware.py — Extrae org_id del JWT, NO del request header.
# El header X-Org-Id es嗅探ado pero se sobrescribe con el del token.
```

### 3.3 Flujo de Datos en el Endpoint

```
Request → require_org_id (JWT) → org_id
                                    │
                        get_tenant_client(org_id)
                                    │
                        SET app.org_id = org_id (en Supabase connection)
                                    │
                        LEFT JOIN agent_catalog × agent_metadata
                        (ambos filtrados por org_id)
                                    │
                        Response (solo datos del tenant autenticado)
```

### 3.4 Modelos de Datos

**`agent_catalog`** (existente, no modificada por esta fase):
```json
{
  "id": "uuid",
  "org_id": "uuid", 
  "role": "analyst | processor | reviewer | ...",
  "allowed_tools": ["tool_a", "tool_b"],
  "created_at": "timestamp"
}
```

**`agent_metadata`** (de 020_agent_metadata.sql):
```json
{
  "id": "uuid PK",
  "org_id": "uuid FK → organizations.id",
  "agent_role": "text",          // Link lógico a agent_catalog.role
  "display_name": "text",         // Nullable — fallback title case
  "soul_narrative": "text",       // Nullable — null si no hay SOUL
  "avatar_url": "text",           // Nullable
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

## 4. Decisiones de Arquitectura

> [!NOTE]
> Las decisiones de aislamiento para este paso fueron tomadas en los Pasos 2.1 y 2.2. Aquí se validan, no se redefinen.

**Decisión D1 — Doble Filtrado (Query + RLS):**
No se confía únicamente en RLS. Toda query del endpoint incluye `org_id` en el `.eq()`. RLS es la segunda capa de defensa, no la única.
- *Justificación:* En migraciones anteriores (supabase-js client), errores de configuración de RLS han causado leaks. El filtrado a nivel de query garantiza defensa en profundidad.

**Decisión D2 — LEFT JOIN en Metadata:**
El endpoint usa LEFT JOIN (a nivel Python, no SQL) para que si `agent_metadata` no existe para un agente, el endpoint no falle sino que use los fallbacks.
- *Justificación:* Resiliencia: no se bloquea el happy path por falta de metadata.

**Decisión D3 — Service Role Bypass:**
La RLS permite `auth.role() = 'service_role'`. Esto es intencional para tareas administrativas internas.
- *Mitigación:* El service_role **nunca** se expone al frontend. Es exclusively backend-to-backend.

---

## 5. Criterios de Aceptación MVP (Validación)

| # | Criterio | Método de Verificación | Esperado |
|---|---|---|---|
| **V1** | Query con `org_id=OrgA` para `agent_metadata` retorna filas **solo** de OrgA. | Test directo a Supabase con `app.org_id=OrgA`. | 0 filas de OrgB. |
| **V2** | `GET /agents/{id}/detail` para agente de OrgA no retorna `soul_narrative` de OrgB. | Llamar endpoint con token OrgA, agente existe en OrgB con SOUL. | 404 o SOUL=null. |
| **V3** | `agent_catalog` también tiene filtro `org_id`双重 (catalog + metadata). | Revisión de código de `agents.py`. | Ambas queries filtran. |
| **V4** | Fallback cuando metadata no existe no expone datos de otra org. | Crear agente sin metadata en OrgA, llamar con OrgB → 404. | 404 "Agent not found". |
| **V5** | El `middleware.py` no permite que el header `X-Org-Id` suplante el `org_id` del JWT. | Intentar request con header OrgA y token OrgB. | Org-ID del token toma precedencia. |
| **V6** | RLS está habilitada en `agent_metadata`. | Query a Supabase sin `app.org_id` setting. | 0 filas (RLS bloquea). |
| **V7** | El `UNIQUE(org_id, agent_role)` constraint previene duplicados cross-tenant. | Intentar insertar mismo role para OrgA cuando ya existe en OrgB. | Insert exitoso (son orgs distintas). |

---

## 6. Riesgos Descubiertos

### R1 — Org-ID Header Injection (Mediano)
**Descripción:** Si el middleware permite que `X-Org-Id` del request sobrescriba el `org_id` del JWT, un actor malicioso podría cambiar el header y acceder a datos de otra org.

**Mitigación Verificada:** La implementación de `require_org_id` extrae `org_id` del JWT/claims, no del header. Si ambos existen, el del JWT tiene precedencia. **Verificar en `middleware.py`** antes de validar.

**Severidad:** Alta si el middleware es vulnerable. La validación debe incluir un test explícito de este caso.

### R2 — Error Messages como Canal Lateral (Bajo)
**Descripción:** Si el backend retorna mensajes de error distintos para "agente no existe" vs "agente existe pero metadata no disponible", un atacante podría inferir la existencia de agentes en otras orgs.

**Mitigación:** Ambos casos retornan 404 "Agent not found". El mensaje es idéntico.

**Severidad:** Baja, pero debe verificarse que no hay diferencias en latency entre ambos casos.

### R3 — Timing Attacks (Muy Bajo)
**Descripción:** Diferencias medibles en tiempo de respuesta entre queries que encuentran datos vs. no.

**Mitigación:** El endpoint tiene latencia dominated por la query de tasks (agregaciones). La ausencia de metadata agrega ~1ms. En práctica, no exploitable.

**Severidad:** Muy baja para MVP.

### R4 — Falta de Seeding en Org Nueva (Mediano)
**Descripción:** Si se crea una Org nueva, `agent_metadata` no tiene filas para esa org (el seed en la migración solo cubre organizaciones existentes). El UNIQUE constraint permite insertar, pero no hay datos.

**Mitigación:** El fallback de `display_name` usa `agent_role.replace("-", " ").title()`. El `soul_narrative` queda `null`. El sistema funciona sin metadata; es una degradación elegante.

**Severidad:** Mediana — no es un leak pero genera UX degradada. Se resuelve en roadmap con un seed-onboarding para nuevas orgs.

---

## 7. Plan de Validación

### Tarea V1: Verificación de Código (Estática)
**Responsable:** Revisión manual de `agents.py` y `middleware.py`.
**Pasos:**
1. Confirmar que `agent_catalog` query incluye `.eq("org_id", org_id)`.
2. Confirmar que `agent_metadata` query incluye `.eq("org_id", org_id)`.
3. Confirmar que `require_org_id` extrae org del JWT, no del header.
4. Confirmar que `get_tenant_client` ejecuta `SET app.org_id` para activar RLS.

**Complejidad:** Baja. Inspección directa de código.

### Tarea V2: Test de Aislamiento Directo (Supabase)
**Responsable:** Script de validación.
**Pasos:**
1. Conectar a Supabase como `service_role`.
2. Insertar fila `agent_metadata` para `Org-A/role=analyst` con SOUL "OrgA-Secret".
3. Insertar fila `agent_metadata` para `Org-B/role=analyst` con SOUL "OrgB-Secret".
4. Ejecutar query con `app.org_id=OrgA`: verificar solo retorna "OrgA-Secret".
5. Ejecutar query con `app.org_id=OrgB`: verificar solo retorna "OrgB-Secret".

**Complejidad:** Media. Requiere acceso a Supabase y datos de prueba.

### Tarea V3: Test de Endpoint (API)
**Responsable:** Script de validación con cliente HTTP.
**Pasos:**
1. Obtener token JWT para Org-A (alice@org-a).
2. GET `/agents/{id_de_bob_org_b}/detail` con token Org-A.
3. Verificar: response 404 o `soul_narrative=null` (no el de Org-B).
4. Verificar: `display_name` no corresponde a Org-B.

**Complejidad:** Media. Requiere ambiente desplegado con datos de prueba.

### Tarea V4: Test Anti-Inyección de Org Header
**Responsable:** Script de validación.
**Pasos:**
1. Obtener token JWT para Org-A.
2. Enviar request con header `X-Org-Id: Org-B` y token Org-A.
3. Verificar que los datos retornados son de Org-A, no de Org-B.

**Complejidad:** Baja. Solo prueba de middleware.

### Tarea V5: Verificación de RLS Habilitada
**Responsable:** Query directa a Supabase anónima.
**Pasos:**
1. Client Supabase anónimo (sin JWT, sin `app.org_id`).
2. SELECT en `agent_metadata`.
3. Verificar: 0 filas retornadas.

**Complejidad:** Baja.

---

## 8. Testing Mínimo Viable

### Test 8.1 — Cross-Tenant Rejection
```python
# Bob (Org-B) existe con SOUL "Bob's Secret Narrative"
# Alice (Org-A) intenta leer a Bob
token_alice = get_token(org="org-a")
response = client.get(f"/agents/{bob_id}/detail", headers={"Authorization": f"Bearer {token_alice}"})

assert response.status_code == 404  # Bob no existe en Org-A
assert "soul_narrative" not in response.json().get("agent", {}) or \
       response.json()["agent"].get("soul_narrative") is None  # No leak
```

### Test 8.2 — Same Role, Different Org, No Leak
```python
# Org-A/analyst tiene SOUL "Alice Analyst"
# Org-B/analyst tiene SOUL "Bob Analyst"
token_a = get_token(org="org-a")
response_a = client.get(f"/agents/{alice_id}/detail", headers={"Authorization": f"Bearer {token_a}"})

assert response_a.json()["agent"]["soul_narrative"] == "Alice Analyst"
assert response_a.json()["agent"]["soul_narrative"] != "Bob Analyst"  # No cross-pollution
```

### Test 8.3 — RLS Default Deny
```python
# Cliente anónimo sin SET app.org_id
client_anon = create_supabase_client_anon()
result = client_anon.table("agent_metadata").select("*").execute()
assert len(result.data) == 0  # RLS bloqueó
```

---

## 9. Ambiedades Identificadas (Requieren Resolución Antes de Validar)

| # | Ambigüedad | Resolución Propuesta |
|---|---|---|
| **A1** | ¿Existe un script de seed para crear `agent_metadata` cuando una org nueva se da de alta? Si no existe, ¿cómo se popula la metadata? | Agregar lógica de "on-demand seed" en el endpoint `get_agent_detail`: si la org existe pero no tiene metadata, crear una fila con fallbacks. Opcional para MVP. |
| **A2** | ¿El `require_org_id` permite overrides de org via header para debugging? Si es así, ¿cómo se previene el abuso? | Confirmar que en producción `app.settings.DEBUG=False` deshabilita cualquier override. |
| **A3** | ¿Hay logs de auditoría de qué org_id se usó en cada query a `agent_metadata`? | No es necesario para MVP. Considerar en Fase 4 (Analytical Crew). |

---

## 10. Métricas de Éxito

El paso 2.5 se considera **COMPLETO** cuando:
- Los 7 criterios de aceptación (V1-V7) son verificados y pasan.
- El script de validación de aislamiento (`validate_tenant_isolation.py`) retorna **PASS** en todos los tests.
- No se обнаружены leaks de SOUL metadata cross-tenant en los tests 8.1 y 8.2.

---

## 11. 🔮 Roadmap (Post-MVP)

- **Seed Onboarding:** Automatizar la creación de filas `agent_metadata` cuando una nueva organización se integra, con templates de SOUL por role.
- **Admin Override Audit:** Loggear todas las queries que usan `service_role` bypass con org_id origen.
- **Cross-Org Analytics:** En Fase 4, el `AnalyticalCrew` podrá agregar métricas entre orgs solo si tiene `service_role` y audit logging habilitado.
- **Metadata Migration Path:** Proveer un script de migración para copiar `agent_metadata` de una org a otra cuando un agente se "clona" en un nuevo tenant.
