# 🚀 Launch Guide - FluxAgentProV2

Guía rápida para levantar y ejecutar el proyecto FluxAgentProV2.

## ⚡ Quick Start

### Opción 1: Usando el launch script (Recomendado)

```bash
# Ejecutar el script de launch
./launch.sh
```

El script automáticamente:
- ✅ Verifica el entorno virtual
- ✅ Verifica variables de entorno
- ✅ Instala dependencias
- ✅ Levanta el servidor

### Opción 2: Usando Make

```bash
# Setup inicial (primera vez)
make setup

# Levantar servidor
make server
```

### Opción 3: Manual

```bash
# 1. Crear entorno virtual
uv venv

# 2. Instalar dependencias
uv sync --all-extras

# 3. Copiar y configurar .env
cp .env.example .env
# Edita .env con tus credenciales

# 4. Levantar servidor
.venv/bin/uvicorn src.api.main:app --reload
```

## 📋 Prerrequisitos

### 1. Python 3.12+

```bash
python3 --version
# Debe mostrar Python 3.12.x o superior
```

### 2. uv (Package Manager)

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verificar instalación
uv --version
```

### 3. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Copiar ejemplo
cp .env.example .env

# Editar con tus credenciales
nano .env  # o tu editor favorito
```

**Variables requeridas:**

```env
# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
SUPABASE_SERVICE_KEY=tu-service-key

# LLM (para CrewAI)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Opcional
APP_ENV=development
LOG_LEVEL=INFO
```

## 🎯 Comandos Principales

### Usando Make

```bash
# Instalar dependencias
make install

# Instalar con dependencias de desarrollo
make dev

# Levantar servidor (development)
make server

# Levantar servidor (production)
make prod

# Ejecutar tests
make test

# Ejecutar tests con coverage
make test-cov

# Limpiar archivos temporales
make clean

# Abrir shell de Python
make shell

# Ver todos los comandos
make help
```

### Usando launch.sh

```bash
# Launch normal
./launch.sh

# Launch con tests previos
./launch.sh --test
```

### Comandos Directos

```bash
# Instalar dependencias
uv sync --all-extras

# Ejecutar tests
.venv/bin/pytest tests/ -v

# Levantar servidor
.venv/bin/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔍 Verificación

### 1. Health Check

```bash
curl http://localhost:8000/health
# Debe retornar: {"status":"ok"}
```

### 2. Documentación API

Abre en tu navegador:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 3. Tests

```bash
.venv/bin/pytest tests/ -v
# Debe mostrar: 151 passed (o más)
```

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Server                        │
│  Port: 8000                                              │
│                                                          │
│  Endpoints:                                              │
│  - GET  /health              (Health check)             │
│  - POST /webhooks/trigger    (Trigger workflow)         │
│  - GET  /tasks/{task_id}     (Get task status)          │
│  - GET  /tasks               (List tasks)               │
│  - POST /approvals/{task_id} (Approve/reject)           │
│  - POST /chat                (Chat with Architect)      │
│  - GET  /workflows           (List workflows)           │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   CrewAI Flows                           │
│  - BaseFlow (lifecycle)                                 │
│  - ArchitectFlow (genera workflows)                     │
│  - DynamicFlow (workflows dinámicos)                    │
│  - MultiCrewFlow (múltiples agentes)                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Supabase (PostgreSQL)                  │
│  - tasks (estado de workflows)                          │
│  - snapshots (estados serializados)                     │
│  - domain_events (event sourcing)                       │
│  - agent_catalog (definiciones de agentes)              │
│  - workflow_templates (templates generados)             │
│  - memory_vectors (memoria semántica)                   │
│  - secrets (credenciales cifradas)                      │
└─────────────────────────────────────────────────────────┘
```

## 📊 Fases del Proyecto

### ✅ Phase 1 - Base Engine
- Motor base de orquestación
- BaseFlow + BaseFlowState
- Event sourcing
- Multi-tenant con RLS

### ✅ Phase 2 - Governance
- Human-in-the-Loop (HITL)
- Vault de secretos
- Guardrails de negocio

### ✅ Phase 3 - Multi-Agent
- Coordinación de múltiples crews
- Memoria semántica vectorial
- Dynamic workflows

### ✅ Phase 4 - Conversational
- ArchitectFlow (genera workflows desde NL)
- Chat endpoint
- Workflow templates

## 🐛 Troubleshooting

### Error: "uv no está instalado"

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reiniciar terminal o ejecutar
source ~/.bashrc  # o ~/.zshrc
```

### Error: "No module named 'src'"

```bash
# Asegúrate de estar en el directorio correcto
cd /home/daniel/develop/Personal/FluxAgentProV2

# Reinstalar en modo editable
uv sync --all-extras
```

### Error: "SUPABASE_URL no está configurada"

```bash
# Verificar que .env existe y tiene las variables
cat .env | grep SUPABASE

# Si no existe, copiar desde .env.example
cp .env.example .env
# Editar .env con tus credenciales
```

### Error: Tests fallando

```bash
# Ejecutar tests con más detalle
.venv/bin/pytest tests/ -v --tb=long

# Ejecutar tests específicos
.venv/bin/pytest tests/unit/test_baseflow.py -v

# Ver coverage
.venv/bin/pytest tests/ --cov=src --cov-report=html
# Abrir htmlcov/index.html en el navegador
```

### Error: Puerto 8000 ya está en uso

```bash
# Usar otro puerto
PORT=8080 make server

# O matar el proceso existente
pkill -f "uvicorn src.api.main:app"
```

## 📚 Recursos Adicionales

- **Documentación API:** http://localhost:8000/docs
- **Tests:** `make test-cov`
- **Logs:** Ver output de la consola donde corre el servidor
- **Makefile:** `make help` para ver todos los comandos

## 🎉 ¡Listo!

El servidor debería estar corriendo en http://localhost:8000

Prueba los endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Listar workflows
curl http://localhost:8000/workflows

# Trigger de workflow
curl -X POST http://localhost:8000/webhooks/trigger \
  -H "Content-Type: application/json" \
  -H "X-Org-ID: tu-org-id" \
  -d '{"flow_type": "generic_flow", "input_data": {"text": "Hello"}}'
```
