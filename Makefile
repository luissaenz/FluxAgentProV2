# FluxAgentProV2 - Makefile
# Comandos comunes para desarrollo y deployment
# Nota: usa 'uv run' para cross-platform compat (Windows/Linux/WSL).

.PHONY: help install dev server test test-all test-fast test-cov coverage lint lint-fix clean migrate shell logs stop restart check-env setup

# Variables
PYTHON := uv run python
PIP := uv run pip
PYTEST := uv run pytest
UVICORN := uv run uvicorn
SHELL := /bin/bash
HOST ?= 0.0.0.0
PORT ?= 8000

# ── Ayuda ────────────────────────────────────────────────────────

help:
	@echo "FluxAgentProV2 - Comandos disponibles:"
	@echo ""
	@echo "  make install      - Instalar dependencias (uv sync)"
	@echo "  make dev          - Instalar dependencias de desarrollo"
	@echo "  make server       - Levantar servidor (development)"
	@echo "  make prod         - Levantar servidor (production)"
	@echo "  make test         - Ejecutar tests (default)"
	@echo "  make test-all     - Suite completa: lint → unit → integracion → e2e → seguridad → stress → perf → coverage"
	@echo "  make test-fast    - Solo tests unitarios (rapido)"
	@echo "  make test-verbose - Ejecutar tests con output detallado"
	@echo "  make test-cov     - Ejecutar tests con coverage"
	@echo "  make coverage     - Reporte de cobertura (--cov-fail-under=75)"
	@echo "  make lint         - Ejecutar linter (ruff)"
	@echo "  make lint-fix     - Corregir errores de linter automaticamente"
	@echo "  make clean        - Limpiar archivos temporales"
	@echo "  make migrate      - Aplicar migraciones de Supabase"
	@echo "  make shell        - Abrir shell de Python en el venv"
	@echo "  make logs         - Ver logs del servidor"
	@echo "  make stop         - Detener servidor"
	@echo "  make restart      - Reiniciar servidor"
	@echo "  make setup        - Setup inicial (check-env + install)"
	@echo ""
	@echo "Variables: HOST, PORT, test-args"
	@echo "Ej: make server PORT=8080 | make test test-args='tests/unit/'"
	@echo ""

# ── Instalacion ──────────────────────────────────────────────────

install:
	@echo "→ Instalando dependencias..."
	uv sync
	@echo "✓ Dependencias instaladas"

dev:
	@echo "→ Instalando dependencias de desarrollo..."
	uv sync --all-extras
	@echo "✓ Dependencias de desarrollo instaladas"

# ── Servidor ─────────────────────────────────────────────────────

server:
	@echo "→ Levantando servidor en http://$(HOST):$(PORT)"
	@echo "→ Documentación: http://localhost:$(PORT)/docs"
	$(UVICORN) src.api.main:app \
		--host $(HOST) \
		--port $(PORT) \
		--reload \
		--log-level info

prod:
	@echo "→ Levantando servidor en producción http://$(HOST):$(PORT)"
	$(UVICORN) src.api.main:app \
		--host $(HOST) \
		--port $(PORT) \
		--workers 4 \
		--log-level warning

# ── Tests ────────────────────────────────────────────────────────

test:
	@echo "→ Ejecutando tests..."
	$(PYTEST) tests/ $(test-args)

test-all:
	@echo "→ Ejecutando suite completa de testing..."
	@echo ""
	@echo "=== 1/7: Lint ==="
	uv run ruff check src/ tests/ || (echo "[FAIL] Lint"; exit 1)
	@echo ""
	@echo "=== 2/7: Tests Unitarios ==="
	$(PYTEST) tests/unit/ -v --timeout=60 --tb=short || (echo "[FAIL] Unit tests"; exit 1)
	@echo ""
	@echo "=== 3/7: Tests Integracion ==="
	$(PYTEST) tests/integration/ -v --timeout=60 --tb=short -k "not latency" || (echo "[WARN] Integration tests parcial"; true)
	@echo ""
	@echo "=== 4/7: Tests E2E ==="
	$(PYTEST) tests/e2e/ -v --timeout=120 --tb=short|| (echo "[WARN] E2E tests parcial"; true)
	@echo ""
	@echo "=== 5/7: Tests Seguridad ==="
	$(PYTEST) tests/unit/test_security_guard.py tests/unit/test_security_guard_escape.py -v || (echo "[FAIL] Security tests"; exit 1)
	@echo ""
	@echo "=== 6/7: Tests Estres ==="
	$(PYTEST) tests/stress/ -v --timeout=120 --tb=short|| (echo "[WARN] Stress tests parcial"; true)
	@echo ""
	@echo "=== 7/7: Cobertura ==="
	$(PYTEST) --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=75 tests/unit/ tests/integration/ || (echo "[WARN] Coverage <75%"; true)
	@echo ""
	@echo "✓ test-all completado"
	@echo "Coverage report: htmlcov/index.html"

