"""Fill the two converted inspection-report Word templates without changing their layout."""

from __future__ import annotations

import html
import io
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Sequence

from .inspection_xls import AGE_HEADERS


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATES = {
    "regular": ("inspection-regular.docx", "401"),
    "assessment": ("inspection-assessment.docx", "133"),
}
TEMPLATE_LIBRARY = {
    "default": {
        "name": "现有默认版",
        "description": "沿用当前报告正文与附表格式",
        "regular": "inspection-regular.docx",
        "assessment": "inspection-assessment.docx",
    },
    "photo": {
        "name": "双页封面版",
        "description": "按提供的照片排版：报告封面、结论页，再接附表",
        "regular": "inspection-photo-regular.docx",
        "assessment": "inspection-photo-assessment.docx",
    },
}
CUSTOMER_PLACEHOLDER = "安丘市天顺燃气有限责任公司"
TEXT_PATTERN = re.compile(rb"(<w:t(?:\s+[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)
PARAGRAPH_PATTERN = re.compile(rb"(<w:p(?:\s+[^>]*)?>)(.*?)(</w:p>)", re.DOTALL)
REPORT_NO_PATTERN = re.compile(r"WFJA-\d{2}-\d{4}(\d{3})")
DATE_PATTERN = re.compile(r"\d{4}年\s*\d{1,2}\s*月\s*\d{1,2}日")
PHOTO_TOKEN_FIELDS = {
    "{{CUSTOMER}}": "customer",
    "{{QUANTITY}}": "quantity",
    "{{REJECTED}}": "rejected",
    "{{REPORT_DATE}}": "date",
    "{{REPORT_NO}}": "report_no",
}
APPENDIX_WIDTHS = (550, 1350, 1050, 2200, 1700, 1989)  # 8839 twips: template page width minus margins
APPENDIX_TITLES = {
    "assessment": "附表:安全评定合格气瓶一览表",  # 四年前
    "regular": "附表:定期检验合格气瓶一览表",  # 四年内
}
PHOTO_APPENDIX_TITLES = {
    "assessment": "附表:定期检验合格气瓶一览表",  # 四年内
    "regular": "附表:安全评定合格气瓶一览表",  # 四年前
}


def _appendix_xml(rows: Sequence[tuple[str, ...]], title: str) -> bytes:
    def cell(value: str, width: int, heading: bool) -> str:
        bold = "<w:b/>" if heading else ""
        return (
            f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
            '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="17"/>'
            f'{bold}</w:rPr><w:t>{html.escape(value, quote=False)}</w:t></w:r></w:p></w:tc>'
        )

    def row(values: Sequence[str], heading: bool = False) -> str:
        if len(values) != len(APPENDIX_WIDTHS):
            raise ValueError("Word 附表列数与预期不符")
        row_properties = '<w:trPr><w:tblHeader w:val="true"/><w:cantSplit/></w:trPr>' if heading else '<w:trPr><w:cantSplit/></w:trPr>'
        return '<w:tr>' + row_properties + ''.join(cell(value, width, heading) for value, width in zip(values, APPENDIX_WIDTHS)) + '</w:tr>'

    title_row = (
        '<w:tr><w:trPr><w:tblHeader w:val="true"/><w:cantSplit/></w:trPr>'
        '<w:tc><w:tcPr><w:tcW w:w="8839" w:type="dxa"/><w:gridSpan w:val="6"/></w:tcPr>'
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="160"/></w:pPr>'
        '<w:r><w:rPr><w:b/><w:rFonts w:eastAsia="宋体"/><w:sz w:val="24"/></w:rPr>'
        f'<w:t>{html.escape(title, quote=False)}</w:t></w:r></w:p></w:tc></w:tr>'
    )
    grid = ''.join(f'<w:gridCol w:w="{width}"/>' for width in APPENDIX_WIDTHS)
    table = (
        '<w:tbl><w:tblPr><w:tblW w:w="8839" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        '<w:tblBorders><w:top w:val="single" w:sz="6" w:color="000000"/>'
        '<w:left w:val="single" w:sz="6" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="6" w:color="000000"/>'
        '<w:right w:val="single" w:sz="6" w:color="000000"/>'
        '<w:insideH w:val="single" w:sz="6" w:color="000000"/>'
        '<w:insideV w:val="single" w:sz="6" w:color="000000"/>'
        '</w:tblBorders><w:tblCellMar><w:top w:w="70" w:type="dxa"/>'
        '<w:bottom w:w="70" w:type="dxa"/><w:left w:w="45" w:type="dxa"/>'
        '<w:right w:w="45" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        f'<w:tblGrid>{grid}</w:tblGrid>{title_row}{row(AGE_HEADERS, True)}'
        + ''.join(row(values) for values in rows) + '</w:tbl>'
    )
    return table.encode("utf-8")


def _appendix_footer_xml() -> bytes:
    def field(name: str) -> str:
        return (
            f'<w:fldSimple w:instr="{name}"><w:r><w:rPr><w:rFonts w:eastAsia="宋体"/>'
            '<w:sz w:val="18"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">第 </w:t></w:r>'
        + field("PAGE") +
        '<w:r><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve"> 页 / 共 </w:t></w:r>'
        + field("SECTIONPAGES") +
        '<w:r><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="18"/></w:rPr><w:t> 页</w:t></w:r>'
        '</w:p></w:ftr>'
    ).encode("utf-8")


def _with_appendix_section(document_xml: bytes, appendix: bytes, footer_relationship: str) -> bytes:
    section_start = document_xml.rfind(b"<w:sectPr")
    section_end = document_xml.find(b"</w:sectPr>", section_start) + len(b"</w:sectPr>")
    if section_start < 0 or section_end < len(b"</w:sectPr>"):
        raise ValueError("Word 模板缺少页面设置")
    original_section = document_xml[section_start:section_end]
    prior_section, section_type_count = re.subn(
        rb'(<w:footerReference w:type="default" r:id="[^"]+"/>)',
        rb'\1<w:type w:val="nextPage"/>',
        original_section,
    )
    appendix_section, footer_count = re.subn(
        rb'<w:footerReference w:type="default" r:id="[^"]+"/>',
        f'<w:footerReference w:type="default" r:id="{footer_relationship}"/>'.encode(),
        original_section,
    )
    appendix_section, page_count = re.subn(rb'<w:pgNumType w:start="\d+"/>', b'<w:pgNumType w:start="1"/>', appendix_section)
    if footer_count != 1 or page_count != 1 or section_type_count != 1:
        raise ValueError("Word 模板的页脚或页码设置与预期不符")
    section_break = b"<w:p><w:pPr>" + prior_section + b"</w:pPr></w:p>"
    return document_xml[:section_start] + section_break + appendix + appendix_section + document_xml[section_end:]


def render_inspection_word(
    kind: str, customer: str, inspection_date: date, quantity: int,
    appendix_rows: Sequence[tuple[str, ...]] = (),
    report_number: int | None = None,
    template_key: str = "default",
) -> bytes:
    if report_number is not None and not 1 <= report_number <= 999:
        raise ValueError("Word 报告序号必须在 001 至 999 之间")
    if template_key not in TEMPLATE_LIBRARY:
        raise ValueError("未知的 Word 模板")
    template_name, original_quantity = TEMPLATES[kind]
    if template_key != "default":
        template_name = TEMPLATE_LIBRARY[template_key][kind]
    template_path = TEMPLATE_DIR / template_name
    original = template_path.read_bytes()
    output = io.BytesIO()
    replacements = {"customer": 0, "quantity": 0, "date": 0, "report_no": 0}
    def replace_paragraph(paragraph: re.Match[bytes]) -> bytes:
        body = paragraph.group(2)
        paragraph_text = "".join(html.unescape(node.group(2).decode("utf-8")) for node in TEXT_PATTERN.finditer(body))
        has_date = bool(DATE_PATTERN.search(paragraph_text))
        date_values = (str(inspection_date.year), f"{inspection_date.month:02d}", f"{inspection_date.day:02d}")
        date_part = 0

        def replace_text(match: re.Match[bytes]) -> bytes:
            nonlocal date_part
            value = html.unescape(match.group(2).decode("utf-8"))
            if template_key != "default":
                tokens = {
                    "{{CUSTOMER}}": customer,
                    "{{QUANTITY}}": str(quantity),
                    "{{REJECTED}}": "0",
                    "{{REPORT_DATE}}": f"{inspection_date.year}年 {inspection_date.month:02d} 月{inspection_date.day:02d}日",
                    "{{REPORT_NO}}": f"WFJA-{inspection_date:%y}-{inspection_date:%m%d}{report_number or (1 if kind == 'regular' else 2):03d}",
                }
                for token, replacement in tokens.items():
                    count = value.count(token)
                    if count:
                        value = value.replace(token, replacement)
                        field = PHOTO_TOKEN_FIELDS[token]
                        replacements[field] = replacements.get(field, 0) + count
                return match.group(1) + html.escape(value, quote=False).encode("utf-8") + match.group(3)
            if CUSTOMER_PLACEHOLDER in value:
                value = value.replace(CUSTOMER_PLACEHOLDER, customer)
                replacements["customer"] += 1
            if value == original_quantity:
                value = str(quantity)
                replacements["quantity"] += 1
            if REPORT_NO_PATTERN.search(value):
                value, count = REPORT_NO_PATTERN.subn(
                    lambda number: f"WFJA-{inspection_date:%y}-{inspection_date:%m%d}{report_number if report_number is not None else int(number.group(1)):03d}",
                    value,
                )
                replacements["report_no"] += count
            if has_date:
                def replace_number(_: re.Match[str]) -> str:
                    nonlocal date_part
                    if date_part >= len(date_values):
                        raise ValueError("Word 模板日期格式与预期不符")
                    result = date_values[date_part]
                    date_part += 1
                    return result

                value = re.sub(r"\d+", replace_number, value)
            return match.group(1) + html.escape(value, quote=False).encode("utf-8") + match.group(3)

        updated = TEXT_PATTERN.sub(replace_text, body)
        if has_date and template_key == "default":
            if date_part != len(date_values):
                raise ValueError("Word 模板日期格式与预期不符")
            replacements["date"] += 1
        return paragraph.group(1) + updated + paragraph.group(3)

    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(output, "w") as target:
        relationships = source.read("word/_rels/document.xml.rels")
        existing_ids = [int(value) for value in re.findall(rb'Id="rId(\d+)"', relationships)]
        footer_relationship = f"rId{max(existing_ids, default=0) + 1}"
        footer_part = "word/footer2.xml"
        if footer_part in source.namelist():
            raise ValueError("Word 模板已有附表页脚，请检查模板结构")
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "word/document.xml":
                data = PARAGRAPH_PATTERN.sub(replace_paragraph, data)
                appendix_titles = PHOTO_APPENDIX_TITLES if template_key == "photo" else APPENDIX_TITLES
                data = _with_appendix_section(data, _appendix_xml(appendix_rows, appendix_titles[kind]), footer_relationship)
            elif item.filename == "word/_rels/document.xml.rels":
                relation = (
                    f'<Relationship Id="{footer_relationship}" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
                    'Target="footer2.xml"/>'
                ).encode()
                data = data.replace(b"</Relationships>", relation + b"</Relationships>", 1)
            elif item.filename == "[Content_Types].xml":
                override = (
                    '<Override PartName="/word/footer2.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                ).encode()
                data = data.replace(b"</Types>", override + b"</Types>", 1)
            elif item.filename == "word/settings.xml" and b"<w:updateFields" not in data:
                data = data.replace(b"</w:settings>", b'<w:updateFields w:val="true"/></w:settings>', 1)
            target.writestr(item, data)
        target.writestr(footer_part, _appendix_footer_xml())

    expected = {"customer": 1, "quantity": 3, "date": 3, "report_no": 1} if template_key == "default" else {
        "customer": 2, "quantity": 3, "date": 4, "report_no": 2, "rejected": 1,
    }
    if replacements != expected:
        raise ValueError(f"Word 模板内容与预期不符：{replacements}")
    return output.getvalue()
