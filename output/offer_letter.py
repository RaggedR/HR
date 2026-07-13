"""Offer letter PDF generator.

Produces a personalised offer letter for each candidate with:
- Company overview
- Role-specific description
- Personality-fit questions (designed for non-traditional candidates)
- Penrose P2 kite-dart tiling background
"""

from __future__ import annotations

import math
import random
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    PageBreak,
)

from models import Dossier

WIDTH, HEIGHT = A4
MARGIN = 2.5 * cm
PHI = (1 + math.sqrt(5)) / 2


# ── Penrose P2 tiling (Robinson triangle deflation) ──────────────

def _rot(px, py, ox, oy, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    dx, dy = px - ox, py - oy
    return (ox + dx * c - dy * s, oy + dx * s + dy * c)


def _tri(shape, side, A, B):
    ang = 36 if shape == "A" else 108
    C = _rot(B[0], B[1], A[0], A[1], ang)
    return (shape, side, A, B, C)


def _deflate(triangles):
    result = []
    for shape, side, A, B, C in triangles:
        if shape == "A":
            if side == "F":
                P = _rot(B[0], B[1], C[0], C[1], -36)
                Q = _rot(B[0], B[1], C[0], C[1], -72)
                result.append(_tri("O", "F", Q, A))
                result.append(_tri("A", "B", C, Q))
                result.append(_tri("A", "F", C, P))
            else:
                P = _rot(C[0], C[1], B[0], B[1], 36)
                Q = _rot(C[0], C[1], B[0], B[1], 72)
                result.append(_tri("O", "B", Q, P))
                result.append(_tri("A", "F", B, P))
                result.append(_tri("A", "B", B, C))
        else:
            if side == "F":
                D = _rot(A[0], A[1], B[0], B[1], -36)
                result.append(_tri("A", "B", B, D))
                result.append(_tri("O", "F", D, C))
            else:
                D = _rot(A[0], A[1], C[0], C[1], 36)
                result.append(_tri("A", "F", C, A))
                result.append(_tri("O", "B", D, A))
    return result


def _make_sun_seed(cx, cy, radius):
    tris = []
    for i in range(5):
        deg = i * 72 - 90
        rad = math.radians(deg)
        Bf = (cx + radius * math.cos(rad), cy + radius * math.sin(rad))
        tris.append(_tri("A", "F", (cx, cy), Bf))
        Bb = _rot(Bf[0], Bf[1], cx, cy, -36)
        tris.append(_tri("A", "B", (cx, cy), Bb))
    return tris


def _generate_penrose_tiling(w, h):
    """Generate Penrose P2 triangles covering a w×h rectangle."""
    random.seed()
    spread = max(w, h) * 0.8
    ox = (random.random() - 0.5) * spread
    oy = (random.random() - 0.5) * spread
    cx, cy = w / 2 + ox, h / 2 + oy

    radius = max(
        math.hypot(cx, cy),
        math.hypot(w - cx, cy),
        math.hypot(cx, h - cy),
        math.hypot(w - cx, h - cy),
    ) * 1.05

    tris = _make_sun_seed(cx, cy, radius)
    for _ in range(7):
        tris = _deflate(tris)

    margin = 20
    return [
        t for t in tris
        if any(
            -margin < v[0] < w + margin and -margin < v[1] < h + margin
            for v in (t[2], t[3], t[4])
        )
    ]


def _ekey(a, b):
    ka = f"{round(a[0] * 100)},{round(a[1] * 100)}"
    kb = f"{round(b[0] * 100)},{round(b[1] * 100)}"
    return (ka + "|" + kb) if ka < kb else (kb + "|" + ka)


def _draw_penrose_background(canvas, doc):
    """Draw a subtle Penrose tiling as the page background."""
    w, h = WIDTH, HEIGHT
    tris = _generate_penrose_tiling(w, h)

    canvas.saveState()

    # Subtle but visible fill colors
    kite_fill = colors.HexColor("#dce8f0")
    dart_fill = colors.HexColor("#f0dcd8")
    edge_color = colors.HexColor("#c0c8d0")

    # Fill triangles
    for shape, side, A, B, C in tris:
        fill = kite_fill if shape == "A" else dart_fill
        p = canvas.beginPath()
        p.moveTo(A[0], A[1])
        p.lineTo(B[0], B[1])
        p.lineTo(C[0], C[1])
        p.close()
        canvas.setFillColor(fill)
        canvas.setStrokeColor(fill)
        canvas.drawPath(p, fill=1, stroke=0)

    # Classify edges to skip axis edges (internal to kite/dart pairs)
    edge_info = {}
    for shape, side, A, B, C in tris:
        axis_edge = (A, B) if side == "F" else (A, C)
        axis_key = _ekey(axis_edge[0], axis_edge[1])
        for p_pt, q_pt in [(A, B), (A, C), (B, C)]:
            k = _ekey(p_pt, q_pt)
            if k not in edge_info:
                edge_info[k] = {"axis": 0, "verts": (p_pt, q_pt)}
            if k == axis_key:
                edge_info[k]["axis"] += 1

    # Draw tile boundary edges only
    canvas.setStrokeColor(edge_color)
    canvas.setLineWidth(0.5)
    for info in edge_info.values():
        if info["axis"] >= 2:
            continue
        p_pt, q_pt = info["verts"]
        canvas.line(p_pt[0], p_pt[1], q_pt[0], q_pt[1])

    canvas.restoreState()
    _draw_victorian_border(canvas, doc)


# ── Victorian wrought-iron border ──────────────────────────────────

def _draw_volute_pair_h(canvas, x1, x2, y_outer, y_inner, stroke_color):
    """Draw a facing volute pair between two bars on a horizontal edge.

    Each volute is a 3-segment bezier spiral: drops from the outer rail
    toward the inner rail, sweeps across, then curls back — like a "6"
    or "9" shape matching wrought-iron fence scrollwork.
    """
    canvas.setStrokeColor(stroke_color)
    canvas.setLineWidth(2.0)

    sw = x2 - x1
    dy = y_inner - y_outer  # signed direction toward inner rail

    # Left volute: starts at bar near outer rail, spirals inward
    p = canvas.beginPath()
    p.moveTo(x1 + sw * 0.04, y_outer + dy * 0.05)
    # Seg 1: drop toward inner rail
    p.curveTo(x1 + sw * 0.04, y_outer + dy * 0.65,
              x1 + sw * 0.12, y_outer + dy * 0.95,
              x1 + sw * 0.30, y_outer + dy * 0.90)
    # Seg 2: sweep right, curve back toward outer rail
    p.curveTo(x1 + sw * 0.45, y_outer + dy * 0.85,
              x1 + sw * 0.48, y_outer + dy * 0.45,
              x1 + sw * 0.40, y_outer + dy * 0.30)
    # Seg 3: tight inward curl
    p.curveTo(x1 + sw * 0.35, y_outer + dy * 0.20,
              x1 + sw * 0.28, y_outer + dy * 0.35,
              x1 + sw * 0.33, y_outer + dy * 0.48)
    canvas.drawPath(p, fill=0, stroke=1)

    # Right volute (mirror)
    p = canvas.beginPath()
    p.moveTo(x2 - sw * 0.04, y_outer + dy * 0.05)
    p.curveTo(x2 - sw * 0.04, y_outer + dy * 0.65,
              x2 - sw * 0.12, y_outer + dy * 0.95,
              x2 - sw * 0.30, y_outer + dy * 0.90)
    p.curveTo(x2 - sw * 0.45, y_outer + dy * 0.85,
              x2 - sw * 0.48, y_outer + dy * 0.45,
              x2 - sw * 0.40, y_outer + dy * 0.30)
    p.curveTo(x2 - sw * 0.35, y_outer + dy * 0.20,
              x2 - sw * 0.28, y_outer + dy * 0.35,
              x2 - sw * 0.33, y_outer + dy * 0.48)
    canvas.drawPath(p, fill=0, stroke=1)


def _draw_volute_pair_v(canvas, y1, y2, x_inner, x_outer, stroke_color):
    """Draw a facing volute pair between two bars on a vertical edge."""
    canvas.setStrokeColor(stroke_color)
    canvas.setLineWidth(2.0)

    sh = y2 - y1
    dx = x_inner - x_outer  # signed direction toward inner rail

    # Bottom volute
    p = canvas.beginPath()
    p.moveTo(x_outer + dx * 0.05, y1 + sh * 0.04)
    p.curveTo(x_outer + dx * 0.65, y1 + sh * 0.04,
              x_outer + dx * 0.95, y1 + sh * 0.12,
              x_outer + dx * 0.90, y1 + sh * 0.30)
    p.curveTo(x_outer + dx * 0.85, y1 + sh * 0.45,
              x_outer + dx * 0.45, y1 + sh * 0.48,
              x_outer + dx * 0.30, y1 + sh * 0.40)
    p.curveTo(x_outer + dx * 0.20, y1 + sh * 0.35,
              x_outer + dx * 0.35, y1 + sh * 0.28,
              x_outer + dx * 0.48, y1 + sh * 0.33)
    canvas.drawPath(p, fill=0, stroke=1)

    # Top volute (mirror)
    p = canvas.beginPath()
    p.moveTo(x_outer + dx * 0.05, y2 - sh * 0.04)
    p.curveTo(x_outer + dx * 0.65, y2 - sh * 0.04,
              x_outer + dx * 0.95, y2 - sh * 0.12,
              x_outer + dx * 0.90, y2 - sh * 0.30)
    p.curveTo(x_outer + dx * 0.85, y2 - sh * 0.45,
              x_outer + dx * 0.45, y2 - sh * 0.48,
              x_outer + dx * 0.30, y2 - sh * 0.40)
    p.curveTo(x_outer + dx * 0.20, y2 - sh * 0.35,
              x_outer + dx * 0.35, y2 - sh * 0.28,
              x_outer + dx * 0.48, y2 - sh * 0.33)
    canvas.drawPath(p, fill=0, stroke=1)


def _draw_victorian_border(canvas, _doc):
    """Draw a Victorian wrought-iron border with volute scrollwork."""
    w, h = WIDTH, HEIGHT
    canvas.saveState()

    iron = colors.HexColor("#1a1a1a")
    iron_fill = colors.HexColor("#222222")

    # Frame geometry
    out = 11 * mm
    inn = 18 * mm
    band = inn - out        # 7 mm decorative band

    # ── Rails (double frame) ──
    canvas.setStrokeColor(iron)
    canvas.setLineWidth(2.0)
    canvas.rect(out, out, w - 2 * out, h - 2 * out)
    canvas.setLineWidth(0.75)
    canvas.rect(inn, inn, w - 2 * inn, h - 2 * inn)

    # ── Corner rosettes ──
    for cx, cy in [(out, out), (w - out, out),
                   (out, h - out), (w - out, h - out)]:
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(iron)
        canvas.setLineWidth(1.5)
        canvas.circle(cx, cy, band * 0.45, fill=1, stroke=1)
        canvas.setFillColor(iron_fill)
        canvas.circle(cx, cy, band * 0.15, fill=1, stroke=0)

    # ── Bar positions ──
    pad = band * 0.5 + 2 * mm

    h_start = out + pad
    h_end = w - out - pad
    h_span = h_end - h_start
    n_h = max(3, round(h_span / (24 * mm)))
    n_h = n_h | 1
    h_step = h_span / (n_h - 1)

    v_start = out + pad
    v_end = h - out - pad
    v_span = v_end - v_start
    n_v = max(3, round(v_span / (24 * mm)))
    n_v = n_v | 1
    v_step = v_span / (n_v - 1)

    def _draw_edge_bars_h(y_out, y_inn):
        canvas.setStrokeColor(iron)
        for i in range(n_h):
            bx = h_start + i * h_step
            canvas.setLineWidth(1.5)
            canvas.line(bx, y_out, bx, y_inn)
        for i in range(n_h - 1):
            _draw_volute_pair_h(canvas,
                                h_start + i * h_step,
                                h_start + (i + 1) * h_step,
                                y_out, y_inn, iron)

    def _draw_edge_bars_v(x_out, x_inn):
        canvas.setStrokeColor(iron)
        for i in range(n_v):
            by = v_start + i * v_step
            canvas.setLineWidth(1.5)
            canvas.line(x_out, by, x_inn, by)
        for i in range(n_v - 1):
            _draw_volute_pair_v(canvas,
                                v_start + i * v_step,
                                v_start + (i + 1) * v_step,
                                x_inn, x_out, iron)

    _draw_edge_bars_h(h - out, h - inn)   # top
    _draw_edge_bars_h(out, inn)            # bottom
    _draw_edge_bars_v(out, inn)            # left
    _draw_edge_bars_v(w - out, w - inn)    # right

    canvas.restoreState()


# ── Company overview (role-agnostic) ──────────────────────────────

COMPANY_OVERVIEW = """\
The company builds AI governance tools for supply chains. We help enterprises \
ensure their AI systems are transparent, auditable, and compliant — from \
procurement to production.

We are a small, research-driven team that values rigour, honesty, and \
creative problem-solving. We use formal methods (including Lean), agentic \
AI engineering, and deep domain expertise to build things that matter.

We are not a typical tech company. We value non-traditional backgrounds, \
diverse perspectives, and people who think differently. If you've taken \
an unconventional path to get here — good. That's what we're looking for.
"""

# ── Role descriptions ─────────────────────────────────────────────

ROLE_DESCRIPTIONS: dict[str, str] = {
    "sales": """\
<b>Role: Enterprise Sales</b>

You'll be our first dedicated salesperson. You'll own the full sales cycle — \
from identifying prospects in supply chain and compliance teams, to closing \
enterprise deals. This is a consultative sale: you'll need to understand both \
the technology and the regulatory landscape well enough to have real \
conversations with CISOs, compliance officers, and supply chain directors.

We're looking for someone who can sell a complex product to cautious buyers \
in regulated industries. Long sales cycles don't scare you — you see them \
as relationship-building opportunities.
""",
    "marketing": """\
<b>Role: Marketing</b>

You'll shape how the world understands AI governance for supply chains. \
That means creating compelling content — blog posts, whitepapers, case studies \
— that translates deep technical concepts for non-technical decision-makers. \
You'll build our presence at conferences, on LinkedIn, and through thought \
leadership.

We need someone who can write clearly about complex topics, who understands \
B2B SaaS marketing, and who gets energised by building a brand from scratch.
""",
    "customer_relations": """\
<b>Role: Customer Relations</b>

You'll be the primary relationship owner for our enterprise customers. \
Onboarding in our space is complex — multi-stakeholder, highly regulated, \
and technically nuanced. You'll guide customers from signing to value \
realisation, making sure they actually use the product to improve their \
AI governance posture.

We need someone who genuinely cares about customer outcomes, who can \
navigate enterprise politics, and who sees renewals as proof of impact.
""",
    "partnerships": """\
<b>Role: Business Development / Partnerships</b>

You'll build the ecosystem around our product — integration partnerships \
with ERP vendors, co-marketing with GRC platforms, channel partnerships \
with consultancies. Supply chain AI governance doesn't exist in isolation; \
you'll connect us to the broader ecosystem.

We need someone who thinks in terms of ecosystem value, not just deal flow. \
You understand that the best partnerships create value for everyone involved.
""",
    "domain_expert": """\
<b>Role: Domain Expert — AI Governance & Supply Chains</b>

You'll be our bridge between technology and industry. You know supply chains \
from the inside — procurement, logistics, compliance, risk management — and \
you understand how AI is changing them. You'll advise on product direction, \
help customers apply our tools, and represent us at industry events.

We need someone who is credible in the room with both engineers and supply \
chain directors. Academic credentials are fine, but practitioner experience \
matters more.
""",
    "product": """\
<b>Role: Product Manager</b>

You'll own the product roadmap for our AI governance platform. That means \
deeply understanding what compliance officers and supply chain managers \
actually need (not just what they say they need), translating those needs \
into features, and working with a small engineering team to ship them.

We need someone who can hold the tension between technical possibility \
and user need, who writes clear specs, and who isn't afraid to say "no" \
to features that don't serve the mission.
""",
    "technical": """\
<b>Role: Technical — Engineering / Research</b>

You'll build the core platform. Our stack includes formal verification \
(Lean), agentic AI systems, and supply chain domain models. Depending on \
your strengths, you might work on proof engineering, ML pipelines, backend \
infrastructure, or all three.

We value depth over breadth, rigour over speed, and working code over \
slide decks. If you have an unusual technical background — mathematics, \
philosophy, linguistics — that's a plus, not a minus.
""",
}

DEFAULT_ROLE_DESCRIPTION = """\
<b>Role: Open Application</b>

We're a small team and we don't always know what we need until we find \
the right person. If you're drawn to AI governance, supply chains, or \
formal methods — and you think you could contribute in a way we haven't \
imagined — we want to hear from you.
"""

# ── Personality-fit questions ─────────────────────────────────────

PERSONALITY_QUESTIONS = [
    (
        "What are you passionate about?",
        "This can be professional, personal, or both. We're interested in "
        "what genuinely drives you — not what you think we want to hear.",
    ),
    (
        "What do you enjoy doing?",
        "What kind of work puts you in flow? When do you lose track of time?",
    ),
    (
        "How do you think you can contribute to our mission?",
        "We're building AI governance for supply chains. What do you bring "
        "that we probably don't have?",
    ),
    (
        "What do you want to learn?",
        "What skills, domains, or ways of thinking are you actively trying "
        "to develop?",
    ),
    (
        "What skills do you want to develop in this role?",
        "We invest in people. Tell us where you want to grow.",
    ),
    (
        "How do you work with others?",
        "Describe a time you collaborated on something difficult. "
        "What was your role? What did you learn about yourself?",
    ),
    (
        "What is your communication style?",
        "Do you think out loud or process internally? Do you prefer written "
        "or verbal? Direct or diplomatic? There's no right answer.",
    ),
    (
        "What motivates you?",
        "What makes you want to do excellent work — not just adequate work?",
    ),
    (
        "What makes you unique and different?",
        "What perspective, experience, or way of thinking do you have that "
        "most people in your field don't?",
    ),
    (
        "What's the biggest difficulty you've overcome in your life?",
        "Professional or personal. We ask because resilience and "
        "self-awareness matter more to us than a smooth career arc.",
    ),
    (
        "How would you describe your personality — honestly?",
        "Not your LinkedIn summary. The real you. Strengths, quirks, "
        "rough edges and all.",
    ),
]


# ── PDF generation ────────────────────────────────────────────────

def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "LetterTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1a237e"),
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        textColor=colors.HexColor("#37474f"),
    ))
    styles.add(ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=15,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a237e"),
        spaceBefore=4 * mm,
        spaceAfter=1 * mm,
    ))
    styles.add(ParagraphStyle(
        "QuestionHint",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#616161"),
        leftIndent=6,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#9e9e9e"),
        alignment=1,
    ))
    return styles


