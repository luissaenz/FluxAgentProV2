# Análisis Técnico — Paso 2.3: Implementar componente `AgentPersonalityCard.tsx`

**Agente:** qwen
**Fecha:** 2026-04-12
**Fase:** 2 — Agent Panel (SOUL)

---

## 1. Diseño Funcional

### Happy Path
1. El usuario navega a `/agents/[id]` desde la lista de agentes.
2. La página carga los datos del agente (Supabase directo) y el detalle enriquecido (REST API `GET /agents/{id}/detail`).
3. En la pestaña **"Información"**, el componente `AgentPersonalityCard.tsx` se renderiza **por encima** de la tarjeta de "Configuración".
4. El componente muestra:
   - **Avatar** (si existe `avatar_url`) o un placeholder con la inicial del `display_name`.
   - **Display name** como título principal (reemplaza el `role` crudo como identidad visible).
   - **Soul narrative** como texto legible, renderizado con párrafos o viñetas según el contenido.
   - **Role** como badge secundario (contexto técnico, no identidad principal).
5. Si el agente **no tiene metadata** (`soul_narrative` es null/empty), el componente muestra un estado vacío con mensaje: *"Este agente aún no tiene una personalidad narrativa definida."*

### Edge Cases
| Caso | Comportamiento |
|------|---------------|
| `soul_narrative` es null o string vacío | Se muestra `EmptyState` con ícono de `Bot` y mensaje informativo. No se rompe la UI. |
| `avatar_url` es null o URL inválida | Se renderiza un avatar placeholder con la primera letra del `display_name` sobre fondo gradiente. |
| `display_name` no existe (fallback del backend) | El backend ya garantiza `display_name` como fallback (`role.replace("-", " ").title()`). El componente lo usa tal cual. |
| `soul_narrative` contiene markdown básico | Se renderiza como texto plano con saltos de línea respetados (`whitespace-pre-line`). **MVP no parsea markdown.** |
| Carga asíncrona | Se muestra `Skeleton` con la misma forma del card mientras `useAgentDetail` no ha respondido. |

### Manejo de Errores
- Si `useAgentDetail` falla (error de red, auth), la página ya maneja el estado de error a nivel de React Query. El componente no necesita retry propio — solo responde a los estados `isLoading`, `isError`, `data` del hook padre.
- Si `avatar_url` apunta a un recurso que no carga, el `onError` del `<img>` hace fallback al placeholder de inicial.

---

## 2. Diseño Técnico

### Componente: `AgentPersonalityCard.tsx`

**Ubicación:** `dashboard/components/shared/AgentPersonalityCard.tsx`

**Props:**
```typescript
interface AgentPersonalityCardProps {
  displayName: string
  role: string
  soulNarrative: string | null
  avatarUrl: string | null
  isLoading: boolean
}
```

**Estructura visual:**
```
┌─────────────────────────────────────────────┐
│ [Avatar]  DisplayName                       │
│           Badge: role                       │
├─────────────────────────────────────────────┤
│  soul_narrative (texto narrativo,           │
│   whitespace-pre-line, text-sm)             │
└─────────────────────────────────────────────┘
```

**Implementación interna:**
- Usa `Card`, `CardContent` de shadcn/ui.
- Avatar: `div` circular de 48px con gradiente (`bg-gradient-to-br from-violet-500 to-indigo-600`) y texto centrado (primera letra de `displayName`, uppercase, `text-lg font-semibold text-white`). Si hay `avatarUrl`, renderiza `<img>` con `onError` fallback.
- DisplayName: `text-lg font-semibold`.
- Role badge: `Badge variant="outline"`.
- Soul narrative: `text-sm text-muted-foreground whitespace-pre-line`.

### Modificación: `agents/[id]/page.tsx`

**Cambios:**
1. Importar `AgentPersonalityCard` y `Skeleton` (ya importado).
2. Extraer los campos enriquecidos del objeto `detail.agent` (que ya incluye `display_name`, `soul_narrative`, `avatar_url` inyectados por el backend).
3. Renderizar `AgentPersonalityCard` dentro del `TabsContent value="info"`, **antes** del Card de "Configuración".
4. El título de la página (h1) pasa de mostrar `agent.role` a mostrar `detail?.agent?.display_name ?? agent.role` — esto da identidad humana inmediatamente al cargar.
5. El Accordion de "SOUL Definition (Prompt)" se **mantiene** para desarrolladores que quieran ver el JSON crudo, pero se mueve **después** de la tarjeta de personalidad.

**Jerarquía visual resultante en Tab "Información":**
```
1. AgentPersonalityCard (nuevo — narrativa visual)
2. Card: Configuración (existente — datos técnicos)
3. Accordion: SOUL Definition JSON (existente — para devs)
```

### Tipos

No se requieren cambios en `types.ts`. El `AgentDetail` ya devuelve `agent` que es de tipo `Agent`, y el backend inyecta los campos extras (`display_name`, `soul_narrative`, `avatar_url`) directamente en el objeto. TypeScript los trata como propiedades dinámicas — se acceden con indexación segura: `detail.agent.display_name`, etc.

