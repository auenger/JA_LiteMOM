"""Build the editable two-page Word templates from the supplied report photos."""

from pathlib import Path
from io import BytesIO
from zipfile import ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


DEST = Path(__file__).resolve().parents[1] / "app" / "templates"
ORGANIZATION = "锦安特种设备检测有限公司"
BODY_SIZE = 13
REPORT_NOTES = (
    "1、本批次检验合格气瓶均已抽真空。",
    "2、对本检验报告结论如有异议，请在取得本报告后15日内向检验机构提出书面意见。",
    "3、本报告仅对检验时的设备状况负责。",
)


def style_body_run(run):
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(BODY_SIZE)
    run.bold = False


def add_text(doc, value, *, size=13, bold=False, align=None, space_after=12):
    paragraph = doc.add_paragraph()
    if align is not None:
        paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(space_after)
    run = paragraph.add_run(value)
    run.bold = bold
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)
    return paragraph


def add_signature(doc, label, image, width, *, space_before=0, space_after):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.space_after = Pt(space_after)
    # Anchor both date fields to the same right edge, regardless of signature width.
    section = doc.sections[-1]
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        section.page_width - section.left_margin - section.right_margin,
        WD_TAB_ALIGNMENT.RIGHT,
    )
    label_run = paragraph.add_run(label)
    style_body_run(label_run)
    style_body_run(paragraph.add_run("  "))
    paragraph.add_run().add_picture(BytesIO(image), width=Cm(width))
    date_run = paragraph.add_run("\t日期：{{REPORT_DATE}}")
    style_body_run(date_run)


def build(kind):
    doc = Document()
    report_name = "检验报告" if kind == "assessment" else "评定报告"
    detail_name = "气瓶定期检验报告" if kind == "assessment" else "气瓶安全评定报告"
    action = "定期检验" if kind == "assessment" else "安全评定"
    with ZipFile(DEST / f"inspection-{kind}.docx") as original:
        inspector_signature = original.read("word/media/image1.png")
        approver_signature = original.read("word/media/image2.png")
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.5)
    section.top_margin, section.bottom_margin = Cm(2.1), Cm(2)
    section.header_distance, section.footer_distance = Cm(1), Cm(1)
    section.footer.paragraphs[0].text = " "
    pg_num = OxmlElement("w:pgNumType")
    pg_num.set(qn("w:start"), "1")
    section._sectPr.append(pg_num)

    add_text(doc, ORGANIZATION, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    add_text(doc, "报告编号：{{REPORT_NO}}", size=9, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=62)
    add_text(doc, "  ".join(report_name),
             size=30, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=175)
    add_text(doc, "委托单位：{{CUSTOMER}}", size=16, space_after=8)
    add_text(doc, "项目名称：钢瓶检测", size=16, space_after=8)
    add_text(doc, "报告日期：{{REPORT_DATE}}", size=16, space_after=34)
    add_text(doc, ORGANIZATION, size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_page_break()
    add_text(doc, ORGANIZATION, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    add_text(doc, "报告编号：{{REPORT_NO}}", size=9, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=20)
    add_text(doc, " ".join(detail_name),
             size=19, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=22)
    add_text(doc, "{{CUSTOMER}}：", size=BODY_SIZE, space_after=14)
    conclusion = add_text(
        doc,
        "根据《气瓶安全技术规程》（TSG 23—2021）及《液化石油气钢瓶定期检验与评定》"
        "（GB/T 8334—2022）的规定，你单位送检的液化石油气瓶共{{QUANTITY}}只，"
        f"经我机构实施{action}，其中{{{{QUANTITY}}}}只气瓶安全性能符合要求（详见附表），"
        "{{QUANTITY}}只气瓶更换了气瓶阀门，{{REJECTED}}只气瓶判报废，并按规定实施消除使用功能处理。",
        size=BODY_SIZE, space_after=18,
    )
    conclusion.paragraph_format.first_line_indent = Pt(26)
    for index, note in enumerate(REPORT_NOTES):
        paragraph = add_text(doc, ("备注：" if index == 0 else "") + note,
                             size=BODY_SIZE, space_after=4)
        paragraph.paragraph_format.left_indent = Pt(BODY_SIZE * 3)
        paragraph.paragraph_format.first_line_indent = Pt(-BODY_SIZE * 3 if index == 0 else 0)
        paragraph.paragraph_format.line_spacing = 1.2
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.keep_with_next = index < len(REPORT_NOTES) - 1
        if index == 0:
            paragraph.paragraph_format.space_before = Pt(18)
    paragraph.paragraph_format.space_after = Pt(30)
    add_signature(doc, "检验员：", inspector_signature, 3.05, space_before=12, space_after=34)
    add_signature(doc, "批准人：", approver_signature, 2.33, space_after=16)
    seal = add_text(doc, "检验单位：（盖章）  {{REPORT_DATE}}",
                    size=BODY_SIZE, align=WD_ALIGN_PARAGRAPH.RIGHT)
    seal.paragraph_format.space_before = Pt(42)
    seal.paragraph_format.right_indent = Cm(0)
    path = DEST / f"inspection-photo-{kind}.docx"
    doc.save(path)
    print(path)


if __name__ == "__main__":
    build("regular")
    build("assessment")
