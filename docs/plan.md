# Plan Maestro: Sistema de Importación de Bundles (ZIP) - v2

*(Documento actualizado exhaustivamente tras Análisis Técnico Unificado del Arquitecto)*

## Objetivo

Eliminar el mecanismo de creación manual y directa de agentes en la base de datos. El usuario desarrollará localmente → probará → exportará/empaquetará un bundle → importará a FAP. **La importación vía Bundle será el único camino de entrada.**

---

## Regla Fundamental

- **Bundle como Único Camino:** Se prohíbe la creación de agentes, flujos o skills mediante formularios manuales o chats directos. Todo debe llegar vía Bundle validado.
- **Atomicidad Transaccional estricta:** La base de datos debe asegurar que o se importa todo el bundle (agentes, flujos, skills) o no se importa nada (`ROLLBACK` total), delegado a la capa SQL mediante RPC.
- **Migración Legacy Soportada:** Los agentes existentes deben poder migrarse y las skills legacy en disco (`src/tools/demo/`) deben coexistir temporalmente con las importadas a BD.

---

## PASO 1. Estabilización: Pruebas en Verde

### Objetivo Inmediato
Antes de iniciar cualquier refactorización o desarrollo del nuevo sistema de bundles, es obligatorio garantizar que el estado actual del código sea estable. Esto significa reparar todos los fallos y errores detectados en la suite de tests actual.

- **Meta**: 100% de los tests en verde (`pytest tests/`).
- **Focos Críticos**:
  - Resolver `ModuleNotFoundError` en tests de `bartenders` (`src.tools.bartenders`).
  - Reparar errores de estado y aserciones en `BaseFlow` y flujos derivados (`ArchitectFlow`, etc.).
  - Solucionar validaciones fallidas en `test_registry_validation.py`.
  - Estabilizar pruebas E2E y de latencia.

---

## PASO 2. El Estándar FAP-Bundle v2

### Estructura del ZIP

```
bundle.zip/
├── manifest.json          # Metadatos + SHA256 por archivo
├── agents/                # JSONs para agent_catalog
│   ├── agent-1.json
│   └── agent-2.json
├── flows/                 # JSONs para workflow_templates
│   └── flow-1.json
├── skills/                # Python (.py) para skill_catalog
│   └── mi_skill.py
└── context/              # MD/JSON para Knowledge Base
    └── conocimiento.md
```

### manifest.json Schema

```json
{
  "version": "2.0",
  "name": "mi-bundle",
  "author": "org@email.com",
  "created_at": "2026-04-27T10:00:00Z",
  "schema_version": "2.0",
  "hashes": {
    "agents/agent-1.json": "sha256:abc123...",
    "skills/mi_skill.py": "sha256:def456..."
  }
}
```

### Límites Técnicos

| Límite | Valor |
|--------|-------|
| ZIP máximo | 50MB (Procesamiento In-Memory sin disco temp) |
| Agentes por bundle | 50 |
| Flujos por bundle | 20 |
| Skills por bundle | 30 |
| Timeout sandbox | 30s |

### Validación de Integridad

Cada archivo debe cumplir: `hash(file) == manifest.hashes[file]`. Si un solo archivo no coincide, **rechazo inmediato** de todo el bundle (HTTP 400).

---

## PASO 3. Seguridad (Sandboxing Real)

### RestrictedPython (Protección Runtime)

AST es la primera línea de defensa, pero `RestrictedPython` es el sandbox real que evita escapes en runtime (ej. vía `__subclasses__`).

```python
from RestrictedPython import compile_restricted
# Uso de compile_restricted para asegurar código limpio antes del import/eval
```

### Módulos Bloqueados en AST

| Categoría | Bloqueado |
|-----------|-----------|
| Sistema | `os`, `subprocess`, `shutil`, `socket`, `mmap`, `ctypes` |
| Dinámico | `eval`, `exec`, `compile`, `open`, `importlib` |
| Introspección | `inspect`, `gc`, `sys` (parcial) |
| Red | `urllib`, `http`, `ftplib` |

### Limitación Crítica

Las skills no pueden instalar dependencias (`pip install`) en runtime. Solo pueden usar módulos del `allowlist` (CrewAI, Pydantic, utilidades stdlib aprobadas).

---

## PASO 4. Persistencia Atómica (Vía PostgreSQL RPC)

La API REST de Supabase no soporta bloques transaccionales interactivos desde Python (`BEGIN/COMMIT`). Para lograr atomicidad real frente a fallos parciales, se implementará una función RPC en PostgreSQL.

