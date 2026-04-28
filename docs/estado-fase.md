# Estado de Fase: Sistema de Importación de Bundles (ZIP) — v15

> 📅 Documento actualizado: 2026-04-28
> 📝 Modo: ACTUALIZACIÓN (Cierre de Paso 17 - CLI Refinement / The Local Forge)

---

## 1. Resumen de Fase

El objetivo de esta fase (**Fase III: Refinamiento y DX**) es elevar la experiencia del desarrollador (DX) y garantizar que el flujo **Local-First** sea robusto, seguro y un espejo fiel del entorno de producción. Tras cerrar la auditoría técnica del backend (Paso 16), el foco se ha trasladado al **FAP-CLI**, convirtiéndolo en una herramienta de grado profesional para desarrollo local.

**Estado Actual:** 🚀 **PASO 17 COMPLETADO Y VALIDADO.** El CLI ahora soporta validación sincronizada, sandbox local restrictivo y flujo completo de autenticación y publicación.

| Paso | Descripción | Estado |
|:---|:---|:---|
| T1-T16| Auditoría de Integridad Técnica y Cierre MVP | ✅ Completado |
| T17 | **CLI Refinement (The Local Forge)** | ✅ Completado |
| T18 | Warmup & Persistence (The Registry Bridge) | ⏳ Pendiente |
| T19 | SemVer & Version Guard | ⏳ Pendiente |
| T20 | Dashboard & Wizard (The Visual Entry) | ⏳ Pendiente |

---

## 2. Estado Actual del Proyecto

### Qué ya está implementado y funcional (verificado contra código):

**Refinamiento de CLI (Paso 17):**
- **Autenticación Persistente (T17.1):** `fap login` implementado. Guarda tokens en `~/.fap/config.json` con permisos restringidos (chmod 600 en POSIX) usando Pydantic para la persistencia (verificado en `src/cli/config.py`).
- **Sincronización de Seguridad (T17.2):** `fap validate --sync` descarga la configuración de seguridad del servidor (`GET /api/bundles/security-config`) para asegurar que la validación local coincida con la del backend (verificado en `src/cli/commands/validate.py`).
- **Sandbox Local (T17.3):** `fap run` permite ejecutar skills localmente usando `RestrictedPython` y el mismo `SecurityGuard` del servidor, garantizando que si una skill corre localmente, correrá en FAP (verificado en `src/cli/commands/run.py`).
- **Pipeline de Publicación (T17.4):** `fap publish` automatiza el empaquetado y subida del bundle usando el token de acceso persistido (verificado en `src/cli/commands/publish.py`).

**Integridad de Backend:**
- **Endpoint de Configuración de Seguridad:** Nuevo endpoint `/api/bundles/security-config` que expone módulos permitidos/prohibidos y versión de Python (verificado en `src/api/routes/bundles.py`).
- **Atomicidad Certificada:** `import_bundle_atomic` garantiza transaccionalidad total (verificado en migración 0027).

---

## 3. Contratos Técnicos Vigentes

### Patrones de Código en Uso (Verificados):
- **RLS (Row Level Security):** Usa `current_org_id()` que lee la variable de sesión `app.org_id` configurada mediante la función RPC `set_config`. ⚠️ *Nota: El plan sugiere `auth.uid()`, pero el código real usa consistentemente el patrón de variable de sesión `app.org_id`* (Verificado en `001_set_config_rpc.sql` y `025_agent_catalog_rls_update.sql`).
- **Auth:** Implementado con `PyJWT`. El CLI usa `httpx` para todas las comunicaciones autenticadas.
- **Sandboxing:** `RestrictedPython >= 7.0` con filtrado AST. Sincronizado entre CLI y Backend.
- **Registry:** Lookup de 4 niveles en `ToolRegistry` con inyección de dependencias de seguridad.

### Estructura del CLI (`fap`):
| Comando | Función | Archivo |
|:---|:---|:---|
| `fap init` | Inicializa estructura de proyecto local | `src/cli/commands/init.py` |
| `fap login` | Gestiona autenticación y tokens | `src/cli/commands/login.py` |
| `fap validate` | Valida bundle (local o remoto con `--sync`) | `src/cli/commands/validate.py` |
| `fap run` | Ejecuta skill en sandbox local | `src/cli/commands/run.py` |
| `fap package` | Genera ZIP con `manifest.json` | `src/cli/commands/package.py` |
| `fap publish` | Empaqueta y sube a FAP | `src/cli/commands/publish.py` |

---

## 4. Registro de Pasos Completados

| Paso | Estado | Archivos Modificados | Decisiones Tomadas | Notas |
|:---|:---|:---|:---|:---|
| T17 | ✅ | `src/cli/`, `src/api/routes/bundles.py`, `pyproject.toml` | Adopción de `Typer` para CLI y `httpx` para red. Paridad de sandbox local/remoto. | DX Nivel Pro |
| T16 | ✅ | `registry.py`, `import_service.py`, `0027_bundle_rpc.sql` | Unificación de criterios de auditoría y cierre de brechas de seguridad | Fase II Auditada |

---

## 5. Criterios de Aceptación (Fase III - Paso 17)

| # | Criterio | Verificación |
|:---|:---|:---|
| 1 | `fap login` persiste credenciales de forma segura | ✅ Verificado (`CLIConfig`) |
| 2 | `fap run` bloquea módulos prohibidos localmente | ✅ Verificado (`SecurityGuard` in CLI) |
| 3 | `fap validate --sync` actualiza reglas desde el server | ✅ Verificado (Endpoint /security-config) |
| 4 | `fap publish` realiza el flujo completo PACK -> UPLOAD | ✅ Verificado (Functional Test) |
| 5 | El CLI es instalable como script de sistema (`pip install -e .`) | ✅ Verificado (`project.scripts` en toml) |

---

## 6. Estado del Repositorio

**Hitos Finales Alcanzados:**
- CLI Refinement (Paso 17) completado al 100%.
- Ecosistema **Local-First** funcional: El desarrollador puede codificar, probar y publicar sin salir de la terminal.
- Sincronización de seguridad garantizada entre cliente y servidor.

---
*Documento actualizado por Antigravity (ATG) siguiendo 0_CONTEXTO.md.*
