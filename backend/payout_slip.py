"""Slip payout PDF untuk kreator (reportlab), meniru tata letak slip Pathway;
hanya kopnya yang berbeda.

Modul ini hanya tata letak: semua teks sudah diformat pemanggil
(main.payout_slip_pdf). Per konten slip menampilkan rantai perhitungan
seperti slip Pathway: Total Revenues (net80, sudah dipotong Pathway 20%),
PayPal Fee, Creator Split, Product Total. Aturan "kreator tidak melihat net"
hanya untuk dashboard/API kreator, tidak untuk slip ini. Gross dan bagian
Squareclouds tetap tidak pernah ditampilkan sebagai baris.

Label berbahasa Inggris (seperti slip Pathway); tanggal dan nama bulan tetap
format Indonesia. Font Helvetica bawaan reportlab, A4, margin 40pt.
"""
import io
from dataclasses import dataclass
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Salinan frontend/public/FLBT.png (logo dengan tulisan), diperkecil.
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"
LOGO_HEIGHT = 22 * mm
# Lebih dari ini (baris tabel), tabel lanjut ke halaman berikut dengan header
# diulang. Blok satu konten tidak pernah dipecah ke dua halaman.
ROWS_PER_PAGE = 30
NO_ITEMS = "No per-content breakdown is available for this payout."


@dataclass
class SlipItem:
    """Blok satu konten di tabel."""
    content: str                    # "Royal Mansion (1.585 units)"
    # Baris (Comment, Price) sebelum Product Total, mis. [("Total Revenues",
    # "$950.99"), ("PayPal Fee 5.00%", "-$47.55"), ("Creator Split 20.00%",
    # "$180.69")]. Kosong = item lama tanpa rantai perhitungan.
    lines: list[tuple[str, str]]
    product_total: str              # "$180.69" = share_usd


@dataclass
class SlipData:
    title: str                      # judul dokumen PDF = nama file tanpa .pdf
    created_on: str                 # tanggal bayar, "7 November 2026"
    revenue_month: str              # "Agustus 2026"; "-" untuk payout lama
    sender: list[str]               # kiri: nama studio, email, alamat (maks 3 baris)
    recipient: list[str]            # kanan: nama, "<username> - Squareclouds Studio", email
    items: list[SlipItem]           # kosong = payout lama tanpa rincian
    total_usd: str                  # Subtotal = Total = Σ Product Total
    exchange_rate: str | None       # "Rp16.500,00/$", hanya payout non-PayPal
    total_idr: str | None
    note: str | None


def _block_rows(item: SlipItem) -> int:
    return len(item.lines) + 1


INK = colors.HexColor("#333333")
MUTED = colors.HexColor("#777777")
LINE = colors.HexColor("#dddddd")
ALT_BG = colors.HexColor("#f6f6f6")

BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12, textColor=INK)
BOLD = ParagraphStyle("bold", parent=BASE, fontName="Helvetica-Bold")
CENTER = ParagraphStyle("center", parent=BASE, alignment=TA_CENTER)
CENTER_BOLD = ParagraphStyle("center_bold", parent=BOLD, alignment=TA_CENTER)
RIGHT = ParagraphStyle("right", parent=BASE, alignment=TA_RIGHT)
RIGHT_BOLD = ParagraphStyle("right_bold", parent=BOLD, alignment=TA_RIGHT)
HEADER_RIGHT = ParagraphStyle("header_right", parent=RIGHT_BOLD, fontSize=9, leading=13)
TOTAL = ParagraphStyle("total", parent=RIGHT_BOLD, fontSize=11.5, leading=15)
SMALL_RIGHT = ParagraphStyle("small_right", parent=RIGHT, fontSize=8.5, leading=11)
SMALL = ParagraphStyle("small", parent=BASE, fontSize=8.5, leading=11)
MUTED_TEXT = ParagraphStyle("muted", parent=BASE, textColor=MUTED)
COMPANY = ParagraphStyle("company", parent=BOLD, fontSize=16, leading=20)

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40  # pt
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
COL_WIDTHS = [CONTENT_WIDTH * 0.5, CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.25]


