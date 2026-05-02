# Testing Guide — FluxAgentPro V2

> **Fase:** VI — Testing (Certificacion Tecnica)
> **Suite actual:** 512+ tests

## Comandos Rapidos

```bash
make test-all        # Suite completa: lint → unit → integration → e2e → security → stress → perf → coverage
make test-fast       # Solo unitarios
make coverage        # Reporte cobertura (threshold 75%)
make lint            # Linter (ruff)
fap test-step N      # Tests del paso N
fap phase-close testing --certify  # Certificacion completa
```

## Estructura de Tests

```
tests/
├── conftest.py              # Fixtures globales
├── unit/                    # Tests unitarios (~30+ archivos)
│   ├── test_mcp_pool_circuit.py
│   ├── test_service_connector.py
│   ├── test_approval_operators.py
│   ├── test_sanitizer.py
│   ├── test_security_guard.py
│   └── ...
├── integration/             # Tests de integracion
│   ├── test_mcp_resilience.py
│   ├── test_handover_real.py
│   ├── test_dynamic_flow.py
│   └── ...
├── e2e/                     # Tests end-to-end
│   ├── test_production_flows.py
│   ├── test_scenario_1_greeter.py
│   └── ...
├── stress/                  # Tests de estres y robustez
│   ├── test_concurrency.py
│   ├── test_edge_cases.py
│   └── test_performance.py
└── test_*.py                # Tests legacy (raiz)
```

## Pasos de Certificacion

### Paso 0: Auditoria de Linea Base
```bash
fap baseline-check
make lint
```
Verifica importabilidad de modulos, suite existente, lint.

### Paso 1: Cobertura Unitaria de Gaps Criticos
```bash
fap test-step 1 --cov
```
30 tests: MCPPool circuit breaker (5), ServiceConnector error paths (7), Approval operators (4), Sanitizer (14).

### Paso 2: Tests de Integracion de Flujos Criticos
```bash
fap test-step 2
```
Tests de integracion para MCP resilience, handover real, approval operators.

### Paso 3: Validacion de Seguridad Profunda
```bash
fap test-step 3
```
Tests E2E de flujos de produccion con validacion de seguridad.

### Paso 4: Hardening de API Publica
```bash
fap test-step 4
```
Tests de estres (concurrencia) + edge cases.

### Paso 5: Tests de Regresion E2E
```bash
fap test-step 5
```
Tests de seguridad: security_guard + escape analysis.

### Paso 6: Performance y Observabilidad
```bash
fap test-step 6
```
Tests de performance (estres/performance).

### Paso 7: Documentacion y Cierre
```bash
fap test-step 7
```
Verifica documentacion (TESTING.md, CHANGELOG.md, README.md, phase-state.md) + lint.

## Estrategia de Mocking

| Componente | Mocking |
|---|---|
| Supabase DB | `mock_service_client` fixture (patch 8 import points) |
| HTTP calls | `patch("httpx.Client")` |
| Vault secrets | `patch("src.tools.service_connector.get_secret")` |
| Time | `unittest.mock.patch("time.time")` por test (no fixture global) |
| MCPPool | `MCPPool.reset()` en fixture `autouse=True` entre tests circuit breaker |
| Pure functions | Import directo, sin mocking |

## Fixtures Globales

Definidas en `tests/conftest.py`:
- `mock_service_client` — Parchea `get_service_client` en 8 puntos de import
- Auto-cleaning entre tests para estado global (MCPPool, etc.)

## Coverage

```bash
make coverage        # pytest --cov=src --cov-report=html --cov-fail-under=75
```
- Threshold minimo: 75%
- Fuentes: `src/` (excluye tests, CLI phase_close y main)
- Reporte HTML en `htmlcov/index.html`

## Notas

- **test_3_5_latency.py:** Fallo conocido en CI. Excluir con `-k "not latency"`.
- **Makefile en Windows nativo:** `find`/`pkill` no disponibles. Usar WSL o comandos manuales.
- **CHANGELOG:** Cada paso DEBE actualizarlo al completarse.
