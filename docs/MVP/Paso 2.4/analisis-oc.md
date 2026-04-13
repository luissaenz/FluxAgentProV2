# Análisis Técnico — Paso 2.4

## 📋 Datos del Paso

- **Paso:** 2.4 [Frontend] — Refactorizar pestaña de "Credenciales y Herramientas"
- **Objetivo:** Utilizar la metadata del `tool_registry` para mostrar descripciones claras de qué hace cada herramienta asignada al agente.
- **Estado en `estado-fase.md`:** ✅ COMPLETADO

---

## 1. Diseño Funcional

### Happy Path

El usuario visualiza el perfil de un agente y accede a la pestaña "Herramientas y Capacidades":

1. El componente `AgentToolsCard` recibe `allowedTools` (lista de herramientas del agente) y `credentials` (del backend).
2. Para cada herramienta, consulta `getToolMetadata(toolName)` del registry estático.
3. Agrupa las herramientas por su primer tag (`category`) para organización visual.
4. Renderiza un grid de tarjetas donde cada tarjeta muestra:
   - Nombre legible (`displayName`)
   - Descripción narrativa (`description`)
   - Badge "Aprobación" si `requiresApproval: true`
   - Badge "Credencial" si la herramienta está en la lista de credenciales del backend
   - Tags visuales (máx. 3, luego "+N")
   - Timeout en segundos si está definido
5. Si hay `credentialDescription` del backend, la muestra en un pie de tarjeta con alerta.

### Edge Cases

| Scenario | Comportamiento |
|----------|----------------|
| `allowedTools` vacío | Muestra estado vacío con icono y mensaje "Sin herramientas configuradas" |
| Herramienta no en registry | Usa fallback: formatea nombre técnico y descripción genérica |
| Credencial sin descripción | No muestra el pie de alerta de credencial |
| Loading state | Muestra skeleton grid de 4 tarjetas |

### Manejo de Errores

- Si el registry no tiene la herramienta: fallback automático (no rompe UI).
- Si credentials viene vacío/null: el set está vacío, no muestra badges de credencial.

---

## 2. Diseño Técnico

### Componentes Involved

| Archivo | Rol |
|---------|-----|
| `dashboard/components/agents/AgentToolsCard.tsx` | Componente principal, renderiza grid de herramientas |
| `dashboard/lib/tool-registry-metadata.ts` | Mapa estático con metadata de herramientas del dominio Bartenders |

### Extensiones de Modelos

**No requiere.** El paso usa metadata estática del frontend (no DB).

### Integración con Contratos Existentes

- **Input:** `AgentToolsCardProps` recibe `allowedTools: string[]` y `credentials: Array<{ tool: string; description: string | null }>`.
- El contrato de `GET /agents/{id}/detail` ya devuelve `credentials` según `estado-fase.md`.
- El componente no necesita cambios en la API.

---

## 3. Decisiones

| Decisión | Justificación |
|----------|----------------|
| Metadata estática en frontend (en lugar de endpoint dinámico) | Evita añadir nuevos endpoints al backend en este sprint. El dominio Bartenders es cerrado y已知. |
| Fallback automático para herramientas desconocidas | Previene UI break si se agregan herramientas nuevas sin actualizar el mapa. |
| Agrupación por primer tag como categoría | Proporciona organización visual sin sobrecomplicar la estructura de datos. |

---

## 4. Criterios de Aceptación

- ✅ El grid de herramientas se renderiza con `displayName` legible (no nombre técnico)
- ✅ La descripción narrativa aparece debajo del nombre
- ✅ Badge "Aprobación" aparece solo cuando `requiresApproval: true`
- ✅ Badge "Credencial" aparece solo cuando la herramienta está en el array `credentials` del backend
- ✅ Las herramientas se agrupan por categoría (primer tag)
- ✅ Estado vacío visible cuando `allowedTools` está vacío
- ✅ Skeleton de carga visible durante `isLoading: true`
- ✅ Herramientas no registry muestran fallback formateado

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|-------------|
| Nueva herramienta agregada al backend sin actualizar el registry estático | El fallback automático evita break; en siguiente sprint, considerar endpoint de metadata dinámico. |
| Tags no definidos para herramienta | Usa "Sin categoría" como default. |

---

## 6. Plan

### Tareas de Implementación (Si no estuviera completado)

1. **Crear mapa estático de metadata** (`tool-registry-metadata.ts`) — Baja complejidad
   - Dependencias: Ninguna
2. **Implementar componente `AgentToolsCard.tsx`** — Media complejidad
   - Dependencias: Mapa de metadata, librería de badges (shadcn)
3. **Integrar en pestaña de agente** — Baja complejidad
   - Dependencias: Componente creado

**Estado Actual:** El paso ya está implementado y funcionales según `estado-fase.md`. El componente `AgentToolsCard` integra correctamente la metadata del registry para mostrar descripciones claras de herramientas.

---

## 🔮 Roadmap (NO implementar ahora)

- **Metadata dinámica desde backend:** Cuando el registry crezca más allá de Bartenders, migrar el mapa a un endpoint `/tools/metadata` para evitar mantener sincronización manual.
- **Búsqueda y filtrado:** Añadir input de búsqueda dentro del grid de herramientas.
- **Test de integración E2E:** Validar que las descripciones mostradas coinciden con el behavior real de cada herramienta.