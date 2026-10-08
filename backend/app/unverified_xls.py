"""Export every pending unverified bottle in the established bordered XLS format."""

from __future__ import annotations

import io
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

import xlwt

from .inspection_xls import _border_style, _date_text, _write_row

if TYPE_CHECKING:
    from .models import UnverifiedBottle


HEADERS = (
    "检验单号", "检验日期", "单据序号", "瓶身编号", "生产日期", "生产厂家",
    "钢瓶规格", "容积（L）", "客户", "检验人员", "上游驳回信息", "状态",
)
MAX_DATA_ROWS_PER_SHEET = 65534  # XLS has 65,536 rows; title and headings use two.
WIDTHS = (20, 14, 12, 20, 14, 30, 16, 12, 24, 16, 60, 18)


def render_unverified_bottles_xls(records: Sequence[UnverifiedBottle]) -> bytes:
    workbook = xlwt.Workbook(encoding="utf-8")
    style = _border_style()
    for sheet_index, start in enumerate(range(0, max(len(records), 1), MAX_DATA_ROWS_PER_SHEET)):
        sheet = workbook.add_sheet(f"未验证钢瓶列表{sheet_index + 1}" if sheet_index else "未验证钢瓶列表")
        sheet.write_merge(0, 0, 0, len(HEADERS) - 1, "未经系统验证瓶子池", style)
        _write_row(sheet, 1, HEADERS, style)
        for column, width in enumerate(WIDTHS):
            sheet.col(column).width = width * 256
        for row_index, record in enumerate(records[start:start + MAX_DATA_ROWS_PER_SHEET], start=2):
            volume = Decimal(str(record.volume or 0))
            _write_row(sheet, row_index, (
                record.document_no, _date_text(record.inspection_date), str(record.sequence),
                record.body_code, _date_text(record.manufacture_date, month_only=True),
                record.manufacturer or "", record.spec_name or "",
                f"{volume:.2f}", record.customer_name or "", record.inspector_name or "",
                record.error_message or "", "未经系统验证",
            ), style)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
