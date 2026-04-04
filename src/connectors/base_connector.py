"""
src/connectors/base_connector.py

Interfaz abstracta que todos los conectores de datos deben implementar.

Los agentes SOLO conocen esta interfaz — nunca la implementación concreta.
Esto garantiza que cambiar de Supabase (Fase 6) a Google Sheets (Fase 7)
no requiera tocar ningún agente.

Regla de uso:
    - read()      → leer registros operativos (con org_id, con RLS)
    - write()     → insertar registro nuevo operativo
    - update()    → actualizar registro existente por PK
    - get_config()→ leer tablas de configuración global (sin org_id)
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseDataConnector(ABC):

    # ------------------------------------------------------------------
    # Operaciones sobre tablas operativas (tienen org_id + RLS)
    # ------------------------------------------------------------------

    @abstractmethod
    def read(self, table: str, filters: dict[str, Any] | None = None) -> list[dict]:
        """
        Leer registros de una tabla operativa.

        Args:
            table:   nombre de la tabla (ej: "precios_bebidas")
            filters: filtros opcionales como {columna: valor}
                     Ejemplo: {"disponible": True, "especialidad": "premium"}

        Returns:
            Lista de dicts con los registros. Lista vacía si no hay resultados.

        Ejemplo:
            bartenders = connector.read(
                "bartenders_disponibles",
                {"disponible": True, "especialidad": "premium"}
            )
        """
        pass

    @abstractmethod
    def write(self, table: str, data: dict) -> dict:
        """
        Insertar un registro nuevo en una tabla operativa.
        El conector inyecta org_id automáticamente.

        Args:
            table: nombre de la tabla
            data:  dict con los campos del registro (sin org_id — se inyecta)

        Returns:
            El registro creado tal como quedó en la base de datos.

        Ejemplo:
            evento = connector.write("eventos", {
                "evento_id": "EVT-2026-002",
                "fecha_evento": "2026-07-20",
                "provincia": "Tucuman",
                "pax": 80,
                ...
            })
        """
        pass

    @abstractmethod
    def update(self, table: str, record_id: str, data: dict) -> dict:
        """
        Actualizar campos de un registro existente.

        Args:
            table:     nombre de la tabla
            record_id: valor de la clave primaria del registro
            data:      dict con los campos a actualizar

        Returns:
            El registro actualizado.

        Ejemplo:
            connector.update("eventos", "EVT-2026-002", {
                "status": "cotizado",
                "cotizacion_id": "COT-2026-002"
            })
        """
        pass

    # ------------------------------------------------------------------
    # Operaciones sobre tablas de configuración (sin org_id, globales)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_config(self, table: str, filters: dict[str, Any] | None = None) -> list[dict]:
        """
        Leer tablas de configuración global de la instalación.

        Tablas soportadas:
            - config_consumo_pax       (consumo por tipo de menú)
            - config_margenes          (márgenes de venta)
            - config_climatico         (factores climáticos NOA)
            - equipamiento_amortizacion (amortización por evento)

        Args:
            table:   nombre de la tabla de configuración
            filters: filtros opcionales (ej: {"tipo_menu": "premium"})

        Returns:
            Lista de dicts con los registros de configuración.

        Ejemplo:
            factor = connector.get_config(
                "config_climatico",
                {"mes": 1}
            )[0]["factor_pct"]  # → 20
        """
        pass

    # ------------------------------------------------------------------
    # Helpers de conveniencia (implementación base, no abstractos)
    # ------------------------------------------------------------------

    def read_one(self, table: str, filters: dict[str, Any]) -> dict | None:
        """
        Leer un único registro. Retorna None si no existe.
        Útil para buscar por ID sin tener que indexar la lista.

        Ejemplo:
            evento = connector.read_one("eventos", {"evento_id": "EVT-2026-001"})
        """
        results = self.read(table, filters)
        return results[0] if results else None

    def get_config_one(self, table: str, filters: dict[str, Any]) -> dict | None:
        """
        Leer un único registro de configuración. Retorna None si no existe.

        Ejemplo:
            consumo = connector.get_config_one(
                "config_consumo_pax",
                {"tipo_menu": "premium"}
            )
        """
        results = self.get_config(table, filters)
        return results[0] if results else None
