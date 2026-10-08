"""Fill one-bottle Word reports by changing only text nodes in the original DOCX."""

from __future__ import annotations

import html
import io
import re
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from .inspection_xls import default_next_inspection_date


TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "RT0017202609100003678853ea.docx"
PARAGRAPH_PATTERN = re.compile(rb"(<w:p(?:\s+[^>]*)?>)(.*?)(</w:p>)", re.DOTALL)
TEXT_PATTERN = re.compile(rb"(<w:t(?:\s+[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)


def _replace_node_text(body: bytes, original: str, replacement: str) -> bytes:
    count = 0

    def replace(match: re.Match[bytes]) -> bytes:
        nonlocal count
        text = html.unescape(match.group(2).decode("utf-8"))
        if text != original:
            return match.group(0)
        count += 1
        return match.group(1) + html.escape(replacement, quote=False).encode("utf-8") + match.group(3)

    updated = TEXT_PATTERN.sub(replace, body)
    if count != 1:
        raise ValueError(f"单瓶报告模板字段 {original!r} 不唯一或不存在")
    return updated


def _volume_text(volume: Decimal) -> str:
    return format(volume.normalize(), "f") if volume else ""


def render_bottle_report_word(
    *,
    body_code: str,
    sequence: int,
    customer_name: str,
    manufacturer: str,
    spec_name: str,
    manufacture_date: date | None,
    volume: Decimal,
    wall_thickness: Decimal,
    inspection_date: date,
    template_bytes: bytes | None = None,
) -> bytes:
    if sequence < 1 or sequence > 9999:
        raise ValueError("单瓶报告序号必须在 1 至 9999 之间")
    source = io.BytesIO(template_bytes if template_bytes is not None else TEMPLATE_PATH.read_bytes())
    output = io.BytesIO()
    record_no = f"{inspection_date:%Y%m%d}{sequence:04d}"
    next_inspection_date = default_next_inspection_date(inspection_date)
    weight_match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:kg|㎏|公斤|千克)\s*", spec_name, flags=re.IGNORECASE)
    spec_weight = weight_match.group(1) if weight_match else spec_name.strip()
    def replace_document(document_xml: bytes) -> bytes:
        found = {"record": 0, "bottle": 0, "customer": 0, "manufacturer": 0,
                 "spec": 0, "volume": 0, "measured_volume": 0, "manufacture_date": 0,
                 "last_inspection_date": 0, "wall_thickness": 0, "next_date": 0,
                 "bottom_date": 0}
        original_manufacture_dates = 0

        def replace_paragraph(match: re.Match[bytes]) -> bytes:
            nonlocal original_manufacture_dates
            body = match.group(2)
            text = "".join(html.unescape(node.group(2).decode("utf-8")) for node in TEXT_PATTERN.finditer(body))
            key = None
            original = replacement = ""
            if "记录编号:" in text and "202609100133" in text:
                key, original, replacement = "record", "202609100133", record_no
            elif text == "000367885":
                key, original, replacement = "bottle", text, body_code
            elif text == "安丘天顺燃气有限责任公司":
                key, original, replacement = "customer", text, customer_name
            elif text == "山东环日集团有限公司":
                key, original, replacement = "manufacturer", text, manufacturer
            elif text == "16㎏":
                key, original, replacement = "spec", "16", spec_weight
                body = _replace_node_text(body, "㎏", "㎏" if weight_match else "")
            elif text == "35.5L":
                key, original, replacement = "volume", "35.5", _volume_text(volume)
            elif text.startswith("实测容积：") and "35.5" in text:
                key, original, replacement = "measured_volume", "35.5", _volume_text(volume)
            elif text == "2018-10-01":
                original_manufacture_dates += 1
                if original_manufacture_dates == 1:
                    key, original, replacement = "manufacture_date", text, manufacture_date.isoformat() if manufacture_date else ""
                elif original_manufacture_dates == 2:
                    key, original, replacement = "last_inspection_date", text, manufacture_date.isoformat() if manufacture_date else ""
            elif text == "2.3mm":
                key, original, replacement = "wall_thickness", "2.3", f"{wall_thickness:.2f}"
            elif text == "2030-09-09":
                key, original, replacement = "next_date", text, next_inspection_date.isoformat()
            elif text == "2026-09-10":
                key, original, replacement = "bottom_date", text, inspection_date.isoformat()
            if key is None:
                return match.group(0)
            found[key] += 1
            return match.group(1) + _replace_node_text(body, original, replacement) + match.group(3)

        updated = PARAGRAPH_PATTERN.sub(replace_paragraph, document_xml)
        expected = {key: (2 if key == "bottom_date" else 1) for key in found}
        if found != expected or original_manufacture_dates != 2:
            raise ValueError(f"单瓶报告模板结构与预期不符：{found}")
        return updated

    with zipfile.ZipFile(source) as template, zipfile.ZipFile(output, "w") as generated:
        for item in template.infolist():
            data = template.read(item.filename)
            if item.filename == "word/document.xml":
                data = replace_document(data)
            generated.writestr(item, data)
    return output.getvalue()
