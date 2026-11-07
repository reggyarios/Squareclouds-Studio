"""Slip payout PDF untuk kreator (reportlab), gaya slip Pathway.

Modul ini hanya tata letak: semua teks sudah diformat pemanggil
(main.payout_slip_pdf). Slip dikirim ke kreator, jadi isinya hanya unit dan
bagian kreator. Tidak ada gross, net, fee PayPal, split %, maupun bagian
Squareclouds; jangan tambahkan field seperti itu ke SlipData.

Label berbahasa Inggris (seperti slip Pathway); tanggal dan nama bulan tetap
format Indonesia. Font Helvetica bawaan reportlab.
"""
import io
from dataclasses import dataclass
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Salinan frontend/public/FLBT.png (logo dengan tulisan), diperkecil.
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"
LOGO_HEIGHT = 18 * mm
# Lebih dari ini, tabel lanjut ke halaman berikut dengan header diulang.
ITEMS_PER_PAGE = 25
NO_ITEMS = "No per-content breakdown is available for this payout."


@dataclass
class SlipData:
    title: str                          # judul dokumen PDF = nama file tanpa .pdf
    created_on: str                     # tanggal bayar, "3 November 2026"
    revenue_month: str                  # "Oktober 2026"; "-" untuk payout lama
    sender: list[str]                   # baris blok pengirim (kiri)
    recipient: list[str]                # baris blok penerima (kanan): nama, username, email, tujuan termask
    items: list[tuple[str, str, str]]   # (konten, unit terjual, USD); kosong = payout lama
    total_units: str | None             # None kalau tidak ada rincian
    total_usd: str
    exchange_rate: str | None           # "Rp16.500,00/$", hanya payout non-PayPal
    total_idr: str | None
    note: str | None
    footer: str


INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#e5e7eb")
HEAD_BG = colors.HexColor("#eceff3")
ALT_BG = colors.HexColor("#f8f9fb")

BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=12, textColor=INK)
BOLD = ParagraphStyle("bold", parent=BASE, fontName="Helvetica-Bold")
RIGHT = ParagraphStyle("right", parent=BASE, alignment=TA_RIGHT)
RIGHT_BOLD = ParagraphStyle("right_bold", parent=BOLD, alignment=TA_RIGHT)
MUTED_TEXT = ParagraphStyle("muted", parent=BASE, textColor=MUTED)
HEADER_RIGHT = ParagraphStyle("header_right", parent=RIGHT_BOLD, fontSize=11, leading=15)
COMPANY = ParagraphStyle("company", parent=BOLD, fontSize=16, leading=20)

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 18 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
COL_WIDTHS = [CONTENT_WIDTH - 70 * mm, 30 * mm, 40 * mm]


def _p(text: str, style: ParagraphStyle = BASE) -> Paragraph:
    # Paragraph memakai markup mini-HTML: teks dari pengguna (nama konten,
    # catatan, alamat) di-escape dulu.
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _logo():
    if not LOGO_PATH.is_file():
        return _p("Squareclouds Studio", COMPANY)
    width, height = ImageReader(str(LOGO_PATH)).getSize()
    return Image(str(LOGO_PATH), width=LOGO_HEIGHT * width / height, height=LOGO_HEIGHT, mask="auto")


def _header(data: SlipData) -> Table:
    right = [
        _p(f"Created On: {data.created_on}", HEADER_RIGHT),
        _p(f"Revenue Month: {data.revenue_month}", HEADER_RIGHT),
    ]
    table = Table([[_logo(), right]], colWidths=[CONTENT_WIDTH * 0.55, CONTENT_WIDTH * 0.45])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, LINE),
    ]))
    return table


def _identity(data: SlipData) -> Table:
    def block(lines: list[str], first: ParagraphStyle, rest: ParagraphStyle) -> list[Paragraph]:
        return [_p(line, first if i == 0 else rest) for i, line in enumerate(lines)]

    table = Table(
        [[block(data.sender, BOLD, BASE), block(data.recipient, RIGHT_BOLD, RIGHT)]],
        colWidths=[CONTENT_WIDTH / 2] * 2,
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _items_table(data: SlipData, start: int, chunk: list[tuple[str, str, str]], last: bool) -> Table:
    rows = [[_p("Content", BOLD), _p("Units Sold", RIGHT_BOLD), _p("Earnings (USD)", RIGHT_BOLD)]]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if chunk:
        for offset, (name, units, amount) in enumerate(chunk):
            rows.append([_p(name), _p(units, RIGHT), _p(amount, RIGHT)])
            # Selang-seling dihitung dari nomor item global, jadi tetap
            # berurutan di halaman berikutnya.
            if (start + offset) % 2 == 1:
                style.append(("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), ALT_BG))
    else:
        rows.append([_p(NO_ITEMS, MUTED_TEXT), "", ""])
        style.append(("SPAN", (0, 1), (-1, 1)))

    if last:
        total_row = len(rows)
        rows.append([_p("Total (USD)", BOLD), _p(data.total_units or "", RIGHT_BOLD), _p(data.total_usd, RIGHT_BOLD)])
        style.append(("LINEABOVE", (0, total_row), (-1, total_row), 1, INK))
        if data.exchange_rate and data.total_idr:
            rows.append([_p("Exchange Rate", MUTED_TEXT), "", _p(data.exchange_rate, RIGHT)])
            rows.append([_p("Total (IDR)", BOLD), "", _p(data.total_idr, RIGHT_BOLD)])

    # repeatRows: kalau satu potongan tetap tidak muat (nama konten panjang
    # yang terlipat), reportlab memecahnya dan mengulang header.
    table = Table(rows, colWidths=COL_WIDTHS, repeatRows=1)
    table.setStyle(TableStyle(style))
    return table


def render(data: SlipData) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 4 * mm,
        title=data.title,
        author="Squareclouds Studio",
        creator="Creator Portal Squareclouds Studio",
    )

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(PAGE_WIDTH / 2, 10 * mm, data.footer)
        canvas.restoreState()

    story = [_header(data), Spacer(1, 8 * mm), _identity(data), Spacer(1, 8 * mm)]
    chunks = [data.items[i:i + ITEMS_PER_PAGE] for i in range(0, len(data.items), ITEMS_PER_PAGE)] or [[]]
    for index, chunk in enumerate(chunks):
        if index:
            story.append(PageBreak())
        last = index == len(chunks) - 1
        story.append(_items_table(data, index * ITEMS_PER_PAGE, chunk, last))
    if data.note:
        story += [Spacer(1, 5 * mm), _p("Note", BOLD), _p(data.note)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
