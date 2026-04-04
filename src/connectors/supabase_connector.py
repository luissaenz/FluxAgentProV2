"""
src/connectors/supabase_connector.py

Implementación del DataConnector para Fase 6.
Lee y escribe en Supabase bajo RLS del tenant (org_id).

En Fase 7 este archivo se reemplaza por google_sheets_connector.py.
Los agentes no cambian — solo cambia qué conector se inyecta al crear el Flow.

Tablas operativas (con org_id + RLS):
    bartenders_disponibles, precios_bebidas, inventario,
    eventos, cotizaciones, ordenes_compra, auditorias, historial_precios

Tablas de configuración (sin org_id, acceso vía service_role):
    config_consumo_pax, config_margenes, config_climatico,
    equipamiento_amortizacion
"""

from typing import Any
from src.connectors.base_connector import BaseDataConnector
from src.db.session import get_tenant_client, get_service_client
import structlog

logger = structlog.get_logger(__name__)

# Tablas de configuración global — no tienen org_id
CONFIG_TABLES = frozenset({
    "config_consumo_pax",
    "config_margenes",
    "config_climatico",
    "equipamiento_amortizacion",
})

# Clave primaria por tabla operativa
TABLE_PKS: dict[str, str] = {
    "bartenders_disponibles": "bartender_id",
    "precios_bebidas":         "producto_id",
    "inventario":              "item_id",
    "eventos":                 "evento_id",
    "cotizaciones":            "cotizacion_id",
    "ordenes_compra":          "orden_id",
    "auditorias":              "auditoria_id",
    "historial_precios":       "id",
}


