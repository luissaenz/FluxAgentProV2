# Análisis Paso 04 — mm
**Builder visual — UI con ReactFlow**
> Agent: mm | Passo: 04 | Data: 2026-05-14

---

## 0️⃣ Verificazione contro Codice Sorgente

| # | Elemento | Verifica | Stato | Evidenza |
|---|---|---|---|---|
| 1 | Tabella `agent_catalog` | grep `004_agent_catalog.sql` | ✅ | mig 004: `role`, `soul_json`, `allowed_tools`, `max_iter` |
| 2 | Tabella `agent_templates` | grep `030_agent_templates.sql` | ✅ | mig 030: `soul_json`, `suggested_tools`, `max_iter` |
| 3 | Endpoint `GET /api/tools/available` | grep `tools.py:46` | ✅ | `ToolInfo` + `ToolsListResponse` |
| 4 | Endpoint `GET /api/templates` | grep `templates.py:54` | ✅ | `TemplateInfo` + `TemplateListResponse` |
| 5 | Endpoint `GET /api/templates/{id}` | grep `templates.py:70` | ✅ | `TemplateDetailResponse` + `soul_json` |
| 6 | `useCurrentOrg` hook | `hooks/useCurrentOrg.ts` | ✅ | `useOrganization()` |
| 7 | `createClient` Supabase | `lib/supabase.ts` | ✅ | browser client |
| 8 | `api` helper (fapFetch) | `lib/api.ts` | ✅ | Bearer token + X-Org-ID |
| 9 | UI components (Input, Textarea, Select, Switch) | `components/ui/*.tsx` | ✅ | Radix primitives |
| 10 | Badge component | `components/ui/badge.tsx` | ✅ | CVA con variant `success` |
| 11 | Sidebar nav (defaultNavItems) | `nav-main.tsx:43` | ✅ | Array di navItem |
| 12 | `agent_catalog` RLS | `004_agent_catalog.sql:22` | ✅ | `tenant_isolation` policy |

**Discrepanze trovate:**

| ID | Discrepanza | Risoluzione |
|---|---|---|
| P4-D1 | Slider component NON esiste in `components/ui/` | Installare `@radix-ui/react-slider` o usare range input nativo |
| P4-D2 | Checkbox component NON esiste | Installare `@radix-ui/react-checkbox` |
| P4-D3 | Plan dice "guardar en `agent_catalog` via Supabase directo" pero no hay endpoint POST dedicado — guardar directo via Supabase client es correcto per plan | Confermato: il frontend scrive direttamente con `supabase.from('agent_catalog').insert()` |
| P4-D4 | Plan dice ruta `/dashboard/app/builder` ma la convenzione del progetto usa `/app/(app)/builder` sotto group route | Usare `app/(app)/builder/page.tsx` (group route esistente) |

---

## 1️⃣ Analisi di Dati (ETAPA 1)

- **Schema `agent_catalog`**: `id UUID`, `org_id UUID`, `role TEXT`, `goal TEXT`, `backstory TEXT` (via `soul_json JSONB`), `allowed_tools TEXT[]`, `max_iter INT`, `is_active BOOLEAN`. Già esiste.
- **Schema `agent_templates`**: `id UUID`, `name`, `description`, `category`, `soul_json JSONB`, `suggested_tools TEXT[]`, `max_iter INT`, `is_system BOOLEAN`. Già esiste.
- **Integrità referenziale**: FK `agent_catalog.org_id → organizations.id`. RLS tenant isolation attivo.
- **RLS**: Policy `agent_catalog_tenant_isolation` — utente vede solo propri org agents.
- **Nessun nuovo schema DB richiesto** — Paso 04 legge da API esistenti e scrive su tabelle esistenti.

**Discrepanza dati:**
- Campo `model` esiste in `Agent` type (types.ts:95) ma `soul_json` è JSONB senza schema fisso. Il plan richiede `llm_provider` e `llm_model` — **NON esistono colonne dedicate**. Devono essere aggiunti a `soul_json` (senza migrazione) o come colonne separate (richiede migrazione).

---

## 2️⃣ Analisi di Codice (ETAPA 2)

**Componenti da creare (con firma e pattern):**

1. **`app/(app)/builder/page.tsx`** — pagina entry
   - Pattern: `app/(app)/agents/page.tsx` → copiare struttura, usare `useCurrentOrg`, React Query per tools e templates
   - Signature: `export default function BuilderPage()`