def _p(text: str, style: ParagraphStyle = BASE) -> Paragraph:
    # Paragraph memakai markup mini-HTML: teks dari pengguna (nama konten,
    # catatan, alamat) di-escape dulu.
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _logo():
    if not LOGO_PATH.is_file():
        return _p("Squareclouds Studio", COMPANY)
    width, height = ImageReader(str(LOGO_PATH)).getSize()
    return Image(str(LOGO_PATH), width=LOGO_HEIGHT * width / height, height=LOGO_HEIGHT, mask="auto")


def _layout_table(rows, col_widths, valign="TOP") -> Table:
    """Tabel tanpa garis/padding samping, hanya untuk menyusun kolom."""
    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), valign),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _header(data: SlipData) -> Table:
    dates = [
        _p(f"Created On: {data.created_on}", HEADER_RIGHT),
        _p(f"Revenue Month: {data.revenue_month}", HEADER_RIGHT),
    ]
    return _layout_table([[_logo(), dates]], [CONTENT_WIDTH * 0.6, CONTENT_WIDTH * 0.4])


def _identity(data: SlipData) -> Table:
    sender = [_p(line) for line in data.sender]
    recipient = [_p(line, RIGHT) for line in data.recipient]
    return _layout_table([[sender, recipient]], [CONTENT_WIDTH / 2] * 2)


def _chunks(items: list[SlipItem]) -> list[list[SlipItem]]:
    """Bagi blok konten per halaman: maksimal ROWS_PER_PAGE baris, blok utuh."""
    chunks, current, rows = [], [], 0
    for item in items:
        if current and rows + _block_rows(item) > ROWS_PER_PAGE:
            chunks.append(current)
            current, rows = [], 0
        current.append(item)
        rows += _block_rows(item)
    return chunks + [current] if current else chunks or [[]]


def _items_table(chunk: list[SlipItem]) -> Table:
    rows = [[_p("Content", BOLD), _p("Comment", CENTER_BOLD), _p("Price", RIGHT_BOLD)]]
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for item in chunk:
        first = len(rows)
        # Baris pertama blok berlatar abu muda (seperti Pathway): nama konten
        # + baris pertama rantai (atau langsung Product Total untuk item lama).
        for index, (comment, price) in enumerate(item.lines):
            rows.append([_p(item.content) if index == 0 else "", _p(comment, CENTER), _p(price, RIGHT)])
        rows.append([
            "" if item.lines else _p(item.content),
            _p("Product Total", CENTER_BOLD),
            _p(item.product_total, RIGHT_BOLD),
        ])
        style += [
            ("BACKGROUND", (0, first), (-1, first), ALT_BG),
            ("LINEBELOW", (0, len(rows) - 1), (-1, len(rows) - 1), 0.5, LINE),
        ]
    if not chunk:
        rows.append([_p(NO_ITEMS, MUTED_TEXT), "", ""])
        style += [("SPAN", (0, 1), (-1, 1)), ("LINEBELOW", (0, 1), (-1, 1), 0.5, LINE)]
    # repeatRows: kalau satu potongan tetap tidak muat (nama konten panjang
    # yang terlipat), reportlab memecahnya dan mengulang header.
    table = Table(rows, colWidths=COL_WIDTHS, repeatRows=1)
    table.setStyle(TableStyle(style))
    return table


def _totals(data: SlipData) -> KeepTogether:
    parts = [
        Spacer(1, 3 * mm),
        _p(f"Subtotal: {data.total_usd}", RIGHT_BOLD),
        HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=4),
        _p(f"Total: {data.total_usd}", TOTAL),
    ]
    if data.exchange_rate and data.total_idr:
        parts += [
            Spacer(1, 1.5 * mm),
            _p(f"Exchange Rate: {data.exchange_rate}", SMALL_RIGHT),
            _p(f"Total (IDR): {data.total_idr}", SMALL_RIGHT),
        ]
    return KeepTogether(parts)


def render(data: SlipData) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=data.title,
        author="Squareclouds Studio",
        creator="Creator Portal Squareclouds Studio",
    )
    story = [_header(data), Spacer(1, 9 * mm), _identity(data), Spacer(1, 9 * mm)]
    for index, chunk in enumerate(_chunks(data.items)):
        if index:
            story.append(PageBreak())
        story.append(_items_table(chunk))
    story.append(_totals(data))
    if data.note:
        story += [Spacer(1, 6 * mm), _p(f"Note: {data.note}", SMALL)]
    doc.build(story)
    return buffer.getvalue()
