"""
src/tools/bartenders/clima_tool.py

Dos responsabilidades separadas:

1. FactorClimaticoTool (Agente 2):
   Lee el factor histórico de config_climatico según mes y provincia.
   Usado en PreventaFlow para presupuestar el riesgo climático.

2. PronosticoRealTool (Agente 5):
   Fase 6: devuelve un pronóstico mock configurable por evento.
   Fase 7: reemplazar _fetch_real_forecast() con llamada a API del SMN.
   Usado en AlertaClimaFlow para detectar desviaciones y disparar ALERTA ROJA.
"""

from typing import Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


# ─── Modelos ───────────────────────────────────────────────────────────────

class FactorClimaticoOutput(BaseModel):
    mes:               int
    factor_pct:        int
    razon:             str
    provincia:         str


class PronosticoRealOutput(BaseModel):
    evento_id:          str
    provincia:          str
    fecha_evento:       str
    temp_historica:     float = Field(..., description="Temperatura histórica esperada (°C)")
    temp_pronosticada:  float = Field(..., description="Temperatura del pronóstico real (°C)")
    desvio_absoluto:    float = Field(..., description="Diferencia en °C (puede ser negativa)")
    desvio_pct:         float = Field(..., description="Desvío relativo al histórico (%)")
    alerta_roja:        bool  = Field(..., description="True si desvío > UMBRAL_ALERTA_PCT")
    descripcion:        str


# ─── Constantes ────────────────────────────────────────────────────────────

UMBRAL_ALERTA_PCT = 10.0  # % de desvío que dispara ALERTA ROJA

# Temperaturas históricas promedio por mes en NOA (°C)
# Fuente: datos climatológicos SMN — usados para comparar con pronóstico real
TEMP_HISTORICA_NOA: dict[int, float] = {
    1: 26.0,  # Enero
    2: 25.5,  # Febrero
    3: 23.0,  # Marzo
    4: 19.0,  # Abril
    5: 14.5,  # Mayo
    6: 11.0,  # Junio
    7: 10.5,  # Julio
    8: 13.0,  # Agosto
    9: 16.5,  # Septiembre
   10: 20.0,  # Octubre
   11: 23.5,  # Noviembre
   12: 25.0,  # Diciembre
}

# Mock de pronósticos por evento para Fase 6
# Estructura: { evento_id: temp_pronosticada }
# Permite simular distintos escenarios sin API externa
MOCK_FORECAST_OVERRIDE: dict[str, float] = {
    "EVT-2026-001": 33.0,  # ola de calor (+7°C vs histórico enero = 26°C)
    # Agregar más eventos según necesidad de demo
}

# Si un evento no está en MOCK_FORECAST_OVERRIDE,
# se usa la temperatura histórica + este delta (0 = sin desvío)
MOCK_DEFAULT_DELTA: float = 0.0


# ─── Tool 1: Factor Climático Histórico (Agente 2) ─────────────────────────

class FactorClimaticoTool(BaseTool):
    name: str = "obtener_factor_climatico"
    description: str = (
        "Obtiene el factor de riesgo climático histórico para un mes dado, "
        "consultando la tabla config_climatico. "
        "Retorna el porcentaje de ajuste a aplicar sobre los costos de productos "
        "y equipamiento en el escandallo."
    )

    connector: Any  # BaseDataConnector

    def _run(self, mes: int, provincia: str = "Tucuman") -> FactorClimaticoOutput:
        if mes < 1 or mes > 12:
            raise ValueError(f"Mes inválido: {mes}. Debe estar entre 1 y 12.")

        config = self.connector.get_config_one("config_climatico", {"mes": mes})

        if not config:
            # Fallback conservador si no hay dato
            return FactorClimaticoOutput(
                mes=mes,
                factor_pct=10,
                razon="Factor default (dato no encontrado en config_climatico)",
                provincia=provincia,
            )

        return FactorClimaticoOutput(
            mes=mes,
            factor_pct=int(config["factor_pct"]),
            razon=config["razon"],
            provincia=provincia,
        )


# ─── Tool 2: Pronóstico Real con Mock (Agente 5) ───────────────────────────

class PronosticoRealTool(BaseTool):
    name: str = "verificar_pronostico_real"
    description: str = (
        "Verifica el pronóstico meteorológico real para un evento específico "
        "y lo compara con el histórico presupuestado. "
        "Si el desvío supera el 10%, activa ALERTA ROJA para disparar "
        "una orden de compra de emergencia. "
        "Fase 6: usa datos mock configurables. "
        "Fase 7: reemplazar con API del SMN."
    )

    connector: Any  # BaseDataConnector

    def _run(
        self,
        evento_id:    str,
        provincia:    str,
        fecha_evento: str,   # formato YYYY-MM-DD
    ) -> PronosticoRealOutput:

        mes = self._extraer_mes(fecha_evento)
        temp_historica   = TEMP_HISTORICA_NOA.get(mes, 20.0)
        temp_pronosticada = self._fetch_real_forecast(evento_id, mes)

        desvio_absoluto = temp_pronosticada - temp_historica
        desvio_pct      = abs(desvio_absoluto) / temp_historica * 100

        alerta_roja = desvio_pct > UMBRAL_ALERTA_PCT

        if alerta_roja:
            descripcion = (
                f"ALERTA ROJA: temperatura pronosticada {temp_pronosticada:.1f}°C "
                f"vs histórica {temp_historica:.1f}°C "
                f"(desvío {desvio_pct:.1f}%). "
                f"Se requiere compra de emergencia de hielo y agua."
            )
        else:
            descripcion = (
                f"Sin alerta: temperatura pronosticada {temp_pronosticada:.1f}°C "
                f"vs histórica {temp_historica:.1f}°C "
                f"(desvío {desvio_pct:.1f}%). "
                f"Dentro del margen normal."
            )

        return PronosticoRealOutput(
            evento_id          = evento_id,
            provincia          = provincia,
            fecha_evento       = fecha_evento,
            temp_historica     = temp_historica,
            temp_pronosticada  = temp_pronosticada,
            desvio_absoluto    = round(desvio_absoluto, 1),
            desvio_pct         = round(desvio_pct, 1),
            alerta_roja        = alerta_roja,
            descripcion        = descripcion,
        )

    def _fetch_real_forecast(self, evento_id: str, mes: int) -> float:
        """
        Fase 6: retorna temperatura mock.
        Fase 7: reemplazar con:
            response = requests.get(
                f"https://api.smn.gob.ar/v1/forecast/{provincia}",
                params={"date": fecha_evento}
            )
            return response.json()["temperatura_max"]
        """
        if evento_id in MOCK_FORECAST_OVERRIDE:
            return MOCK_FORECAST_OVERRIDE[evento_id]

        # Sin override: usar histórico + delta default (sin desvío)
        return TEMP_HISTORICA_NOA.get(mes, 20.0) + MOCK_DEFAULT_DELTA

    @staticmethod
    def _extraer_mes(fecha_evento: str) -> int:
        """Extrae el número de mes de una fecha en formato YYYY-MM-DD."""
        try:
            parts = fecha_evento.split("-")
            if len(parts) != 3:
                raise ValueError("Debe contener exactamente 2 guiones")
            year, month, day = parts
            if len(year) != 4 or len(month) != 2 or len(day) != 2:
                raise ValueError("Formato debe ser YYYY-MM-DD (4-2-2 dígitos)")
            return int(month)
        except (IndexError, ValueError):
            raise ValueError(
                f"Formato de fecha inválido: '{fecha_evento}'. "
                f"Esperado: YYYY-MM-DD"
            )
