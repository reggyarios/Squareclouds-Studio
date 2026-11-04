"""Bot sinkronisasi Pathway Creators -> database Squareclouds.

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
        loc = page.locator(html_selector).first if html_selector else None
        html = loc.inner_html() if (loc is not None and loc.count()) else page.content()
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
    # Klik menu sidebar, jangan tebak URL-nya.
    page.get_by_role("link", name=re.compile(r"^\s*Offers\s*$")).first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("table", timeout=20_000)
    log(f"  URL Offers: {page.url}")
    dump(page, "offers")
    offers: list[dict] = []

    for tab in OFFER_TABS:
        pat = re.compile(rf"^\s*{re.escape(tab)}\s*\d*\s*$")
        tab_el = page.locator("[role=tab], button, a").filter(has_text=pat)
        if tab_el.count() == 0:
            log(f"  tab '{tab}' tidak ditemukan, dilewati")
            dump(page, f"tab-missing-{tab.lower().replace(' ', '-')}")
            continue
        tab_el.first.click()
        page.wait_for_timeout(800)
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

        c_status = col("STATUS")
        c_title = col("TITLE") if col("TITLE") is not None else col("NAME")
        c_pack = col("PACK") if col("PACK") is not None else col("TYPE")
        c_tier = col("TIER")
        c_by, c_date = col("CREATED BY"), col("CREATED DATE")
        c_rel = col("RELEASE")

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

            release = None
            if c_rel is not None:
                t = cells.nth(c_rel).locator("time")
                if t.count():
                    dt = t.first.get_attribute("datetime") or ""
                    release = dt[:10] or None

            offers.append({
                "release_date": release,
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
    """Menyadap response Server Action /dashboard/sales lewat page.route."""

    def __init__(self, page):
        self.catalog: dict | None = None
        self.series: list[dict] = []
        page.route(re.compile(r".*/dashboard/sales(\?.*)?$"), self._on_route)

    def _on_route(self, route):
        req = route.request
        try:
            resp = route.fetch()
            if req.method == "POST" and resp.headers.get("content-type", "").startswith("text/x-component"):
                for obj in parse_action_body(resp.text()):
                    if "content" in obj and "links" in obj:
                        self.catalog = obj
                    elif "days" in obj and "products" in obj:
                        self.series.append(obj)
            route.fulfill(response=resp)
        except Exception as e:  # noqa: BLE001
            log(f"  (capture gagal: {str(e).splitlines()[0]})")
            try:
                route.continue_()
            except Exception:  # noqa: BLE001
                pass


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
    """Buat filter Offers hanya berisi satu produk: Clear, lalu centang `name`."""
    pop = _open_offers_dropdown(page)
    dump(page, f"dropdown-{re.sub(r'[^a-z0-9]+', '-', name.lower())}",
         "[role=dialog], [data-radix-popper-content-wrapper]")

    clear = pop.get_by_role("button", name=re.compile(r"^\s*Clear\s*$", re.I))
    if clear.count():
        clear.first.click()
        page.wait_for_timeout(300)

    label = pop.locator("label").filter(has_text=re.compile(rf"^\s*{re.escape(name)}\s*$"))
    if label.count() == 0:
        raise RuntimeError(f"label offer '{name}' tidak ada di dropdown")
    cb = label.first.locator("button[role=checkbox]")
    if cb.count() and cb.first.get_attribute("aria-checked") != "true":
        cb.first.click()
    elif cb.count() == 0:
        label.first.click()
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)


def scrape_sales(page, full: bool) -> tuple[list[dict], dict[str, list[dict]]]:
    """Kembalikan (katalog, {productID: days[]})."""
    log("Membaca halaman Sales...")
    cap = SalesCapture(page)
    page.get_by_role("link", name=re.compile(r"^\s*Sales\s*$")).first.click()
    page.wait_for_url(re.compile(r"/dashboard/sales"), timeout=20_000)
    page.get_by_text("Export CSV").first.wait_for(timeout=20_000)
    page.wait_for_load_state("networkidle")
    log(f"  URL Sales: {page.url}")
    dump(page, "sales")

    rng = "All time" if full else "90d"
    n_before = len(cap.series)
    btn = page.get_by_text(rng, exact=True)
    if btn.count() == 0:
        sys.exit(f"Tombol rentang '{rng}' tidak ditemukan di halaman Sales.")
    btn.first.click()
    for _ in range(60):
        if len(cap.series) > n_before:
            break
        page.wait_for_timeout(250)
    log(f"  rentang: {rng}")

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
        # tunggu response yang filternya persis produk ini
        match = None
        for _ in range(60):
            for obj in cap.series[before:]:
                prods = [x.get("productID") for x in obj.get("products", [])]
                if prods == [pid]:
                    match = obj
            if match:
                break
            page.wait_for_timeout(250)
        if not match:
            log(f"  [~] '{name}' belum dapat response, coba ulang...")
            before = len(cap.series)
            try:
                select_only_offer(page, name)
            except Exception as e:  # noqa: BLE001
                log(f"  [!] gagal lagi: {e}")
                continue
            for _ in range(60):
                for obj in cap.series[before:]:
                    if [x.get("productID") for x in obj.get("products", [])] == [pid]:
                        match = obj
                if match:
                    break
                page.wait_for_timeout(250)
            if not match:
                log(f"  [!] '{name}' tetap tidak dapat response, dilewati")
                dump(page, "no-match")
                continue
        days = match["days"]
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
            if o.get("release_date") and not c.release_date:
                c.release_date = o["release_date"]
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
                if not c.tier:
                    c.tier = min(TIER_PRICE, key=lambda t: abs(TIER_PRICE[t] - c.price))
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
            try:
                page.unroute_all(behavior="ignoreErrors")
            except Exception:  # noqa: BLE001
                pass
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
