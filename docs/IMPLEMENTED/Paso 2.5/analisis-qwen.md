# Análisis Técnico — Paso 2.5: Test de Aislamiento Multi-Tenant para SOUL

## 1. Diseño Funcional

### Happy Path
1. Se crea un escenario con **dos organizaciones distintas** (Org A y Org B).
2. En cada org se registra un agente con el **mismo `agent_role`** (ej: `"analyst"`).
3. Se inserta metadata SOUL distinta en cada org para ese rol (different `soul_narrative`, `display_name`).
4. Se consulta `GET /agents/{id}/detail` con `X-Org-ID: Org A`.
5. Se verifica que **solo** se devuelve la metadata de Org A.
6. Se repite con `X-Org-ID: Org B` y se verifica que **solo** se devuelve la metadata de Org B.
7. Se confirma que **no hay fuga cruzada** de datos SOUL entre organizaciones.

### Edge Cases Relevantes para MVP
- **Mismo agent_role en distintas orgs:** El caso central. La tabla `agent_metadata` tiene UNIQUE(org_id, agent_role), pero el código debe filtrar correctamente por `org_id` antes de devolver datos.
- **Agente sin metadata:** Si un rol existe en `agent_catalog` pero no tiene entrada en `agent_metadata`, el endpoint debe devolver fallbacks (ya implementado en paso 2.2).
- **RLS deshabilitado o bypass accidental:** El `TenantClient` usa `service_role` + `set_config('app.org_id')`. Si el RPC falla silenciosamente, la política RLS podría no filtrar. El test debe verificar que el filtro se aplica a nivel de aplicación **y** RLS.

### Manejo de Errores
- Si la consulta de metadata devuelve datos de otra org (fallo catastrófico), el test **falla explícitamente** con assert que identifique la org filtrada.
- Si RLS no está activo en la tabla `agent_metadata`, el test de aislamiento directo a DB falla con mensaje claro.

---

## 2. Diseño Técnico

### Componentes Involucrados

| Componente | Rol en este paso |
|---|---|
| `GET /agents/{id}/detail` | Endpoint bajo prueba — ya implementado (paso 2.2). |
| `TenantClient` | Context manager que setea `app.org_id` via RPC. |
| `agent_metadata` RLS policy | Política `agent_metadata_tenant_isolation` que restringe por `app.org_id`. |
| Test suite | Nuevo archivo: `tests/integration/test_soul_isolation.py`. |

### Estrategia de Test

El test tiene **dos capas** de verificación:

**Capa A — Aislamiento a nivel de aplicación (Python):**
- Mock de DB que rastrea qué `org_id` se pasa a `.eq("org_id", org_id)`.
- Se verifica que la query incluye **siempre** el `org_id` del request.
- Se verifica que el resultado inyectado en `agent` corresponde exclusivamente al org consultado.

**Capa B — Aislamiento a nivel de RLS (SQL directo):**
- Con un cliente service_role, se insertan datos de prueba en dos orgs.
- Se ejecuta una query **sin** filtro de `org_id` directo (simulando bypass) para verificar que RLS bloquea.
- Se ejecuta una query con `set_config('app.org_id', org_a)` y se verifica que solo devuelve datos de Org A.

### Interfaces (Inputs/Outputs del Test)

**Inputs:**
- Dos org IDs generados (`uuid4()`).
- Dos agent roles idénticos (`"analyst"`).
- Dos `soul_narrative` distintos: `"SOUL_ORG_A"` y `"SOUL_ORG_B"`.
- Dos `display_name` distintos: `"Agent A"` y `"Agent B"`.

**Outputs verificados:**
- Response del endpoint con `agent.soul_narrative == "SOUL_ORG_A"` cuando `X-Org-ID` es Org A.
- Response del endpoint con `agent.soul_narrative == "SOUL_ORG_B"` cuando `X-Org-ID` es Org B.
- Confirmación de que `agent.soul_narrative` **nunca** contiene el valor de la org incorrecta.

### Modelo de Datos (Verificación)

La tabla `agent_metadata` ya existe (migración 020). El test **no modifica** el esquema. Solo inserta datos de prueba y verifica lecturas.

---

## 3. Decisiones

