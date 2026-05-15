# 🧠 Análisis técnico — Paso 8 (Export Dialog y flujo de exportación) 

AGENTE: x<environment_details>
PASO: 8

## 0️⃣ Verificación contra Código Fuente (OBLIGATORIA)
- ExportDialog real: presente como Dialog inline en CrewCanvas.tsx (no archivo separado). Evidencia: dashboard/components/builder/CrewCanvas.tsx:559-571.
- Acción de exportar: botón Export en CrewCanvas llama confirmExport, que envía payload a /bundles/export. Evidencia: CrewCanvas.tsx:208-246.
- Endpoint backend: POST /api/bundles/export existe y valida goal/backstory; orquestra ExportService. Evidencia: src/api/routes/bundles.py:199-210, 215-238. 
- Orquestador de export: ExportService.export(payload) genera ZIP y nombre; usa create_base_manifest. Evidencia: src/services/export_service.py:21-41, 62-70; src/utils/bundle_utils.py (creación de manifest).
- Estructura del ZIP exportado: manifest.json + agents.json + (opcional) skills/*.py; MVP actual envuelve agents y optional skills; flows no incluidos. Evidencia: src/services/export_service.py:39-49, 52-67; src/services/bundle_schemas.py (AgentExportItem, SkillExportItem, ExportBundleRequest).
- Descarga del ZIP: Response (no StreamingResponse) desde la ruta export; headers para descarga. Evidencia: bundles.py:241-247.
- Copy as JSON: disponible en la UI; implementado en CrewCanvas.tsx (handleCopyJSON). Evidencia: CrewCanvas.tsx:362-366.
- Integración con AgentForm: Export disponible desde CrewCanvas; no hay separación en AgentForm. Evidencia: estructura de CrewCanvas.tsx y Connector con AgentForm no observable aquí. 

## 1️⃣ Análisis de Datos (ETAPA 1)
- Datos exportables: agentes (roles, soul_json, herramientas permitidas, max_iter) y, opcionalmente, skills (name, code). Estructura de payload esperada por ExportBundleRequest (bundle_name, agents, skills). Evidencia: src/services/bundle_schemas.py, ExportBundleRequest y AgentExportItem.
- Patrones de seguridad: require_org_id en endpoint; validación de contenido de soul_json (goal/backstory) en endpoint export. Evidencia: src/api/routes/bundles.py lines donde se valida soul_json y longitud mínima; 214-238; 248-253.
- Riesgo de grandes bundles: flows vacíos en MVP; assets de skills opcionales. Evidencia: src/services/export_service.py y export endpoint. 

## 2️⃣ Análisis de Código (ETAPA 2)
- Interfaces principales:
  - AgentExportItem(role: str, soul_json: Dict, allowed_tools: List[str], max_iter: int)
  - SkillExportItem(name: str, code: str)
  - ExportBundleRequest(bundle_name?: str, agents: List[AgentExportItem], skills?: Dict[str, str])
  - BundleManifest, BundleInfo, BundleRPCResult, BundleValidationResult
  Evidencia: src/services/bundle_schemas.py.
- Patrones: separación entre controlador HTTP y lógica de negocio (ExportService). Evidencia: src/api/routes/bundles.py vs src/services/export_service.py.
- Reutilización de utils: create_base_manifest para manifest.json. Evidencia: src/services/export_service.py (import de create_base_manifest).
- Validaciones: en endpoint, verificación de soul_json.goal y soul_json.backstory con longitud mínima 10; 422 si inválido. Evidencia: src/api/routes/bundles.py export().
- Detección de errores: manejo de MalformedVersionError, VersionDowngradeError, VersionConflictError, BundleError, SecurityError; 500 genérico. Evidencia: src/api/routes/bundles.py lines 95-113.

## 3️⃣ Análisis de Backend (ETAPA 3)
- Endpoints relevantes:
  - POST /api/bundles/export: Input ExportBundleRequest; Output ZIP; 200 con zip; errores 422/400/500; manejo de org_id. Evidencia: src/api/routes/bundles.py export() y export endpoint. 
  - GET /security-config, /history, /{bundle_id}/details, etc. (no bloquea el comportamiento de export). Evidencia: bundles.py.
- Contratos entre frontend y backend: payload agents (role, soul_json, allowed_tools, max_iter); opciones para skills; zip resultante debe ser descargable. Evidencia: ExportBundleRequest y ExportService. 
- Manejo de errores: 400 para invalid data; 409 para conflictos de versión; 500 para errores internos. Evidencia: src/api/routes/bundles.py.

## 4️⃣ Análisis de Fullstack + DX (ETAPA 4)
- Flujo end-to-end: UI de Export Crew desde CrewCanvas; al exportar se obtiene ZIP descargable; usuario puede Copy as JSON. Evidencia: CrewCanvas.tsx export dialog y Copy JSON;  export endpoint. 
- DX recomendada (con base en el plan):
  - Separar ExportDialog en componente own: ExportDialog.tsx y un hook para datos; actualmente es export dialog inline. Evidencia: presencia de Dialog en CrewCanvas.tsx y ausencia de ExportDialog.tsx.
  - Añadir checkbox Include skills en la UI; actual MVP envía solo agents. Evidencia: no existe include-skills control en UI; payload generado en canvasToExportPayload y confirmExport comprende solo Agents.
  - Añadir visual summary pre-export (número de agentes, roles únicos, etc.) antes de confirmar export. Evidencia: exportWarning actualiza con una nota genérica; no hay resumen detallado.
  - Integración UX con AgentForm: export operativo desde Canvas con guardado y posible vista previa del código generado; no hay integración con AgentForm para export directo ahí. Evidencia: estructura de componentes.
- DX toolchain propuesta: un CLI `fap bundle export` (ya en plan) y un wizard de exportación para confirmar datos antes de exportar. Evidencia: plan.md.

## 🔍 VERIFICACIÓN OBLIGATORIA CONTRA CÓDIGO FUENTE
- A) Endpoints y contratos: /api/bundles/export existe; ExportBundleRequest valida bundle_name, agents y skills. Evidencia: src/api/routes/bundles.py export + src/services/bundle_schemas.py ExportBundleRequest.
- B) Lógica de export: ExportService crea manifest con create_base_manifest; agentes/skills se serializan para empaquetar; zip generado por BundleManager. Evidencia: src/services/export_service.py; src/utils/bundle_utils.py; src/services/bundle_manager.py (no mostrado, pero acuedo). 
- C) Estructura del ZIP: manifest.json + agents.json + skills/*.py (si proporcionados). Evidencia: export_service.py + Skill handling en 52-61.
- D) Flujo de UI: botón Export en CrewCanvas abre dialog; confirmExport envía payload; descarga ZIP. Evidencia: CrewCanvas.tsx 208-246 y 559-571.
- E) Copy JSON: Implementation en CrewCanvas.tsx 362-366.

## ⚠️ DISCREPANCIAS ENCONTRADAS (resolución propuesta)
- D1. ExportDialog separado: No hay ExportDialog.tsx; la UI del Paso 8 está integrada como Dialog dentro de CrewCanvas.tsx. -> Crear ExportDialog.tsx para alinear al plan.
- D2. Include skills: UI no muestra checkbox; export solo envía agents. -> Añadir Include Skills option en UI y adaptar payload a skills[].
- D3. Resumen pre-export: no hay resumen detallado; se usa exportWarning genérico. -> Implementar resumen previo (número de agentes, roles, herramientas) antes de abrir export.
- D4. Integración con AgentForm: plan indica integración desde AgentForm; actual está desde CrewCanvas. -> Añadir integración o al menos enlace visible entre AgentForm y ExportDialog.

## 🧩 Criterios de Aceptación (adaptados a estado actual)
- Endpoints: POST /api/bundles/export responde 200 y entrega ZIP descargable. Evidencia: destino endpoint y prueba de descarga en navegador. 
- Validación de datos: soul_json.goal/backstory con longitud mínima 10. Evidencia: src/api/routes/bundles.py export().
- Estructura del ZIP: manifest.json; agents.json; skills/*.py si present; flows vacíos. Evidencia: ExportService y build de zip.
- UX: Export Crew dialog presente; Copy as JSON funciona. Evidencia: CrewCanvas.tsx.
- DX: Al menos una herramienta DX propuesta (p. ej., CLI bundle export) documentada en plan; ya existente en la spec. Evidencia: plan.md.

## ⚠️ Riesgos
- Tamaño de bundles y performance en parsing/hashes. 
- Seguridad: validación de archivos y permisos de ejecución; manejo de org_id.
- Compatibilidad: rutas y firmas deben mantenerse en sync con migraciones actuales en supabase.

## 🗺️ Plan de Implementación (resumen de acciones para alinear con plan futuro)
- Crear ExportDialog.tsx y extraer lógica de confirmExport a hook, para cumplir paso 8 exacto.
- Agregar opción Include Skills en el diálogo y adaptar ExportBundleRequest para recibir skills[].
- Añadir pre-exports summary con conteo de agentes y roles, y validaciones previas.
- Integrar ExportDialog con AgentForm y con CrewCanvas para coherencia UX.
- Mantener paso a paso pruebas E2E para exportación (CLI y UI).

### Evidencia detallada (con rutas y líneas clave)
- UI Export dialog actual: dashboard/components/builder/CrewCanvas.tsx:559-571
- Botón Export y flujo: CrewCanvas.tsx:482-494, 604-627
- Endpoints backend: src/api/routes/bundles.py export: 199-214, 241-247
- Orquestador de export: src/services/export_service.py:21-41, 62-70
- Export payload y skills handling: src/services/export_service.py:42-50, 52-67
- Pydantic models: src/services/bundle_schemas.py ExportBundleRequest, AgentExportItem, SkillExportItem: 111-116, 95-101
- Security / validation: bundles.py 215-238
- Copy JSON: CrewCanvas.tsx:362-366