2. **`components/builder/AgentForm.tsx`** — form completo agente
   - Pattern: `components/flows/RunFlowDialog.tsx` (usa `react-hook-form` + `@hookform/resolvers`)
   - Campi: `role` (Input), `goal` (Textarea), `backstory` (Textarea), `llm_provider` (Select), `llm_model` (Select dinamico), `allowed_tools` (multi-select), `max_iter` (slider 1-10), `verbose` (Switch), `reasoning` (Switch), `inject_date` (Switch), `memory` (Switch)
   - Zod schema per validazione (min length su role/goal/backstory)
   - Imports: `@hookform/resolvers/zod`, `react-hook-form`, `zod`, `lucide-react`, UI components

3. **`components/builder/BuilderCanvas.tsx`** — wrapper ReactFlow (vuoto MVP)
   - Pattern: struttura canvas vuoto, sarà popolato in Paso 07
   - Signature: `export function BuilderCanvas()`

4. **`components/builder/BuilderLayout.tsx`** — layout split 60/40
   - Signature: `export function BuilderLayout({ children }: { left: React.ReactNode, right: React.ReactNode })`
   - Split CSS: flex con `flex-[60%]` e `flex-[40%]`

**Dipendenze frontend da installare:**
- `reactflow` (obbligatorio)
- `@radix-ui/react-slider` (manca nel progetto — nuovo)
- `@radix-ui/react-checkbox` (manca nel progetto — nuovo)

**Imports esatti da usare:**
```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase'
import { api } from '@/lib/api'
import { useCurrentOrg } from '@/hooks/useCurrentOrg'
import { useQuery } from '@tanstack/react-query'
```

---

## 3️⃣ Analisi di Backend (ETAPA 3)

**APIs usate dal frontend (già esistenti):**

| Endpoint | Metodo | Auth | Payload | Risposta |
|---|---|---|---|---|
| `GET /api/tools/available` | GET | `X-Org-ID` | query: `?source=&category=` | `ToolsListResponse { tools: ToolInfo[] }` |
| `GET /api/templates` | GET | None | query: `?category=` | `TemplateListResponse { templates: TemplateInfo[] }` |
| `GET /api/templates/{id}` | GET | None | path: template_id | `TemplateDetailResponse` |
| Supabase `agent_catalog` | INSERT | RLS (jwt) | `{ org_id, role, soul_json, allowed_tools, max_iter }` | row inserita |

**Note:**
- Nessun nuovo endpoint backend richiesto.
- Il frontend scrive direttamente su Supabase (RLS gestisce `org_id` dal JWT).
- `soul_json` deve contenere: `role`, `goal`, `backstory`, `llm_provider`, `llm_model`, `verbose`, `reasoning`, `inject_date`, `memory`.

---

## 4️⃣ Analisi di Fullstack + DX (ETAPA 4)

**Flujo end-to-end:**
```
User → /builder
  → GET /api/tools/available (React Query)
  → GET /api/templates (React Query)
  → Compila AgentForm (Zod validation)
  → supabase.from('agent_catalog').insert()
    → RLS inject org_id dal JWT
    → agent_catalog row creata
```

**Gaps identificati:**
1. `model` column in `agent_catalog` (types.ts:95) ma non c'è colonna DB. Il plan richiede `llm_provider`/`llm_model` — inconsistenza tra types e schema.
2. No `POST /api/agents` endpoint — frontend bypassa API e scrive direto Supabase. Funziona ma non è RESTful.
3. LLM model select dinamico (secondo provider) richiede mappatura provider → models. Nessuna API per questo — serve hardcoded map o nuovo endpoint.

### DX & Tooling (OBBLIGATORIO)

```
### Herramienta Propuesta: fap builder scaffold
- Qué automatiza: Generazione automatizzata di componenti starter per il builder (AgentForm, BuilderCanvas, BuilderLayout) basata su template. Evita boilerplate ripetitivo.
- Tipo: script / generatore CLI
- Cómo se usa: uv run python scripts/builder_scaffold.py --type agent-form --output components/builder/AgentForm.tsx
- Impacto per l'utente finale: Il developer non scrive boilerplate da zero. Genera scheletro completo con Zod schema, imports, e struttura già collegata a Supabase.
- Prioridad: Tarea 0 — implementar antes que el resto del paso
```

---

## 5️⃣ Criteri di Accettazione

