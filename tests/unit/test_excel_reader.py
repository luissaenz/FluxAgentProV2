"""tests/unit/test_excel_reader.py — Tests para ExcelReaderTool con datos reales."""

from __future__ import annotations

import json

from src.tools.excel_reader import ExcelReaderTool


def test_read_precios_bebidas():
    """Lee precios_bebidas.xlsx y verifica estructura."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("precios_bebidas.xlsx")
    data = json.loads(raw)

    assert "Datos" in data
    rows = data["Datos"]
    assert len(rows) >= 5, f"Esperaba >= 5, got {len(rows)}"

    first = rows[0]
    assert "producto_id" in first, f"Keys: {list(first.keys())}"
    assert "nombre" in first
    assert "precio_ars" in first
    assert first["producto_id"] == "GIN-001"


def test_read_eventos():
    """Lee eventos.xlsx y verifica columnas."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("eventos.xlsx")
    data = json.loads(raw)

    assert "Datos" in data
    rows = data["Datos"]
    assert len(rows) >= 1

    evt = rows[0]
    assert evt["evento_id"] == "EVT-2026-001"
    assert evt["tipo_evento"] == "boda"
    assert evt["pax"] == 150


def test_read_consumo_config():
    """Lee config_consumo_pax.xlsx y verifica tipos de menú."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("config_consumo_pax.xlsx")
    data = json.loads(raw)

    assert "Datos" in data
    rows = data["Datos"]
    tipos = [r["tipo_menu"] for r in rows if "tipo_menu" in r]
    assert "basico" in tipos
    assert "estandar" in tipos
    assert "premium" in tipos


def test_read_margenes():
    """Lee config_margenes.xlsx (multi-sheet)."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("config_margenes.xlsx")
    data = json.loads(raw)

    assert "Margenes" in data
    assert "Climatico" in data

    margenes = data["Margenes"]
    opts = [m["opcion"] for m in margenes if "opcion" in m]
    assert "basica" in opts
    assert "recomendada" in opts


def test_read_file_not_found():
    """Archivo inexistente retorna error."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("no_existe.xlsx")
    data = json.loads(raw)
    assert "error" in data


def test_read_all_sheets_multi_sheet():
    """Lee multi-sheet retorna todas las sheets."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("config_margenes.xlsx")
    data = json.loads(raw)

    assert "Margenes" in data
    assert "Climatico" in data
    rows = data["Climatico"]
    assert len(rows) >= 1
    assert "mes" in rows[0]


def test_read_inventario():
    """Lee inventario.xlsx."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("inventario.xlsx")
    data = json.loads(raw)

    assert "Datos" in data
    first = data["Datos"][0]
    assert "item_id" in first
    assert "stock_actual" in first


def test_read_bartenders():
    """Lee bartenders_disponibles.xlsx."""
    tool = ExcelReaderTool(org_id="test")
    raw = tool._run("bartenders_disponibles.xlsx")
    data = json.loads(raw)

    assert "Datos" in data
    rows = data["Datos"]
    assert len(rows) >= 2
    nombres = [b.get("nombre", "") for b in rows]
    assert any("Juan" in n for n in nombres)
