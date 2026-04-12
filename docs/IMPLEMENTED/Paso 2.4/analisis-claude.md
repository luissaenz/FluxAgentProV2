# Análisis Técnico - Paso 2.4: Refactorizar pestaña de "Herramientas" (Metadata-driven UI)

## 1. Diseño Funcional

### Happy Path
1. El usuario navega a `/agents/[id]` y selecciona la pestaña **"Herramientas"**
2. `AgentToolsCard` recibe `allowed_tools` (del agente) y `credentials` (del endpoint enriquecido)
3. Cada herramienta se renderiza como tarjeta con:
   - Nombre legible (`displayName` del mapping)
   - Descripción narrativa (`description`)
   - Badges contextuales: "Aprobación" (ámbar), "Credencial" (azul)
   - Tags visuales (máx 3 + contador)
   - Indicador de timeout
4. Las herramientas se agrupan por categoría (primer tag)
5. Estado vacío si no hay herramientas

### Edge Cases (MVP)
- **Herramienta sin metadata en mapa estático:** Fallback con nombre formateado (snake_case → Title Case) y descripción genérica
- **Herramienta sin credencial:** No muestra badge de credencial ni descripción asociada
- **Muchas tags (>3):** Limita a 3 y muestra `+N`
- **Loading:** Skeleton con grid 2 columnas

### Manejo de Errores
- Si `allowedTools` es null/undefined → treat as empty array
- Metadata corrupta → fallback seguro sin romper UI
- Credenciales faltantes → Badge omitido, no error

---

## 2. Diseño Técnico

### Componentes Modificados
- **`dashboard/components/agents/AgentToolsCard.tsx`** — Creado
  - Grid responsive (1 col mobile, 2 cols desktop)
  - Función `groupToolsByCategory()` por primer tag
  - Componente interno `ToolCard` con layout completo

### Metadata Registry
- **`dashboard/lib/tool-registry-metadata.ts`** — Creado
  - `TOOL_REGISTRY_METADATA`: mapa estático de 8 herramientas del dominio Bartenders
  - `getToolMetadata()`: getter con fallback automático
  - `formatToolName()`: formateador snake_case → Title Case

### Interfaces
```typescript
interface ToolMetadata {
  displayName: string
  description: string
  tags?: string[]
  requiresApproval?: boolean
  timeoutSeconds?: number
}

interface AgentToolsCardProps {
  allowedTools: string[]
  credentials: Array<{ tool: string; description: string | null }>
  isLoading?: boolean
}
```

### Integración en agents/[id]/page.tsx
- `AgentToolsCard` ubicado en `TabsContent value="info"` (pestaña "Informacion")
- Props: `allowedTools={agent.allowed_tools || []}` y `credentials={credentials}`

### Decisión: Mapa Estático vs Endpoint Backend
- **Elección:** Mapa estático en frontend
- **Justificación:** Evita nuevo endpoint en Fase 2, mantiene MVP focused
- **Contrato coherente:** No contradice ningún contrato existente en `estado-fase.md`

---

## 3. Decisiones

| Decisión | Justificación |
|----------|----------------|
| Mapa estático frontend | Elimina dependencia de nuevo endpoint backend en sprint actual |
| Agrupación por primer tag | Categorización simple sin cambios en modelo de datos |
| Badges contextuales selectivos | Evita sobrecarga visual; solo información crítica |
| Fallback robusto | Garantiza UI funcional aunque metadata esté incompleta |
| Grid responsive 2 cols | Consistente con diseño Shadcn/Tailwind del dashboard |
| Animaciones premium (Framer Motion) | Eleva percepción de calidad según estándar "Premium UI" |

---

## 4. Criterios de Aceptación

- [x] `AgentToolsCard` renderiza en pestaña "Información" del agente
- [x] Nombres legibles en lugar de técnicos (mapeados desde registry)
- [x] Descripciones narrativas claras para herramientas conocidas
- [x] Badge "Aprobación" (ámbar) visible solo cuando `requiresApproval: true`
- [x] Badge "Credencial" (azul) visible solo cuando existe en `credentials` del backend
- [x] Agrupación por categorías basada en tags
- [x] Loading state con skeletons coherentes
- [x] Empty state con mensaje explicativo e icono `Wrench`
- [x] Descripción de credencial visible cuando existe
- [x] Diseño responsive (mobile/desktop)
- [x] Componente libre de errores de compilación TypeScript

---

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Metadata desactualizada con nuevas herramientas | Media | Bajo | Proceso de actualización documentado; fallback muestra nombre formateado |
| Performance con >20 herramientas | Baja | Medio | Grid responsivo + animaciones ligeras; virtualización en roadmap si es necesario |
| Inconsistencia entre credentials backend y frontend | Baja | Medio | Tests unitarios con mocks verifican contratos |
| Tool registry no cubre todas las herramientas | Media | Bajo | Fallback robusto: nombre formateado + descripción genérica |

---

## 6. Plan

### Tareas Implementadas (Completado ✅)

1. **[Baja]** Crear `tool-registry-metadata.ts` con mapa estático de 8 herramientas Bartenders
2. **[Baja]** Implementar `getToolMetadata()` y `formatToolName()` con fallbacks
3. **[Media]** Crear `AgentToolsCard.tsx` con grid, grouping y ToolCard interno
4. **[Baja]** Integrar `AgentToolsCard` en `agents/[id]/page.tsx`
5. **[Baja]** Verificar compilación TypeScript sin errores
6. **[Baja]** Testing visual end-to-end

### Dependencias
- Requiere **Paso 2.2** (backend enriquecido con `allowed_tools` y `credentials`)

---

## 🔮 Roadmap (NO implementar ahora)

- **Endpoint dinámico de metadata:** Backend sirve metadata de herramientas, eliminando mapa estático
- **Paginación/Virtualización:** Para agentes con >20 herramientas
- **Búsqueda/Filtrado:** Campo de búsqueda dentro del componente
- **Tooltips interactivos:** Hover con ejemplos de uso y parámetros
- **Iconos personalizados por herramienta:** Mapping de iconos Lucide
- **Modo edición admin:** Permiti configurar descripciones customizadas por org
