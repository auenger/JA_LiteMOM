import io
import hashlib
import zipfile
from datetime import date
from xml.etree import ElementTree

from backend.app.inspection_word import TEMPLATE_DIR, render_inspection_word

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def document_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    return "".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))


def assert_expected_signatures(template_name: str, content: bytes):
    template_path = TEMPLATE_DIR / template_name
    with zipfile.ZipFile(template_path) as template, zipfile.ZipFile(io.BytesIO(content)) as generated:
        images = [name for name in template.namelist() if name.startswith("word/media/")]
        assert len(images) == 2
        assert all(generated.read(name) == template.read(name) for name in images)
        assert hashlib.sha256(generated.read("word/media/image1.png")).hexdigest() == (
            "734e3fa4c871f2128eabad31aa287a5f0fd18a3ce1c79199c45e89cf95f01a3f"
        )
        assert hashlib.sha256(generated.read("word/media/image2.png")).hexdigest() == (
            "d262dd205b90eeb9074dffd381235d6a926322277c9d58578f7a06d38e1e791b"
        )
        assert "仿宋".encode("utf-8") in generated.read("word/document.xml")


def test_regular_word_template_replaces_customer_quantity_and_dates():
    content = render_inspection_word("regular", "测试燃气公司", date(2026, 9, 12), 369)
    text = document_text(content)
    assert "测试燃气公司：" in text
    assert text.count("369只") == 3
    assert "401只" not in text
    assert text.count("2026年 09 月12日") == 3
    assert "WFJA-26-0912001" in text
    assert "定期检验" in text
    assert "附表:定期检验合格气瓶一览表" in text
    assert_expected_signatures("inspection-regular.docx", content)


def test_assessment_word_template_replaces_customer_quantity_and_dates():
    content = render_inspection_word("assessment", "评定客户", date(2026, 9, 12), 12)
    text = document_text(content)
    assert "评定客户：" in text
    assert text.count("12只") == 3
    assert "133只" not in text
    assert text.count("2026年 09 月12日") == 3
    assert "WFJA-26-0912002" in text
    assert "安全评定" in text
    assert "附表:安全评定合格气瓶一览表" in text
    assert_expected_signatures("inspection-assessment.docx", content)


def test_word_report_number_changes_only_the_three_digit_suffix():
    regular = render_inspection_word("regular", "测试公司", date(2026, 9, 12), 0, report_number=3)
    assessment = render_inspection_word("assessment", "测试公司", date(2026, 9, 12), 0, report_number=4)
    assert "WFJA-26-0912003" in document_text(regular)
    assert "WFJA-26-0912004" in document_text(assessment)
    assert_expected_signatures("inspection-regular.docx", regular)
    assert_expected_signatures("inspection-assessment.docx", assessment)


def test_word_appendix_starts_on_new_page_and_keeps_six_column_table():
    rows = [("1", "瓶-001", "2022.09", "测试厂家", "35.50", "2030.09.11")]
    content = render_inspection_word("regular", "测试客户", date(2026, 9, 12), 1, rows)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", NS)
    assert body is not None
    table = body.find("w:tbl", NS)
    assert table is not None
    table_index = list(body).index(table)
    assert table_index > 0
    section_break = body[table_index - 1]
    assert section_break.find("w:pPr/w:sectPr/w:type", NS).get(f"{{{NS['w']}}}val") == "nextPage"
    assert body.find("w:sectPr/w:pgNumType", NS).get(f"{{{NS['w']}}}start") == "1"
    rows_xml = table.findall("w:tr", NS)
    assert len(rows_xml) == 3
    assert rows_xml[0].find("w:trPr/w:tblHeader", NS) is not None
    assert rows_xml[0].find("w:tc/w:tcPr/w:gridSpan", NS).get(f"{{{NS['w']}}}val") == "6"
    assert "附表:定期检验合格气瓶一览表" in "".join(rows_xml[0].itertext())
    assert rows_xml[1].find("w:trPr/w:tblHeader", NS) is not None
    assert all(len(row.findall("w:tc", NS)) == 6 for row in rows_xml[1:])
    assert ["".join(cell.itertext()) for cell in rows_xml[2].findall("w:tc", NS)] == list(rows[0])
    assert len(table.findall("w:tblPr/w:tblBorders/*", NS)) == 6
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        footer = ElementTree.fromstring(archive.read("word/footer2.xml"))
        assert footer.find("w:p/w:pPr/w:jc", NS).get(f"{{{NS['w']}}}val") == "center"
        assert [node.get(f"{{{NS['w']}}}instr") for node in footer.findall(".//w:fldSimple", NS)] == ["PAGE", "SECTIONPAGES"]
        relationships = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
        footer_references = [item for item in relationships if item.get("Target") == "footer2.xml"]
        assert len(footer_references) == 1
        assert body.find("w:sectPr/w:footerReference", NS).get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") == footer_references[0].get("Id")
        content_types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
        assert any(item.get("PartName") == "/word/footer2.xml" for item in content_types)
        assert ElementTree.fromstring(archive.read("word/settings.xml")).find("w:updateFields", NS) is not None
    assert_expected_signatures("inspection-regular.docx", content)