### Modelo de Datos (Migración `026_bundle_system.sql`)

1. **`bundle_imports`**: Auditoría de cada importación con su hash global.
2. **`skill_catalog`**: Registro dinámico de skills Python.
3. **`agent_catalog` (Extensión)**: Se añade FK `bundle_id` para trazabilidad de su origen.

```sql
CREATE TABLE bundle_imports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  bundle_name TEXT NOT NULL,
  bundle_hash TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  imported_at TIMESTAMPTZ DEFAULT now(),
  error_detail TEXT
);

CREATE TABLE skill_catalog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundle_imports(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  code_source TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, name)
);

ALTER TABLE agent_catalog ADD COLUMN bundle_id UUID REFERENCES bundle_imports(id) ON DELETE SET NULL;
```

### Transacción RPC (Migración `027_bundle_rpc.sql`)

```sql
CREATE OR REPLACE FUNCTION import_bundle_atomic(payload JSONB) 
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  -- Insert into bundle_imports
  -- FOR EACH agent IN payload -> Upsert into agent_catalog (by org_id, role)
  -- FOR EACH flow IN payload -> Upsert into workflow_templates (by org_id, flow_type)
  -- FOR EACH skill IN payload -> Upsert into skill_catalog (by org_id, name)
  -- Return success
EXCEPTION WHEN OTHERS THEN
  -- ROLLBACK automático garantizado por PG
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;
```

### Estrategia de Upsert

Si el agente/flow/skill ya existe en la org, se actualiza:
- Agentes: Unique por `(org_id, role)`. (Corrección: El identificador único no es `name`).
- Flujos: Unique por `(org_id, flow_type)`.
- Skills: Unique por `(org_id, name)`.

---

## PASO 5. Pipeline de Importación (Lado Backend)

```
1. POST /api/bundles/import (multipart/form-data)
   └─ Upload de ZIP a memoria (<50MB).

2. BUNDLE MANAGER (Integridad)
   └─ Extrae en memoria (BytesIO).
   └─ Calcula SHA256 y verifica contra manifest.json.

3. SECURITY GUARD (Seguridad)
   └─ AST scan: bloquea imports prohibidos.
   └─ RestrictedPython compile: asegura sandboxing y timeouts (max 30s).

4. IMPORT SERVICE (Transacción)
   └─ Invoca supabase.rpc('import_bundle_atomic', payload)
   └─ Si falla: HTTP 500 informando que ningún cambio persistió.
   └─ Si éxito: HTTP 201 Created.
```

---

## PASO 6. Developer Experience (FAP-CLI)

| Comando | Función |
|---------|---------|
| `fap-cli init --name mi-bundle` | Crea estructura de carpetas (`agents/`, `skills/`, `manifest.json`) |
| `fap-cli validate` | Ejecuta el Security Scanner (AST/RestrictedPython) en local antes de subir |
| `fap-cli package` | Calcula todos los SHA256, actualiza el manifest, y comprime el bundle en ZIP |
| `fap-cli export-agents` | Exporta agentes de BD local a estructura bundle para facilitar migraciones |

---

## PASO 7. Migración de Agentes y Skills (Legacy)

### Agentes
Herramienta de Exportación CLI genera un bundle (`migrate.zip`) con los agentes pre-existentes extraídos del `agent_catalog` para estandarizar su formato. 

### Skills
Actualmente las skills viven en disco (`src/tools/demo/*.py`). El `ToolRegistry` se refactorizará para tener un enfoque **híbrido** temporal:
- Buscar primero en la BD (`skill_catalog`).
- Fallback a disco (legacy `tools/demo/`).
En un futuro (Post-MVP), los scripts legacy se migrarán a bundles formales y se eliminarán del repositorio FAP.

---

## PASO 8. Eliminación del Mecanismo Actual (T1: Limpieza Legacy)

1. **`src/flows/architect_flow.py`**:
   - Actualmente inserta de manera no-atómica (`_persist_agents()`, `_persist_template()`).
   - Se debe **refactorizar como paso inicial (Paso 0)**. Se eliminan los métodos de persistencia directa y pasará a retornar la estructura JSON de un Bundle validado en lugar de ejecutar `db.insert()`.
2. **`src/api/routes/agents.py`**:
   - Eliminar cualquier endpoint de creación manual (`POST / PATCH`). Debe quedar en formato Solo Lectura (`GET`).
3. **Crews**:
   - No requieren cambios (siguen leyendo de `agent_catalog`).

---

## PASO 9. Matriz de Pruebas (Actualizada)

