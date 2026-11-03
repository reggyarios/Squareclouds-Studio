"""Bot sinkronisasi Pathway Creators -> database SquareClouds.

Apa yang dilakukan (sekali jalan, lalu selesai):
  1. Login ke creators.pathway.studio dengan PATHWAY_USERNAME / PATHWAY_PASSWORD (.env).
  2. Baca katalog offer dari /dashboard/offers (5 tab: In Development, Review,
     Submissions, Pending Release, Published): judul, status, pack type, tier.
  3. Baca penjualan harian per produk dari /dashboard/sales dengan menyadap
     response halaman itu sendiri (tidak meniru request internal Pathway).
  4. Upsert ke tabel contents (kunci: pathway_product_id, fallback nama) dan
     daily_sales (kunci: tanggal + content_id). Unit disimpan apa adanya.

Pemakaian (dari folder backend, venv aktif):
  venv/bin/python pathway_bot.py                 # sinkron 90 hari terakhir
  venv/bin/python pathway_bot.py --full          # sinkron seluruh riwayat (run pertama)
  venv/bin/python pathway_bot.py --dry-run       # tampilkan hasil, DB tidak disentuh
  venv/bin/python pathway_bot.py --debug         # simpan screenshot + HTML ke debug_pathway/

Instalasi sekali:
  venv/bin/pip install playwright
  venv/bin/playwright install --with-deps chromium
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

BASE = os.getenv("PATHWAY_BASE", "https://creators.pathway.studio").rstrip("/")
USERNAME = os.getenv("PATHWAY_USERNAME")
PASSWORD = os.getenv("PATHWAY_PASSWORD")

OFFER_TABS = ["In Development", "Review", "Submissions", "Pending Release", "Published"]

# Harga per tier (dipakai hanya untuk konten yang belum punya penjualan).
TIER_PRICE = {
    1: 0.37, 2: 0.74, 3: 1.12, 4: 1.49, 5: 1.87, 6: 2.24, 7: 2.62, 8: 2.99,
    9: 3.37, 10: 3.74, 11: 4.12, 12: 4.49, 13: 4.87, 14: 5.24, 15: 5.62,
    16: 5.99, 17: 6.37, 18: 6.74, 19: 7.12,
}

DEBUG_DIR = BACKEND / "debug_pathway"
_debug = False
_shot = 0


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def dump(page, name: str, html_selector: str | None = None) -> None:
    """Simpan screenshot (+ potongan HTML) saat --debug."""
    global _shot
    if not _debug:
        return
    DEBUG_DIR.mkdir(exist_ok=True)
    _shot += 1
    base = DEBUG_DIR / f"{_shot:02d}-{name}"
    try:
        page.screenshot(path=f"{base}.png", full_page=True)
        html = page.locator(html_selector).first.inner_html() if html_selector else page.content()
        Path(f"{base}.html").write_text(html, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log(f"  (debug dump gagal: {e})")


# ---------------------------------------------------------------------------
# Parsing response Server Action Next.js: baris "N:{json}"
# ---------------------------------------------------------------------------
def parse_action_body(body: str) -> list[dict]:
    out = []
    for line in body.splitlines():
        m = re.match(r"^\d+:(\{.*\})$", line)
        if not m:
            continue
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def login(page) -> None:
    if not USERNAME or not PASSWORD:
        sys.exit("PATHWAY_USERNAME / PATHWAY_PASSWORD belum ada di .env")
    log("Login ke Pathway...")
    page.goto(BASE + "/", wait_until="networkidle")
    dump(page, "login-page")

    user_box = page.get_by_label(re.compile("username", re.I))
    if user_box.count() == 0:
        user_box = page.locator("input:not([type=password])").first
    user_box.fill(USERNAME)
    page.locator("input[type=password]").first.fill(PASSWORD)
    page.get_by_role("button", name=re.compile(r"sign in", re.I)).click()
    page.wait_for_url(re.compile(r"/dashboard"), timeout=30_000)
    page.wait_for_load_state("networkidle")
    log("Login OK.")
    dump(page, "after-login")


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------
def _cell_lines(cell) -> list[str]:
    return [s.strip() for s in cell.inner_text().split("\n") if s.strip()]


def scrape_offers(page) -> list[dict]:
    log("Membaca halaman Offers...")
    page.goto(BASE + "/dashboard/offers", wait_until="networkidle")
    dump(page, "offers")
    offers: list[dict] = []

    for tab in OFFER_TABS:
        tab_el = page.get_by_role("tab", name=re.compile(rf"^{re.escape(tab)}"))
        if tab_el.count() == 0:
            tab_el = page.get_by_text(re.compile(rf"^{re.escape(tab)}\s*\d*$")).first
        tab_el.click()
        page.wait_for_timeout(600)
        dump(page, f"offers-{tab.lower().replace(' ', '-')}", "table")

        table = page.locator("table").first
        if table.count() == 0:
            log(f"  {tab}: tabel tidak ditemukan")
            continue
        headers = [h.strip().upper() for h in table.locator("thead th").all_inner_texts()]
        rows = table.locator("tbody tr")
        n = rows.count()
        log(f"  {tab}: {n} baris")

        def col(name: str) -> int | None:
            for i, h in enumerate(headers):
                if name in h:
                    return i
            return None

        c_status, c_title = col("STATUS"), col("TITLE")
        c_pack, c_tier = col("PACK"), col("TIER")
        c_by, c_date = col("CREATED BY"), col("CREATED DATE")

        for r in range(n):
            row = rows.nth(r)
            cells = row.locator("td")
            if cells.count() == 0:
                continue

            def txt(idx: int | None) -> list[str]:
                return _cell_lines(cells.nth(idx)) if idx is not None and idx < cells.count() else []

            title_lines = txt(c_title)
            if not title_lines:
                continue
            tier_txt = " ".join(txt(c_tier))
            tier_m = re.search(r"(\d+)", tier_txt)
            href = None
            link = row.locator("a[href*='/offers/']")
            if link.count():
                href = link.first.get_attribute("href")
            offer_id = None
            if href:
                m = re.search(r"/offers/([^/?#]+)", href)
                offer_id = m.group(1) if m else None

            offers.append({
                "title": title_lines[0],
                "with": title_lines[1] if len(title_lines) > 1 else None,
                "tab": tab,
                "status_text": " ".join(txt(c_status)) or tab,
                "pack_type": " ".join(txt(c_pack)) or None,
                "tier": int(tier_m.group(1)) if tier_m else None,
                "created_by": " ".join(txt(c_by)) or None,
                "created_date": " ".join(txt(c_date)) or None,
                "offer_id": offer_id,
            })
    return offers


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------
class SalesCapture:
    """Menampung response Server Action dari /dashboard/sales."""

    def __init__(self, page):
        self.catalog: dict | None = None
        self.series: list[dict] = []
        page.on("response", self._on_response)

    def _on_response(self, resp):
        try:
            req = resp.request
            if req.method != "POST" or "/dashboard/sales" not in resp.url:
                return
            if not resp.headers.get("content-type", "").startswith("text/x-component"):
                return
            for obj in parse_action_body(resp.text()):
                if "content" in obj and "links" in obj:
                    self.catalog = obj
                elif "days" in obj and "products" in obj:
                    self.series.append(obj)
        except Exception as e:  # noqa: BLE001
            log(f"  (capture gagal: {e})")


def _click_text_button(page, label: str) -> bool:
    btn = page.get_by_role("button", name=re.compile(rf"^{re.escape(label)}$", re.I))
    if btn.count() == 0:
        btn = page.get_by_text(label, exact=True)
    if btn.count() == 0:
        return False
    btn.first.click()
    return True


def _open_offers_dropdown(page):
    trig = page.get_by_role("button", name=re.compile(r"offers", re.I)).first
    trig.click()
    page.wait_for_timeout(300)
    pop = page.locator(
        "[role=dialog], [role=menu], [role=listbox], [data-radix-popper-content-wrapper]"
    ).last
    return pop


def select_only_offer(page, name: str) -> None:
    """Buat filter Offers hanya berisi satu produk."""
    pop = _open_offers_dropdown(page)
    dump(page, f"dropdown-{re.sub(r'[^a-z0-9]+', '-', name.lower())}",
         "[role=dialog], [role=menu], [role=listbox], [data-radix-popper-content-wrapper]")

    # 1) Kosongkan pilihan kalau ada "All your offers" / "Select all" yang tercentang.
    for pat in (r"all your offers", r"select all", r"all offers"):
        allopt = pop.get_by_text(re.compile(pat, re.I))
        if allopt.count():
            el = allopt.first
            state = (el.get_attribute("aria-checked") or el.get_attribute("data-state") or "")
            if state in ("true", "checked", ""):
                el.click()
                page.wait_for_timeout(200)
            break

    # 2) Pastikan hanya `name` yang tercentang: klik yang lain jika masih aktif.
    for opt in pop.get_by_role("menuitemcheckbox").all() + pop.get_by_role("option").all() \
            + pop.get_by_role("checkbox").all():
        label = opt.inner_text().strip()
        checked = (opt.get_attribute("aria-checked") or opt.get_attribute("data-state") or "") \
            in ("true", "checked")
        if label == name and not checked:
            opt.click()
        elif label != name and checked and not re.search(r"all", label, re.I):
            opt.click()
        page.wait_for_timeout(100)

    # fallback terakhir: klik teks persis
    target = pop.get_by_text(name, exact=True)
    if target.count() and (target.first.get_attribute("aria-checked") or "") != "true":
        target.first.click()

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)


def scrape_sales(page, full: bool) -> tuple[list[dict], dict[str, list[dict]]]:
    """Kembalikan (katalog, {productID: days[]})."""
    log("Membaca halaman Sales...")
    cap = SalesCapture(page)
    page.goto(BASE + "/dashboard/sales", wait_until="networkidle")
    page.wait_for_timeout(1000)
    dump(page, "sales")

    rng = "All time" if full else "90d"
    if not _click_text_button(page, rng):
        log(f"  tombol rentang '{rng}' tidak ditemukan, pakai default halaman")
    page.wait_for_timeout(1500)

    if not cap.catalog:
        sys.exit("Katalog Sales tidak tertangkap. Jalankan dengan --debug dan kirim folder debug_pathway/.")
    catalog = cap.catalog["content"]
    log(f"  katalog: {len(catalog)} produk dengan penjualan")

    per_product: dict[str, list[dict]] = {}
    for item in catalog:
        pid, name = item["productID"], item["contentName"]
        before = len(cap.series)
        try:
            select_only_offer(page, name)
        except Exception as e:  # noqa: BLE001
            log(f"  [!] gagal memilih offer '{name}': {e}")
            dump(page, "select-fail")
            continue
        # tunggu response baru
        for _ in range(30):
            if len(cap.series) > before:
                break
            page.wait_for_timeout(250)
        if len(cap.series) == before:
            log(f"  [!] tidak ada response untuk '{name}'")
            continue
        days = cap.series[-1]["days"]
        nz = sum(1 for d in days if d.get("units"))
        per_product[pid] = days
        log(f"  {name:28} {len(days):5} hari, {nz:4} hari ada penjualan")
    return catalog, per_product


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def upsert(offers: list[dict], catalog: list[dict], per_product: dict[str, list[dict]],
           dry_run: bool) -> None:
    from database import SessionLocal  # noqa: WPS433
    import models  # noqa: WPS433

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db = SessionLocal()
    try:
        by_pid = {c.pathway_product_id: c for c in db.query(models.Content)
                  if c.pathway_product_id}
        by_name = {c.name.lower(): c for c in db.query(models.Content)}
        cat_by_name = {c["contentName"].lower(): c for c in catalog}

        def get_or_create(name: str, pid: str | None) -> models.Content:
            c = by_pid.get(pid) if pid else None
            if c is None:
                c = by_name.get(name.lower())
            if c is None:
                c = models.Content(name=name, price=0.0, status="Development")
                db.add(c)
                db.flush()
                by_name[name.lower()] = c
            if pid and not c.pathway_product_id:
                c.pathway_product_id = pid
                by_pid[pid] = c
            return c

        # 1) Offers -> contents
        for o in offers:
            cat = cat_by_name.get(o["title"].lower())
            c = get_or_create(o["title"], cat["productID"] if cat else None)
            c.name = o["title"]
            c.status = o["tab"]
            c.pathway_status = o["status_text"]
            c.pack_type = o["pack_type"]
            c.content_type = o["pack_type"] or c.content_type
            c.tier = o["tier"]
            if o["offer_id"]:
                c.pathway_offer_id = o["offer_id"]
            if cat:
                c.world_type = cat.get("worldType")
                rd = cat.get("releaseDate")
                c.release_date = rd[:10] if rd else None
            if (c.price or 0) == 0 and o["tier"] in TIER_PRICE:
                c.price = TIER_PRICE[o["tier"]]
            c.last_synced_at = now

        # 2) Katalog Sales yang tidak muncul di Offers (jaga-jaga)
        for cat in catalog:
            c = get_or_create(cat["contentName"], cat["productID"])
            if not c.pack_type:
                c.pack_type = cat.get("contentType")
                c.content_type = c.content_type or cat.get("contentType")
            c.world_type = c.world_type or cat.get("worldType")
            if not c.release_date and cat.get("releaseDate"):
                c.release_date = cat["releaseDate"][:10]
            c.last_synced_at = now

        # 3) Penjualan harian
        existing = {(s.date, s.content_id): s for s in db.query(models.DailySales)}
        ins = upd = 0
        for pid, days in per_product.items():
            c = by_pid.get(pid)
            if not c:
                continue
            tot_units = sum(d.get("units", 0) for d in days)
            tot_gross = sum(d.get("gross", 0) for d in days)
            if tot_units:
                c.price = round(tot_gross / tot_units, 2)
            for d in days:
                units = int(d.get("units", 0))
                key = (d["date"], c.id)
                row = existing.get(key)
                if row:
                    if row.quantity != units:
                        row.quantity = units
                        upd += 1
                elif units > 0:
                    db.add(models.DailySales(date=d["date"], content_id=c.id, quantity=units))
                    ins += 1

        log(f"contents: {len(offers)} offer diproses | daily_sales: +{ins} baru, {upd} diperbarui")
        if dry_run:
            db.rollback()
            log("DRY RUN: tidak ada yang disimpan.")
        else:
            db.commit()
            log("Tersimpan ke database.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
def main() -> None:
    global _debug
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="sinkron seluruh riwayat (All time)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--headed", action="store_true", help="tampilkan browser (untuk laptop)")
    args = ap.parse_args()
    _debug = args.debug

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        try:
            login(page)
            offers = scrape_offers(page)
            catalog, per_product = scrape_sales(page, full=args.full)
        finally:
            if _debug:
                DEBUG_DIR.mkdir(exist_ok=True)
                (DEBUG_DIR / "result.json").write_text(json.dumps({
                    "offers": offers if "offers" in locals() else None,
                    "catalog": catalog if "catalog" in locals() else None,
                    "per_product_counts": {k: len(v) for k, v in per_product.items()}
                    if "per_product" in locals() else None,
                }, indent=2, ensure_ascii=False), encoding="utf-8")
            browser.close()

    upsert(offers, catalog, per_product, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
