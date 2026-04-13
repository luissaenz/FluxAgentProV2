# Análisis Técnico — Paso 2.4: Refactorizar Pestaña de "Credenciales y Herramientas"

## 1. Diseño Funcional

### Contexto Actual
El agente `qwen` ha detectado que **Paso 2.4 ya fue marcado como COMPLETADO ✅** en `estado-fase.md`. Sin embargo, al analizar la implementación actual, se identifica una **divergencia con el plan original**:

- **Plan original (mvp-Definition.md):** Una sola pestaña unificada de "Credenciales y Herramientas" que use metadata del `tool_registry` para mostrar descripciones claras.
- **Implementación actual:** Dos pestañas separadas:
  - Tab "Información" → contiene `AgentToolsCard` (muestra herramientas + badges de credencial inline).
  - Tab "Credenciales en Vault" → lista cruda de credenciales sin enriquecimiento visual.

### Problema Identificado
La pestaña **"Credenciales en Vault"** (líneas 217-249 de `agents/[id]/page.tsx`) es redundante y de baja calidad visual:
- Muestra una lista plana de `{tool, description}` sin usar la metadata del registry.
- No aporta información que no esté ya en `AgentToolsCard` (que ya muestra badge "Credencial" + descripción).
- El usuario debe navegar entre dos tabs para entender la misma información fragmentada.

### Happy Path (Refactorización)
1. El usuario entra a la vista de detalle de un agente.
2. En la pestaña "Información", ve `AgentPersonalityCard` seguido de `AgentToolsCard`.
3. `AgentToolsCard` muestra cada herramienta como tarjeta enriquecida con:
   - Nombre legible y descripción narrativa (del registry).
   - Badge "Credencial" si la herramienta tiene credencial asociada.
   - Descripción de la credencial inline (con icono de advertencia).
   - Badges de "Aprobación" y "Timeout".
4. **La pestaña "Credenciales en Vault" se elimina** porque toda la información está consolidada en `AgentToolsCard`.
5. Si el usuario quiere ver solo herramientas con credenciales, el componente ya las distingue visualmente.

### Edge Cases
- **Agente sin herramientas:** `AgentToolsCard` ya maneja el empty state con ícono y mensaje.
- **Herramienta con credencial pero sin descripción:** Se muestra el badge "Credencial" sin el bloque de descripción adicional (comportamiento actual correcto).
- **Herramienta no registrada en el registry:** Fallback a nombre formateado + descripción genérica (comportamiento actual correcto).

### Manejo de Errores
- Si la carga de credentials falla (backend error), se muestra `isLoading` state con skeletons (ya implementado).
- Si `credentials` llega como array vacío, las herramientas no muestran badge de credencial (comportamiento correcto).

---

## 2. Diseño Técnico

### Componentes Existentes
| Componente | Estado | Acción |
|---|---|---|
| `AgentToolsCard.tsx` | ✅ Implementado y funcional | **Se mantiene** como componente principal |
| `AgentPersonalityCard.tsx` | ✅ Implementado | **Se mantiene** sin cambios |
| Tab "Credenciales en Vault" | ✅ Existe pero es redundante | **Se elimina** de la page |

### Cambios en `agents/[id]/page.tsx`
1. **Eliminar** el `<TabsTrigger value="credentials">` y su `<TabsContent value="credentials">` completo (líneas 140 y 217-249).
2. **Renombrar** el tab "Informacion" → "Detalle" (opcional, mejora semántica).
3. **Mantener** `AgentToolsCard` dentro del tab "Información" con props `allowedTools` y `credentials`.

### Interfaz de Datos (sin cambios)
- `AgentDetail.credentials`: `Array<{ tool: string; description: string | null }>` — contrato vigente desde `estado-fase.md`, se respeta.
- `Agent.allowed_tools`: `string[]` — sin cambios.

### Modelo de Datos (sin cambios)
No se requiere modificación alguna en schemas, tipos ni contratos API. El backend ya envía `credentials` enriquecidos en `GET /agents/{id}/detail`.

---

## 3. Decisiones