| Caso | Escenario | Validación Esperada |
|------|-----------|-----------|
| B1 | Agente simple | Insert exitoso en `agent_catalog` |
| B2 | Skill válida | Compila en RestrictedPython y queda en `skill_catalog` |
| B3 | Bundle corrupto (hash mismatch) | Rechazado en `BundleManager`, error 400 |
| B4 | Skill maliciosa (`import os`) | Rechazado por `SecurityGuard`, error 400 |
| B5 | **Fallo transaccional (Atómico)** | Forzar error SQL en flow 5/10. Rollback 100% (cero insertados). Comprobable verificando DB tras RPC. |
| B6 | Upsert (Agent ya existe) | Actualiza el registro coincidiendo `(org_id, role)`, no duplica |
| B7 | Timeout sandbox | Bucle infinito bloqueado a los 30s |
| B8 | Límite de tamaño >50MB | API rechaza con HTTP 413 |
| B9 | CLI `validate` local | Detecta las mismas fallas de seguridad que la API sin enviar a BD |

---

## PASO 10. Cronograma y Componentes a Construir

| Tarea | Descripción | Dependencias |
|:---|:---|:---|
| **T0. Estabilización de Tests** | Reparar todos los tests fallidos y errores en la suite actual (`pytest`). La aplicación debe tener 100% de tests en verde antes de nuevos cambios. | Ninguna |
| **T1. Limpieza Legacy** | Poda quirúrgica de `ArchitectFlow`: eliminar `_persist_template`, `_persist_agents`, y `_register_dynamic_flow`. Adaptar `ArchitectState` y `_run_crew` para retornar solo JSON. | Ninguna |
| **T2. Setup y Migraciones** | Añadir `restrictedpython` a `pyproject.toml`. Migraciones `026_bundle_system.sql` y `027_bundle_rpc.sql` (RPC Atómico). | T1 |
| **T3. `BundleManager`** | Parsing In-Memory, ZIP extraction, Hashing SHA256 vs manifest. | T2 |
| **T4. `SecurityGuard`** | AST Scanning y compilación con RestrictedPython. | T2 |
| **T5. `ImportService` + API** | Endpoint `/bundles/import` + invocación de RPC `import_bundle_atomic`. | T3, T4 |
| **T6. Refactor Existente** | Híbrido ToolRegistry (DB + FS). (El refactor de ArchitectFlow ya se realizó en T1). | T5 |
| **T7. FAP-CLI** | Utilidad CLI (`init`, `validate`, `package`). | T5 |

---

## PASO 11. Dependencias Externas

```toml
restrictedpython >= 7.0   # AÑADIR (Bloqueante para el Paso 2)
pydantic >= 2.10.0
supabase >= 2.10.0
# hash y zip usan stdlib
```

---

## PASO 12. Decisiones Arquitectónicas Formalizadas

| Decisión | Justificación | Origen |
|----------|--------------|--------|
| **Transacciones vía Función RPC** | PostgREST no soporta `BEGIN...COMMIT` desde un cliente externo. La única manera de garantizar un Rollback Atómico completo si un agent/flow falla, es procesar todo del lado del motor (PL/pgSQL). | Análisis Unificado |
| **Clave Única en Agentes (`role`)** | El Upsert de agentes no se hace por `name`, se hace por la dupla `(org_id, role)` para mantener consistencia con el diseño de base de datos de la fase previa. | Análisis Unificado |
| **Memoria 100% (In-Memory Streams)** | Evita path traversal vulnerabilities y ahorra I/O al no escribir archivos `temp/` en disco durante la validación del ZIP. | Análisis Unificado |
| **`bundle_id` opcional en Agents** | Se añadió FK a `agent_catalog` pero es `ON DELETE SET NULL` para no bloquear compatibilidad con la base de datos actual (migración legacy). | Análisis Unificado |

---

## PASO 13. Criterios de Aceptación MVP

| # | Criterio | Tipo | Verificable por |
|---|----------|------|-----------------|
| 1 | `fap-cli validate <archivo.zip>` retorna `exit code 0` si hashes y seguridad son correctos | Técnico | `echo $?` después del comando |
| 2 | `POST /api/bundles/import` con ZIP válido retorna HTTP 201 y status 'committed' en `bundle_imports` | Funcional | curl + SELECT en Supabase |
| 3 | Bundle alterado post-packaging es rechazado con HTTP 400 "Hash mismatch" | Robustez | Modificar .json interno del ZIP y subir |
| 4 | Skill con `import os` es bloqueada con HTTP 400 | Seguridad | Subir bundle con skill maliciosa |
| 5 | Bundle con 10 agentes donde #5 falla SQL = 0 cambios en DB | Atomicidad | Forzar error en agent #5 y verificar |
| 6 | Agente existente (`org_id + role`) se actualiza sin error de clave duplicada | Funcional | Re-importar bundle con mismo agente |
| 7 | `restrictedpython>=7.0` instalado en `pyproject.toml` | Técnico | `pip show restrictedpython` |