def generate_offer_letter(
    dossiers: list[Dossier],
    role: str = "technical",
    output_path: str | Path | None = None,
) -> Path:
    """Generate offer letter PDFs for a list of candidates.

    One letter per candidate, personalised with their name.
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = (
            Path(__file__).parent.parent / "data" / f"offer_letters_{timestamp}.pdf"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)

    styles = _build_styles()
    role_desc = ROLE_DESCRIPTIONS.get(role, DEFAULT_ROLE_DESCRIPTION)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    elements = []

    for i, dossier in enumerate(dossiers):
        role_title = role_desc.split("</b>")[0].replace("<b>", "").strip()
        name = (
            dossier.profile.name
            or dossier.keys.name
            or "Candidate"
        )

        # Header
        elements.append(Spacer(1, 1 * cm))
        elements.append(Paragraph(
            f"Hello, {name}",
            styles["LetterTitle"],
        ))
        elements.append(Paragraph(
            f"We are currently hiring for the {role_title} "
            f"and you have caught our eye.",
            styles["Body"],
        ))

        # Company overview
        elements.append(Paragraph("About Us", styles["SectionHead"]))
        for para in COMPANY_OVERVIEW.strip().split("\n\n"):
            elements.append(Paragraph(para.strip(), styles["Body"]))

        # Role description
        elements.append(Paragraph("The Role", styles["SectionHead"]))
        for para in role_desc.strip().split("\n\n"):
            elements.append(Paragraph(para.strip(), styles["Body"]))

        # Personality-fit questions
        elements.append(PageBreak())
        elements.append(Spacer(1, 5 * mm))
        elements.append(Paragraph(
            "Getting to Know You",
            styles["SectionHead"],
        ))
        elements.append(Paragraph(
            "We care more about who you are than what's on your CV. "
            "Please answer these questions in whatever format feels natural "
            "— bullet points, paragraphs, voice memo, video, whatever works "
            "for you. There are no right answers.",
            styles["Body"],
        ))

        for q_num, (question, hint) in enumerate(PERSONALITY_QUESTIONS, 1):
            elements.append(Paragraph(
                f"{q_num}. {question}",
                styles["Question"],
            ))
            elements.append(Paragraph(hint, styles["QuestionHint"]))

        # Footer
        elements.append(Spacer(1, 1 * cm))
        elements.append(Paragraph(
            f"Generated {datetime.now().strftime('%d %B %Y')} · "
            f"Confidential",
            styles["Footer"],
        ))

        if i < len(dossiers) - 1:
            elements.append(PageBreak())

    doc.build(
        elements,
        onFirstPage=_draw_penrose_background,
        onLaterPages=_draw_penrose_background,
    )
    return output_path
