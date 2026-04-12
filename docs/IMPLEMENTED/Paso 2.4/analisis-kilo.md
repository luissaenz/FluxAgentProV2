# Análisis Técnico - Paso 2.4: Refactorizar pestaña de "Credenciales y Herramientas"

## 1. Diseño Funcional

### Happy Path
1. El usuario navega a la página de detalle de un agente específico (`/agents/{id}`)
2. En la pestaña "Información", se muestra la `AgentPersonalityCard` seguida de `AgentToolsCard`
3. `AgentToolsCard` recibe la lista de `allowed_tools` del agente y las `credentials` del backend
4. Se agrupan las herramientas por categoría basada en el primer tag de metadata
5. Para cada herramienta, se muestra una tarjeta con:
   - Nombre legible (displayName)
   - Descripción narrativa
   - Badges indicadores (Aprobación, Credencial, Timeout)
   - Tags adicionales (máximo 3 + indicador de más)
   - Descripción de credencial si aplica

### Edge Cases
- **Sin herramientas asignadas:** Se muestra estado vacío con icono y mensaje explicativo
- **Herramienta sin metadata:** Fallback a nombre formateado y descripción genérica
- **Herramienta con muchos tags:** Muestra primeros 3 + contador de restantes
- **Credenciales faltantes:** Herramientas sin credencial no muestran badge ni descripción de credencial
- **Loading state:** Skeleton loader durante carga de datos

### Manejo de Errores
- Si `allowedTools` es null/undefined, se trata como array vacío
- Metadata faltante usa fallbacks seguros sin romper la UI
- Componente es resistente a datos corruptos del backend

## 2. Diseño Técnico

### Componentes Nuevos/Modificaciones
- **Nuevo:** `AgentToolsCard.tsx` en `dashboard/components/agents/`
- **Modificación:** `lib/tool-registry-metadata.ts` - Añadido mapa estático de metadata para herramientas conocidas
- **Integración:** Modificado `agents/[id]/page.tsx` para incluir `AgentToolsCard` en la pestaña "Información"

### Interfaces (Inputs/Outputs)
**AgentToolsCard Props:**
- `allowedTools: string[]` - Lista de nombres técnicos de herramientas permitidas
- `credentials: Array<{tool: string, description: string | null}>` - Credenciales del backend
- `isLoading?: boolean` - Flag para mostrar skeletons

**ToolMetadata Interface:**
- `displayName: string`
- `description: string`
- `tags?: string[]`
- `requiresApproval?: boolean`
- `timeoutSeconds?: number`

### Modelos de Datos
- Sin cambios en modelos backend existentes
- Frontend usa `TOOL_REGISTRY_METADATA` como mapa estático centralizado
- Compatible con contratos existentes del endpoint `GET /agents/{id}/detail`

### APIs/Endpoints
- Utiliza datos existentes del endpoint `GET /agents/{id}/detail` (campos `agent.allowed_tools` y `credentials`)
- No requiere nuevos endpoints backend

## 3. Decisiones

### Decisiones Técnicas Tomadas
1. **Metadata Frontend:** Se optó por mapa estático en lugar de nuevo endpoint backend para evitar scope creep en Fase 2
2. **Categorización por Tags:** Agrupación visual usando primer tag de metadata para mejor organización
3. **Badges Contextuales:** Solo mostrar badges relevantes (Aprobación, Credencial) para no sobrecargar UI
4. **Fallback Robusto:** Sistema de fallbacks para herramientas sin metadata sin romper experiencia
5. **Diseño Responsive:** Grid adaptativo (1 columna mobile, 2 desktop) usando Tailwind responsive

### Justificaciones
- **Mapa Estático:** Reduce complejidad backend y mantiene MVP focused. Las herramientas conocidas del dominio Bartenders están mapeadas.
- **Categorización:** Mejora navegación visual sin requerir cambios backend.
- **Badges Selectivos:** Prioriza información crítica sobre exhaustividad.
- **Fallbacks:** Garantiza resiliencia ante herramientas nuevas no mapeadas.
- **Responsive:** Sigue estándares de accesibilidad y UX del proyecto.

## 4. Criterios de Aceptación
- El componente `AgentToolsCard` se renderiza correctamente en la pestaña "Información" de agentes
- Las herramientas muestran nombres legibles en lugar de nombres técnicos
- Las descripciones narrativas explican claramente qué hace cada herramienta
- Los badges de "Aprobación" aparecen solo en herramientas que requieren aprobación humana
- Los badges de "Credencial" aparecen solo cuando hay credencial asociada en el backend
- Las herramientas se agrupan por categorías basadas en sus tags
- El estado de carga muestra skeletons apropiados durante fetch
- El estado vacío muestra mensaje explicativo cuando no hay herramientas
- Las descripciones de credenciales se muestran cuando están disponibles
- El componente es responsive y funciona en mobile y desktop

## 5. Riesgos
- **Metadata Desactualizada:** El mapa estático puede quedar obsoleto si se añaden nuevas herramientas backend. *Mitigación:* Documentar proceso de actualización del mapa en README técnico.
- **Performance con Muchas Herramientas:** Grid puede saturarse visualmente con >20 herramientas. *Mitigación:* Implementar paginación/virtualización en roadmap si se confirma necesidad.
- **Dependencia de Backend:** Cambios en estructura de `credentials` pueden romper integración. *Mitigación:* Tests unitarios del componente con mocks.
- **Consistencia Multi-tenant:** Metadata compartida entre orgs podría filtrar información. *Mitigación:* Verificado que metadata es solo de frontend y no contiene datos sensibles.

## 6. Plan
1. **Baja:** Crear mapa estático `TOOL_REGISTRY_METADATA` en `lib/tool-registry-metadata.ts` con herramientas conocidas del dominio
2. **Baja:** Implementar función `getToolMetadata()` con fallbacks seguros
3. **Media:** Crear componente `AgentToolsCard` con grid responsive y lógica de agrupación por categorías
4. **Baja:** Implementar componente interno `ToolCard` con badges contextuaes y layout optimizado
5. **Baja:** Añadir estados de loading y empty state con skeletons y mensajes apropiados
6. **Baja:** Integrar `AgentToolsCard` en `agents/[id]/page.tsx` pasando props correctos
7. **Baja:** Testing manual: Verificar renderizado correcto con datos de prueba
8. **Baja:** Testing visual: Confirmar responsive design en diferentes viewports

**Dependencias:** Requiere Paso 2.2 completado (backend con `allowed_tools` y `credentials`)

## 🔮 Roadmap (NO implementar ahora)
- **Paginación/Virtualización:** Para agentes con muchas herramientas (>20)
- **Búsqueda/Filtrado:** Campo de búsqueda dentro del componente para localizar herramientas específicas
- **Metadata Dinámica:** Endpoint backend para metadata de herramientas, eliminando mapa estático
- **Tooltips Interactivos:** Hover con ejemplos de uso o parámetros de cada herramienta
- **Analytics de Uso:** Tracking de qué herramientas son más visualizadas por usuarios
- **Modo Edición:** Permitir administradores editar descripciones customizadas por organización