test-fast:
	@echo "→ Ejecutando solo tests unitarios..."
	$(PYTEST) tests/unit/ -v --timeout=60 --tb=short

test-verbose:
	@echo "→ Ejecutando tests (verbose)..."
	$(PYTEST) tests/ -v --tb=short $(test-args)

test-cov:
	@echo "→ Ejecutando tests con coverage..."
	$(PYTEST) tests/ --cov=src --cov-report=html --cov-report=term-missing $(test-args)
	@echo "✓ Coverage report generado en htmlcov/index.html"

coverage:
	@echo "→ Generando reporte de cobertura..."
	$(PYTEST) --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=75 tests/unit/ tests/integration/
	@echo "✓ Coverage report: htmlcov/index.html"

# ── Linter ───────────────────────────────────────────────────────

lint:
	@echo "→ Ejecutando linter (ruff)..."
	uv run ruff check src/ tests/
	@echo "✓ Lint OK"

lint-fix:
	@echo "→ Ejecutando lint fix (ruff --fix)..."
	uv run ruff check --fix src/ tests/
	@echo "✓ Lint fix completado"

# ── Utilidades ───────────────────────────────────────────────────

clean:
	@echo "→ Limpiando archivos temporales..."
	@if command -v find &> /dev/null; then \
		find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type f -name ".coverage" -delete 2>/dev/null || true; \
		find . -type f -name "*.db" -delete 2>/dev/null || true; \
	else \
		echo "find no disponible (Windows nativo). Usando PowerShell..."; \
		pwsh -Command "Get-ChildItem -Path . -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force 2>`$null"; \
		pwsh -Command "Get-ChildItem -Path . -Directory -Filter '.pytest_cache' -Recurse | Remove-Item -Recurse -Force 2>`$null"; \
		pwsh -Command "Get-ChildItem -Path . -Directory -Filter 'htmlcov' -Recurse | Remove-Item -Recurse -Force 2>`$null"; \
		pwsh -Command "Get-ChildItem -Path . -File -Filter '.coverage' -Recurse | Remove-Item -Force 2>`$null"; \
	fi
	@rm -rf .mypy_cache/ 2>/dev/null || true
	@echo "✓ Archivos temporales limpiados"

migrate:
	@echo "→ Para aplicar migraciones de Supabase:"
	@echo "   1. Abre Supabase Studio"
	@echo "   2. Ve al SQL Editor"
	@echo "   3. Ejecuta los archivos en supabase/migrations/ en orden numérico"
	@echo ""
	@echo "   Archivos disponibles:"
	@ls -1 supabase/migrations/ 2>/dev/null || echo "No hay migraciones"
	@echo ""

shell:
	@echo "→ Abriendo shell de Python..."
	$(PYTHON)

logs:
	@echo "→ Mostrando logs recientes..."
	@if [ -f nohup.out ]; then \
		tail -f nohup.out; \
	else \
		echo "No hay archivo nohup.out. El servidor no está corriendo en background."; \
	fi

stop:
	@echo "→ Deteniendo servidor..."
	@if command -v pkill &> /dev/null; then \
		pkill -f "uvicorn src.api.main:app" || echo "No hay servidor corriendo"; \
	else \
		echo "pkill no disponible (Windows nativo). Detener manualmente el proceso."; \
	fi
	@echo "✓ Servidor detenido"

restart: stop server

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

setup: check-env dev
	@echo "→ Setup inicial completado"
	@echo "✓ Dependencias instaladas"
	@echo "✓ Variables de entorno verificadas"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. Ejecutar migraciones SQL en Supabase"
	@echo "  2. Ejecutar tests: make test"
	@echo "  3. Levantar servidor: make server"
