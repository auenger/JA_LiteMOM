"""Render the full inspection list as the supplied cylinder receipt form."""

from __future__ import annotations

import io
from decimal import Decimal
from typing import TYPE_CHECKING

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

if TYPE_CHECKING:
    from .models import InspectionDocument


SENDING_UNIT = "锦安特种设备检测有限公司"
TABLE_HEADERS = (
    "序号", "气瓶编号", "制造单位", "规格\n型号", "制造日期", "产权单位",
    "上次检验日期", "初步外观检查情况（合格打“√”，不合格打“×”并注明缺陷）", "处置结果", "备注",
)
TABLE_WIDTHS = (1.1, 2.5, 4.8, 1.5, 1.9, 3.0, 2.6, 7.1, 2.2, 1.2)


def _set_font(run, size: float = 8, bold: bool = False) -> None:
    run.font.name = "宋体"
    run.font.size = Pt(size)
    run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")


def _write_cell(cell, value: str, *, size: float = 8, bold: bool = False, center: bool = False) -> None:
    cell.text = ""
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.line_spacing = 1
    for index, part in enumerate(value.split("\n")):
        if index:
            paragraph.add_run().add_break()
        _set_font(paragraph.add_run(part), size, bold)


def _set_borders(table) -> None:
    properties = table._tbl.tblPr
    borders = properties.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:color"), "000000")


def _set_widths(row, widths: tuple[float, ...]) -> None:
    for cell, width in zip(row.cells, widths):
        cell.width = Cm(width)


def _set_table_width(table, width_cm: float) -> None:
    table_width = table._tbl.tblPr.first_child_found_in("w:tblW")
    table_width.set(qn("w:type"), "dxa")
    table_width.set(qn("w:w"), str(round(Cm(width_cm).twips)))


def _repeat_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    marker = OxmlElement("w:tblHeader")
    marker.set(qn("w:val"), "true")
    properties.append(marker)


def render_inspection_receipt_word(
    document: InspectionDocument, *, contact: str | None = None, phone: str | None = None,
) -> bytes:
    """Use the first-page fields and continuing ten-column table from 来瓶登记0824天顺369成功.doc."""
    report = Document()
    section = report.sections[0]
    section.page_width = Mm(297)
    section.page_height = Mm(210)
    section.left_margin = Cm(0.9)
    section.right_margin = Cm(0.9)
    section.top_margin = Cm(0.8)
    section.bottom_margin = Cm(0.8)

    title = report.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(2)
    _set_font(title.add_run("液化石油气钢瓶接收记录表"), 15, True)

    heading = report.add_table(rows=1, cols=2)
    heading.autofit = False
    heading.columns[0].width = Cm(14.5)
    heading.columns[1].width = Cm(13.4)
    _set_table_width(heading, 27.9)
    _set_widths(heading.rows[0], (14.5, 13.4))
    _write_cell(heading.cell(0, 0), f"检验单位名称：{document.customer_name}", size=9)
    _write_cell(heading.cell(0, 1), f"记录编号：JA-JSJL-{document.inspection_date:%y}{document.id:03d}", size=9)

    info = report.add_table(rows=4, cols=4)
    info.autofit = False
    info.alignment = WD_TABLE_ALIGNMENT.LEFT
    info_widths = (3.0, 10.5, 3.0, 11.4)
    for column, width in zip(info.columns, info_widths):
        column.width = Cm(width)
    _set_table_width(info, 27.9)
    for row in info.rows:
        _set_widths(row, info_widths)
    _set_borders(info)
    _write_cell(info.cell(0, 0).merge(info.cell(0, 3)), "一、送检单位基本信息", bold=True)
    for column, value in enumerate(("送检单位名称", SENDING_UNIT, "联系人", contact or "")):
        _write_cell(info.cell(1, column), value)
    sent_date = document.inspection_date
    for column, value in enumerate(("联系电话", phone or "", "送检日期", f"{sent_date.year}年{sent_date.month}月{sent_date.day}日")):
        _write_cell(info.cell(2, column), value)
    _write_cell(info.cell(3, 0), "送检事由")
    _write_cell(info.cell(3, 1).merge(info.cell(3, 3)), "☑ 定期检验  □ 不定期检验  □ 故障复检  □ 其他：________")

    table = report.add_table(rows=1, cols=len(TABLE_HEADERS))
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_width(table, 27.9)
    for column, width in zip(table.columns, TABLE_WIDTHS):
        column.width = Cm(width)
    _set_borders(table)
    header = table.rows[0]
    _set_widths(header, TABLE_WIDTHS)
    _repeat_header(header)
    for cell, value in zip(header.cells, TABLE_HEADERS):
        _write_cell(cell, value, size=7, bold=True, center=True)

    for line in sorted(document.lines, key=lambda item: item.sequence):
        row = table.add_row()
        row.height = Cm(0.82)
        row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        _set_widths(row, TABLE_WIDTHS)
        volume = Decimal(str(line.volume or 0))
        manufacture_date = line.manufacture_date.strftime("%Y.%m") if line.manufacture_date else ""
        values = (
            str(line.sequence), line.body_code, line.manufacturer or "",
            f"{volume:g}" if volume > 0 else (line.spec.name if line.spec else ""),
            manufacture_date,
            document.customer_name, manufacture_date,
            "√裂纹  √凹陷  √鼓包  √腐蚀  √变形\n√钢印清晰  √检验标志有效  √使用登记证",
            "☑接收待检\n□不予接收", "",
        )
        for index, (cell, value) in enumerate(zip(row.cells, values)):
            _write_cell(cell, value, size=7 if index in (7, 8) else 8, center=index in (0, 3, 4, 6))

    output = io.BytesIO()
    report.save(output)
    return output.getvalue()
