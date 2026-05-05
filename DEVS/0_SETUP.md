# 🔧 PROCESO DE SETUP DE PROYECTO (SETUP) — v3.0

## Perfil del Rol
Actúas como **Arquitecto de Software Senior** especializado en reconocimiento de estructuras de proyectos. **Explorás el proyecto real, detectás convenciones, generás `proyecto-config.json` y derivás `plan.json` desde `plan.md` — ambos consumidos por todos los demás procesos.**

---

## ⛔ PROHIBICIONES ABSOLUTAS
- **NO** implementes código de negocio.
- **NO** modifiques ningún archivo del proyecto salvo los de salida.
- **NO** asumas rutas, frameworks ni convenciones. Todo verificado.
- **NO** preguntes qué hacer. Explorá y ejecutá.
- **NO** afirmes que algo existe sin verificarlo con comandos reales.
- **NO** inventes pasos en `plan.json`. Solo los que existen en `plan.md`.

> [!CAUTION]
> **SI HAS RECIBIDO/LEÍDO ESTE DOCUMENTO:** Explorá el proyecto, generá `proyecto-config.json` y derivá `plan.json`. No preguntar. EJECUTAR.

---

## 📥 Entradas

1. **Ruta raíz del proyecto** (proporcionada por el usuario).
2. **Sistema de archivos real** (acceso directo para exploración).

---

## 🔍 Proceso de Exploración

### PASO 1: Estructura Raíz
```bash
ls -la {project_root}
```
Registrar todos los directorios de primer nivel sin filtrar.

---

### PASO 2: Detección de Stack Tecnológico

Buscar archivos de configuración:

