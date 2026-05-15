# FluxAgentProV2 - Makefile
# Comandos comunes para desarrollo y deployment

.PHONY: help install dev server test lint clean migrate

# Variables
PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn
HOST ?= 0.0.0.0
PORT ?= 8000

# Default target
help:
	@echo "FluxAgentProV2 - Comandos disponibles:"
	@echo ""
	@echo "  make install      - Instalar dependencias (uv sync)"
	@echo "  make dev          - Instalar dependencias de desarrollo"
	@echo "  make server       - Levantar servidor (development)"
	@echo "  make prod         - Levantar servidor (production)"
	@echo "  make test         - Ejecutar tests"
	@echo "  make test-verbose - Ejecutar tests con output detallado"
	@echo "  make test-cov     - Ejecutar tests con coverage"
	@echo "  make lint         - Ejecutar linter (si está configurado)"
	@echo "  make clean        - Limpiar archivos temporales"
	@echo "  make migrate      - Aplicar migraciones de Supabase"
	@echo "  make shell        - Abrir shell de Python en el venv"
	@echo "  make logs         - Ver logs del servidor"
	@echo ""
	@echo "Variables de entorno:"
	@echo "  HOST   - Host del servidor (default: 0.0.0.0)"
	@echo "  PORT   - Puerto del servidor (default: 8000)"
	@echo ""
	@echo "Ejemplos:"
	@echo "  make server PORT=8080"
	@echo "  make test test-args='tests/unit/'"

# Instalar dependencias básicas
install:
	@echo "→ Instalando dependencias..."
	@if command -v uv &> /dev/null; then \
		uv sync; \
	else \
		echo "uv no está instalado. Usando pip..."; \
		$(PIP) install -e .; \
	fi
	@echo "✓ Dependencias instaladas"

# Instalar dependencias de desarrollo
dev:
	@echo "→ Instalando dependencias de desarrollo..."
	@if command -v uv &> /dev/null; then \
		uv sync --all-extras; \
	else \
		echo "uv no está instalado. Usando pip..."; \
		$(PIP) install -e ".[dev]"; \
	fi
	@echo "✓ Dependencias de desarrollo instaladas"

# Levantar servidor en modo desarrollo
server:
	@echo "→ Levantando servidor en http://$(HOST):$(PORT)"
	@echo "→ Documentación: http://localhost:$(PORT)/docs"
	@$(UVICORN) src.api.main:app \
		--host $(HOST) \
		--port $(PORT) \
		--reload \
		--log-level info

# Levantar servidor en modo producción
prod:
	@echo "→ Levantando servidor en producción http://$(HOST):$(PORT)"
	@$(UVICORN) src.api.main:app \
		--host $(HOST) \
		--port $(PORT) \
		--workers 4 \
		--log-level warning

# Ejecutar tests
test:
	@echo "→ Ejecutando tests..."
	@$(PYTEST) tests/ $(test-args)

# Ejecutar tests con output detallado
test-verbose:
	@echo "→ Ejecutando tests (verbose)..."
	@$(PYTEST) tests/ -v --tb=short $(test-args)

# Ejecutar tests con coverage
test-cov:
	@echo "→ Ejecutando tests con coverage..."
	@$(PYTEST) tests/ --cov=src --cov-report=html --cov-report=term-missing $(test-args)
	@echo "✓ Coverage report generado en htmlcov/index.html"

# Ejecutar linter (placeholder - agregar cuando se configure)
lint:
	@echo "→ Ejecutando linter..."
	@if command -v ruff &> /dev/null; then \
		ruff check src/ tests/; \
	else \
		echo "ruff no está instalado. Skipping lint..."; \
	fi

# Limpiar archivos temporales
clean:
	@echo "→ Limpiando archivos temporales..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.pyc" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "*.db" -delete 2>/dev/null || true
	@rm -rf .mypy_cache/ 2>/dev/null || true
	@echo "✓ Archivos temporales limpiados"

# Aplicar migraciones de Supabase (manual - requiere login)
migrate:
	@echo "→ Para aplicar migraciones de Supabase:"
	@echo "   1. Abre Supabase Studio"
	@echo "   2. Ve al SQL Editor"
	@echo "   3. Ejecuta los archivos en supabase/migrations/ en orden numérico"
	@echo ""
	@echo "   Archivos disponibles:"
	@ls -1 supabase/migrations/ 2>/dev/null || echo "   No hay migraciones"
	@echo ""

# Abrir shell de Python en el entorno virtual
shell:
	@echo "→ Abriendo shell de Python..."
	@.venv/bin/python

# Ver logs (útil cuando se corre en background)
logs:
	@echo "→ Mostrando logs recientes..."
	@if [ -f nohup.out ]; then \
		tail -f nohup.out; \
	else \
		echo "No hay archivo nohup.out. El servidor no está corriendo en background."; \
	fi

# Detener servidor (si está corriendo en background)
stop:
	@echo "→ Deteniendo servidor..."
	@pkill -f "uvicorn src.api.main:app" || echo "No hay servidor corriendo"
	@echo "✓ Servidor detenido"

# Restart servidor
restart: stop server

# Check de variables de entorno
check-env:
	@echo "→ Verificando variables de entorno..."
	@if [ ! -f ".env" ]; then \
		echo "ERROR: No existe .env"; \
		echo "Copia .env.example a .env y configura las variables"; \
		exit 1; \
	fi
	@required_vars="SUPABASE_URL SUPABASE_SERVICE_KEY"; \
	for var in $$required_vars; do \
		if ! grep -q "^$$var=" .env; then \
			echo "ERROR: Falta variable $$var en .env"; \
			exit 1; \
		fi; \
	done
	@echo "✓ Variables de entorno verificadas"

# Setup inicial del proyecto
setup: check-env dev
	@echo "→ Setup inicial completado"
	@echo "✓ Dependencias instaladas"
	@echo "✓ Variables de entorno verificadas"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. Ejecutar migraciones SQL en Supabase"
	@echo "  2. Ejecutar tests: make test"
	@echo "  3. Levantar servidor: make server"
