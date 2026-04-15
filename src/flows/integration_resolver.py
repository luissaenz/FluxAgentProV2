"""src/flows/integration_resolver.py — Resuelve herramientas alucinadas contra el catálogo real.

Logic:
1. Extract hint from LLM (e.g. "google_sheets_read")
2. Fuzzy match against service_tools (e.g. "google_sheets.read_spreadsheet")
3. Verify service activation and credentials
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

from ..db.session import get_service_client
from ..db.vault import upsert_secret, list_secrets

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Resultado de la resolución de integraciones para un workflow."""
    available: List[str] = field(default_factory=list)          # Tools reales encontradas y listas
    needs_activation: List[str] = field(default_factory=list)   # Service IDs que faltan habilitar
    not_found: List[str] = field(default_factory=list)          # Tools alucinadas sin ningún match
    needs_credentials: List[str] = field(default_factory=list)  # Secret names que faltan en Vault
    tool_mapping: Dict[str, str] = field(default_factory=dict)  # Mapping: alucinada -> real
    
    @property
    def is_ready(self) -> bool:
        """True si el workflow se puede persistir y ejecutar inmediatamente."""
        return not (self.needs_activation or self.not_found or self.needs_credentials)


class IntegrationResolver:
    """Valida y mapea tools de un WorkflowDefinition contra el catálogo productivo."""

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.db = get_service_client()
        self._service_tools_cache: List[Dict[str, Any]] = []

    async def resolve(self, workflow_def: Dict[str, Any]) -> ResolutionResult:
        """
        Analiza el workflow y resuelve dependencias de tools.
        
        Args:
            workflow_def: Diccionario del WorkflowDefinition (model_dump)
        """
        logger.info("Iniciando resolución de integraciones para org '%s'", self.org_id)
        
        # 1. Extraer todas las tools alucinadas (hints)
        hints = set()
        for agent in workflow_def.get("agents", []):
            for tool in agent.get("allowed_tools", []):
                hints.add(tool)
        
        result = ResolutionResult()
        
        if not hints:
            logger.debug("No se detectaron tools en el workflow")
            return result

        # Pre-cargar catálogo para matching eficiente
        await self._load_catalog()
        
        # 2. Match fuzzy para cada hint
        matched_services = set()
        for hint in hints:
            real_tool_id = self._find_tool_match(hint)
            
            if real_tool_id:
                result.tool_mapping[hint] = real_tool_id
                service_id = real_tool_id.split(".")[0]
                matched_services.add(service_id)
                logger.debug("Match: '%s' -> '%s'", hint, real_tool_id)
            else:
                result.not_found.append(hint)
                logger.warning("Tool no encontrada: '%s'", hint)

        # 3. Verificar activación de servicios involucrados
        active_services = await self._get_active_services()
        
        for svc_id in matched_services:
            if svc_id not in active_services:
                result.needs_activation.append(svc_id)
                logger.info("Servicio requiere activación: '%s'", svc_id)
            else:
                # 4. Verificar credenciales en Vault
                missing_secrets = await self._check_missing_secrets(svc_id)
                if missing_secrets:
                    result.needs_credentials.extend(missing_secrets)
                    logger.info("Faltan secretos para '%s': %s", svc_id, missing_secrets)
                else:
                    # Tool está disponible y lista
                    # (Available se llena con las reales que pasaron filtros)
                    for alucinada, real in result.tool_mapping.items():
                        if real.startswith(f"{svc_id}."):
                            result.available.append(real)

        return result

    async def _load_catalog(self) -> None:
        """Cargar service_tools en memoria."""
        res = self.db.table("service_tools").select("id, name, service_id").execute()
        self._service_tools_cache = res.data or []

    def _find_tool_match(self, hint: str) -> Optional[str]:
        """Estrategia de matching en 3 niveles."""
        # Nivel 1: Exact Match (id)
        for tool in self._service_tools_cache:
            if tool["id"] == hint:
                return tool["id"]
        
        # Nivel 2: Keyword match dentro del servicio inferido
        # Ej: "google_sheets_read" -> hint_service="google_sheets"
        hint_service = hint.split("_")[0] if "_" in hint else hint
        potential_tools = [t for t in self._service_tools_cache if t["service_id"] == hint_service]
        
        if potential_tools:
            # Buscar coincidencia en name
            best_match = None
            best_score = 0.0
            for t in potential_tools:
                score = SequenceMatcher(None, hint.lower(), t["name"].lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = t["id"]
            
            if best_score > 0.6: # SUPUESTO: 0.6 es umbral aceptable para matching de keywords
                return best_match

        # Nivel 3: ILIKE global por nombre
        best_match = None
        best_score = 0.0
        for t in self._service_tools_cache:
            score = SequenceMatcher(None, hint.lower(), t["name"].lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = t["id"]
        
        if best_score > 0.7: # Umbral más estricto para match global
            return best_match
            
        return None

    async def _get_active_services(self) -> List[str]:
        """Obtener IDs de servicios activos para la org."""
        res = (
            self.db.table("org_service_integrations")
            .select("service_id")
            .eq("org_id", self.org_id)
            .eq("status", "active")
            .execute()
        )
        return [row["service_id"] for row in res.data or []]

    async def _check_missing_secrets(self, service_id: str) -> List[str]:
        """Verificar si faltan secretos requeridos por el servicio."""
        # Obtener secretos requeridos por el catálogo
        svc_res = (
            self.db.table("service_catalog")
            .select("required_secrets")
            .eq("id", service_id)
            .maybe_single()
            .execute()
        )
        
        if not svc_res.data or not svc_res.data.get("required_secrets"):
            return []
            
        required = svc_res.data["required_secrets"]
        current = list_secrets(self.org_id)
        
        return [s for s in required if s not in current]

    async def activate_service(self, service_id: str) -> None:
        """Activa un servicio para la org (lo pone en pending_setup)."""
        self.db.table("org_service_integrations").upsert({
            "org_id": self.org_id,
            "service_id": service_id,
            "status": "pending_setup", # Requiere configuración manual o wizard
        }, on_conflict="org_id,service_id").execute()
        logger.info("Servicio '%s' activado (pending_setup) para org '%s'", service_id, self.org_id)

    async def store_credential(self, secret_name: str, secret_value: str) -> None:
        """Almacena credencial en Vault."""
        upsert_secret(self.org_id, secret_name, secret_value)

    def apply_mapping(self, workflow_def: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Reemplaza tools alucinadas por tools reales en el workflow_def."""
        if not mapping:
            return workflow_def
            
        for agent in workflow_def.get("agents", []):
            tools = agent.get("allowed_tools", [])
            new_tools = []
            for t in tools:
                new_tools.append(mapping.get(t, t))
            agent["allowed_tools"] = new_tools
            
        return workflow_def