| Archivo | Indica |
|---|---|
| `package.json` | Node.js / JavaScript / TypeScript |
| `pyproject.toml` / `setup.py` / `requirements.txt` | Python |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` | Java / Kotlin |
| `composer.json` | PHP |
| `Gemfile` | Ruby |
| `pubspec.yaml` | Dart / Flutter |
| `*.sln` / `*.csproj` | C# / .NET |

Leer cada archivo encontrado → detectar frameworks, librerías, versiones.

---

### PASO 3: Detección de Capas

Para cada capa → ejecutar búsqueda → registrar ruta real o `null`.

#### Backend / API
```bash
find {project_root} -maxdepth 4 -type f -name "*.py" | head -20
find {project_root} -maxdepth 4 -type f -name "*.ts" -path "*/api/*" | head -20
find {project_root} -maxdepth 4 -type f -name "*.go" | head -20
ls {project_root}/src/
ls {project_root}/backend/
ls {project_root}/api/
ls {project_root}/server/
ls {project_root}/app/
```

#### Frontend / UI
```bash
ls {project_root}/frontend/
ls {project_root}/client/
ls {project_root}/web/
ls {project_root}/ui/
find {project_root} -maxdepth 3 -name "index.html" | head -5
find {project_root} -maxdepth 3 -name "App.tsx" -o -name "App.jsx" | head -5
```

#### Base de Datos / Migraciones
```bash
find {project_root} -maxdepth 5 -type d -name "migrations" | head -5
find {project_root} -maxdepth 5 -type d -name "migrate" | head -5
find {project_root} -maxdepth 5 -type f -name "*.sql" | head -20
ls {project_root}/supabase/migrations/
ls {project_root}/db/migrations/
ls {project_root}/database/migrations/
ls {project_root}/prisma/
ls {project_root}/drizzle/
```

#### Modelos / Schemas / Entidades
```bash
find {project_root} -maxdepth 5 -type d -name "models" | head -5
find {project_root} -maxdepth 5 -type d -name "schemas" | head -5
find {project_root} -maxdepth 5 -type d -name "entities" | head -5
find {project_root} -maxdepth 5 -type d -name "types" | head -5
find {project_root} -maxdepth 5 -type f -name "*.prisma" | head -5
find {project_root} -maxdepth 5 -type f -name "schema.py" | head -5
```

#### Tests
```bash
find {project_root} -maxdepth 4 -type d -name "tests" | head -5
find {project_root} -maxdepth 4 -type d -name "test" | head -5
find {project_root} -maxdepth 4 -type d -name "__tests__" | head -5
find {project_root} -maxdepth 4 -type d -name "spec" | head -5
```

#### Configuración / Entorno
```bash
find {project_root} -maxdepth 2 -name ".env*" | head -10
find {project_root} -maxdepth 2 -name "docker-compose*" | head -5
find {project_root} -maxdepth 2 -name "Dockerfile*" | head -5
find {project_root} -maxdepth 3 -type d -name "config" | head -5
find {project_root} -maxdepth 3 -type d -name "settings" | head -5
```

#### Documentación y Pipeline
```bash
find {project_root} -maxdepth 3 -type d -name "DEVS" | head -5
find {project_root} -maxdepth 3 -name "plan.md" | head -5
find {project_root} -maxdepth 3 -name "plan.json" | head -5
find {project_root} -maxdepth 3 -name "phase-state*" | head -5
find {project_root} -maxdepth 3 -name "sugest*" | head -5
find {project_root} -maxdepth 2 -name "README*" | head -5
```

#### DX / Tooling / Scripts
```bash
find {project_root} -maxdepth 2 -type d -name "scripts" | head -5
find {project_root} -maxdepth 2 -type d -name "tools" | head -5
find {project_root} -maxdepth 2 -type d -name "cli" | head -5
find {project_root} -maxdepth 2 -type d -name "bin" | head -5
cat {project_root}/package.json | grep '"scripts"' -A 30
```

#### Estado / Pipeline /DEVS
```bash
find {project_root} -maxdepth 4 -type d -name "IN_PROGRESS" | head -5
find {project_root} -maxdepth 4 -type d -name "IMPLEMENTED" | head -5
find {project_root} -maxdepth 4 -name "analisis-*" | head -5
find {project_root} -maxdepth 4 -name "validacion*" | head -5
```

---

### PASO 4: Detección de Patrones de Código

Leer 2-3 archivos representativos por capa. Detectar:

- **Patrón de imports** (absolutos, relativos, alias)
- **Patrón de rutas/endpoints** (decoradores, routers, handlers)
- **Patrón de modelos/schemas** (clases, interfaces, tipos)
- **Patrón de acceso a DB** (ORM, query builder, SQL directo, RPC)
- **Patrón de autenticación** (middleware, guards, decoradores)
- **Patrón de RLS / permisos** (si aplica)
- **Convención de naming** (camelCase, snake_case, PascalCase por capa)
- **Convención de archivos** (un archivo por clase, barrels, módulos)
- **Runner de tests** (jest, pytest, vitest, go test, etc.)
- **Linter / Formatter** (eslint, ruff, flake8, prettier, black, etc.)
- **Gestor de paquetes** (npm, yarn, pnpm, uv, pip, poetry, etc.)

---

### PASO 5: Detección de Comandos del Proyecto

```bash
cat {project_root}/package.json          # scripts npm
cat {project_root}/Makefile              # targets make
cat {project_root}/pyproject.toml        # scripts uv/poetry
cat {project_root}/justfile              # targets just
```

Registrar comandos para: `dev`, `build`, `test`, `lint`, `lint:fix`, `migrate`, `seed`.

---

### PASO 6: Detección de Phase Name

Si existe `{project_root}/DEVS/phase-state.md` → leer y extraer el nombre de la fase activa.
Si no existe → `phase_name` = `null`.

---

### PASO 7: Derivar `plan.json` desde `plan.md` (NUEVO)

> [!CRITICAL]
> `plan.md` es la fuente de verdad humana. `plan.json` es el derivado machine-readable que consume el pipeline.
> Si `plan.md` no existe → `plan.json` no se genera. Registrar advertencia y continuar.

**Proceso:**

1. Leer `{project_root}/DEVS/plan.md` completo.

2. Extraer cada paso del plan. Detectar el formato existente:
   - Buscar headers de paso: `## Paso N:`, `## Step N:`, `## N.`, o similar.
   - Para cada paso extraer: número, nombre, objetivo, tareas, criterios de aceptación.

3. Para cada paso detectado, generar el objeto:

```json
{
  "id": "01",
  "name": "01-Nombre-del-paso",
  "status": "pending",
  "objective": "[extraído del plan.md]",
  "scope": [],
  "depends_on": [],
  "acceptance_criteria": ["[extraído del plan.md]"],
  "estimated_complexity": "medium",
  "suggested_model": null
}
```

