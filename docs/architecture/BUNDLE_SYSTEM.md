# Bundle System Architecture

Este documento describe el sistema de empaquetado y despliegue atómico de agentes, flujos y herramientas en FluxAgentPro-v2.

## 1. Concepto Core
El sistema de Bundles permite desplegar capacidades completas (agentes + lógica + herramientas) como una unidad atómica mediante archivos ZIP. Esto elimina las inconsistencias de despliegues parciales y asegura que todas las dependencias estén presentes.

## 2. Estructura del Bundle (ZIP)
Un bundle válido debe seguir esta estructura:
```text
bundle.zip
├── manifest.json       # Definición de archivos y sus hashes (SHA-256)
├── agents/             # Definiciones JSON de agentes
│   └── researcher.json
├── flows/              # Definiciones JSON de workflows
│   └── data_analysis.json
└── skills/             # Código fuente Python para herramientas
    └── custom_tool.py
```

## 3. Pipeline de Importación
La importación es gestionada por `BundleManager` y `SecurityGuard`:

1.  **Recepción**: El ZIP se recibe en memoria (no se guarda en disco).
2.  **Validación de Tamaño**: Máximo 10MB (configurable en `src/config.py`).
3.  **Integridad**: Se verifican los hashes de cada archivo contra el `manifest.json`.
4.  **Seguridad (Sandbox)**: Los archivos en `skills/` son auditados por `SecurityGuard` usando `RestrictedPython`.
5.  **Persistencia Atómica**: Todo el contenido se inserta en una sola transacción mediante la función RPC `import_bundle_atomic` en Supabase/PostgreSQL.

## 4. Restricciones de Seguridad
- **RestrictedPython**: No se permiten imports peligrosos (`os`, `subprocess`, `sys`), ni acceso a `__builtins__` no autorizados.
- **Límites Operativos**:
    - Máximo 15 agentes por bundle.
    - Máximo 20 flows por bundle.
    - Máximo 30 skills por bundle.
- **Validación de Grafo**: Los flows son validados para detectar ciclos de dependencias antes de ser aceptados.

## 5. Referencia Técnica
- **Servicio**: `src/services/bundle_manager.py`
- **Seguridad**: `src/services/security_guard.py`
- **Schemas**: `src/services/bundle_schemas.py`
- **DB**: Función `import_bundle_atomic` (SQL Migration 20240428_bundle_system.sql)
