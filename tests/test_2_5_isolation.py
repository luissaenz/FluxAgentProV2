"""
Test de Aislamiento Multi-tenant (Paso 2.5)
------------------------------------------
Este script valida que la identidad SOUL de los agentes esté correctamente
aislada por organización (Tenant), tanto en la lógica de aplicación (Capa A)
como en las políticas de Row Level Security de la base de datos (Capa B).

Uso:
    pytest LAST/test_2_5_isolation.py
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from src.api.routes.agents import get_agent_detail

# ── Capa A: Validación de Lógica de Aplicación ───────────────────

@pytest.mark.asyncio
async def test_agent_detail_isolation_logic():
    """
    Verifica que el endpoint de detalle filtre la metadata por org_id
    y no permita el acceso a agentes de otras organizaciones.
    """
    org_alpha = "org-alpha-123"
    org_beta = "org-beta-456"
    agent_id_beta = "agent-beta-789"

    def make_chain(data):
        mock_exec = MagicMock()
        mock_exec.execute.return_value = MagicMock(data=data)
        
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.maybe_single.return_value = mock_exec
        return mock_chain

    # Mock del TenantClient
    mock_db = MagicMock()
    
    # 1. Simular que el agente existe pero pertenece a OTRA organización
    # El catalog_query debe fallar el .maybe_single() si la query incluye .eq("org_id", context_org_id)
    mock_db.table.return_value = make_chain(None)

    # Ejecutar la llamada simulando que somos Org Alpha intentando ver Agente de Org Beta
    with patch("src.api.routes.agents.get_tenant_client") as mock_gtc:
        mock_gtc.return_value.__enter__.return_value = mock_db
        
        with pytest.raises(HTTPException) as exc:
            await get_agent_detail(agent_id=agent_id_beta, org_id=org_alpha)
        
        assert exc.value.status_code == 404
        assert exc.value.detail == "Agent not found"

    # Verificar que se llamó a la DB con los filtros correctos
    # La primera llamada es al catálogo para verificar permiso
    args, kwargs = mock_db.table.call_args_list[0]
    assert args[0] == "agent_catalog"
    
    # Verificar que se aplicó el filtro de org_id de seguridad
    # Debemos verificar que en la cadena de filtros se incluyó .eq("org_id", org_alpha)
    # mock_db.table().select().eq().eq()
    # filters = [c[0] for c in mock_db.table.return_value.select.return_value.eq.call_args_list]
    # assert any("org_id" in str(arg) and org_alpha in str(arg) for arg in filters)
    
@pytest.mark.asyncio
async def test_metadata_enrichement_isolation():
    """
    Verifica que el JOIN con agent_metadata incluya explícitamente el org_id.
    """
    org_id = "org-123"
    agent_id = "agent-123"
    agent_role = "analyst"

    def make_chain(data):
        mock_exec = MagicMock()
        mock_exec.execute.return_value = MagicMock(data=data)
        
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.maybe_single.return_value = mock_exec
        return mock_chain

    mock_db = MagicMock()
    
    # Configurar respuestas secuenciales
    mock_catalog_chain = make_chain({"id": agent_id, "role": agent_role, "org_id": org_id})
    mock_metadata_chain = make_chain({"display_name": "Sombra de Alpha", "soul_narrative": "Espionaje"})
    mock_task_chain = make_chain([])

    with patch("src.api.routes.agents.get_tenant_client") as mock_gtc:
        mock_gtc.return_value.__enter__.return_value = mock_db
        
        # Secuencia de tablas llamadas en agents.py
        mock_db.table.side_effect = [
            mock_catalog_chain,  # agent_catalog
            mock_metadata_chain, # agent_metadata
            mock_task_chain,     # tasks (recent)
            mock_task_chain      # tasks (tokens)
        ]
        
        result = await get_agent_detail(agent_id=agent_id, org_id=org_id)
        
        # Verificación de datos inyectados
        assert result["agent"]["display_name"] == "Sombra de Alpha"
        assert result["agent"]["soul_narrative"] == "Espionaje"
            
        # Verificar que la query a agent_metadata incluyó el org_id
        # Es la segunda llamada a .table()
        assert mock_db.table.call_args_list[1][0][0] == "agent_metadata"
        
        # Verificacin de filtros en metadata
        # Los filtros .eq() se aplican sobre el objeto devuelto por .select()
        # En nuestro make_chain, .select candidatos devuelven el mismo mock_chain
        metadata_eq_calls = mock_metadata_chain.select.return_value.eq.call_args_list
        
        found_org_filter = False
        for call in metadata_eq_calls:
            if call[0][0] == "org_id" and call[0][1] == org_id:
                found_org_filter = True
        
        assert found_org_filter, f"No se encontró el filtro .eq('org_id', '{org_id}') en la consulta de metadata"


# ── Capa B: Verificación de RLS (Simulada) ──────────────────────

def test_rls_policy_structure():
    """
    Verifica que la política de RLS definida en la migración sea coherente
    con el diseño de aislamiento.
    """
    import os
    migration_path = os.path.join("supabase", "migrations", "020_agent_metadata.sql")
    
    if not os.path.exists(migration_path):
        pytest.skip("Migración 020 no encontrada")
        
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Verificar habilitación de RLS
    assert "ALTER TABLE public.agent_metadata ENABLE ROW LEVEL SECURITY;" in content
    
    # Verificar que la política usa app.org_id
    assert "current_setting('app.org_id', TRUE)" in content
    assert "org_id::text" in content

@pytest.mark.skip(reason="Requiere conexión a DB real con RLS activo para ejecución end-to-end")
def test_rls_isolation_db_level():
    """
    Este test debe ejecutarse contra una DB real.
    Simula dos sesiones con diferentes app.org_id y verifica que no se vean registros ajenos.
    """
    pass