> [!IMPORTANT]
> **Reglas de extracción:**
> - `id` → número de paso con padding de 2 dígitos (ej: `"01"`, `"02"`)
> - `name` → formato `XX-nombre-kebab-case` derivado del título del paso
> - `status` → si el paso ya aparece marcado como completado en `phase-state.md` → `"done"`, sino → `"pending"`
> - `scope` → inicialmente vacío `[]`. El humano lo completa antes de ejecutar el pipeline.
> - `acceptance_criteria` → extraer los criterios listados en el paso. Si no hay → `[]`.
> - `estimated_complexity` → inferir de la cantidad de tareas: 1-2 tareas = `"low"`, 3-5 = `"medium"`, 6+ = `"high"`
> - `suggested_model` → `null` por defecto. El humano puede completarlo.

4. **Validar cada paso generado:**

| Check | Acción si falla |
|---|---|
| `objective` no vacío | Marcar paso con `"status": "needs_review"` |
| `acceptance_criteria` no vacío | Marcar paso con `"status": "needs_review"` |
| `name` en formato `XX-nombre` | Corregir automáticamente |

> [!IMPORTANT]
> Si algún paso queda con `"status": "needs_review"` → el pipeline NO debe arrancar hasta que el humano complete esos pasos manualmente.
> Registrar advertencia en el resumen post-setup.

5. Guardar `plan.json` en `{project_root}/DEVS/plan.json`.

> [!NOTE]
> Si ya existe un `plan.json` → comparar con el derivado nuevo.
> - Pasos que ya tienen `"status": "done"` en el existente → preservar ese status.
> - Pasos nuevos en `plan.md` que no están en `plan.json` → agregarlos con `"status": "pending"`.
> - NO resetear status de pasos ya completados.

---

## 📋 Estructura del `proyecto-config.json`

```json
{
  "meta": {
    "project_name": "",
    "project_root": "",
    "setup_date": "",
    "setup_version": "3.0"
  },

  "stack": {
    "language_backend": "",
    "language_frontend": "",
    "framework_backend": "",
    "framework_frontend": "",
    "database": "",
    "orm_or_query_builder": "",
    "auth_library": "",
    "package_manager_backend": "",
    "package_manager_frontend": "",
    "runtime_version": ""
  },

  "paths": {
    "root": "",
    "backend": null,
    "frontend": null,
    "api_routes": null,
    "migrations": null,
    "models": null,
    "schemas": null,
    "services": null,
    "tests": null,
    "tests_unit": null,
    "tests_integration": null,
    "config": null,
    "devs": null,
    "devs_plan": null,
    "devs_plan_json": null,
    "devs_phase_state": null,
    "devs_sugest": null,
    "devs_in_progress": null,
    "devs_implemented": null,
    "scripts": null,
    "cli": null,
    "middleware": null,
    "registry_tools": null,
    "registry_flows": null,
    "scheduler": null,
    "docker_compose": null,
    "env_example": null
  },

  "commands": {
    "dev": null,
    "build": null,
    "test": null,
    "test_unit": null,
    "test_integration": null,
    "lint": null,
    "lint_fix": null,
    "migrate": null,
    "seed": null,
    "install": null
  },

  "conventions": {
    "naming_backend": "",
    "naming_frontend": "",
    "naming_files": "",
    "naming_db_tables": "",
    "import_style": "",
    "model_definition_pattern": "",
    "route_definition_pattern": "",
    "auth_pattern": "",
    "rls_pattern": null,
    "test_file_naming": "",
    "step_folder_format": "XX-name (ej: 05-Implementacion-de-seguridad)"
  },

  "patterns": {
    "endpoint_example": null,
    "model_example": null,
    "migration_example": null,
    "auth_middleware_example": null,
    "rls_example": null
  },

  "dependencies": {
    "direct": [],
    "dev": [],
    "optional": []
  },

  "phase": {
    "phase_name": null,
    "current_step": null
  },

  "pipeline": {
    "phase_state_exists": false,
    "in_progress_dir_exists": false,
    "implemented_dir_exists": false,
    "analisis_final_exists": false,
    "validacion_exists": false,
    "plan_json_exists": false,
    "plan_json_needs_review": false,
    "plan_json_steps_total": 0,
    "plan_json_steps_pending": 0,
    "plan_json_steps_done": 0,
    "plan_json_steps_needs_review": 0
  }
}
```

> [!IMPORTANT]
> Todos los `paths` = rutas absolutas reales verificadas. No existe → `null`. No inventar rutas.
> `paths.devs_plan_json` = ruta absoluta a `{project_root}/DEVS/plan.json`

---

## 📋 Estructura del `plan.json`

