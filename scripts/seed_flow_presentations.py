"""
Seed flow_presentations for a specific organization.

Usage:
    python scripts/seed_flow_presentations.py <org_id>

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.
"""

import json
import os
import sys

from supabase import create_client

CONFIGS = {
    "PreventaFlow": {
        "card": {
            "title": {"from": "$.evento_id"},
            "amount": {"from": "$.opcion_recomendada", "format": "currency_ars"},
        },
        "detail": {
            "sections": [
                {
                    "type": "fields",
                    "title": "Cotización",
                    "fields": [
                        {"label": "Evento", "from": "$.evento_id"},
                        {"label": "Cotización", "from": "$.cotizacion_id"},
                        {"label": "Bartenders", "from": "$.bartenders_necesarios"},
                        {"label": "Factor Climático", "from": "$.factor_climatico", "format": "pct"},
                    ],
                },
                {
                    "type": "fields",
                    "title": "Opciones de Precio",
                    "fields": [
                        {"label": "Básica", "from": "$.opcion_basica", "format": "currency_ars"},
                        {"label": "Recomendada", "from": "$.opcion_recomendada", "format": "currency_ars"},
                        {"label": "Premium", "from": "$.opcion_premium", "format": "currency_ars"},
                        {"label": "Escandallo Total", "from": "$.escandallo_total", "format": "currency_ars"},
                    ],
                },
            ]
        },
    },
    "ReservaFlow": {
        "card": {
            "title": {"from": "$.evento_id"},
            "icon": {"from": "$.status", "map": {"confirmado": "✅", "pendiente": "⏳"}},
        },
        "detail": {
            "sections": [
                {
                    "type": "fields",
                    "title": "Reserva",
                    "fields": [
                        {"label": "Evento", "from": "$.evento_id"},
                        {"label": "Estado", "from": "$.status"},
                        {"label": "Necesita Head", "from": "$.necesita_head", "format": "boolean_yn"},
                        {"label": "Stock OK", "from": "$.stock_ok", "format": "boolean_yn"},
                    ],
                },
                {"type": "key_value_list", "title": "Bartenders Asignados", "from": "$.bartenders"},
                {"type": "accordion", "title": "Hoja de Ruta", "default": "collapsed", "from": "$.hoja_de_ruta"},
            ]
        },
    },
    "AlertaClimaFlow": {
        "card": {
            "title": {"from": "$.evento_id"},
            "icon": {"from": "$.alerta_roja", "map": {"true": "🔴", "false": "🟢"}},
            "amount": {"from": "$.total_ars", "format": "currency_ars"},
        },
        "detail": {
            "sections": [
                {
                    "type": "fields",
                    "title": "Alerta Climática",
                    "fields": [
                        {"label": "Evento", "from": "$.evento_id"},
                        {"label": "Alerta Roja", "from": "$.alerta_roja", "format": "boolean_yn"},
                        {"label": "Acción", "from": "$.accion"},
                        {"label": "Orden", "from": "$.orden_id"},
                        {"label": "Total", "from": "$.total_ars", "format": "currency_ars"},
                    ],
                },
                {
                    "type": "fields",
                    "title": "Mensaje",
                    "fields": [{"label": "Detalle", "from": "$.mensaje"}],
                },
            ]
        },
    },
    "CierreFlow": {
        "card": {
            "title": {"from": "$.evento_id"},
            "amount": {"from": "$.ganancia_neta", "format": "currency_ars"},
        },
        "detail": {
            "sections": [
                {
                    "type": "fields",
                    "title": "Cierre de Evento",
                    "fields": [
                        {"label": "Evento", "from": "$.evento_id"},
                        {"label": "Estado", "from": "$.status"},
                        {"label": "Auditoría", "from": "$.auditoria_id"},
                        {"label": "Margen", "from": "$.margen_pct", "format": "pct"},
                        {"label": "Ganancia Neta", "from": "$.ganancia_neta", "format": "currency_ars"},
                        {"label": "Próximo Contacto", "from": "$.proxima_contacto", "format": "date"},
                    ],
                }
            ]
        },
    },
    "CotizacionFlow": {
        "card": {
            "title": {"from": "$.evento_id", "label": "Cotización"},
            "amount": {"from": "$.total", "format": "currency_ars"},
        },
        "detail": {
            "sections": [
                {
                    "type": "fields",
                    "title": "Cotización",
                    "fields": [
                        {"label": "Evento", "from": "$.evento_id"},
                        {"label": "Total", "from": "$.total", "format": "currency_ars"},
                        {"label": "Descuento", "from": "$.descuento", "format": "pct"},
                    ],
                }
            ]
        },
    },
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_flow_presentations.py <org_id>")
        sys.exit(1)

    org_id = sys.argv[1]
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, key)

    for flow_type, config in CONFIGS.items():
        result = (
            client.table("flow_presentations")
            .upsert(
                {
                    "org_id": org_id,
                    "flow_type": flow_type,
                    "presentation_config": config,
                },
                on_conflict="org_id,flow_type",
            )
            .execute()
        )
        print(f"  {flow_type}: {'OK' if result.data else 'SKIP'}")

    print(f"\nSeeded {len(CONFIGS)} flow presentations for org {org_id}")


if __name__ == "__main__":
    main()
