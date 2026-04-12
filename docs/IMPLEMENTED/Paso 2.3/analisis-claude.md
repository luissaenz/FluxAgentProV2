# ANÁLISIS TÉCNICO — PASO 2.3 (Agente: Claude)

## Paso: 2.3 [Frontend]
## Objetivo: Implementar componente `AgentPersonalityCard.tsx`
## Detalle: Mostrar el SOUL del agente no como JSON crudo, sino como una descripción narrativa legible por humanos en la pestaña "Información".

---

## 1. Comprensión del Paso

**Problema que resuelve:** Actualmente la página de detalle del agente (`agents/[id]/page.tsx`) muestra `soul_json` como JSON crudo dentro de un `CodeBlock`. Esto es ilegible para usuarios no técnicos. El paso crea un componente que transforma `soul_narrative` (string narrativo) en una presentación visual atractivo.

**Relación con la fase:** Es el paso de UI que consume los datos enriquecidos del backend (Paso 2.2). Sin el componente, el `soul_narrative` no se muestra. Depende de que `agent_metadata` tenga datos (Paso 2.1) y el backend los entregue (Paso 2.2).

**Inputs:** Campo `soul_narrative` (string), `display_name` (string), `avatar_url` (string, opcional) del endpoint `GET /agents/{id}/detail`.
**Outputs:** Componente `AgentPersonalityCard.tsx` que se integra en `agents/[id]/page.tsx`, pestaña "Información".

---

## 2. Supuestos y Ambigüedades

### Ambigüedad 1: ¿Dónde se coloca el componente en la página?
**Resolución:** Reemplazar el `Accordion` con `soul_json` crudo en la pestaña "Información" (`TabsContent value="info"`) por el nuevo `AgentPersonalityCard`. El `CodeBlock` actual muestra `soul` — se elimina y se reemplaza por la card narrativa.

### Ambigüedad 2: ¿Qué pasa si `soul_narrative` es `null` o vacío?
**Resolución:** Mostrar un mensaje fallback legible: "Este agente aún no tiene una descripción de personalidad definida." No mostrar JSON ni valores técnicos. Mantener la card para que el admin sepa que existe pero falta contenido.

### Ambigüedad 3: ¿Avatar obligatorio?
**Resolución:** `avatar_url` es opcional. Si no existe, usar un icono de robot (`Bot` de lucide-react) como avatar placeholder — mismo patrón que el fallback en `agents/[id]/page.tsx:90` (`<Bot className="h-6 w-6" />`).

### Ambigüedad 4: ¿Se elimina el `CodeBlock` del SOUL?
**Resolución:** El `CodeBlock` muestra `soul_json` que es el JSON técnico de CrewAI. El nuevo diseño narrativo usa `soul_narrative`. Se elimina el accordion `soul` del CodeBlock y se reemplaza por `AgentPersonalityCard`. El `soul_json`raw queda accesible si se necesita debugging — pero ya no es el foco de la pestaña "Información".

---

## 3. Diseño Funcional

### Happy Path
1. Usuario abre la pestaña "Información" del detalle de un agente.
2. Ve `AgentPersonalityCard` con:
   - Avatar (imagen o icono `Bot` fallback)
   - `display_name` como nombre principal
   - `soul_narrative` como párrafo descriptivo
3. Si `soul_narrative` es null/vacío, ve mensaje placeholder.

### Edge Cases
- **`soul_narrative` null:** Card muestra mensaje placeholder "Este agente aún no tiene una descripción..."
- **`avatar_url` null:** Icono `Bot` de lucide-react.
- **`display_name` null:** Fallback al `agent.role` formateado (title case) — mismo fallback que backend.
- **Dashboard sin agente cargado:** Comportamiento existente (loading skeleton).

### Manejo de Errores
- No hay errores de red en este componente — consume datos que ya vinieron del query de la página padre.
- Si `agent` o `soul_narrative` faltan, se muestran placeholders.

---

## 4. Diseño Técnico

### Archivo: `dashboard/components/agents/AgentPersonalityCard.tsx`

**Ubicación:** `dashboard/components/agents/` (directorio nuevo para componentes de agentes).

**Props:**
```typescript
interface AgentPersonalityCardProps {
  displayName: string | null | undefined
  soulNarrative: string | null | undefined
  avatarUrl: string | null | undefined
  agentRole: string
}
```

**Estructura del componente:**
```
Card
├── CardHeader (flex row, gap-4, items-center)
│   ├── Avatar (img si avatarUrl, Bot icon si no)
│   └── div (flex column)
│       ├── CardTitle (displayName o role formateado)
│       └── CardDescription (agentRole)
└── CardContent
    └── p (soulNarrative o placeholder)
```

