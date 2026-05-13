# Final Plan: Claude Code → FAP Agent Import Pipeline

## Objetivo
Claude Code genera agentes → FAP importa via bundle → verificar progresivamente.

## Niveles de complejidad (7 niveles)

### Nivel 1 — Agente simple sin tools
- Bundle: manifest.json + agents/*.json (role/goal/backstory/model)
- Test: `test_claude_import_level_1.py`
- Verificar: GET /agents/by-role, POST /agents/{role}/run → completed

### Nivel 2 — Agente con built-in tool
- Bundle + allowed_tools: ["excel_reader"]
- Test: `test_claude_import_level_2.py`
- Verificar: tool call real, last_tool_calls >= 1

### Nivel 3 — Agente con MCP tool
- Bundle + org_mcp_servers config + MCP tool en allowed_tools
- Test: `test_claude_import_level_3.py`
- Verificar: MCP tool resuelta via resolve_tools_async()

### Nivel 4 — Flujo condicional (DynamicWorkflow)
- Bundle + workflow_templates con definition JSON + operadores >=, <=, ==
- Test: `test_claude_import_level_4.py`
- Verificar: ramas condicionales según input

### Nivel 5 — Multi-agente con handover
- Bundle + múltiples agentes + handover entre ellos
- Test: `test_claude_import_level_5.py`
- Verificar: secuencia A → B con output intermedio

### Nivel 6 — HITL (Human In The Loop)
- Bundle + pending_approvals step
- Test: `test_claude_import_level_6.py`
- Verificar: pausa → approve → continúa / reject → termina

### Nivel 7 — Sistema completo
- Bundle con MCP + condicional + multi-agente + HITL + tools
- Test: `test_claude_import_level_7.py`
- Verificar: ciclo completo funcional

## Mecanismo de importación
1. Claude Code genera archivos en dir (agents/, manifest.json, skills/, flows/)
2. `fap package <dir>` → actualiza hashes → ZIP
3. `fap bundle import <zip>` → POST /api/bundles/import
4. `GET /agents/by-role/{role}` + `POST /agents/{role}/run` → verificar

## Bundle schema (v2)
```
my-bundle/
├── manifest.json      # version: "2.0", agents[], skills[], hashes
├── agents/
│   └── <role>.json    # role, soul_json, allowed_tools, model, max_iter
├── skills/            # opcional (*.py)
└── flows/             # opcional (*.py)
```

## Nuevos archivos a crear
| Archivo | Propósito |
|---------|-----------|
| `src/cli/commands/bundle_import.py` | CLI `fap bundle import <zip>` |
| `data/seed/level-1/` ... `data/seed/level-7/` | Bundles seed por nivel |
| `tests/e2e/test_claude_import_level_1.py` ... `7` | Tests E2E por nivel |

## Decisiones
- Bundles seed generados por mí (simulan output de CC)
- Después documentamos schema para CC genere directo
- MCP demo propio (clima_tool) sin depender de externos
- Cada nivel se prueba individualmente antes de avanzar
- `fap generate` descartado — CC no necesita saber de FAP, solo generar archivos

## Pendiente pre-Nivel 1
- `fap bundle import` CLI command
- Script de limpieza DB (`wipe_db.py` o `cleanup_db.py`)
- Bundle seed nivel 1
- Test E2E nivel 1
