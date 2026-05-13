# FAP Bundle Schema v2

Formato oficial de bundles para FluxAgentPro-v2. Usado por `fap package`, `fap validate`, `POST /api/bundles/import`.

---

## 1. Estructura de directorios

```
my-bundle/
├── manifest.json          # Requerido — metadatos + hashes
├── agents/                # Requerido (mínimo 1 agente)
│   ├── recepcionista.json
│   └── ...
├── skills/                # Opcional — tools Python
│   ├── excel_reader.py
│   └── ...
├── flows/                 # Opcional — workflows JSON o Python
│   ├── reserva.json
│   ├── reserva.py
│   └── ...
└── context/               # Opcional — archivos de contexto
    └── ...
```

---

## 2. manifest.json

### Schema

```json
{
  "version": "2.0",
  "bundle_info": {
    "name": "my-bundle",
    "description": "Descripción del bundle",
    "version": "1.0.0",
    "author": "user"
  },
  "hashes": {}
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `version` | `string` | Sí | Siempre `"2.0"` |
| `bundle_info.name` | `string` | Sí | 3-100 caracteres |
| `bundle_info.description` | `string` | No | |
| `bundle_info.version` | `string` | Sí | SemVer (e.g. `"1.0.0"`) |
| `bundle_info.author` | `string` | No | Default: `"user"` |
| `hashes` | `object` | Sí | Mapa `ruta -> "sha256:<hex>"`. Vacío `{}` si `fap package` va a generarlos |

### Reglas

- `hashes` se deja vacío durante desarrollo. `fap package` lo computa automáticamente.
- Hash format: `sha256:` + 64 hex chars.
- NO incluyas campos extra (e.g. `agents: []`, `compatibility`) — son ignorados.

---

## 3. agents/<role>.json

### Schema

```json
{
  "role": "recepcionista",
  "soul_json": {
    "role": "Recepcionista de Hotel",
    "goal": "Atender al usuario y proveer información del hotel.",
    "backstory": "Sos un recepcionista profesional con atención personalizada."
  },
  "allowed_tools": [],
  "model": "groq/llama-3.3-70b-versatile",
  "max_iter": 3,
  "is_active": true
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `role` | `string` | Sí | — | Identificador único del agente. Coincide con nombre del archivo (sin `.json`). 1-100 chars |
| `soul_json.role` | `string` | Sí | `role` | Nombre visible del agente |
| `soul_json.goal` | `string` | Sí | `"Complete the assigned task."` | Objetivo del agente. Mínimo 10 caracteres |
| `soul_json.backstory` | `string` | Sí | `"You are a highly efficient AI agent."` | Personalidad y contexto. Mínimo 10 caracteres |
| `soul_json.rules` | `array[string]` | No | `[]` | Reglas de comportamiento adicionales |
| `allowed_tools` | `array[string]` | No | `[]` | Tools habilitadas. Vacío `[]` = sin tools |
| `model` | `string` | No | — | **Informativo.** La selección real de LLM es global por settings |
| `max_iter` | `int` | No | `5` | Máximo de iteraciones. Rango: 1-5 |
| `is_active` | `bool` | No | `true` | Activo al importar |

### Reglas

- `role` (top-level) DEBE coincidir con el filename sin `.json`. Ej: `agents/recepcionista.json` → `role: "recepcionista"`.
- `allowed_tools` vacío `[]` = agente sin herramientas. Solo habla.
- Tools built-in disponibles: `excel_reader`, `service_connector`.
- Tools MCP: `mcp:<server>:<tool>` (e.g. `mcp:filesystem:read_file`).
- `max_iter` ≤ 5 para producción. Usar 3 para agentes conversacionales simples.
- `soul_json` se usa para construir el agente CrewAI. `role`, `goal` y `backstory` son obligatorios para que el LLM funcione correctamente.

---

## 4. skills/*.py

Skills Python que se registran como tools en el `ToolRegistry` en memoria.

### Reglas

- Cada archivo `.py` expone al menos una clase con nombre que termina en `Tool` o con atributo `_is_tool = True`.
- Debe heredar de `BaseTool` de `crewai_tools` o seguir el patrón de tool del proyecto.
- El código pasa por `SecurityGuard` (AST scan + RestrictedPython).
- No se permite `import src`, `import os`, `import subprocess` (bloqueado por seguridad).
- Máximo 30 skills por bundle.

### Ejemplo mínimo

```python
from crewai_tools import BaseTool

class SaludarTool(BaseTool):
    name: str = "saludar"
    description: str = "Saluda al usuario por su nombre"

    def _run(self, nombre: str) -> str:
        return f"Hola {nombre}! Bienvenido."
```

---

## 5. flows/ — Workflows

### 5.1 Flujo JSON

```json
{
  "name": "reserva_workflow",
  "description": "Flujo de reserva para el hotel",
  "flow_type": "reserva",
  "steps": [
    {
      "id": "step_1",
      "name": "Tomar reserva",
      "description": "El agente recepcionista toma los datos de la reserva",
      "agent_role": "recepcionista"
    }
  ],
  "agents": [
    {
      "role": "recepcionista",
      "goal": "Tomar reservas del hotel",
      "backstory": "Sos un recepcionista que toma reservas.",
      "allowed_tools": [],
      "rules": [],
      "model": "claude-sonnet-4-20250514",
      "max_iter": 3
    }
  ]
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | `string` | Sí | Nombre del workflow |
| `description` | `string` | Sí | Mínimo 10 caracteres |
| `flow_type` | `string` | Sí | Identificador único del flow |
| `steps[].id` | `string` | Sí | ID único del paso |
| `steps[].name` | `string` | Sí | Nombre visible del paso |
| `steps[].description` | `string` | Sí | Mínimo 10 caracteres |
| `steps[].agent_role` | `string` | Sí | Debe coincidir con `role` de algún agente en `agents[]` |
| `steps[].requires_approval` | `bool` | No | Si `true`, pausa para HITL |
| `agents[]` | `AgentDefinition[]` | Sí | Misma estructura que AgentDefinition (flat, sin `soul_json`) |
| `agents[].role` | `string` | Sí | 1-100 chars |
| `agents[].goal` | `string` | Sí | Mínimo 10 chars |
| `agents[].backstory` | `string` | Sí | Mínimo 10 chars |
| `agents[].allowed_tools` | `array[string]` | No | Default `[]` |
| `agents[].rules` | `array[string]` | No | Default `[]` |
| `agents[].model` | `string` | No | Default `"claude-sonnet-4-20250514"`. Debe estar en `ALLOWED_MODELS` |
| `agents[].max_iter` | `int` | No | Default 5. Rango 1-5 |

### 5.2 Flujo Python

Flujo en `flows/<flow_type>.py`. Debe exponer una clase que tenga `create_task_record` o `_run_crew`.

---

## 6. Formatos de tool reference

### 6.1 Built-in tools

| Nombre | Cómo referenciarlo | Descripción |
|--------|-------------------|-------------|
| Excel Reader | `"excel_reader"` | Lee archivos Excel y extrae datos |
| Service Connector | `"service_connector"` | Conecta con APIs externas |

### 6.2 MCP tools

Formato: `"mcp:<server_name>:<tool_name>"`

Ejemplo:
```json
"allowed_tools": ["mcp:filesystem:read_file", "mcp:google:search"]
```

---

## 7. Límites del bundle

| Recurso | Límite |
|---------|--------|
| Tamaño ZIP | `max_bundle_size_mb` (configurable, default ~50MB) |
| Agentes por bundle | `max_agents_per_bundle` (configurable) |
| Skills por bundle | 30 |
| Flows por bundle | 20 |
| `max_iter` por agente | 1-5 |

---

## 8. Flujo de trabajo recomendado

### 8.1 Generación con Claude Code

```
1. Claude Code crea:  manifest.json + agents/<role>.json
2. NO incluir hashes — dejarlos como {}
3. Ejecutar:     fap validate <dir>          # verifica estructura
4. Ejecutar:     fap package <dir>           # genera hashes + .zip
5. Ejecutar:     fap bundle import <zip>     # importa a FAP
```

### 8.2 Reglas para Claude Code

- `allowed_tools: []` si el agente solo conversa. No inventar tools.
- `max_iter` bajo (3) para agentes conversacionales. Subir a 5 solo si necesita múltiples pasos.
- `is_active: true` siempre.
- No generar skills/ ni flows/ a menos que se pida explícitamente.
- El `role` del filename DEBE coincidir con el campo `role` dentro del JSON.
- `soul_json.goal` y `soul_json.backstory` en el idioma que el usuario pida.

---

## 9. Validación

```bash
# Validar directorio
fap validate ./my-bundle

# Validar ZIP
fap validate ./my-bundle.zip

# Validar sincronizando config de seguridad con servidor
fap validate ./my-bundle --sync
```

`fap validate` verifica:
- Estructura de directorios
- Existencia de `manifest.json`
- Integridad de hashes (si existen)
- Seguridad de skills (AST scan)
- Parseo completo vía `BundleManager.process_zip()`

---

## 10. Ejemplo completo (Nivel 1)

```
data/seed/level-1/
├── manifest.json
└── agents/
    └── recepcionista.json
```

### manifest.json
```json
{
  "version": "2.0",
  "bundle_info": {
    "name": "level-1-greeter",
    "description": "Agente recepcionista simple - Nivel 1: sin tools",
    "version": "1.0.0",
    "author": "claude-code"
  },
  "hashes": {}
}
```

### agents/recepcionista.json
```json
{
  "role": "recepcionista",
  "soul_json": {
    "role": "Recepcionista de Hotel",
    "goal": "Recibir al usuario, saludarlo amablemente y ofrecer ayuda.",
    "backstory": "Sos un recepcionista profesional de un hotel boutique. Tenés excelente trato con huéspedes, hablás de forma cálida y servicial. Respondes siempre en español."
  },
  "allowed_tools": [],
  "model": "groq/llama-3.3-70b-versatile",
  "max_iter": 3,
  "is_active": true
}
```
