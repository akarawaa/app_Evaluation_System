"""ReportLab has no OpenType text-shaping engine, so two Thai combining
marks stacked on one base consonant (an "above" vowel like ั/ิ plus a tone
mark like ่/้) collide instead of the tone mark rendering above the vowel --
see docs/PROJECT_STATUS.md and app/services/pdf.py's _fix_thai_stacking.
Pure unit tests against the PDF builder directly (no server needed)."""
from app.services.pdf import _fix_thai_stacking, _p, build_evaluation_pdf
from reportlab.lib.styles import ParagraphStyle


def test_stacking_fix_wraps_tone_mark_after_above_vowel():
    style = ParagraphStyle("t", fontSize=10)
    out = _fix_thai_stacking("รวมทั้งสิ้น", style.fontSize)
    # ทั้ง = ท + ั (above vowel) + ้ (tone) + ง -- the tone mark must be lifted
    assert '<super rise="2.2pt" size="10pt">้</super>' in out
    # a lone tone mark with no preceding above-vowel is left untouched
    assert "ง" in out and "ั" in out


def test_stacking_fix_is_noop_for_plain_text():
    style = ParagraphStyle("t", fontSize=10)
    assert _fix_thai_stacking("สม่ำเสมอ", style.fontSize) == "สม่ำเสมอ"


def test_p_escapes_xml_special_characters():
    style = ParagraphStyle("t", fontSize=10)
    # a name/comment containing &, <, > must not break or be interpreted as
    # markup by Paragraph's own XML-like parser (pre-existing gap, closed
    # alongside the stacking fix since every call site was touched anyway)
    para = _p("R&D <team> \"lead\"", style)
    assert para is not None  # would have raised during Paragraph parsing if unescaped


def test_build_evaluation_pdf_handles_stacking_and_special_chars():
    ev = {
        "kind": "annual", "status": "draft",
        "period_start": None, "period_end": None,
        "eval_score": 100, "eval_max": 140, "total_score": 100, "percentage": 71.43,
        "items": [], "comments": [], "attendance": {}, "approvals": [], "acknowledgement": None,
        "_employee": {"full_name": "ทดสอบ ทั้งสิ้น & <ทีม>", "emp_code": "T01", "position": "ตำแหน่งที่ทั้งหมด"},
        "_evaluator": {"full_name": "สมหมาย ใจดี"},
        "_company": {"name": "บริษัท ทดลอง จำกัด"},
    }
    pdf_bytes = build_evaluation_pdf(ev)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