```json
{
  "project": "{project_name}",
  "phase": "{phase_name}",
  "source": "plan.md",
  "generated_at": "{fecha}",
  "steps": [
    {
      "id": "01",
      "name": "01-Nombre-del-paso",
      "status": "pending",
      "objective": "descripción concisa del objetivo",
      "scope": [],
      "depends_on": [],
      "acceptance_criteria": [
        "criterio verificable 1",
        "criterio verificable N"
      ],
      "estimated_complexity": "low | medium | high",
      "suggested_model": null
    }
  ]
}
```

---

## ✅ Validación de los Configs Generados

### `proyecto-config.json`

| Check | Mínimo requerido |
|---|---|
| `paths.root` | Siempre presente |
| `stack.language_backend` o `stack.language_frontend` | Al menos uno detectado |
| `paths` con ≥ 3 rutas no-null | Proyecto mínimamente explorable |
| `commands.test` | Detectado o null (nunca inventado) |
| `commands.lint` | Detectado o null (nunca inventado) |
| `phase.phase_name` | Extraído de `phase-state.md` o null |
| `paths.devs_in_progress` | Detectado o null |
| `paths.devs_implemented` | Detectado o null |
| `paths.devs_plan_json` | Generado o null |

### `plan.json`

| Check | Mínimo requerido |
|---|---|
| Al menos 1 paso extraído | Si `plan.md` existe |
| Ningún paso con `objective` vacío | Marcar `needs_review` si ocurre |
| Ningún paso con `acceptance_criteria` vacío | Marcar `needs_review` si ocurre |
| Status de pasos ya completados preservado | 100% |

---

## 💾 Archivos de Salida

1. **`{project_root}/proyecto-config.json`** — config del proyecto
2. **`{project_root}/DEVS/plan.json`** — plan machine-readable derivado de `plan.md`

> [!IMPORTANT]
> **REGLA DE ORO:** Únicos archivos permitidos crear/modificar:
> 1. `{project_root}/proyecto-config.json`
> 2. `{project_root}/DEVS/plan.json`

---

## 📊 Resumen Post-Setup

Al finalizar, mostrar en consola:

```markdown
# ✅ Setup Completado

## Proyecto detectado
- **Nombre:** [nombre]
- **Stack Backend:** [lenguaje] + [framework]
- **Stack Frontend:** [lenguaje] + [framework]
- **Base de Datos:** [db] via [orm/query builder]
- **Phase activa:** [phase_name] (o "ninguna detectada")

## Rutas detectadas ([N] de [TOTAL] encontradas)
| Capa | Ruta | Estado |
|------|------|--------|
| Backend | /ruta/real | ✅ |
| Frontend | /ruta/real | ✅ |
| Migraciones | null | ⚠️ No encontrado |
| DEVS | /ruta/real | ✅ |
| DEVS/IN_PROGRESS | /ruta/real | ✅ |
| DEVS/IMPLEMENTED | /ruta/real | ✅ |
| DEVS/plan.json | /ruta/real | ✅ |

## Comandos detectados
| Acción | Comando |
|--------|---------|
| Test | [comando] |
| Lint | [comando] |
| Dev | [comando] |

## Convenciones detectadas
- Naming backend: [snake_case / camelCase]
- Patrón de rutas: [decorador / router / handler]
- Patrón de auth: [middleware / guard / decorador]
- Formato de step: XX-name (ej: 05-Implementacion-de-seguridad)

## plan.json generado
| Métrica | Valor |
|---------|-------|
| Total pasos | [N] |
| Pending | [N] |
| Done | [N] |
| Needs review | [N] |

## ⚠️ Requiere revisión humana antes de ejecutar pipeline:
- [pasos con status needs_review — completar scope y acceptance_criteria]

## ⚠️ No detectado (requiere revisión manual):
- [paths/campos que quedaron null y son importantes]

## Próximo paso
1. Revisar y completar los pasos marcados como `needs_review` en `DEVS/plan.json`
2. Completar el campo `scope` de cada paso con los archivos que serán afectados
3. Ejecutar el pipeline
```

---

## 🔁 Re-ejecución

Correr nuevamente para **actualizar** ambos configs si el proyecto cambia:
- Re-explora desde cero.
- Sobreescribe `proyecto-config.json`.
- **Actualiza `plan.json` de forma aditiva** — preserva status de pasos existentes, agrega pasos nuevos de `plan.md`.
- Muestra diff de lo que cambió respecto al anterior (si existe).

---

**Idioma de respuesta:** Español 🇪🇸