| Decisión | Justificación |
|---|---|
| **Test de integración, no unitario** | El aislamiento multi-tenant requiere verificar la interacción real entre el endpoint, el TenantClient y RLS. Un unit test con mocks no puede garantizar que RLS funciona correctamente. |
| **Dos capas de verificación (app + RLS)** | La capa de app verifica que el código filtra correctamente. La capa de RLS verifica que la política de DB está activa. Ambas son necesarias para afirmar "aislamiento garantizado". |
| **Usar FastAPI TestClient** | Permite llamar al endpoint real con headers controlados sin levantar un servidor HTTP. Ya hay patrón establecido en `test_tickets_execute.py`. |
| **No depender de Supabase real para CI** | Los tests usan mocks en CI. Se añade un marcador `@pytest.mark.requires_supabase` para ejecución opcional con DB real en validación manual. |

---

## 4. Criterios de Aceptación

- [ ] El test crea dos organizaciones con agentes del mismo `agent_role` pero distinta metadata SOUL.
- [ ] Al consultar con `X-Org-ID: Org A`, el campo `agent.soul_narrative` contiene **solo** el valor de Org A.
- [ ] Al consultar con `X-Org-ID: Org B`, el campo `agent.soul_narrative` contiene **solo** el valor de Org B.
- [ ] El test verifica que la query a `agent_metadata` incluye `.eq("org_id", org_id)` con el org correcto.
- [ ] El test de RLS directo confirma que la política `agent_metadata_tenant_isolation` está activa (`ENABLE ROW LEVEL SECURITY`).
- [ ] El test pasa en modo mock sin necesidad de Supabase real.
- [ ] Si se ejecuta con `--requires-supabase`, el test valida aislamiento con DB real.

---

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| **RLS no se puede verificar con mocks** | La capa de mocks solo verifica que el código llama con el org_id correcto. La verificación de RLS real se marca como `requires_supabase` y se ejecuta manualmente antes de deploy. |
| **El endpoint actual no devuelve `org_id` en la respuesta** | No es necesario: el test compara el `soul_narrative` devuelto contra el valor esperado de esa org. Si hay fuga, el valor será incorrecto y el assert falla. |
| **TenantClient no setea `app.org_id` correctamente** | El test de capa A verifica que `.eq("org_id", org_id)` se llama explícitamente. Si TenantClient falla, el test de capa B (RLS) lo detecta. |
| **Datos de seed conflictivos** | El test usa `uuid4()` para org IDs, evitando colisión con datos existentes. Limpieza con `DELETE` al finalizar. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|---|---|---|
| 1 | Crear `tests/integration/test_soul_isolation.py` con estructura de fixtures para dos orgs. | Baja | — |
| 2 | Implementar `test_endpoint_isolation`: llama al endpoint con cada org_id y verifica que `soul_narrative` no se filtra. | Media | Tarea 1 |
| 3 | Implementar `test_query_includes_org_id`: verifica que la cadena de query incluye `.eq("org_id", <correct_org>)`. | Baja | Tarea 1 |
| 4 | Implementar `test_rls_policy_active`: verifica via SQL directo que `agent_metadata` tiene RLS habilitado. | Media | — |
| 5 | Añadir marcador `@pytest.mark.requires_supabase` para la capa B. | Baja | Tarea 4 |
| 6 | Ejutar tests existentes para asegurar que no hay regressión. | Baja | Tareas 2-5 |

**Orden recomendado:** 1 → 2 → 3 → 4 → 5 → 6.

---

## 🔮 Roadmap (NO implementar ahora)

- **Test automatizado con Supabase real en CI:** Actualmente la verificación de RLS requiere DB real. A futuro, se puede integrar con Supabase CLI en pipeline de CI para validar RLS automáticamente.
- **Extender aislamiento a todos los endpoints:** Este test cubre `GET /agents/{id}/detail`. Debería replicarse el patrón para `GET /workflows`, `GET /tasks`, `GET /tickets`, etc.
- **Audit log de accesos cross-org:** Si algún request intenta acceder a datos de otra org (por bug o ataque), registrar el evento para detección temprana.
- **RLS con user_id:** Actualmente el aislamiento es por `org_id`. A futuro, se puede añadir filtrado por `user_id` dentro de la org para roles no-admin.
