# 🧠 Análisis Técnico — Paso 03: Endpoints CRUD para templates de agentes

> **Agente:** GF
> **Paso:** 3

---

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)

| # | Elemento | Verificación | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Tabla `agent_catalog` | Existe con `soul_json`, `allowed_tools`, `max_iter` | ✅ | `004_agent_catalog.sql:6-17` |
| 2 | Middleware `require_org_id` | Existe y extrae `X-Org-ID` | ✅ | `src/api/middleware.py:143` |
| 3 | Router registration pattern | Directo en `main.py` | ✅ | `src/api/main.py:98-112` |
| 4 | Global tables pattern | `service_catalog` (global) | ✅ | `024_service_catalog.sql:8` |
| 5 | Naming de migraciones | Siguiente disponible: `030` | ✅ | `ls supabase/migrations` (hasta 029) |
| 6 | `get_service_client` | Bypass RLS para lecturas globales | ✅ | `src/db/session.py:55` |

**Discrepancias encontradas:**
1. **RLS en el plan:** El plan menciona "lectura pública". En FAP, "público" suele significar "cualquier organización autenticada". No se usará `tenant_isolation` sino una política de lectura abierta para usuarios autenticados.
2. **Ubicación del router:** El plan sugiere registrar en `src/api/__init__.py`, pero el patrón real es `src/api/main.py`.

---

## 1️⃣ Análisis de Datos (ETAPA 1)

### Schema: Tabla `agent_templates`
Se creará una tabla global para almacenar los templates predefinidos del builder.

```sql
CREATE TABLE IF NOT EXISTS agent_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT NOT NULL,      -- 'Research', 'Development', 'Support', etc.
    soul_json       JSONB NOT NULL,     -- { "role": str, "goal": str, "backstory": str }
    suggested_tools TEXT[] DEFAULT '{}',
    max_iter        INTEGER DEFAULT 3,
    is_system       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### RLS Policies
- **SELECT**: Permitido para cualquier usuario autenticado (anon/authenticated).
- **INSERT/UPDATE/DELETE**: Solo `service_role`.

```sql
ALTER TABLE agent_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "templates_read_all" ON agent_templates
    FOR SELECT USING (true);

CREATE POLICY "templates_write_service_role" ON agent_templates
    FOR ALL USING (auth.role() = 'service_role');
```

---

## 2️⃣ Análisis de Código (ETAPA 2)

### Modelos Pydantic (`src/api/routes/templates.py`)

```python
class AgentTemplateInfo(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    category: str
    soul_json: Dict[str, str]
    suggested_tools: List[str]
    max_iter: int
    is_system: bool

class TemplatesListResponse(BaseModel):
    templates: List[AgentTemplateInfo]
    count: int
```

### Imports exactos
```python
from uuid import UUID
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from src.api.middleware import require_org_id
from src.db.session import get_service_client
```

---

## 3️⃣ Análisis de Backend (ETAPA 3)

### Endpoints

1. **`GET /api/templates`**
   - **Filtros:** `category: Optional[str]`
   - **Auth:** `require_org_id` (para asegurar que es una request de una org válida)
   - **Lógica:** Consulta directa a `agent_templates` usando `service_client` (o `anon_client` si RLS lo permite).

2. **`GET /api/templates/{id}`**
   - **Auth:** `require_org_id`
   - **Lógica:** Retorna el template o 404.

### Ejemplo Response (Happy Path)
```json
{
  "templates": [
    {
      "id": "...",
      "name": "Research Agent",
      "category": "Research",
      "soul_json": {
        "role": "Researcher",
        "goal": "Find latest papers...",
        "backstory": "You are a PhD..."
      }
    }
  ],
  "count": 1
}
```

---

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)

### Herramienta Propuesta: `fap templates seed`
- **Qué automatiza:** Inserción de los 8 templates iniciales y futuros templates del sistema sin usar SQL manual.
- **Tipo:** CLI command (sub-comando de `fap`)
- **Cómo se usa:** `uv run python -m src.cli.main templates seed`
- **Impacto para el usuario final:** Facilita el setup inicial del builder en nuevos entornos (dev/prod).
- **Prioridad:** Tarea 0.

### Flujo End-to-End
1. **Migración:** Crea la tabla.
2. **Seed:** Popula con 8 templates base.
3. **API:** Expone `GET` para el Dashboard.
4. **UX:** El builder consumirá estos templates para autocompletar el `AgentForm` (Paso 05).

---

## 5️⃣ Criterios de Aceptación

- ✅ [DATA] Tabla `agent_templates` creada con migración `030_agent_templates.sql`.
- ✅ [DATA] RLS configurado (Lectura pública, escritura protegida).
- ✅ [BACKEND] Endpoint `GET /api/templates` funciona con filtro por categoría.
- ✅ [BACKEND] Endpoint `GET /api/templates/{id}` retorna 404 si no existe.
- ✅ [DX] Comando `fap templates seed` inserta los 8 templates iniciales.
- ✅ [FULLSTACK] Los templates retornados incluyen `soul_json` completo.

---

## 6️⃣ Riesgos

| Riesgo | Severidad | Causa | Mitigación |
|---|---|---|---|
| Inconsistencia de campos | Media | El builder espera campos que no están en el template | Sincronizar `AgentTemplateInfo` con `AgentForm` del Paso 04 |
| Templates duplicados en seed | Baja | Ejecutar seed varias veces | Usar `ON CONFLICT (name) DO UPDATE` en el seed |
| Latencia en listado | Baja | Muchos templates en el futuro | Añadir paginación básica si `count > 100` |

---

## 7️⃣ Plan de Implementación

| # | Tarea | Artefacto | Interfaz exacta | Patrón a seguir | Etapa | Complejidad | Tiempo Est. | Dependencias | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 0 | **DX**: Comando seed | `src/cli/commands/templates.py` | `def seed_templates()` | `scripts/seed_system_bundles.py` | DX | Media | 1h | Ninguna | `fap templates seed --help` |
| 1 | Migración SQL | `supabase/migrations/030_templates.sql` | Tabla `agent_templates` + RLS | `004_agent_catalog.sql` | DATA | Baja | 0.5h | Tarea 0 | Ver tabla en Supabase |
| 2 | Modelos y Router | `src/api/routes/templates.py` | `GET /api/templates`, `GET /{id}` | `src/api/routes/integrations.py` | BACKEND | Media | 1h | Tarea 1 | `pytest -k templates` |
| 3 | Registro Router | `src/api/main.py` | `from .routes.templates import router` | `src/api/main.py:112` | BACKEND | Baja | 0.2h | Tarea 2 | `/api/templates` responde |
| 4 | Ejecutar Seed | — | `fap templates seed` | — | FULLSTACK | Baja | 0.3h | Tarea 0-1 | `GET /api/templates` count >= 8 |

**Tiempo total estimado:** 3.0 horas

---

## 🔮 Roadmap (NO implementar ahora)
- Permitir a los usuarios guardar sus propios agentes como templates (User Templates).
- Marketplace de templates compartidos entre organizaciones.
- Versionado de templates de sistema.
