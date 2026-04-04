"""
tests/unit/test_supabase_connector.py

Tests del SupabaseMockConnector.
Usan mocks de get_tenant_client y get_service_client
para no requerir una instancia real de Supabase.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from src.connectors.supabase_connector import SupabaseMockConnector

ORG_ID  = "11111111-1111-1111-1111-111111111111"
USER_ID = "test-user"


@pytest.fixture
def connector():
    return SupabaseMockConnector(org_id=ORG_ID, user_id=USER_ID)


@pytest.fixture
def mock_tenant_db():
    """Mock del cliente Supabase con RLS de tenant."""
    db = MagicMock()
    # Encadenar .table().select().execute(), .table().insert().execute(), etc.
    db.table.return_value = db
    db.select.return_value = db
    db.insert.return_value = db
    db.update.return_value = db
    db.eq.return_value = db
    db.is_.return_value = db
    db.execute.return_value = MagicMock(data=[])
    return db


@pytest.fixture
def mock_service_db():
    """Mock del cliente Supabase service_role."""
    db = MagicMock()
    db.table.return_value = db
    db.select.return_value = db
    db.eq.return_value = db
    db.rpc.return_value = db
    db.execute.return_value = MagicMock(data=[])
    return db


# ─── read() ────────────────────────────────────────────────────────────────

class TestRead:
    def test_read_sin_filtros(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[
            {"bartender_id": "BAR-001", "nombre": "Juan Perez", "org_id": ORG_ID}
        ])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.read("bartenders_disponibles")

        assert len(result) == 1
        assert result[0]["bartender_id"] == "BAR-001"

    def test_read_con_filtros(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[
            {"bartender_id": "BAR-001", "disponible": True, "especialidad": "premium"}
        ])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.read("bartenders_disponibles",
                                    {"disponible": True, "especialidad": "premium"})

        # Verificar que se llamó eq() para cada filtro
        assert mock_tenant_db.eq.call_count == 2

    def test_read_tabla_config_lanza_error(self, connector):
        with pytest.raises(ValueError, match="tabla de configuración"):
            connector.read("config_consumo_pax")

    def test_read_retorna_lista_vacia_si_no_hay_datos(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=None)
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.read("eventos")

        assert result == []


# ─── write() ───────────────────────────────────────────────────────────────

class TestWrite:
    def test_write_inyecta_org_id(self, connector, mock_tenant_db):
        registro_creado = {
            "evento_id": "EVT-2026-002",
            "org_id": ORG_ID,
            "status": "nuevo"
        }
        mock_tenant_db.execute.return_value = MagicMock(data=[registro_creado])

        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.write("eventos", {
                "evento_id": "EVT-2026-002",
                "status": "nuevo"
                # org_id NO está en el input — debe inyectarse
            })

        # Verificar que insert recibió org_id
        insert_call_args = mock_tenant_db.insert.call_args[0][0]
        assert insert_call_args["org_id"] == ORG_ID
        assert result["evento_id"] == "EVT-2026-002"

    def test_write_tabla_config_lanza_error(self, connector):
        with pytest.raises(ValueError, match="tabla de configuración"):
            connector.write("config_margenes", {"opcion": "basica"})

    def test_write_lanza_error_si_no_retorna_datos(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            with pytest.raises(ValueError, match="no retornó datos"):
                connector.write("eventos", {"evento_id": "X"})


# ─── update() ──────────────────────────────────────────────────────────────

class TestUpdate:
    def test_update_usa_pk_correcto(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[
            {"evento_id": "EVT-001", "status": "cotizado"}
        ])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.update("eventos", "EVT-001", {"status": "cotizado"})

        # Debe usar "evento_id" como columna de filtro
        mock_tenant_db.eq.assert_called_with("evento_id", "EVT-001")
        assert result["status"] == "cotizado"

    def test_update_tabla_sin_pk_lanza_error(self, connector):
        with pytest.raises(ValueError, match="no está en TABLE_PKS"):
            connector.update("tabla_inexistente", "X", {})

    def test_update_lanza_error_si_no_encuentra_registro(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            with pytest.raises(ValueError, match="no encontró registro"):
                connector.update("eventos", "EVT-INEXISTENTE", {"status": "x"})


# ─── get_config() ──────────────────────────────────────────────────────────

class TestGetConfig:
    def test_get_config_factor_climatico(self, connector, mock_service_db):
        mock_service_db.execute.return_value = MagicMock(data=[
            {"mes": 1, "factor_pct": 20, "razon": "Enero: calor extremo NOA"}
        ])
        with patch("src.connectors.supabase_connector.get_service_client",
                   return_value=mock_service_db):
            result = connector.get_config("config_climatico", {"mes": 1})

        assert result[0]["factor_pct"] == 20

    def test_get_config_tabla_operativa_lanza_error(self, connector):
        with pytest.raises(ValueError, match="no es una tabla de configuración"):
            connector.get_config("eventos")

    def test_get_config_one_retorna_none_si_no_existe(self, connector, mock_service_db):
        mock_service_db.execute.return_value = MagicMock(data=[])
        with patch("src.connectors.supabase_connector.get_service_client",
                   return_value=mock_service_db):
            result = connector.get_config_one("config_climatico", {"mes": 99})

        assert result is None


# ─── reserve_stock() ───────────────────────────────────────────────────────

class TestReserveStock:
    def test_reserve_stock_exitosa(self, connector, mock_service_db):
        mock_service_db.execute.return_value = MagicMock(data={
            "ok": True,
            "item_id": "GIN-001",
            "cantidad_reservada": 5,
            "stock_disponible_restante": 7
        })
        with patch("src.connectors.supabase_connector.get_service_client",
                   return_value=mock_service_db):
            result = connector.reserve_stock("GIN-001", 5)

        mock_service_db.rpc.assert_called_once_with("reserve_inventory_item", {
            "p_org_id":   ORG_ID,
            "p_item_id":  "GIN-001",
            "p_cantidad": 5,
        })
        assert result["ok"] is True

    def test_reserve_stock_sin_disponible_lanza_error(self, connector, mock_service_db):
        mock_service_db.execute.return_value = MagicMock(data={
            "error": "Stock insuficiente para GIN-001: disponible=2, solicitado=10"
        })
        with patch("src.connectors.supabase_connector.get_service_client",
                   return_value=mock_service_db):
            with pytest.raises(ValueError, match="Stock insuficiente"):
                connector.reserve_stock("GIN-001", 10)


# ─── read_one() helper ─────────────────────────────────────────────────────

class TestReadOne:
    def test_read_one_retorna_primer_resultado(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[
            {"evento_id": "EVT-001", "status": "nuevo"}
        ])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.read_one("eventos", {"evento_id": "EVT-001"})

        assert result["evento_id"] == "EVT-001"

    def test_read_one_retorna_none_si_no_existe(self, connector, mock_tenant_db):
        mock_tenant_db.execute.return_value = MagicMock(data=[])
        with patch("src.connectors.supabase_connector.get_tenant_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_tenant_db)
            mock_ctx.return_value.__exit__  = MagicMock(return_value=False)

            result = connector.read_one("eventos", {"evento_id": "NO-EXISTE"})

        assert result is None