def test_word_appendix_accepts_many_rows_for_normal_word_pagination():
    rows = [(str(index), f"瓶-{index:04d}", "2022.09", "测试厂家", "35.50", "2030.09.11") for index in range(1, 501)]
    content = render_inspection_word("assessment", "测试客户", date(2026, 9, 12), len(rows), rows)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    table = root.find("w:body/w:tbl", NS)
    assert table is not None
    assert len(table.findall("w:tr", NS)) == 502
    assert len(table.findall("w:tblGrid/w:gridCol", NS)) == 6


def test_photo_template_has_cover_report_page_and_appendix():
    content = render_inspection_word(
        "regular", "诸城市惠泽燃气公司", date(2026, 9, 21), 2,
        [("1", "瓶-001", "2020.06", "测试厂家", "35.50", "2030.09.20")],
        report_number=164, template_key="photo",
    )
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        xml = archive.read("word/document.xml")
    text = document_text(content)
    assert text.count("诸城市惠泽燃气公司") == 2
    assert text.count("锦安特种设备检测有限公司") == 3
    assert "烟台金弘安气瓶检测有限公司" not in text
    assert text.count("WFJA-26-0921164") == 2
    assert "2只气瓶安全性能符合要求" in text
    assert "0只气瓶判报废" in text
    assert "附表:安全评定合格气瓶一览表" in text
    assert b'w:type="page"' in xml
    assert b'w:val="nextPage"' in xml
    with zipfile.ZipFile(io.BytesIO(content)) as generated, zipfile.ZipFile(TEMPLATE_DIR / "inspection-regular.docx") as original:
        assert generated.read("word/media/image1.png") == original.read("word/media/image1.png")
        assert generated.read("word/media/image2.png") == original.read("word/media/image2.png")
    root = ElementTree.fromstring(xml)
    paragraphs = root.findall(".//w:body/w:p", NS)
    signature_paragraphs = [
        paragraph for paragraph in paragraphs
        if paragraph.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip") is not None
    ]
    assert len(signature_paragraphs) == 2
    assert "检验员：" in "".join(signature_paragraphs[0].itertext())
    assert "批准人：" in "".join(signature_paragraphs[1].itertext())
    conclusion = next(paragraph for paragraph in paragraphs if "根据《气瓶安全技术规程》" in "".join(paragraph.itertext()))
    assert conclusion.find("w:pPr/w:ind", NS).get(f"{{{NS['w']}}}firstLine") == "520"
    assert signature_paragraphs[0].find("w:pPr/w:spacing", NS).get(f"{{{NS['w']}}}before") == "240"
    seal = next(paragraph for paragraph in paragraphs if "检验单位：（盖章）" in "".join(paragraph.itertext()))
    assert seal.find("w:pPr/w:jc", NS).get(f"{{{NS['w']}}}val") == "right"
    assert seal.find("w:pPr/w:spacing", NS).get(f"{{{NS['w']}}}before") == "840"
    assert seal.find("w:pPr/w:ind", NS).get(f"{{{NS['w']}}}right") == "0"


def test_photo_report_names_match_four_year_groups():
    for kind, cover, detail, action, appendix in (
        ("assessment", "检  验  报  告", "气 瓶 定 期 检 验 报 告", "实施定期检验", "附表:定期检验合格气瓶一览表"),
        ("regular", "评  定  报  告", "气 瓶 安 全 评 定 报 告", "实施安全评定", "附表:安全评定合格气瓶一览表"),
    ):
        content = render_inspection_word(kind, "测试客户", date(2026, 9, 12), 1, template_key="photo")
        text = document_text(content)
        assert cover in text
        assert detail in text
        assert action in text
        assert appendix in text
        assert "备注：1、本批次检验合格气瓶均已抽真空。" in text
        assert "2、对本检验报告结论如有异议，请在取得本报告后15日内向检验机构提出书面意见。" in text
        assert "3、本报告仅对检验时的设备状况负责。" in text
        assert text.index("备注：1、") < text.index("3、本报告") < text.index("检验员：") < text.index("批准人：")