---

## PASO 14. Cronograma Detallado (55h MVP + 16h opcional)

| Día | Entregable | Tareas | Horas |
|-----|-----------|--------|-------|
| **0** | Poda Inicial | T1: Limpieza Legacy en `architect_flow.py` | 2h |
| **1** | Setup + Schema | T2: restrictedpython + Migraciones 026+027 | 5h |
| **2** | BundleManager | T3: Extract, hash, validate manifest | 6h |
| **3** | SecurityGuard | T4: AST + RestrictedPython sandbox | 10h |
| **4** | ImportService + API | T5: RPC call + endpoint `/bundles/import` | 6h |
| **5** | FAP-CLI + Refactor | T6: CLI init/validate/package + ArchitectFlow | 10h |
| **6** | Pruebas E2E | T7: Tests B1-B9, fixes | 8h |
| **7** | Migration tool | T8: export-agents + legacy skills script | 8h |
| **MVP Total** | | | **55h** |

### Tareas Opcionales (Post-MVP)

| # | Tarea | Estimación | Prioridad |
|---|-------|-----------|-----------|
| T9 | Dashboard Wizard UI | 8h | BAJA |
| T10 | Bundle-Builder Agent | 8h | BAJA |

> **Bundle-Builder Agent** (T10) no está en el critical path. Puede implementarse después de que el import core funcione.

### Dependencias entre Tareas

```
T0 (4h) ── T1 (2h) ── T2 (5h) ──┬── T3 (6h) ──┬── T4 (10h)
                              │             │
                              │             └── T5 (6h) ── T6 (10h) ── T7 (8h)
                              │
                              └────────────────────────── T8 (8h)
```

---

## PASO 15. 🔮 Roadmap (NO implementar en MVP)

### Post-MVP Features

| # | Feature | Descripción | Pre-requisito |
|---|---------|-------------|---------------|
| R1 | **Hot-Reload de Skills** | Cargar código de `skill_catalog` en `ToolRegistry` sin restart de API | ImportService funcionando |
| R2 | **Dashboard Wizard UI** | Interfaz web para upload de bundles con preview | API `/bundles/import` completa |
| R3 | **Bundle-Builder Agent** | Agente IA que genera bundles desde lenguaje natural | Wizard UI |
| R4 | **Firmas Digitales** | Require firma criptográfica en manifest para bundles de proveedores verificados | Demanda de usuarios externos |
| R5 | **Versión de Bundles** | Prevenir downgrades: bloquear import si bundle tiene versión menor que existente | `bundle_id` en agents |
| R6 | **Seccomp Sandbox (Linux)** | Hardening del sandbox con `seccomp` para prevenir `ctypes`/`mmap` | MVP running 2 semanas sin incidentes |

### Decisiones de Diseño para Futuro

- **`bundle_id` en `agent_catalog`:** Ya implementado, permite auditoría de origen de cada agente
- **Soft deletes:** En lugar de hard delete, marcar `is_active=False` cuando un bundle se desactiva
- **Incremental imports:** Solo actualizar archivos modificados vs full replace (ahorra tiempo en bundles grandes)

---

## PASO 16. Correcciones vs Versión Anterior

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Transacción | Cliente REST con rollback manual (incorrecto) | RPC PL/pgSQL atómico |
| Unique key agente | `(org_id, name)` (incorrecto) | `(org_id, role)` |
| ArchitectFlow | "Eliminar `_persist_agents()`" (mutilar) | "Refactorizar para retornar definición" |
| Tablas | Asumía que existían | Crear en migración 026+027 |
| Dependencias | No mencionaba | `restrictedpython>=7.0` obligatorio |
| bundle_id | No estaba en plan | FK agregada a `agent_catalog` con ON DELETE SET NULL |
| Skills legacy | No mencionaba coexistencia | ToolRegistry híbrido temporal |
| Limitación sandbox | No documentada | ctypes, importlib bloqueados en AST |
| Estimación | 5 días = 40h | 7 días = 55h mínimo MVP (Incluye T1) |
