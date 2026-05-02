# Changelog

All notable changes to FluxAgentPro V2 are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-05-01

### Added

#### Paso 7 — Documentacion y Cierre
- `TESTING.md` — Guia completa de testing con comandos por paso (0-7), mocking strategy, fixtures
- `CHANGELOG.md` — Registro de cambios (este archivo)
- `Makefile targets` — `test-all`, `test-fast`, `coverage` — suite completa CI
- Makefile migrado a `uv run` para cross-platform (Windows/Linux/WSL)
- `pyproject.toml` — `[tool.coverage.run]` y `[tool.coverage.report]` config con threshold 75%
- `fap phase-close` — Soporte Fase VI (`--phase testing`) con `--full`, `--certify`, `run_coverage()`
- `fap test-step` — Mapeos para pasos 4 (stress), 6 (performance), 7 (docs check)
- Carpeta `DEVS/IMPLEMENTED/testing/07-Documentacion-y-Cierre/`
- `phase-state.md` — Actualizado: 8/8 pasos, bug `>=`/`<=`/`==` marcado resuelto
- `README.md` — Actualizado a Fase VI — Testing

#### Paso 6 — Performance y Observabilidad
- Tests de performance en `tests/stress/test_performance.py`
- Observabilidad de metricas de ejecucion

#### Paso 5 — Tests de Regresion E2E
- Tests de seguridad: `test_security_guard.py`, `test_security_guard_escape.py`
- Suite E2E de regresion

#### Paso 4 — Hardening de API Publica
- Tests de estres: `test_concurrency.py`, `test_edge_cases.py`
- Robustez ante carga concurrente y casos limite

#### Paso 3 — Validacion de Seguridad Profunda
- Tests E2E de flujos de produccion con validacion de seguridad
- SecurityGuard scanning + RestrictedPython sandboxing

#### Paso 2 — Tests de Integracion de Flujos Criticos
- Tests de integracion: MCP resilience, handover real, dynamic flow
- Suite de integracion para flujos multi-paso

#### Paso 1 — Cobertura Unitaria de Gaps Criticos
- 30 tests unitarios: MCPPool circuit breaker (5), ServiceConnector error paths (7), Approval operators (4), Sanitizer (14)
- DX tool `fap test-step 1`
- Bug `>=`/`<=`/`==` resuelto en `dynamic_flow.py` — operadores compuestos con orden correcto

#### Paso 0 — Auditoria de Linea Base
- Verificacion de importabilidad de todos los modulos `src/`
- Suite existente: 100% pass
- Lint estricto: 0 errores
- Fixtures `conftest.py` funcionales

### Changed
- Makefile: targets `.venv/bin/` migrados a `uv run` (cross-platform)
- `phase_close.py`: Generalizado para soportar `--phase testing` manteniendo backward compat con Fase V
- `test_step.py`: Agregados pasos 4, 6, 7 a STEP_TEST_FILES y STEP_COVERAGE_FILES
- `pyproject.toml`: Agregada config de coverage con threshold 75%
- `README.md`: Estado actualizado a Fase VI — Testing
- `phase-state.md`: Bug `>=`/`<=`/`==` marcado como resuelto

### Fixed
- Bug `>=`/`<=`/`==` en `dynamic_flow.py` — operadores compuestos ahora parseados con orden correcto (compuestos antes que simples)
