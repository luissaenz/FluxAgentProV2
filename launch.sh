#!/usr/bin/env bash
# FluxAgentProV2 - Launch Script
# Levanta el servidor FastAPI con todas las dependencias y validaciones

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Directorio del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info "FluxAgentProV2 - Launch Script"
log_info "=============================="

# 1. Verificar que existe .venv
if [ ! -d ".venv" ]; then
    log_warning "No se encontró .venv. Creando entorno virtual..."
    if command -v uv &> /dev/null; then
        uv venv
        log_success "Entorno virtual creado con uv"
    else
        log_error "uv no está instalado. Instálalo con: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

# 2. Verificar que existe .env
if [ ! -f ".env" ]; then
    log_warning "No se encontró .env. Copiando desde .env.example..."
    cp .env.example .env
    log_warning "Edita .env con tus credenciales antes de continuar"
    log_warning "Variables requeridas:"
    log_warning "  - SUPABASE_URL"
    log_warning "  - SUPABASE_ANON_KEY"
    log_warning "  - SUPABASE_SERVICE_KEY"
    log_warning "  - ANTHROPIC_API_KEY (opcional para CrewAI)"
    log_warning "  - OPENAI_API_KEY (opcional para embeddings)"
    read -p "Presiona Enter después de configurar .env..."
fi

# 3. Verificar variables de entorno críticas
log_info "Verificando variables de entorno..."
missing_vars=()

if [ -z "$SUPABASE_URL" ] && ! grep -q "^SUPABASE_URL=" .env; then
    missing_vars+=("SUPABASE_URL")
fi

if [ -z "$SUPABASE_SERVICE_KEY" ] && ! grep -q "^SUPABASE_SERVICE_KEY=" .env; then
    missing_vars+=("SUPABASE_SERVICE_KEY")
fi

if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error "Faltan variables de entorno: ${missing_vars[*]}"
    log_error "Edita .env y configura estas variables"
    exit 1
fi

log_success "Variables de entorno verificadas"

# 4. Instalar dependencias
log_info "Verificando dependencias..."
if [ ! -f ".venv/bin/uvicorn" ]; then
    log_info "Instalando dependencias con uv..."
    uv sync --all-extras
    log_success "Dependencias instaladas"
else
    log_success "Dependencias verificadas"
fi

# 5. Ejecutar tests (opcional, solo en modo desarrollo)
if [ "$APP_ENV" = "development" ] && [ "$1" = "--test" ]; then
    log_info "Ejecutando tests..."
    .venv/bin/pytest tests/ -v --tb=short
    if [ $? -eq 0 ]; then
        log_success "Todos los tests pasaron"
    else
        log_error "Algunos tests fallaron"
        exit 1
    fi
fi

# 6. Configurar parámetros del servidor
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"
WORKERS="${WORKERS:-1}"

# En producción, desactivar reload y usar múltiples workers
if [ "$APP_ENV" = "production" ]; then
    RELOAD=false
    WORKERS="${WORKERS:-4}"
fi

# 7. Launch del servidor
log_info "========================================"
log_info "FluxAgentProV2 - Iniciando servidor"
log_info "========================================"
log_info "Environment: ${APP_ENV:-development}"
log_info "Host: $HOST"
log_info "Port: $PORT"
log_info "Reload: $RELOAD"
log_info "Workers: $WORKERS"
log_info "========================================"
log_info "Endpoints disponibles:"
log_info "  - GET  /health              (Health check)"
log_info "  - POST /webhooks/trigger    (Trigger workflow)"
log_info "  - GET  /tasks/{task_id}     (Get task status)"
log_info "  - GET  /tasks               (List tasks)"
log_info "  - POST /approvals/{task_id} (Approve/reject task)"
log_info "  - POST /chat                (Chat with Architect)"
log_info "  - GET  /workflows           (List workflows)"
log_info "========================================"
log_info "Documentación API:"
log_info "  - Swagger UI: http://localhost:$PORT/docs"
log_info "  - ReDoc:      http://localhost:$PORT/redoc"
log_info "========================================"

if [ "$RELOAD" = "true" ]; then
    log_info "Modo reload activado - auto-reload en cambios de código"
fi

log_success "¡Servidor listo!"
echo ""

# 8. Ejecutar uvicorn
exec .venv/bin/uvicorn src.api.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload=$RELOAD \
    --workers $WORKERS
