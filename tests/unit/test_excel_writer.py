"""tests/unit/test_excel_writer.py — Tests para ExcelWriterTool."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.tools.excel_reader import ExcelReaderTool
from src.tools.excel_writer import ExcelWriterTool

SAMPLE_DATA = json.dumps([
    {"producto": "Gordon Pink", "cantidad": 10, "precio": 12000},
    {"producto": "Beefeater", "cantidad": 5, "precio": 28000},
], ensure_ascii=False)


def test_write_and_read_roundtrip(tmp_path):
    """Escribir y luego leer verifica roundtrip."""
    writer = ExcelWriterTool(org_id="test")
    reader = ExcelReaderTool(org_id="test")

    with (
        patch("src.tools.excel_writer.BASE_DIR", tmp_path),
        patch("src.tools.excel_reader.BASE_DIR", tmp_path),
    ):
        write_result = writer._run("test_roundtrip.xlsx", data=SAMPLE_DATA)
        write_data = json.loads(write_result)
        assert write_data["status"] == "ok"
        assert write_data["rows_written"] == 2

        read_raw = reader._run("test_roundtrip.xlsx")
        read_data = json.loads(read_raw)
        assert "Datos" in read_data
        rows = read_data["Datos"]
        assert len(rows) >= 2
        assert rows[0]["producto"] == "Gordon Pink"
        assert float(rows[0]["cantidad"]) == 10


def test_write_overwrite_mode(tmp_path):
    """Overwrite reemplaza datos existentes."""
    writer = ExcelWriterTool(org_id="test")
    reader = ExcelReaderTool(org_id="test")

    with (
        patch("src.tools.excel_writer.BASE_DIR", tmp_path),
        patch("src.tools.excel_reader.BASE_DIR", tmp_path),
    ):
        writer._run("test_overwrite.xlsx", data=SAMPLE_DATA)
        new_data = json.dumps([{"producto": "Nuevo", "cantidad": 1}], ensure_ascii=False)
        writer._run("test_overwrite.xlsx", data=new_data, mode="overwrite")

        read_raw = reader._run("test_overwrite.xlsx")
        read_data = json.loads(read_raw)
        rows = read_data["Datos"]
        assert len(rows) == 1
        assert rows[0]["producto"] == "Nuevo"


def test_write_append_mode(tmp_path):
    """Append agrega filas sin borrar existentes."""
    writer = ExcelWriterTool(org_id="test")
    reader = ExcelReaderTool(org_id="test")

    with (
        patch("src.tools.excel_writer.BASE_DIR", tmp_path),
        patch("src.tools.excel_reader.BASE_DIR", tmp_path),
    ):
        writer._run("test_append.xlsx", data=SAMPLE_DATA)
        more_data = json.dumps([{"producto": "Extra", "cantidad": 3}], ensure_ascii=False)
        writer._run("test_append.xlsx", data=more_data, mode="append")

        read_raw = reader._run("test_append.xlsx")
        read_data = json.loads(read_raw)
        rows = read_data["Datos"]
        assert len(rows) >= 3


def test_write_invalid_json():
    """JSON inválido retorna error."""
    writer = ExcelWriterTool(org_id="test")
    result = writer._run("test.xlsx", data="not json")
    data = json.loads(result)
    assert "error" in data


def test_write_empty_data():
    """Data vacío retorna error."""
    writer = ExcelWriterTool(org_id="test")
    result = writer._run("test.xlsx", data="[]")
    data = json.loads(result)
    assert "error" in data


def test_write_not_array():
    """Data no array retorna error."""
    writer = ExcelWriterTool(org_id="test")
    result = writer._run("test.xlsx", data='"string"')
    data = json.loads(result)
    assert "error" in data
