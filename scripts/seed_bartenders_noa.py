#!/usr/bin/env python3
"""
scripts/seed_bartenders_noa.py

Inserta los datos reales de las planillas Excel en las tablas operativas
de Supabase, bajo el org_id de la organización Bartenders NOA.

Uso:
    python scripts/seed_bartenders_noa.py --org-id <uuid>

    # O dejar que el script busque la org por nombre:
    python scripts/seed_bartenders_noa.py --org-name "Bartenders NOA"

Prerequisitos:
    - Migraciones 009, 010, 011, 012 ya ejecutadas en Supabase
    - Variables de entorno: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import os
import sys
from datetime import date
from supabase import create_client, Client


# ─── Datos reales de planillas ─────────────────────────────────────────────

BARTENDERS = [
    {"bartender_id": "BAR-001", "nombre": "Juan Perez",       "telefono": "+54 381 XXX-0001", "especialidad": "premium", "es_head_bartender": True,  "tarifa_hora_ars": 50000, "eventos_realizados": 47, "calificacion": 4.8, "disponible": True, "fecha_proxima_reserva": "2026-04-10"},
    {"bartender_id": "BAR-002", "nombre": "Maria Garcia",     "telefono": "+54 381 XXX-0002", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 23, "calificacion": 4.5, "disponible": True, "fecha_proxima_reserva": "2026-03-28"},
    {"bartender_id": "BAR-003", "nombre": "Carlos Lopez",     "telefono": "+54 381 XXX-0003", "especialidad": "premium", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 31, "calificacion": 4.7, "disponible": True, "fecha_proxima_reserva": "2026-04-05"},
    {"bartender_id": "BAR-004", "nombre": "Ana Martinez",     "telefono": "+54 381 XXX-0004", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 19, "calificacion": 4.3, "disponible": True, "fecha_proxima_reserva": "2026-04-02"},
    {"bartender_id": "BAR-005", "nombre": "Roberto Silva",    "telefono": "+54 381 XXX-0005", "especialidad": "premium", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 42, "calificacion": 4.9, "disponible": True, "fecha_proxima_reserva": "2026-04-08"},
    {"bartender_id": "BAR-006", "nombre": "Lucia Rodriguez",  "telefono": "+54 381 XXX-0006", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 15, "calificacion": 4.2, "disponible": True, "fecha_proxima_reserva": "2026-03-30"},
    {"bartender_id": "BAR-007", "nombre": "Martin Gonzalez",  "telefono": "+54 381 XXX-0007", "especialidad": "premium", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 28, "calificacion": 4.6, "disponible": True, "fecha_proxima_reserva": "2026-04-12"},
    {"bartender_id": "BAR-008", "nombre": "Sofia Fernandez",  "telefono": "+54 381 XXX-0008", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 21, "calificacion": 4.4, "disponible": True, "fecha_proxima_reserva": "2026-04-01"},
    {"bartender_id": "BAR-009", "nombre": "Diego Torres",     "telefono": "+54 381 XXX-0009", "especialidad": "premium", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 35, "calificacion": 4.8, "disponible": True, "fecha_proxima_reserva": "2026-04-09"},
    {"bartender_id": "BAR-010", "nombre": "Gabriela Lopez",   "telefono": "+54 381 XXX-0010", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 18, "calificacion": 4.3, "disponible": True, "fecha_proxima_reserva": "2026-03-29"},
    {"bartender_id": "BAR-011", "nombre": "Fernando Ruiz",    "telefono": "+54 381 XXX-0011", "especialidad": "premium", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 39, "calificacion": 4.7, "disponible": True, "fecha_proxima_reserva": "2026-04-11"},
    {"bartender_id": "BAR-012", "nombre": "Patricia Alvarez", "telefono": "+54 381 XXX-0012", "especialidad": "clasica", "es_head_bartender": False, "tarifa_hora_ars": 35000, "eventos_realizados": 25, "calificacion": 4.5, "disponible": True, "fecha_proxima_reserva": "2026-04-03"},
]

PRECIOS_BEBIDAS = [
    {"producto_id": "GIN-001",    "nombre": "Gordon's Pink",       "categoria": "gin",    "presentacion_ml": 700, "precio_ars": 12000, "precio_por_coctel":  800, "proveedor": "Distribuidora NOA", "fuente": "Carrefour Tucuman", "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia": 14000},
    {"producto_id": "GIN-002",    "nombre": "Beefeater",           "categoria": "gin",    "presentacion_ml": 700, "precio_ars": 28000, "precio_por_coctel": 1867, "proveedor": "Distribuidora NOA", "fuente": "Mayorista X",       "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia": 30000},
    {"producto_id": "WHISKY-001", "nombre": "Old Smuggler",        "categoria": "whisky", "presentacion_ml": 750, "precio_ars":  7000, "precio_por_coctel":  467, "proveedor": "Distribuidora NOA", "fuente": "Dia Tucuman",        "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia":  8000},
    {"producto_id": "WHISKY-002", "nombre": "Johnnie Walker Red",  "categoria": "whisky", "presentacion_ml": 750, "precio_ars": 25000, "precio_por_coctel": 1667, "proveedor": "Distribuidora NOA", "fuente": "Mayorista X",       "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia": 27000},
    {"producto_id": "VODKA-001",  "nombre": "Smirnoff",            "categoria": "vodka",  "presentacion_ml": 700, "precio_ars":  8000, "precio_por_coctel":  533, "proveedor": "Distribuidora NOA", "fuente": "Carrefour Tucuman", "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia":  9000},
    {"producto_id": "RON-001",    "nombre": "Bacardi",             "categoria": "ron",    "presentacion_ml": 750, "precio_ars": 18000, "precio_por_coctel": 1200, "proveedor": "Distribuidora NOA", "fuente": "Mayorista X",       "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia": 20000},
    {"producto_id": "TEQUILA-001","nombre": "Jose Cuervo",         "categoria": "tequila","presentacion_ml": 750, "precio_ars": 22000, "precio_por_coctel": 1467, "proveedor": "Distribuidora NOA", "fuente": "Mayorista X",       "fecha_actualizacion": "2026-03-27", "es_oferta": False, "precio_base_referencia": 25000},
]

INVENTARIO = [
    {"item_id": "GIN-001",    "nombre": "Gordon's Pink 700ml",  "categoria": "espiritoso", "stock_actual": 24,  "stock_reservado": 12, "unidad": "botella", "stock_minimo":  6, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "WHISKY-001", "nombre": "Old Smuggler 750ml",   "categoria": "espiritoso", "stock_actual": 18,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  4, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "GIN-002",    "nombre": "Beefeater 700ml",      "categoria": "espiritoso", "stock_actual":  8,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  2, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "WHISKY-002", "nombre": "Johnnie Walker Red",   "categoria": "espiritoso", "stock_actual":  6,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  2, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "VODKA-001",  "nombre": "Smirnoff 700ml",       "categoria": "espiritoso", "stock_actual": 12,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  3, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "RON-001",    "nombre": "Bacardi 750ml",        "categoria": "espiritoso", "stock_actual": 10,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  3, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "TEQUILA-001","nombre": "Jose Cuervo 750ml",    "categoria": "espiritoso", "stock_actual":  8,  "stock_reservado":  0, "unidad": "botella", "stock_minimo":  2, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "HIELO-001",  "nombre": "Hielo 2kg",            "categoria": "consumible", "stock_actual": 50,  "stock_reservado":  0, "unidad": "bolsa",   "stock_minimo": 20, "ultima_actualizacion": "2026-03-27"},
    {"item_id": "AGUA-001",   "nombre": "Agua mineral 1.5L",    "categoria": "consumible", "stock_actual": 100, "stock_reservado":  0, "unidad": "botella", "stock_minimo": 30, "ultima_actualizacion": "2026-03-27"},
]

# Evento de ejemplo para probar el escandallo en demo
EVENTO_DEMO = {
    "evento_id":      "EVT-2026-001",
    "fecha_evento":   "2026-01-15",
    "provincia":      "Tucuman",
    "localidad":      "San Miguel de Tucumán",
    "tipo_evento":    "boda",
    "pax":            150,
    "duracion_horas": 5,
    "tipo_menu":      "premium",
    "restricciones":  None,
    "status":         "cotizado",
    "escandallo_id":  "ESC-2026-001",
    "cotizacion_id":  "COT-2026-001",
}

COTIZACION_DEMO = {
    "cotizacion_id":     "COT-2026-001",
    "evento_id":         "EVT-2026-001",
    "escandallo_total":  2956716,
    "opcion_basica":     4927860,
    "opcion_recomendada":5376757,
    "opcion_premium":    5913432,
    "factor_climatico":  20,
    "fecha_generacion":  "2026-01-05",
    "opcion_elegida":    "recomendada",
    "status":            "generada",
}

ORDEN_COMPRA_DEMO = {
    "orden_id":         "OC-2026-001",
    "evento_id":        "EVT-2026-001",
    "fecha_generacion": "2026-01-08",
    "motivo":           "alerta_climatica",
    "proveedor":        "Distribuidora NOA",
    "items": [
        {"producto_id": "GIN-001",   "cantidad": 10, "precio_unitario": 12000},
        {"producto_id": "HIELO-001", "cantidad": 15, "precio_unitario":  3000},
        {"producto_id": "AGUA-001",  "cantidad": 20, "precio_unitario":   800},
    ],
    "total_ars":        220000,
    "status":           "pendiente",
    "fecha_entrega":    "2026-01-12",
}

AUDITORIA_DEMO = {
    "auditoria_id":       "AUD-2026-001",
    "evento_id":          "EVT-2026-001",
    "precio_cobrado":     5376757,
    "costo_real":         4608458,
    "margen_pct":         14.3,
    "mermas":             250000,
    "desvio_climatico":   "+7°C vs histórico enero",
    "compras_emergencia": 220000,
    "leccion":            "Enero NOA con ola de calor: factor +20% fue correcto. "
                          "Próximo enero: considerar margen premium (+50%).",
    "fecha_cierre":       "2026-01-16",
}

HISTORIAL_PRECIOS_DEMO = [
    {"fecha": "2026-03-27", "producto_id": "GIN-001",    "precio_ars": 12000, "fuente": "Carrefour Tucuman", "variacion_pct":  0.0},
    {"fecha": "2026-03-27", "producto_id": "GIN-001",    "precio_ars": 11500, "fuente": "Mayorista X",       "variacion_pct": -4.2},
    {"fecha": "2026-03-27", "producto_id": "WHISKY-001", "precio_ars":  6800, "fuente": "Dia Tucuman",       "variacion_pct": -2.9},
]


# ─── Lógica del script ─────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: Definir SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    return create_client(url, key)


def get_org_id(db: Client, org_name: str | None, org_id: str | None) -> str:
    if org_id:
        return org_id
    result = db.table("organizations").select("id").eq("name", org_name).execute()
    if not result.data:
        print(f"ERROR: Org '{org_name}' no encontrada. Crear primero en FAP.")
        sys.exit(1)
    return result.data[0]["id"]


def seed_table(db: Client, table: str, rows: list[dict], org_id: str,
               pk: str, skip_org_id: bool = False) -> None:
    inserted = 0
    skipped = 0
    for row in rows:
        data = dict(row)
        if not skip_org_id:
            data["org_id"] = org_id
        try:
            db.table(table).insert(data).execute()
            inserted += 1
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR en {table} [{data.get(pk)}]: {e}")
    print(f"  {table}: {inserted} insertados, {skipped} ya existían")


def main():
    parser = argparse.ArgumentParser(description="Seed Bartenders NOA en Supabase")
    parser.add_argument("--org-id",   help="UUID de la org (prioridad sobre --org-name)")
    parser.add_argument("--org-name", default="Bartenders NOA",
                        help="Nombre de la org (default: 'Bartenders NOA')")
    parser.add_argument("--skip-demo", action="store_true",
                        help="No insertar datos de demo (evento, cotización, etc.)")
    args = parser.parse_args()

    db = get_supabase_client()
    org_id = get_org_id(db, args.org_name, args.org_id)
    print(f"\nOrg ID: {org_id}")
    print(f"Org:    {args.org_name or args.org_id}\n")

    print("── Tablas maestras ──────────────────────────────")
    seed_table(db, "bartenders_disponibles", BARTENDERS,     org_id, "bartender_id")
    seed_table(db, "precios_bebidas",        PRECIOS_BEBIDAS, org_id, "producto_id")
    seed_table(db, "inventario",             INVENTARIO,      org_id, "item_id")

    if not args.skip_demo:
        print("\n── Datos de demo (EVT-2026-001) ─────────────────")
        seed_table(db, "eventos",        [EVENTO_DEMO],        org_id, "evento_id")
        seed_table(db, "cotizaciones",   [COTIZACION_DEMO],    org_id, "cotizacion_id")
        seed_table(db, "ordenes_compra", [ORDEN_COMPRA_DEMO],  org_id, "orden_id")
        seed_table(db, "auditorias",     [AUDITORIA_DEMO],     org_id, "auditoria_id")
        seed_table(db, "historial_precios", HISTORIAL_PRECIOS_DEMO, org_id, "id")

    print("\n✅ Seed completado.")
    print(f"\nPróximo paso:")
    print(f"  Verificar en Supabase Dashboard → Table Editor")
    print(f"  Filtrar por org_id = {org_id}")


if __name__ == "__main__":
    main()
