# 📋 ANÁLISIS TÉCNICO — Paso 2.3: AgentPersonalityCard.tsx

**Agente:** Oc (Frontend)  
**Paso:** 2.3 [Frontend]: Implementar componente `AgentPersonalityCard.tsx`  
**Objetivo:** Mostrar el SOUL del agente como narrativa legible en la pestaña "Información"

---

## 1. Diseño Funcional

### 1.1 Happy Path
El componente `AgentPersonalityCard` se renderiza en la pestaña "Información" de `AgentDetailPage`, reemplazando el Accordion que actualmente muestra el JSON crudo (`soul_json`).

**Flujo:**
1. El componente recibe props: `displayName` (string), `soulNarrative` (string | null), `avatarUrl` (string | null), `role` (string)
2. Si existe `avatarUrl`, renderiza imagen circular a la izquierda
3. Si existe `soulNarrative`, renderiza como texto legible con máximo 2-3 párrafos
4. Si NO existe `soulNarrative`, muestra estado vacío amigable: "Aún no se ha definido Personality"
5. El fallback visual usa el `role` del agente si no hay `displayName`

**Layout:** Tarjeta horizontal con Avatar + Info (nombre + narrativa). Estilo profesional, no técnico.

### 1.2 Edge Cases
- `soulNarrative` es `null` o vacío → Mostrar mensaje de "pending configuration"
- `avatarUrl` es `null` → Renderizar initials del `displayName` en un badge circular
- `displayName` vacío → Usar `role` formateado como fallback
- Narrative muy larga (>500 chars) → Truncar con "Ver más" o mostrar completo si es corto

### 1.3 Manejo de Errores
- Error de red al cargar avatar → Fallback a initials badge
- Visual: Si todo falla, mostrar solo el nombre del agente sin bloqueos

---

## 2. Diseño Técnico

### 2.1 Componente Nuevo
**Ubicación:** `dashboard/components/agents/AgentPersonalityCard.tsx`

**Interfaz:**
```typescript
interface AgentPersonalityCardProps {
  displayName?: string | null
  soulNarrative?: string | null
  avatarUrl?: string | null
  role: string
  className?: string
}
```

### 2.2 Integración en AgentDetailPage
**Archivo:** `dashboard/app/(app)/agents/[id]/page.tsx`

**Cambio línea 153-160 (Accordion SOUL):**
- Reemplazar el Accordion actual por el nuevo componente
- Extraer `displayName`, `soulNarrative`, `avatarUrl` del hook `useAgentDetail`:
  - `detail?.agent.display_name`
  - `detail?.agent.soul_narrative`
  - `detail?.agent.avatar_url`

### 2.3 Modelos de Datos
El backend ya retorna estos campos enriquecidos (ver `src/api/routes/agents.py`:
- `display_name`: string (fallback: role formateado)
- `soul_narrative`: string | null (narrativa enriquecida)
- `avatar_url`: string | null (URL de avatar)

---

## 3. Decisiones

| Decisión | Justificación |
|----------|----------------|
| Badge de iniciales si no hay avatar | UX consistente; no rompe si falta imagen |
| Truncamiento de narrativa >500 chars | Evitar layout breaking en cards pequeñas |
| Mensaje "pending" si narrativa null | Claridad para el usuario operacional |

---

## 4. Criterios de Aceptación

- [ ] `AgentPersonalityCard.tsx` se renderiza en Pestaña "Información"
- [ ] Si `soul_narrative` existe, se muestra como texto legible (no JSON)
- [ ] Si `soul_narrative` es null, muestra mensaje de pending
- [ ] Avatar o initials badge se muestra correctamente
- [ ] Fallback a `display_name` o `role` cuando faltan datos
- [ ] Diseño responsive (mobile-friendly)

---

## 5. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| El backend no retorna `display_name` aún | El fallback del backend ya injecta estos campos |
| Narrative muy larga rompe layout | CSS max-height o truncamiento |

---

## 6. Plan

| # | Tarea | Complejidad | Dependencias |
|---|-------|-------------|---------------|
| 1 | Crear `dashboard/components/agents/AgentPersonalityCard.tsx` | Media | Hook `useAgentDetail` retorna datos |
| 2 | Importar en `agents/[id]/page.tsx` | Baja | Paso 1 completo |
| 3 | Reemplazar Accordion por componente nuevo | Baja | Paso 2 completo |
| 4 | Verificar con datos reales (con/sin metadata) | Baja | Backend 2.2 verificado |

---

## 🔮 Roadmap (NO implementar ahora)

- **Avatar upload:** Permitir al usuario subir avatar desde la UI
- **Edición de narrativa:** Form para editar `soul_narrative` en tiempo real
- **Plantillas:** Ofrecer templates de narrativa predefinidos por rol
- **Markdown render:** Soportar negritas, listas en `soul_narrative`

---