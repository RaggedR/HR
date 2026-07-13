"""PDF dossier output — CV-style, one page per candidate."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from models import Dossier

WIDTH, HEIGHT = A4
MARGIN = 2 * cm

# Colour palette
NAVY = "#1a237e"
DARK_GREY = "#37474f"
MID_GREY = "#607d8b"
LIGHT_GREY = "#eceff1"
BODY_TEXT = "#263238"
GREEN = "#2e7d32"
AMBER = "#ef6c00"
RED = "#c62828"
ACCENT = "#0d47a1"
SIDEBAR_BG = "#f5f7fa"


class ConfidenceBar(Flowable):
    """Visual confidence meter."""

    def __init__(self, confidence: float, width: float = 5 * cm, height: float = 6 * mm):
        super().__init__()
        self.confidence = confidence
        self.bar_width = width
        self.bar_height = height
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(colors.HexColor("#e0e0e0"))
        self.canv.roundRect(0, 0, self.bar_width, self.bar_height, 2, fill=1, stroke=0)

        if self.confidence > 0.7:
            fill = colors.HexColor(GREEN)
        elif self.confidence > 0.4:
            fill = colors.HexColor(AMBER)
        else:
            fill = colors.HexColor(RED)

        self.canv.setFillColor(fill)
        filled = self.bar_width * self.confidence
        self.canv.roundRect(0, 0, filled, self.bar_height, 2, fill=1, stroke=0)

        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawCentredString(
            self.bar_width / 2, 1.5, f"{self.confidence:.0%}"
        )


class AccentRule(Flowable):
    """A short accent line under the name, like a CV header."""

    def __init__(self, width: float = 3 * cm, color: str = ACCENT):
        super().__init__()
        self.rule_width = width
        self.rule_color = color
        self.width = width
        self.height = 3

    def draw(self):
        self.canv.setStrokeColor(colors.HexColor(self.rule_color))
        self.canv.setLineWidth(2)
        self.canv.line(0, 0, self.rule_width, 0)


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "CandidateName",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        spaceAfter=1 * mm,
        textColor=colors.HexColor(NAVY),
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "CurrentRole",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor(ACCENT),
        fontName="Helvetica-Bold",
        spaceAfter=1 * mm,
    ))
    styles.add(ParagraphStyle(
        "PreviousRole",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor(MID_GREY),
        spaceAfter=0.5 * mm,
    ))
    styles.add(ParagraphStyle(
        "LocationText",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor(DARK_GREY),
        spaceBefore=1 * mm,
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=10,
        leading=13,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=colors.HexColor(NAVY),
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        spaceAfter=2 * mm,
        textColor=colors.HexColor(BODY_TEXT),
    ))
    styles.add(ParagraphStyle(
        "SmallBody",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        spaceAfter=1.5 * mm,
        textColor=colors.HexColor(MID_GREY),
    ))
    styles.add(ParagraphStyle(
        "ContactItem",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor(DARK_GREY),
        spaceAfter=0.5 * mm,
    ))
    styles.add(ParagraphStyle(
        "GapText",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#795548"),
        leftIndent=8,
        spaceAfter=1 * mm,
    ))
    styles.add(ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#bdbdbd"),
        alignment=1,
    ))
    styles.add(ParagraphStyle(
        "TitlePage",
        parent=styles["Title"],
        fontSize=28,
        textColor=colors.HexColor(NAVY),
    ))
    styles.add(ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor(MID_GREY),
        spaceAfter=2 * mm,
    ))
    return styles


def _render_candidate_page(dossier: Dossier, styles) -> list:
    """Build CV-style flowable elements for one candidate page."""
    k = dossier.keys
    p = dossier.profile
    v = dossier.verification
    elements = []

    # === HEADER ===
    name = p.name or k.name or "Unknown Candidate"
    elements.append(Paragraph(name, styles["CandidateName"]))
    elements.append(AccentRule())
    elements.append(Spacer(1, 2 * mm))

    # Current role (first one, prominent)
    if p.roles:
        elements.append(Paragraph(p.roles[0], styles["CurrentRole"]))

    # Location
    if p.location:
        elements.append(Paragraph(f"\u2302  {p.location}", styles["LocationText"]))

    elements.append(Spacer(1, 3 * mm))

    # === CONTACT INFO — horizontal table ===
    contact_items = []
    if k.linkedin_url:
        contact_items.append(("LinkedIn", k.linkedin_url))
    if k.email:
        contact_items.append(("Email", k.email))
    if k.github_handle:
        contact_items.append(("GitHub", f"github.com/{k.github_handle}"))
    seen = set()
    for label, url in (p.links or {}).items():
        if url and label.lower() not in ("github", "linkedin"):
            norm = url.lower().rstrip("/")
            if norm not in seen:
                seen.add(norm)
                contact_items.append((label.title(), url))

    if contact_items:
        rows = [[
            Paragraph(f"<b>{label}:</b>  {value}", styles["ContactItem"])
        ] for label, value in contact_items]
        t = Table(rows, colWidths=[16.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SIDEBAR_BG)),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph(
            "<i>No contact details found</i>", styles["SmallBody"]
        ))

    # === CAREER HISTORY ===
    if p.roles and len(p.roles) > 1:
        elements.append(Paragraph("CAREER HISTORY", styles["SectionHead"]))
        for role in p.roles[1:5]:
            elements.append(Paragraph(f"\u2022  {role}", styles["PreviousRole"]))

    # === PROFILE SUMMARY ===
    elements.append(Paragraph("PROFILE", styles["SectionHead"]))
    if p.summary:
        elements.append(Paragraph(p.summary, styles["Body"]))

    # === VERIFICATION ===
    elements.append(Paragraph("VERIFICATION", styles["SectionHead"]))

    status = "CONFIRMED" if v.confirmed else "UNCONFIRMED"
    status_color = GREEN if v.confirmed else RED
    elements.append(Paragraph(
        f'Identity: <font color="{status_color}"><b>{status}</b></font>',
        styles["Body"],
    ))

    if v.refute_notes:
        notes = v.refute_notes
        if len(notes) > 300:
            notes = notes[:297] + "..."
        elements.append(Paragraph(notes, styles["SmallBody"]))

    # === GAPS ===
    if p.gaps:
        elements.append(Paragraph("GAPS & NEXT STEPS", styles["SectionHead"]))
        for gap in p.gaps[:4]:
            elements.append(Paragraph(f"\u2022  {gap}", styles["GapText"]))
        if p.next_key_needed:
            elements.append(Spacer(1, 1 * mm))
            elements.append(Paragraph(
                f"<b>Next step:</b> {p.next_key_needed}", styles["SmallBody"]
            ))

    return elements


def generate_pdf(
    dossiers: list[Dossier],
    output_path: str | Path | None = None,
    title: str = "Candidate Dossiers",
) -> Path:
    """Generate a PDF with one CV-style page per candidate."""
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent.parent / "data" / f"candidates_{timestamp}.pdf"

    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = []

    # Title page
    elements.append(Spacer(1, 6 * cm))
    elements.append(Paragraph(title, styles["TitlePage"]))
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(
        f"{len(dossiers)} candidates  \u00b7  {datetime.now().strftime('%d %B %Y')}",
        styles["Subtitle"],
    ))
    elements.append(Paragraph(
        "Ranked by confidence score",
        styles["Subtitle"],
    ))

    # Summary table
    if dossiers:
        elements.append(Spacer(1, 1 * cm))
        table_data = [["#", "Name", "Current Role", "Location"]]
        for i, d in enumerate(dossiers, 1):
            name = d.profile.name or d.keys.name or "?"
            role = d.profile.roles[0][:45] if d.profile.roles else "—"
            loc = (d.profile.location or "—")[:20]
            table_data.append([str(i), name[:28], role, loc])

        t = Table(table_data, colWidths=[0.8 * cm, 4.5 * cm, 7.5 * cm, 3.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    elements.append(PageBreak())

    # One page per candidate
    for i, dossier in enumerate(dossiers):
        page_elements = _render_candidate_page(dossier, styles)
        elements.extend(page_elements)

        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(
            f"Candidate {i + 1} of {len(dossiers)}  \u00b7  "
            f"{dossier.created_at[:10]}",
            styles["Footer"],
        ))

        if i < len(dossiers) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    return output_path
