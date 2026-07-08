"""Evaluation PDF export (Phase 3) using ReportLab + a Thai TTF font.

Font path is configurable via PDF_FONT_PATH; falls back to common Windows/Linux
Thai fonts. Bundle an OFL font (e.g. Sarabun) for production deployments.
"""
import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_FONT = "ThaiFont"
_registered = False

_FONT_CANDIDATES = [
    os.environ.get("PDF_FONT_PATH"),
    r"C:\Windows\Fonts\LeelawUI.ttf",
    r"C:\Windows\Fonts\leelawad.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/usr/share/fonts/truetype/tlwg/Sarabun.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]

_STATUS_TH = {
    "draft": "ร่าง", "submitted": "ส่งแล้ว (รอ ผจก.แผนก)",
    "dept_approved": "ผจก.แผนกอนุมัติ (รอ MD)", "md_approved": "MD อนุมัติ (รอ HR)",
    "finalized": "ปิดใบแล้ว", "returned": "ตีกลับให้แก้",
}
_STEP_TH = {"dept_manager": "ผจก.แผนก", "md": "กรรมการผู้จัดการ", "hr": "ฝ่ายบุคคล"}


def _ensure_font() -> None:
    global _registered
    if _registered:
        return
    for path in _FONT_CANDIDATES:
        if path and os.path.exists(path):
            pdfmetrics.registerFont(TTFont(_FONT, path))
            _registered = True
            return
    raise RuntimeError("No Thai TTF font found; set PDF_FONT_PATH")


def _fmt(v) -> str:
    return "—" if v is None else str(v)


def build_evaluation_pdf(ev: dict) -> bytes:
    _ensure_font()
    title = ParagraphStyle("title", fontName=_FONT, fontSize=15, leading=19, alignment=1)
    sub = ParagraphStyle("sub", fontName=_FONT, fontSize=10, leading=13, alignment=1, textColor=colors.HexColor("#475569"))
    h2 = ParagraphStyle("h2", fontName=_FONT, fontSize=11, leading=15, spaceBefore=8, spaceAfter=2, textColor=colors.HexColor("#0f172a"))
    normal = ParagraphStyle("n", fontName=_FONT, fontSize=9.5, leading=13)
    small = ParagraphStyle("s", fontName=_FONT, fontSize=9, leading=12, textColor=colors.HexColor("#475569"))

    emp = ev.get("_employee", {})
    evaluator = ev.get("_evaluator", {})
    company = ev.get("_company", {})
    kind_th = "ประจำปี" if ev["kind"] == "annual" else f"ทดลองงาน ({_fmt(ev.get('probation_checkpoint'))} วัน)"

    flow = []
    flow.append(Paragraph(_fmt(company.get("name")), sub))
    flow.append(Paragraph("แบบประเมินผลการปฏิบัติงาน", title))
    flow.append(Spacer(1, 6))

    info = [
        [Paragraph("ชื่อ-นามสกุล", small), Paragraph(_fmt(emp.get("full_name")), normal),
         Paragraph("รหัสพนักงาน", small), Paragraph(_fmt(emp.get("emp_code")), normal)],
        [Paragraph("ตำแหน่ง", small), Paragraph(_fmt(emp.get("position")), normal),
         Paragraph("ผู้ประเมิน", small), Paragraph(_fmt(evaluator.get("full_name")), normal)],
        [Paragraph("ชนิดการประเมิน", small), Paragraph(kind_th, normal),
         Paragraph("สถานะ", small), Paragraph(_STATUS_TH.get(ev["status"], ev["status"]), normal)],
        [Paragraph("ช่วงเวลา", small),
         Paragraph(f"{_fmt(ev.get('period_start'))} – {_fmt(ev.get('period_end'))}", normal),
         Paragraph("คิดเป็น", small),
         Paragraph(f"{_fmt(ev.get('percentage'))}%", normal)],
    ]
    t = Table(info, colWidths=[3 * cm, 6.5 * cm, 3 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)

    # group items by category
    cats: dict[int, dict] = {}
    for it in ev.get("items", []):
        c = cats.setdefault(it["category_order"], {"name": it["category_name"], "items": []})
        c["items"].append(it)
    comments = {c["category_order"]: c.get("comment") for c in ev.get("comments", [])}

    for order in sorted(cats):
        cat = cats[order]
        flow.append(Paragraph(f"{order}. {cat['name']}", h2))
        rows = [[Paragraph("หัวข้อ", small), Paragraph("คะแนน", small)]]
        for it in sorted(cat["items"], key=lambda x: x["item_order"]):
            rows.append([Paragraph(it["item_name"], normal), Paragraph(_fmt(it.get("score")), normal)])
        ct = Table(rows, colWidths=[15 * cm, 2.5 * cm])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        flow.append(ct)
        if comments.get(order):
            flow.append(Paragraph(f"ข้อคิดเห็น: {comments[order]}", small))

    # totals
    flow.append(Paragraph("สรุปคะแนน", h2))
    att = ev.get("attendance") or {}
    totals = [
        [Paragraph("คะแนนประเมิน", small), Paragraph(f"{_fmt(ev.get('eval_score'))} / {_fmt(ev.get('eval_max'))}", normal),
         Paragraph("คะแนนการมา-ลา", small), Paragraph(f"{_fmt(att.get('attendance_score'))} / 40", normal)],
        [Paragraph("รวมทั้งสิ้น", small), Paragraph(_fmt(ev.get("total_score")), normal),
         Paragraph("คิดเป็นร้อยละ", small), Paragraph(f"{_fmt(ev.get('percentage'))}%", normal)],
    ]
    tt = Table(totals, colWidths=[3 * cm, 6.5 * cm, 3 * cm, 5 * cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(tt)

    approvals = ev.get("approvals", [])
    if approvals:
        flow.append(Paragraph("การอนุมัติ", h2))
        for a in approvals:
            step = _STEP_TH.get(a["step"], a["step"])
            dec = "อนุมัติ" if a["decision"] == "approved" else "ตีกลับ"
            note = f" — {a['comment']}" if a.get("comment") else ""
            flow.append(Paragraph(f"• {step}: {dec}{note}", small))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            title="แบบประเมินผลการปฏิบัติงาน")
    doc.build(flow)
    return buf.getvalue()