| # | Decisión | Justificación |
|---|---|---|
| 1 | **Eliminar tab "Credenciales en Vault"** en lugar de enriquecerlo | La información ya está presente en `AgentToolsCard` con badges inline. Mantener ambos tabs genera duplicación cognitiva y fragmenta la comprensión del usuario. |
| 2 | **No modificar `AgentToolsCard`** | El componente ya cumple el objetivo del paso 2.4: usa metadata del registry, muestra descripciones claras, badges de credencial/aprobación/timeout. Está funcionalmente completo. |
| 3 | **No tocar el backend** | El contrato `GET /agents/{id}/detail` ya devuelve `credentials` correctamente. No hay ambigüedad ni deuda técnica en la capa de API. |
| 4 | **No añadir filtro "solo con credenciales"** al tab | Para MVP, la diferenciación visual (badges) es suficiente. Un toggle/filtro sería mejora de roadmap. |

---

## 4. Criterios de Aceptación

- [ ] La pestaña "Credenciales en Vault" **no existe** en la UI de detalle de agente.
- [ ] El tab "Información" (renombrado "Detalle" opcionalmente) muestra `AgentPersonalityCard` + `AgentToolsCard`.
- [ ] `AgentToolsCard` muestra herramientas con badge "Credencial" para aquellas que tienen credencial asociada.
- [ ] Las herramientas sin registro en el registry muestran nombre formateado como fallback.
- [ ] Al cargar datos, se muestran skeletons en `AgentToolsCard`.
- [ ] No hay errores de compilación (Next.js build pasa sin warnings nuevos).
- [ ] El código eliminado (tab credentials) no deja imports huérfanos (ej: `Key` de lucide-react si solo se usaba ahí).

---

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Eliminación de tab rompe tests E2E existentes | Medio | Verificar que no haya tests apuntando al tab "credentials". Si los hay, actualizarlos. |
| Pérdida de información si un usuario necesitaba la lista plana de credenciales | Bajo | Toda la info está en `AgentToolsCard`. La lista plana no añadía valor diferencial. |
| Imports huérfanos tras eliminar el tab | Bajo (linting lo detecta) | Ejecutar `next lint` o `tsc --noEmit` post-cambio para detectar unused imports. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|---|---|---|
| 1 | Eliminar `<TabsTrigger value="credentials">` y `<TabsContent value="credentials">` de `agents/[id]/page.tsx` | Baja | — |
| 2 | Limpiar imports no utilizados tras la eliminación (ej: `Key` si solo se usaba en el tab eliminado) | Baja | Tarea 1 |
| 3 | Ejecutar `tsc --noEmit` en `dashboard/` para verificar sin errores de tipo | Baja | Tarea 2 |
| 4 | Ejecutar `next lint` para verificar sin warnings | Baja | Tarea 2 |
| 5 | Verificación visual: navegar a `/agents/{id}` y confirmar que el tab "Credenciales" ya no aparece y que `AgentToolsCard` renderiza correctamente | Baja | Tarea 3, 4 |

**Total de tareas:** 5 | **Complejidad general:** Baja (refactor de UI, sin cambios de lógica ni backend).

---

## 🔮 Roadmap (NO implementar ahora)

- **Filtro/Toggle "Solo con credenciales":** Permitir al usuario filtrar las herramientas para ver solo las que requieren credencial.
- **Vista de gestión de credenciales:** UI para que un admin asocie/desasocie credenciales del Vault a herramientas del agente (actualmente la asociación viene del backend sin UI de gestión).
- **Metadata dinámica desde backend:** Mover el `TOOL_REGISTRY_METADATA` del frontend a un endpoint del backend para que las descripciones se gestionen centralizadamente y no requieran deploy del frontend para añadir herramientas nuevas.
- **Iconos por categoría de herramienta:** En lugar de tags genéricos, asignar íconos específicos (clima = 🌤️, inventario = 📦, costos = 💰) para escaneo visual más rápido.
- **Estado-fase.md:** Actualizar el estado del Paso 2.4. Si este análisis se acepta, el paso debería marcarse como "En revisión" hasta que se apliquen los cambios y se valide.
