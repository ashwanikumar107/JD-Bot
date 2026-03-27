"""
core/resume_generator.py – Generate an optimized resume PDF using reportlab.
"""

import os
import logging
import re
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


# ── Color palette ─────────────────────────────────────────────────────────────
DARK_BLUE = colors.HexColor("#1B3A5C")
ACCENT_BLUE = colors.HexColor("#2E86C1")
LIGHT_GRAY = colors.HexColor("#F2F3F4")
MID_GRAY = colors.HexColor("#7F8C8D")
BLACK = colors.black


def _build_styles():
    """Create a complete stylesheet for the resume."""
    base = getSampleStyleSheet()

    styles = {
        "name": ParagraphStyle(
            "ResumeName",
            parent=base["Normal"],
            fontSize=24,
            fontName="Helvetica-Bold",
            textColor=DARK_BLUE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "contact": ParagraphStyle(
            "ResumeContact",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=DARK_BLUE,
            spaceBefore=10,
            spaceAfter=2,
        ),
        "job_title": ParagraphStyle(
            "JobTitle",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=BLACK,
            spaceAfter=1,
        ),
        "company": ParagraphStyle(
            "Company",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Oblique",
            textColor=ACCENT_BLUE,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=BLACK,
            leftIndent=14,
            spaceAfter=2,
            alignment=TA_JUSTIFY,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=BLACK,
            spaceAfter=4,
            alignment=TA_JUSTIFY,
        ),
        "skills_label": ParagraphStyle(
            "SkillsLabel",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=DARK_BLUE,
        ),
    }
    return styles


def _section_divider():
    return HRFlowable(
        width="100%",
        thickness=1,
        color=ACCENT_BLUE,
        spaceAfter=4,
        spaceBefore=2,
    )


def _parse_name_contact(resume_text: str) -> tuple[str, str]:
    """Try to extract candidate name and contact info from top of resume."""
    lines = [l.strip() for l in resume_text.split("\n") if l.strip()]

    name = lines[0] if lines else "Your Name"

    # Find lines with email / phone / LinkedIn
    contact_parts = []
    for line in lines[1:8]:
        if any(x in line.lower() for x in ["@", "phone", "tel:", "+", "linkedin", "github", "email"]):
            contact_parts.append(line)
        elif re.search(r"\+?\d[\d\s\-().]{7,}", line):
            contact_parts.append(line)

    contact = "  |  ".join(contact_parts) if contact_parts else "email@example.com  |  +1 (000) 000-0000"
    return name, contact


def _inject_missing_skills(text: str, missing_skills: list[str]) -> str:
    """Append missing skills to the text (for the skills section)."""
    if not missing_skills:
        return text
    additions = ", ".join(s.title() for s in missing_skills[:8])
    return text + f"\n• Additional (Recommended): {additions}"


def _split_into_bullets(text: str) -> list[str]:
    """Split a block of text into bullet points."""
    raw_bullets = re.split(r"\n|•|\u2022|\*|-\s", text)
    return [b.strip() for b in raw_bullets if len(b.strip()) > 10]


def generate_optimized_resume(
    resume_text: str,
    eval_result: dict,
    suggestions: list[str],
    user_id: int,
) -> str:
    """
    Generate a polished optimized resume PDF.

    Args:
        resume_text   : Original resume text
        eval_result   : Output of nlp_engine.evaluate()
        suggestions   : List of suggestions from suggestion_engine
        user_id       : Telegram user ID (used in filename)

    Returns:
        Path to generated PDF file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"optimized_resume_{user_id}_{timestamp}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _build_styles()
    story = []

    # ── Parse resume sections ─────────────────────────────────────────────────
    from pdf_parser import extract_sections
    sections = extract_sections(resume_text)

    name, contact_info = _parse_name_contact(resume_text)

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph(name, styles["name"]))
    story.append(Paragraph(contact_info, styles["contact"]))
    story.append(_section_divider())

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    summary_text = sections.get(
        "summary",
        "Motivated professional with strong technical background seeking to leverage "
        "expertise to contribute to team success. Proven track record of delivering "
        "high-quality solutions and collaborating effectively in fast-paced environments."
    )
    story.append(Paragraph("PROFESSIONAL SUMMARY", styles["section_header"]))
    story.append(_section_divider())
    story.append(Paragraph(summary_text[:600], styles["body"]))
    story.append(Spacer(1, 6))

    # ── SKILLS ────────────────────────────────────────────────────────────────
    story.append(Paragraph("SKILLS", styles["section_header"]))
    story.append(_section_divider())

    skills_text = sections.get("skills", "")
    if eval_result["missing_skills"]:
        # Build skills table with matched + recommended
        matched = eval_result["matched_skills"] if "matched_skills" in eval_result else []
        missing = eval_result["missing_skills"]

        skill_data = []
        if matched:
            matched_str = " • ".join(s.title() for s in matched[:12])
            skill_data.append(["✅ Matched Skills:", matched_str])
        if missing:
            missing_str = " • ".join(s.title() for s in missing[:8])
            skill_data.append(["⭐ Add to Resume:", missing_str])

        if skills_text:
            existing_bullets = _split_into_bullets(skills_text)
            for bullet in existing_bullets[:5]:
                story.append(Paragraph(f"• {bullet}", styles["bullet"]))

        if skill_data:
            skill_table = Table(skill_data, colWidths=[1.5 * inch, 5.5 * inch])
            skill_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(skill_table)
    else:
        bullets = _split_into_bullets(skills_text) if skills_text else [
            "Python, JavaScript, SQL, React",
            "AWS, Docker, Kubernetes",
            "Agile, Scrum, CI/CD",
        ]
        for bullet in bullets[:10]:
            story.append(Paragraph(f"• {bullet}", styles["bullet"]))

    story.append(Spacer(1, 6))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", styles["section_header"]))
    story.append(_section_divider())

    exp_text = sections.get("experience", "")
    if exp_text:
        # Try to split into individual roles
        role_blocks = re.split(
            r"\n(?=[A-Z][a-z].*(?:Engineer|Developer|Manager|Analyst|Designer|Lead|Director|Officer))",
            exp_text
        )
        if len(role_blocks) <= 1:
            role_blocks = exp_text.split("\n\n")

        for block in role_blocks[:4]:
            if not block.strip():
                continue
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if lines:
                story.append(Paragraph(lines[0], styles["job_title"]))
                if len(lines) > 1:
                    story.append(Paragraph(lines[1], styles["company"]))
                for line in lines[2:8]:
                    if line:
                        story.append(Paragraph(f"• {line}", styles["bullet"]))
                story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("• [Add your work experience here with quantifiable achievements]", styles["bullet"]))
        story.append(Spacer(1, 4))

    # ── EDUCATION ────────────────────────────────────────────────────────────
    story.append(Paragraph("EDUCATION", styles["section_header"]))
    story.append(_section_divider())

    edu_text = sections.get("education", "")
    if edu_text:
        for line in edu_text.split("\n")[:6]:
            if line.strip():
                story.append(Paragraph(line.strip(), styles["body"]))
    else:
        story.append(Paragraph("[Add your educational qualifications here]", styles["body"]))

    story.append(Spacer(1, 6))

    # ── PROJECTS ─────────────────────────────────────────────────────────────
    proj_text = sections.get("projects", "")
    if proj_text:
        story.append(Paragraph("PROJECTS", styles["section_header"]))
        story.append(_section_divider())
        for line in proj_text.split("\n")[:8]:
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", styles["bullet"]))
        story.append(Spacer(1, 6))

    # ── CERTIFICATIONS ────────────────────────────────────────────────────────
    cert_text = sections.get("certifications", "")
    if cert_text:
        story.append(Paragraph("CERTIFICATIONS", styles["section_header"]))
        story.append(_section_divider())
        for line in cert_text.split("\n")[:5]:
            if line.strip():
                story.append(Paragraph(f"• {line.strip()}", styles["bullet"]))
        story.append(Spacer(1, 6))

    # ── OPTIMIZATION NOTES (footer box) ──────────────────────────────────────
    if eval_result["missing_skills"] or eval_result["missing_keywords"]:
        story.append(Spacer(1, 8))
        note_lines = ["📌 *Resume Optimization Notes (added by AI):*"]
        if eval_result["missing_skills"]:
            note_lines.append(
                "• Consider adding: " + ", ".join(eval_result["missing_skills"][:5])
            )
        if eval_result["missing_keywords"]:
            note_lines.append(
                "• Key terms to include: " + ", ".join(list(eval_result["missing_keywords"])[:5])
            )
        note_lines.append(f"• Match Score: {eval_result['total_score']}%")

        note_style = ParagraphStyle(
            "Note",
            parent=getSampleStyleSheet()["Normal"],
            fontSize=8,
            fontName="Helvetica-Oblique",
            textColor=MID_GRAY,
            backColor=LIGHT_GRAY,
            borderPad=6,
            leftIndent=6,
            rightIndent=6,
            spaceAfter=2,
        )
        for line in note_lines:
            story.append(Paragraph(line, note_style))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    logger.info(f"Generated resume: {output_path}")
    return output_path
