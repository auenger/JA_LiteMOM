import io
import zipfile
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree

from backend.app.bottle_report_word import TEMPLATE_PATH, render_bottle_report_word


def test_single_bottle_report_replaces_only_selected_text_nodes():
    generated = render_bottle_report_word(
        body_code="TEST-001",
        sequence=7,
        customer_name="测试送检单位",
        manufacturer="测试制造厂",
        spec_name="15kg",
        manufacture_date=date(2022, 1, 15),
        volume=Decimal("8.80"),
        wall_thickness=Decimal("2.45"),
        inspection_date=date(2026, 9, 12),
    )
    with zipfile.ZipFile(TEMPLATE_PATH) as template, zipfile.ZipFile(io.BytesIO(generated)) as report:
        assert report.namelist() == template.namelist()
        for name in template.namelist():
            if name != "word/document.xml":
                assert report.read(name) == template.read(name)
        xml = report.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        template_root = ElementTree.fromstring(template.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
        text = "".join(node.text or "" for node in root.iter(namespace))
        assert "记录编号: 202609120007" in text
        assert "TEST-001" in text
        assert "测试送检单位" in text
        assert "测试制造厂" in text
        assert "实际容积(V)8.8L" in text
        assert "实测容积：8.8 L" in text
        assert "制造年月2022-01-15" in text
        assert "上次检验日期2022-01-15" in text
        assert "设计壁厚(S)2.45mm" in text
        assert "2018-10-01" not in text
        assert "下次检验日期2030-09-11" in text
        assert text.count("2026-09-12") == 2
        assert "15㎏" in text
        assert "2.1MPa" in text
        assert "35.5L瓶6mm" in text
        for document_root in (root, template_root):
            for node in document_root.iter(namespace):
                node.text = ""
        assert ElementTree.tostring(root) == ElementTree.tostring(template_root)


def test_single_bottle_report_clears_template_dates_when_manufacture_date_is_missing():
    generated = render_bottle_report_word(
        body_code="TEST-002",
        sequence=8,
        customer_name="测试送检单位",
        manufacturer="测试制造厂",
        spec_name="15kg",
        manufacture_date=None,
        volume=Decimal("35.50"),
        wall_thickness=Decimal("0.00"),
        inspection_date=date(2026, 9, 12),
    )
    with zipfile.ZipFile(io.BytesIO(generated)) as report:
        root = ElementTree.fromstring(report.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
        text = "".join(node.text or "" for node in root.iter(namespace))
        assert "2018-10-01" not in text
        assert "设计壁厚(S)0.00mm" in text
