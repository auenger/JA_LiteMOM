from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import xlrd

from backend.app import unverified_xls


def test_unverified_export_keeps_all_rows_across_xls_sheets(monkeypatch):
    monkeypatch.setattr(unverified_xls, "MAX_DATA_ROWS_PER_SHEET", 2)
    records = [SimpleNamespace(
        document_no=f"JY-{index}", inspection_date=date(2026, 9, 14), sequence=index,
        body_code=f"CODE-{index}", manufacture_date=None, manufacturer="测试厂家",
        spec_name=None, volume=Decimal("35.5"), customer_name="测试客户",
        inspector_name="测试员", error_message="气瓶信息不存在",
    ) for index in range(1, 4)]
    workbook = xlrd.open_workbook(file_contents=unverified_xls.render_unverified_bottles_xls(records))
    assert workbook.nsheets == 2
    assert workbook.sheet_by_index(0).nrows == 4
    assert workbook.sheet_by_index(1).nrows == 3
    assert [workbook.sheet_by_index(index).cell_value(row, 3) for index, row in ((0, 2), (0, 3), (1, 2))] == [
        "CODE-1", "CODE-2", "CODE-3",
    ]
    assert workbook.sheet_by_index(1).cell_value(2, 7) == "35.50"


def test_unverified_export_empty_pool_has_standard_headers():
    workbook = xlrd.open_workbook(file_contents=unverified_xls.render_unverified_bottles_xls([]))
    assert workbook.nsheets == 1
    assert workbook.sheet_by_index(0).nrows == 2