```
✅ [DATA] Tabla `agent_catalog` existe con columnas correctas (004_agent_catalog.sql verificado)
✅ [CODE] `AgentForm.tsx` existe con tutti i campi del Agent CrewAI + validación Zod
✅ [CODE] `BuilderLayout.tsx` implementa split 60/40 responsive
✅ [CODE] `BuilderCanvas.tsx` wrapper ReactFlow (vuoto, listo para Paso 07)
✅ [CODE] `builder/page.tsx` ruta accesible con React Query per tools y templates
✅ [BACKEND] GET /api/tools/available retorna tools reales (verificado en tools.py)
✅ [BACKEND] GET /api/templates retorna templates (verificado en templates.py)
✅ [BACKEND] Save Agent escribe en `agent_catalog` via Supabase con RLS
✅ [FULLSTACK] Ruta /builder accesible da sidebar navigation
✅ [FULLSTACK] Validación Zod no permite guardar sin role/goal/backstory
✅ [FULLSTACK] Multi-select tools carga dal endpoint reale
✅ [DX] Script scaffold genera boilerplate boilerplate dei componenti builder
```

---

## 6️⃣ Rischi

| Rischio | Severità | Causa | Mitigazione |
|---|---|---|---|
| LLM model select dinamico senza API dedicata | Alta | Provider → models map non esiste | Hardcoded map in AgentForm o nuovo endpoint `GET /api/llm/models` |
| `soul_json` schema non validato lato DB | Media | JSONB senza constraint. Frontend può scrivere invalid JSON | Post-MVP: Pydantic validator nel seed templates |
| Checkbox e Slider component mancanti | Media | package.json non li include | Installare `@radix-ui/react-checkbox` + `@radix-ui/react-slider` |
| ReactFlow SSR issue | Media | Plan dice dynamic import per canvas | Usare `next/dynamic` con `ssr: false` per BuilderCanvas |

---

## 7️⃣ Piano di Implementazione

| # | Task | Artefatto | Interfaccia esatta | Pattern | Etapa | Compl | Tempo | Deps | Verificazione |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX: builder_scaffold.py** | `scripts/builder_scaffold.py` | `def run(tool: str, output: Path):` | — | DX | Media | 1h | Nessuna | `python scripts/builder_scaffold.py --help` senza errori |
| 1 | Install dipendenze ReactFlow + Radix | `dashboard/package.json` | aggiungere `reactflow`, `@radix-ui/react-slider`, `@radix-ui/react-checkbox` | — | CODE | Bassa | 0.5h | T0 | `npm install` senza errori |
| 2 | Creare `AgentForm.tsx` | `components/builder/AgentForm.tsx` | `export function AgentForm({ onSave, onClear }: { onSave: (data: AgentFormData) => void, onClear: () => void })` | `RunFlowDialog.tsx` (hook-form pattern) | CODE | Alta | 3h | T1 | Componente renderizza senza errori TypeScript |
| 3 | Creare `BuilderLayout.tsx` | `components/builder/BuilderLayout.tsx` | `export function BuilderLayout({ left: React.ReactNode, right: React.ReactNode })` | CSS flex split | CODE | Bassa | 0.5h | T1 | Layout 60/40 verificato con CSS |
| 4 | Creare `BuilderCanvas.tsx` | `components/builder/BuilderCanvas.tsx` | `export function BuilderCanvas()` | wrapper con placeholder | CODE | Bassa | 0.5h | T1 | Componente mounta senza crash |
| 5 | Creare `builder/page.tsx` | `app/(app)/builder/page.tsx` | `export default function BuilderPage()` | `agents/page.tsx` | FULLSTACK | Media | 2h | T2, T3, T4 | Pagina accede da `/builder`, carica tools + templates |
| 6 | Aggiungere "Builder" in sidebar | `nav-main.tsx` | aggiungere `{ title: 'Builder', url: '/builder', icon: Wand2 }` a `defaultNavItems` | esistente | FULLSTACK | Bassa | 0.5h | T5 | Sidebar mostra "Builder" |

**Tempo totale stimato:** ~7.5h

---

## 🔮 Roadmap (NO implementar ora)

- Provider → LLM models API dedicata (`GET /api/llm/models?provider=`)
- Validazione schema `soul_json` con JSON Schema constraint in DB
- Cache locale di tools/templates con React Query (`staleTime`)
- Drag-and-drop del canvas (Paso 07)

---

## 🚫 Reglas de Oro

- ✅ Analisi specifico per il passo, non tutto il sistema
- ✅ TODO verificato contro codice reale
- ✅ Discrepanze rilevate con risoluzione concreta
- ✅ DX tooling proposta
- ✅ Tabelle atomiche con interfaccia esatta e verifica inline
- ✅ Tempo stimato per ogni task