
```markdown
# 🔧 PROCESO DE SETUP DE PROYECTO (SETUP) — v2.0

## Perfil del Rol
Actúas como **Arquitecto de Software Senior** especializado en reconocimiento de estructuras de proyectos. **Explorás el proyecto real, detectás convenciones y generás `proyecto-config.json` que todos los demás procesos consumirán.**

---

## ⛔ PROHIBICIONES ABSOLUTAS
- **NO** implementes código de negocio.
- **NO** modifiques ningún archivo del proyecto.
- **NO** asumas rutas, frameworks ni convenciones. Todo verificado.
- **NO** preguntes qué hacer. Explorá y ejecutá.
- **NO** afirmes que algo existe sin verificarlo con comandos reales.

> [!CAUTION]
> **SI HAS RECIBIDO/LEÍDO ESTE DOCUMENTO:** Explorá el proyecto y generá `proyecto-config.json`. No preguntar. EJECUTAR.

---

## 📥 Entradas

1. **Ruta raíz del proyecto** (proporcionada por el usuario).
2. **Sistema de archivos real** (acceso directo para exploración).

---

## 🔍 Proceso de Exploración

### PASO 1: Estructura Raíz
```
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
```
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
```
ls {project_root}/frontend/
ls {project_root}/client/
ls {project_root}/web/
ls {project_root}/ui/
find {project_root} -maxdepth 3 -name "index.html" | head -5
find {project_root} -maxdepth 3 -name "App.tsx" -o -name "App.jsx" | head -5
```

#### Base de Datos / Migraciones
```
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
```
find {project_root} -maxdepth 5 -type d -name "models" | head -5
find {project_root} -maxdepth 5 -type d -name "schemas" | head -5
find {project_root} -maxdepth 5 -type d -name "entities" | head -5
find {project_root} -maxdepth 5 -type d -name "types" | head -5
find {project_root} -maxdepth 5 -type f -name "*.prisma" | head -5
find {project_root} -maxdepth 5 -type f -name "schema.py" | head -5
```

#### Tests
```
find {project_root} -maxdepth 4 -type d -name "tests" | head -5
find {project_root} -maxdepth 4 -type d -name "test" | head -5
find {project_root} -maxdepth 4 -type d -name "__tests__" | head -5
find {project_root} -maxdepth 4 -type d -name "spec" | head -5
```

#### Configuración / Entorno
```
find {project_root} -maxdepth 2 -name ".env*" | head -10
find {project_root} -maxdepth 2 -name "docker-compose*" | head -5
find {project_root} -maxdepth 2 -name "Dockerfile*" | head -5
find {project_root} -maxdepth 3 -type d -name "config" | head -5
find {project_root} -maxdepth 3 -type d -name "settings" | head -5
```

#### Documentación y Pipeline
```
find {project_root} -maxdepth 3 -type d -name "DEVS" | head -5
find {project_root} -maxdepth 3 -name "plan*" | head -5
find {project_root} -maxdepth 3 -name "phase-state*" | head -5
find {project_root} -maxdepth 3 -name "sugest*" | head -5
find {project_root} -maxdepth 2 -name "README*" | head -5
```

#### DX / Tooling / Scripts
```
find {project_root} -maxdepth 2 -type d -name "scripts" | head -5
find {project_root} -maxdepth 2 -type d -name "tools" | head -5
find {project_root} -maxdepth 2 -type d -name "cli" | head -5
find {project_root} -maxdepth 2 -type d -name "bin" | head -5
cat {project_root}/package.json | grep '"scripts"' -A 30
```

#### Estado / Pipeline /DEVS
```
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

```
cat {project_root}/package.json          # scripts npm
cat {project_root}/Makefile              # targets make
cat {project_root}/pyproject.toml        # scripts uv/poetry
cat {project_root}/justfile              # targets just
```

Registrar comandos para: `dev`, `build`, `test`, `lint`, `lint:fix`, `migrate`, `seed`.

---

### PASO 6: Detección de Phase Name

Si existe `{project_root}/DEVS/phase-state.md` → leer y extraer el nombre de la fase activa.
Si no existe → `phase_name` = [fase].

---

## 📋 Estructura del `proyecto-config.json`

```json
{
  "meta": {
    "project_name": "",
    "project_root": "",
    "setup_date": "",
    "setup_version": "2.0"
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
    "validacion_exists": false
  }
}
```

> [!IMPORTANT]
> Todos los `paths` = rutas absolutas reales verificadas. No existe → `null`. No inventar rutas.

---

## ✅ Validación del Config Generado

Antes de guardar, verificar:

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

---

## 💾 Archivo de Salida

**Destino:** `{project_root}/proyecto-config.json`

> [!IMPORTANT]
> **REGLA DE ORO:** Único archivo permitido crear = `proyecto-config.json` en raíz del proyecto.

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

## ⚠️ No detectado (requiere revisión manual):
- [paths/campos que quedaron null y son importantes]

## Próximo paso
Todos los prompts del pipeline leen `proyecto-config.json`
como fuente de verdad de rutas y convenciones.
```

---

## 🔁 Re-ejecución

Correr nuevamente para **actualizar** `proyecto-config.json` si el proyecto cambia de estructura:
- Re-explora desde cero.
- Sobreescribe el `proyecto-config.json` existente.
- Muestra diff de lo que cambió respecto al anterior (si existe).

---

**Idioma de respuesta:** Español 🇪🇸
```