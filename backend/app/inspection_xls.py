"""Render inspection-document exports as real Excel 97–2003 XLS workbooks."""

from __future__ import annotations

import io
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import xlwt

if TYPE_CHECKING:
    from .models import InspectionDocument, InspectionDocumentLine


FULL_HEADERS = (
    "序号", "设备品种", "产品编号", "生产日期", "生产厂家", "容积",
    "检验日期", "下次检验日期", "检验结果", "检验人员",
)
AGE_HEADERS = ("序号", "气瓶编号", "制造日期", "制造单位名称或代号", "公称容积（L）", "下次检验日期")
EXPORT_KINDS = ("full", "verified", "unverified")


def _border_style() -> xlwt.XFStyle:
    border = xlwt.Borders()
    border.left = border.right = border.top = border.bottom = xlwt.Borders.THIN
    border.left_colour = border.right_colour = border.top_colour = border.bottom_colour = 0x08
    style = xlwt.XFStyle()
    style.borders = border
    return style


def default_next_inspection_date(inspection_date: date) -> date:
    return date(inspection_date.year + 4, inspection_date.month, 1) + timedelta(days=inspection_date.day - 2)


def _date_text(value: date | None, *, month_only: bool = False) -> str:
    return value.strftime("%Y.%m" if month_only else "%Y.%m.%d") if value else ""


def _write_row(sheet: xlwt.Worksheet, row: int, values: tuple[str, ...], style: xlwt.XFStyle) -> None:
    for column, value in enumerate(values):
        sheet.write(row, column, value, style)


def _ordered_lines(document: InspectionDocument) -> list[InspectionDocumentLine]:
    return sorted(document.lines, key=lambda line: line.sequence)


def split_inspection_lines_by_age(
    document: InspectionDocument, inspection_date: date | None = None,
) -> tuple[list[InspectionDocumentLine], list[InspectionDocumentLine]]:
    """Return older-than-four-years first, then within-four-years, comparing months only."""
    selected_date = inspection_date or document.inspection_date
    boundary_month = (selected_date.year - 4) * 12 + selected_date.month
    lines = [line for line in document.lines if not line.is_unverified]
    lines.sort(key=lambda line: (-(line.manufacture_date or date.min).toordinal(), line.sequence))
    older = [line for line in lines if not line.manufacture_date or line.manufacture_date.year * 12 + line.manufacture_date.month < boundary_month]
    within = [line for line in lines if line.manufacture_date and line.manufacture_date.year * 12 + line.manufacture_date.month >= boundary_month]
    return older, within


def inspection_age_table_rows(
    document: InspectionDocument, lines: list[InspectionDocumentLine], inspection_date: date | None = None,
) -> list[tuple[str, ...]]:
    """The former four-year XLS columns, reused as each Word report's appendix."""
    default_next_date = _date_text(default_next_inspection_date(inspection_date or document.inspection_date))
    rows = []
    for index, line in enumerate(lines, start=1):
        volume = Decimal(str(line.volume or 0))
        rows.append((
            str(index), line.body_code, _date_text(line.manufacture_date, month_only=True),
            line.manufacturer or "", f"{volume:.2f}" if volume > 0 else "", default_next_date,
        ))
    return rows


def render_inspection_xls(document: InspectionDocument, kind: str, export_date: date | None = None) -> tuple[bytes, int]:
    if kind not in EXPORT_KINDS:
        raise ValueError("不支持的检验单导出类型")
    workbook = xlwt.Workbook(encoding="utf-8")
    style = _border_style()
    selected_date = export_date or document.inspection_date
    default_next_date = _date_text(default_next_inspection_date(selected_date))

    lines = _ordered_lines(document)
    if kind == "verified":
        lines = [line for line in lines if not line.is_unverified]
    elif kind == "unverified":
        lines = [line for line in lines if line.is_unverified]
    sheet = workbook.add_sheet("检验气瓶列表")
    sheet.write_merge(0, 0, 0, 1, "充装单位名称", style)
    sheet.write_merge(0, 0, 2, 9, document.customer_name, style)
    _write_row(sheet, 1, FULL_HEADERS, style)
    for index, line in enumerate(lines, start=1):
        volume = Decimal(str(line.volume or 0))
        _write_row(sheet, index + 1, (
            str(line.sequence if kind != "verified" else index), line.device_category or "焊接气瓶", line.body_code,
            _date_text(line.manufacture_date, month_only=True), line.manufacturer or "",
            f"{volume:.2f}" if volume > 0 else "", _date_text(selected_date),
            default_next_date,
            "合格" if line.inspection_result == "GOOD" else line.inspection_result,
            line.inspector_name or document.inspector_name,
        ), style)
    widths = (6, 12, 16, 12, 30, 10, 12, 14, 10, 10)
    for column, width in enumerate(widths):
        sheet.col(column).width = width * 256
    quantity = len(lines)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue(), quantity