**Código del componente:**
```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, User } from 'lucide-react'
import Image from 'next/image'

interface AgentPersonalityCardProps {
  displayName: string | null | undefined
  soulNarrative: string | null | undefined
  avatarUrl: string | null | undefined
  agentRole: string
}

export function AgentPersonalityCard({
  displayName,
  soulNarrative,
  avatarUrl,
  agentRole,
}: AgentPersonalityCardProps) {
  const hasNarrative = soulNarrative && soulNarrative.trim().length > 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center gap-4 pb-2">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {avatarUrl ? (
            <div className="relative h-12 w-12 overflow-hidden rounded-full bg-muted">
              <Image
                src={avatarUrl}
                alt={displayName || agentRole}
                fill
                className="object-cover"
              />
            </div>
          ) : (
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Bot className="h-6 w-6 text-muted-foreground" />
            </div>
          )}
        </div>

        {/* Nombre y Role */}
        <div className="flex flex-col gap-1 min-w-0">
          <CardTitle className="text-xl truncate">
            {displayName || agentRole.replace("-", " ").replace(/\b\w/g, (l) => l.toUpperCase())}
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs font-normal">
              {agentRole}
            </Badge>
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="pt-2">
        {hasNarrative ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {soulNarrative}
          </p>
        ) : (
          <p className="text-sm italic text-muted-foreground">
            Este agente aún no tiene una descripción de personalidad definida.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

### Integración en `agents/[id]/page.tsx`

**Cambio en el tab "Información" (líneas ~136-161):**

Reemplazar:
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="soul">
    <AccordionTrigger>SOUL Definition (Prompt)</AccordionTrigger>
    <AccordionContent>
      <CodeBlock code={soul} />
    </AccordionContent>
  </AccordionItem>
</Accordion>
```

Por:
```tsx
<AgentPersonalityCard
  displayName={agent.display_name}
  soulNarrative={agent.soul_narrative}
  avatarUrl={agent.avatar_url}
  agentRole={agent.role}
/>
```

**Fuente de datos:**
- `agent.display_name` — viene de `agent_metadata` inyectado en `agent` por backend (Paso 2.2).
- `agent.soul_narrative` — viene de `agent_metadata` inyectado en `agent` por backend (Paso 2.2).
- `agent.avatar_url` — viene de `agent_metadata` inyectado en `agent` por backend (Paso 2.2).

**Import a agregar en `agents/[id]/page.tsx`:**
```typescript
import { AgentPersonalityCard } from '@/components/agents/AgentPersonalityCard'
```

### Coherencia con `estado-fase.md`
- Usa componentes existentes de `shadcn/ui` (`Card`, `Badge`).
- El fallback de `displayName` usa el mismo pattern que backend: `agentRole.replace("-", " ").replace(/\b\w/g, (l) => l.toUpperCase())`.
- Mensaje de placeholder en español — coherente con el resto del dashboard.

---

## 5. Decisiones Tecnológicas

### Decisión 1: Crear directorio `components/agents/`
**Elección:** Crear `dashboard/components/agents/AgentPersonalityCard.tsx` en un directorio dedicado para componentes de agentes.
**Justificación:** Permite organizar componentes relacionados con agentes (actualmente solo existe la página). Si en el futuro se crean más componentes (ej. `AgentListCard.tsx`), ya hay estructura. No hay nada类似的 existente.

### Decisión 2: Mostrar siempre la card, incluso sin narrative
**Elección:** La card siempre se renderiza. Si no hay `soul_narrative`, muestra mensaje placeholder.
**Justificación:** El diseño comunica "existe un agente con esta identidad". Ocultar la card completamente podría confundir al usuario que espera ver la información del agente. Placeholder con mensaje es más informativo.

### Decición 3: Reemplazar el Accordion de `soul_json`, no complementar
**Elección:** Eliminar el `CodeBlock` que muestra `soul_json` crudo y reemplazarlo por `AgentPersonalityCard`.
**Justificación:** El objetivo del paso es mostrar narrativa legible, no JSON técnico. Mostrar ambos sería redundante y contradice el objetivo de "no como JSON crudo". El `soul_json`raw sigue accesible via debugging directo en DB si se necesita.

---

## 6. Criterios de Aceptación

