"""src/services/warmup.py — Warming up registries for low-latency execution.

This service pre-loads dynamic assets (flows and skills) from the database 
into the L1 memory cache of their respective registries.
"""

import logging
from typing import Dict

from src.db.session import get_tenant_client
from src.flows.registry import flow_registry
from src.tools.registry import tool_registry

logger = logging.getLogger(__name__)


def warmup_registries(org_id: str) -> Dict[str, int]:
    """Pre-load flows and skills into L1 memory cache for a given org_id.
    
    This is essential for system initialization (Analisis-FINAL §2.3) to ensure
    that dynamic assets are ready in memory before first use, avoiding 
    database latency during request execution.
    """
    stats = {"flows": 0, "skills": 0}
    
    try:
        with get_tenant_client(org_id) as db:
            # 1. Warmup Flows (workflow_templates)
            flows_res = (
                db.table("workflow_templates")
                .select("flow_type")
                .eq("org_id", org_id)
                .eq("is_active", True)
                .execute()
            )
            if flows_res.data:
                for flow in flows_res.data:
                    flow_type = flow["flow_type"]
                    try:
                        # Calling .get(..., org_id) triggers _load_from_db 
                        # which populates the L1 cache.
                        flow_registry.get(flow_type, org_id=org_id)
                        stats["flows"] += 1
                    except Exception as e:
                        logger.debug("Warmup: Flow '%s' could not be loaded: %s", flow_type, e)

            # 2. Warmup Skills (skill_catalog)
            skills_res = (
                db.table("skill_catalog")
                .select("name")
                .eq("org_id", org_id)
                .execute()
            )
            if skills_res.data:
                for skill in skills_res.data:
                    skill_name = skill["name"]
                    try:
                        # Calling .get(..., org_id) triggers _load_from_db
                        # which populates the L1 cache.
                        tool_registry.get(skill_name, org_id=org_id)
                        stats["skills"] += 1
                    except Exception as e:
                        logger.debug("Warmup: Skill '%s' could not be loaded: %s", skill_name, e)
                        
        logger.info("Warmup complete for org '%s': %s", org_id, stats)
        return stats
        
    except Exception as exc:
        logger.error("Warmup failed for org '%s': %s", org_id, exc)
        return stats