class SupabaseMockConnector(BaseDataConnector):
    """
    Fase 6: DataConnector sobre Supabase.

    Fase 7: Reemplazar por GoogleSheetsConnector.
    La interfaz es idéntica — los agentes no cambian.

    Args:
        org_id:  UUID de la organización activa (se usa para RLS)
        user_id: UUID del usuario o "scheduler" para jobs automáticos
    """

    def __init__(self, org_id: str, user_id: str = "system"):
        self.org_id = org_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Tablas operativas
    # ------------------------------------------------------------------

    def read(self, table: str, filters: dict[str, Any] | None = None) -> list[dict]:
        """
        Lee registros de una tabla operativa bajo RLS del tenant.

        El TenantClient llama a set_config('app.org_id', org_id) antes de
        cada query, activando las políticas RLS definidas en 011_rls.sql.
        """
        self._assert_operational(table)
        try:
            with get_tenant_client(self.org_id, self.user_id) as db:
                query = db.table(table).select("*")
                if filters:
                    for col, val in filters.items():
                        if val is None:
                            query = query.is_(col, "null")
                        elif isinstance(val, bool):
                            query = query.eq(col, str(val).lower())
                        else:
                            query = query.eq(col, val)
                result = query.execute()
                return result.data or []
        except Exception as e:
            logger.error("connector.read.error",
                         table=table, filters=filters, error=str(e))
            raise

    def write(self, table: str, data: dict) -> dict:
        """
        Inserta un registro nuevo. Inyecta org_id automáticamente.
        """
        self._assert_operational(table)
        payload = dict(data)
        payload["org_id"] = self.org_id  # siempre inyectado — nunca del agente

        try:
            with get_tenant_client(self.org_id, self.user_id) as db:
                result = db.table(table).insert(payload).execute()
                if not result.data:
                    raise ValueError(f"Insert en {table} no retornó datos")
                logger.info("connector.write.ok",
                            table=table, pk=self._get_pk_value(table, payload))
                return result.data[0]
        except Exception as e:
            logger.error("connector.write.error",
                         table=table, error=str(e))
            raise

    def update(self, table: str, record_id: str, data: dict) -> dict:
        """
        Actualiza campos de un registro existente por su PK.
        RLS garantiza que solo se actualicen registros del tenant.
        """
        self._assert_operational(table)
        pk_col = self._get_pk_col(table)

        try:
            with get_tenant_client(self.org_id, self.user_id) as db:
                result = (
                    db.table(table)
                    .update(data)
                    .eq(pk_col, record_id)
                    .execute()
                )
                if not result.data:
                    raise ValueError(
                        f"Update en {table} no encontró registro con {pk_col}={record_id}"
                    )
                logger.info("connector.update.ok",
                            table=table, record_id=record_id)
                return result.data[0]
        except Exception as e:
            logger.error("connector.update.error",
                         table=table, record_id=record_id, error=str(e))
            raise

    # ------------------------------------------------------------------
    # Tablas de configuración global
    # ------------------------------------------------------------------

    def get_config(self, table: str, filters: dict[str, Any] | None = None) -> list[dict]:
        """
        Lee tablas de configuración global usando service_role (sin RLS de tenant).
        Estas tablas no tienen org_id y son compartidas por todos los tenants.
        """
        self._assert_config(table)
        try:
            db = get_service_client()
            query = db.table(table).select("*")
            if filters:
                for col, val in filters.items():
                    query = query.eq(col, val)
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error("connector.get_config.error",
                         table=table, filters=filters, error=str(e))
            raise

    # ------------------------------------------------------------------
    # Operaciones atómicas especiales (no en la interfaz base)
    # Necesarias para evitar race conditions en inventario
    # ------------------------------------------------------------------

    def reserve_stock(self, item_id: str, cantidad: int) -> dict:
        """
        Reserva stock de forma atómica usando una RPC de Supabase.
        Evita race conditions entre flows simultáneos.

        Lanza ValueError si no hay stock suficiente.

        Args:
            item_id:  ID del item en inventario
            cantidad: unidades a reservar

        Returns:
            El registro de inventario actualizado.
        """
        try:
            db = get_service_client()
            result = db.rpc("reserve_inventory_item", {
                "p_org_id":   self.org_id,
                "p_item_id":  item_id,
                "p_cantidad": cantidad,
            }).execute()

            if result.data and result.data.get("error"):
                raise ValueError(result.data["error"])

            logger.info("connector.reserve_stock.ok",
                        item_id=item_id, cantidad=cantidad)
            return result.data
        except Exception as e:
            logger.error("connector.reserve_stock.error",
                         item_id=item_id, cantidad=cantidad, error=str(e))
            raise

    def release_stock(self, item_id: str, cantidad: int) -> dict:
        """
        Libera stock reservado (cuando se cancela un evento).
        Operación inversa a reserve_stock().
        """
        try:
            db = get_service_client()
            result = db.rpc("release_inventory_item", {
                "p_org_id":   self.org_id,
                "p_item_id":  item_id,
                "p_cantidad": cantidad,
            }).execute()
            logger.info("connector.release_stock.ok",
                        item_id=item_id, cantidad=cantidad)
            return result.data
        except Exception as e:
            logger.error("connector.release_stock.error",
                         item_id=item_id, cantidad=cantidad, error=str(e))
            raise

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _get_pk_col(self, table: str) -> str:
        pk = TABLE_PKS.get(table)
        if not pk:
            raise ValueError(
                f"Tabla '{table}' no está en TABLE_PKS. "
                f"Agregar su PK antes de llamar a update()."
            )
        return pk

    def _get_pk_value(self, table: str, data: dict) -> str | None:
        pk = TABLE_PKS.get(table)
        return data.get(pk) if pk else None

    def _assert_operational(self, table: str) -> None:
        if table in CONFIG_TABLES:
            raise ValueError(
                f"'{table}' es una tabla de configuración. "
                f"Usar get_config() en lugar de read() / write() / update()."
            )

    def _assert_config(self, table: str) -> None:
        if table not in CONFIG_TABLES:
            raise ValueError(
                f"'{table}' no es una tabla de configuración reconocida. "
                f"Tablas válidas: {sorted(CONFIG_TABLES)}"
            )