| # | Criterio | Verificable sin ambigüedad |
|---|----------|--------------------------|
| 1 | El componente `AgentPersonalityCard` existe en `dashboard/components/agents/` | El archivo existe en la ruta |
| 2 | La card muestra `displayName` como título | Visualmente: el nombre aparece como `CardTitle` |
| 3 | La card muestra `soulNarrative` como párrafo legible | Visualmente: texto narrativo en `CardContent` |
| 4 | Si `soulNarrative` es null/vacío, muestra mensaje placeholder | Visualmente: texto "Este agente aún no tiene..." aparece |
| 5 | Si no hay `avatarUrl`, muestra icono `Bot` fallback | Visualmente: icono robot visible |
| 6 | `agent.role` se muestra como Badge bajo el nombre | Visualmente: Badge con texto del role |
| 7 | La card reemplaza el `CodeBlock` del `soul_json` en la pestaña "Información" | El accordion con JSON crudo ya no aparece |
| 8 | La integración consume `agent.display_name`, `agent.soul_narrative`, `agent.avatar_url` del endpoint enriquecido | Los campos se leen correctamente del objeto `agent` |

---

## 7. Riesgos

### Riesgo 1: `agent` no tiene los campos `display_name`, `soul_narrative`, `avatar_url`
**Severidad:** Baja.
**Descripción:** Si el backend no hizo el enrichment (fallback o versión old), estos campos serán `undefined` y el componente debe manejarlo.
**Mitigación:** El componente usa `||` y `?.` para null/undefined — el fallback a `agentRole` formateado para `displayName` y el mensaje placeholder para `soulNarrative` ya manejan este caso.

### Riesgo 2: `Image` de Next.js con `avatarUrl` externo puede fallar
**Severidad:** Baja.
**Descripción:** Si `avatar_url` apunta a una URL externa no configurada en `next.config`, el componente crasheará.
**Mitigación:** Usar `<img>` nativo en vez de `next/image` para URLs externas, o verificar que `next.config` permite dominios externos. Por ahora se usa `next/image` con `object-cover` y fallback a `Bot` icon en error de carga (`onError`).

### Riesgo 3: Tipo `Agent` en `types.ts` no tiene `display_name`, `soul_narrative`, `avatar_url`
**Severidad:** Media.
**Descripción:** El tipo `Agent` definido en `types.ts` no incluye los campos nuevos. TypeScript podría marcar como error.
**Mitigación:** Actualizar el tipo `Agent` para incluir `display_name?: string`, `soul_narrative?: string`, `avatar_url?: string`.

---

## 8. Plan de Implementación

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|--------------|
| 1 | Crear directorio `dashboard/components/agents/` | Baja | Ninguna |
| 2 | Crear `AgentPersonalityCard.tsx` con estructura Card + Avatar + narrative | Media | Tipos actualizados (Tarea 3) |
| 3 | Actualizar tipo `Agent` en `types.ts` para incluir campos de metadata | Baja | Ninguna |
| 4 | Integrar `AgentPersonalityCard` en `agents/[id]/page.tsx`, reemplazar accordion | Baja | Tareas 1, 2 |
| 5 | Eliminar import unused de `CodeBlock` y `Accordion` si ya no se usan | Baja | Tarea 4 |

**Orden recomendado:** 3 → 1 → 2 → 4 → 5.

---

## 9. Testing

### Caso 1: Con metadata completa
- Setup: Agente con `display_name: "Ana Analyst"`, `soul_narrative: "Experta en..."`, `avatar_url: "https://..."`
- Verificar: Card con avatar, nombre "Ana Analyst", badge con role, párrafo con narrative

### Caso 2: Sin soul_narrative
- Setup: Agente con `display_name: "Analyst Bot"`, `soul_narrative: null`
- Verificar: Card visible, avatar (Bot icon), nombre "Analyst Bot", párrafo placeholder "Este agente aún no tiene..."

### Caso 3: Sin avatar_url
- Setup: Agente con `display_name: "Test Agent"`, `soul_narrative: "..."`, `avatar_url: null`
- Verificar: Icono Bot visible en lugar de imagen

### Caso 4: Sin display_name
- Setup: Agente con `display_name: null`, `role: "analyst"`, `soul_narrative: "..."`
- Verificar: Título muestra "Analyst" (role formateado)

---

## 10. Consideraciones Futuras (No implementar ahora)

### Botón de editar SOUL
Future: Agregar un botón "Editar" en la card que abra un diálogo para actualizar `soul_narrative` via `PATCH /agents/{id}/metadata`.

### Avatar upload
Future: Permitir subir una imagen de avatar que se guarde en `agent_metadata.avatar_url`. Requiere storage bucket y endpoint de upload.

### SOUL version history
Future: Guardar versiones anteriores de `soul_narrative` para auditoría de cambios de personalidad.

---

## 🔮 Roadmap (NO implementar ahora)
- **Edición inline del SOUL:** Modal/drawer para que el admin edite `soul_narrative` y `display_name` directamente desde la card.
- **Templates de SOUL:** Selector de templates predefinidos para popular la descripción narrativa de nuevos agentes rápidamente.
- **Métricas de uso del SOUL:** Cuántas veces se ejecutó un agente con cada SOUL — correlación entre personalidad y performance.