Para tipado estricto, se puede extender `Agent` en `types.ts` con campos opcionales, pero **no es necesario para el MVP** — el acceso seguro con `?? null` es suficiente.

---

## 3. Decisiones

| Decisión | Justificación |
|----------|---------------|
| **No parsear markdown en `soul_narrative`** | El MVP necesita mostrar texto legible, no un renderer markdown. `whitespace-pre-line` maneja saltos de línea naturales sin añadir dependencia (`react-markdown`). Se puede añadir después. |
| **Avatar placeholder con gradiente** | Evita dependencia de librerías de avatar (como `react-avatar`). El gradiente `from-violet-500 to-indigo-600` coincide con la paleta dark-mode del proyecto. |
| **Mantener el Accordion JSON para devs** | Los ingenieros necesitan ver el `soul_json` crudo para debugging. No eliminar esta capacidad; solo cambiar su jerarquía visual. |
| **No crear un hook nuevo** | `useAgentDetail` ya devuelve los campos enriquecidos. El componente solo necesita props — no lógica de fetching propia. |
| **Card en lugar de sección libre** | Sigue el patrón existente de shadcn/ui en el proyecto. Coherencia visual garantizada. |

---

## 4. Criterios de Aceptación

- [ ] El componente `AgentPersonalityCard.tsx` existe en `dashboard/components/shared/`.
- [ ] El componente acepta las props: `displayName`, `role`, `soulNarrative`, `avatarUrl`, `isLoading`.
- [ ] Cuando `soulNarrative` tiene contenido, se muestra como texto legible dentro de un Card.
- [ ] Cuando `soulNarrative` es null/vacío, se muestra un EmptyState con mensaje en español.
- [ ] Cuando `avatarUrl` es null, se muestra un avatar placeholder con la inicial del displayName.
- [ ] Cuando `avatarUrl` existe pero falla la carga (onError), se hace fallback al placeholder.
- [ ] La página `agents/[id]/page.tsx` renderiza `AgentPersonalityCard` en la pestaña "Información" antes que la card de Configuración.
- [ ] El h1 del página muestra `display_name` cuando está disponible, fallback a `role` si no.
- [ ] Se muestra Skeleton mientras `useAgentDetail` está cargando.
- [ ] El Accordion de SOUL Definition JSON se mantiene accesible debajo de la tarjeta de personalidad.
- [ ] No hay errores de TypeScript al compilar (`npm run build` pasa sin errores).

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|-----------|
| **El backend inyecta campos dinámicos que TypeScript no reconoce** | Acceso seguro con `?.` y `?? null`. Si el tipado causa problemas en build, añadir campos opcionales a la interfaz `Agent` en `types.ts`. |
| **`soul_narrative` viene con formato inconsistente (JSON, HTML, texto)** | El backend ya lo define como `text` en la migración 020. MVP asume texto plano. Si llega JSON stringified, se muestra tal cual — es un bug de datos, no de UI. |
| **Avatar URL externa causa CORS o mixed-content** | El `onError` fallback cubre el caso visual. Para producción, validar que las URLs sean HTTPS en el backend. |
| **El componente se siente "desconectado" del resto de la página** | Usar las mismas clases de Card, spacing (`space-y-4`), y paleta de colores que los componentes existentes. |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Crear `dashboard/components/shared/AgentPersonalityCard.tsx` con toda la lógica de renderizado (avatar, displayName, narrative, empty state) | Baja | — |
| 2 | Modificar `dashboard/app/(app)/agents/[id]/page.tsx`: importar componente, extraer campos enriquecidos de `detail.agent`, insertar en Tab "Información", actualizar h1 | Baja | Tarea 1 |
| 3 | (Opcional) Extender interfaz `Agent` en `types.ts` con `display_name?`, `soul_narrative?`, `avatar_url?` para tipado estricto | Baja | — |
| 4 | Verificar build sin errores: `cd dashboard && npm run build` | Media | Tareas 1, 2 |
| 5 | Verificación visual: navegar a `/agents/[id]` con un agente que tenga metadata y uno que no | Baja | Tareas 1, 2 |

**Orden recomendado:** 1 → 3 → 2 → 4 → 5

---

## 🔮 Roadmap (NO implementar ahora)

- **Markdown/Rich Text rendering:** Si `soul_narrative` evoluciona a formato rico, integrar `react-markdown` o un renderer de bloques.
- **Avatar personalizado:** Permitir upload de imagen real con crop, almacenada en Supabase Storage.
- **Editabilidad:** Un botón de "Editar personalidad" que abra un modal para modificar `soul_narrative` y `display_name` desde el frontend (actualmente solo lectura).
- **Animación de entrada:** Framer Motion para que la tarjeta aparezca con fade-in suave.
- **Tipado estricto del agente enriquecido:** Crear interfaz `AgentEnriched` que extienda `Agent` con los campos de metadata de forma explícita, en lugar de acceso dinámico.
- **Internacionalización:** Si el sistema se traduce, `soul_narrative` debería soportar versiones por idioma.
