"""Slip payout PDF untuk kreator (reportlab), meniru tata letak slip Pathway;
hanya kopnya yang berbeda.

Modul ini hanya tata letak: semua teks sudah diformat pemanggil
(main.payout_slip_pdf). Slip dikirim ke kreator, jadi isinya hanya bagian
kreator per konten. Tidak ada unit, gross, net, fee PayPal, split %, bagian
Squareclouds, maupun potongan apa pun; jangan tambahkan field seperti itu ke
SlipData.

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
# Lebih dari ini, tabel lanjut ke halaman berikut dengan header diulang.
ITEMS_PER_PAGE = 30
COMMENT = "Creator Earnings"
NO_ITEMS = "No per-content breakdown is available for this payout."


@dataclass
class SlipData:
    title: str                      # judul dokumen PDF = nama file tanpa .pdf
    created_on: str                 # tanggal bayar, "7 November 2026"
    revenue_month: str              # "Agustus 2026"; "-" untuk payout lama
    sender: list[str]               # kiri: nama studio, email, alamat (maks 3 baris)
    recipient: list[str]            # kanan: nama, "<username> - Squareclouds Studio", email
    items: list[tuple[str, str]]    # (konten, "$22.80"); kosong = payout lama tanpa rincian
    total_usd: str                  # Subtotal = Total (tidak ada potongan)
    exchange_rate: str | None       # "Rp16.500,00/$", hanya payout non-PayPal
    total_idr: str | None
    note: str | None


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


def _items_table(start: int, chunk: list[tuple[str, str]]) -> Table:
    rows = [[_p("Content", BOLD), _p("Comment", CENTER_BOLD), _p("Price", RIGHT_BOLD)]]
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
    ]
    if chunk:
        for offset, (name, amount) in enumerate(chunk):
            rows.append([_p(name), _p(COMMENT, CENTER), _p(amount, RIGHT)])
            # Selang-seling dihitung dari nomor item global, jadi tetap
            # berurutan di halaman berikutnya.
            if (start + offset) % 2 == 1:
                style.append(("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), ALT_BG))
    else:
        rows.append([_p(NO_ITEMS, MUTED_TEXT), "", ""])
        style.append(("SPAN", (0, 1), (-1, 1)))
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
    chunks = [data.items[i:i + ITEMS_PER_PAGE] for i in range(0, len(data.items), ITEMS_PER_PAGE)] or [[]]
    for index, chunk in enumerate(chunks):
        if index:
            story.append(PageBreak())
        story.append(_items_table(index * ITEMS_PER_PAGE, chunk))
    story.append(_totals(data))
    if data.note:
        story += [Spacer(1, 6 * mm), _p(f"Note: {data.note}", SMALL)]
    doc.build(story)
    return buffer.getvalue()
