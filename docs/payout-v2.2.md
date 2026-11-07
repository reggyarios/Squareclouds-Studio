# Spek v2.2: Perhitungan pendapatan, preferensi payout, dan riwayat pembayaran

Lanjutan dari `docs/creator-portal-v2.md`. Aturan kerja sama: commit kecil per bagian, `py_compile` + `npm run build`
+ `pytest` sebelum tiap commit, jangan sentuh `.env`, `backend/uploads/`, dan semua hal CMS.
Untuk spek ini **boleh** mengubah `backend/pathway_bot.py` (hanya bagian yang disebut di §2).

## 0. Rantai uang (sumber kebenaran)

```
gross          = harga × unit                      (dari Pathway: field `gross` per hari)
net80          = gross × 80%                      (dari Pathway: field `creator` per hari = yang diterima Squareclouds dari Pathway)
net            = net80 × (1 − paypal_fee_pct/100)  (fee PayPal saat Pathway membayar Squareclouds; default 5%)
bagian_kreator = net × split_pct/100               (split per konten, total kreator ≤ 80%)
bagian_sq      = net − Σ bagian_kreator
IDR            = USD × idr_rate                    (hanya untuk payout non-PayPal; default 16500)
```

`paypal_fee_pct` dan `idr_rate` diatur admin (tabel `settings`), bukan hardcoded.
Selalu pakai angka `gross`/`net80` **dari Pathway** bila ada; fallback `price × unit × 0.8` hanya jika nilainya NULL
(baris lama yang belum disinkron). 0 dari Pathway dihormati sebagai 0.

## 1. Database

Model & kolom baru (semua lewat `backend/scripts/migrate_payouts.py`, pola ADD COLUMN IF NOT EXISTS + `create_all`, aman diulang):

- `daily_sales`: `gross_usd Float NULL`, `net80_usd Float NULL`, tanpa default (NULL = belum disinkron).
  Kalau kolom sudah ada sebagai NOT NULL DEFAULT 0 (versi awal migrasi): DROP NOT NULL / DROP DEFAULT.
- `settings` (model `Setting`): `key String PK`, `value String NOT NULL`, `updated_at String`.
  Seed jika belum ada: `paypal_fee_pct=5`, `idr_rate=16500`.
- `users`: `payout_method String NULL` (`paypal` | `bank` | `ewallet`), `payout_details String NULL` (JSON):
  - paypal: `{"paypal_email"}`
  - bank: `{"bank_name", "account_number", "account_name"}`
  - ewallet: `{"provider": "DANA|GoPay|OVO|ShopeePay", "phone", "account_name"}`
- `payouts` (model `Payout`): `id, user_id FK users (index), amount_usd Float, idr_rate Float NULL, amount_idr Float NULL,
  method String, details String (JSON snapshot saat dibayar), note String NULL, paid_at String, created_by Integer FK users, created_at String`.
- `users.wallet_balance` dan tabel `earning_history`: **tidak dipakai lagi**. Jangan ditulis/dibaca; biarkan kolom/tabelnya ada.

## 2. Bot (`backend/pathway_bot.py`, fungsi `upsert`)

Di loop `for d in days`: simpan juga `gross_usd = float(d.get("gross", 0))` dan `net80_usd = float(d.get("creator", 0))`
— baik saat membuat baris baru maupun memperbarui baris yang sudah ada (anggap berubah jika selisih > 0.001).
Perbarui pesan log "daily_sales: +N baru, M diperbarui" supaya tetap benar.

## 3. Modul perhitungan: `backend/earnings.py`

Satu tempat untuk semua rumus, dipakai endpoint kreator dan admin:

- `get_setting_float(db, key, default)` + `set_setting(db, key, value)`.
- `content_rows(db, user_id=None, month=None)` → per (konten[, bulan]): `units, gross_usd, net80_usd, net_usd`.
- `creator_summary(db, user, include_internal: bool)` → `{total_earned_usd, total_paid_usd, outstanding_usd, idr_rate,
  outstanding_idr (None jika paypal/belum set), by_content: [{content_id, name, status, units, share_usd}],
  by_month: [{month, share_usd}], payouts: [...]}`.
  Dengan `include_internal=True` (hanya untuk admin) tambahkan `gross_usd, net_usd, split_pct` di `by_content`/`by_month`.
  **Kreator tidak pernah menerima gross, net80, net, split %, maupun bagian Squareclouds** — field itu tidak boleh ada di respons kreator.
- `admin_overview(db, month=None)` → total gross, net80, net, Σ bagian kreator, bagian Squareclouds, per konten.
Semua pembulatan ke 2 desimal hanya saat output.

## 4. Endpoint

Admin (`require_admin`):
- `GET /settings` → `{paypal_fee_pct, idr_rate}`; `PUT /settings` body sama, validasi `0 ≤ fee ≤ 100`, `rate > 0`.
- `GET /users/{id}/earnings` → `creator_summary(include_internal=True)` + `months` + `payout_method` + `payout_details` **penuh**
  (admin perlu untuk membayar).
  `months` = `earnings.creator_months(db, user)`: dari bulan pertama kreator punya share > 0 sampai **bulan lengkap terakhir**,
  urut lama → baru (bulan kosong di antaranya ikut dengan share 0). Tiap item
  `{month, units, share_usd, share_idr, paid, payout_id}`; `share_idr = share_usd × idr_rate` saat ini, `None` untuk PayPal/belum diisi.
  Bulan lengkap terakhir = bulan sebelum bulan dari tanggal terakhir di **seluruh** `daily_sales` (data terakhir 2026-11-05 → 2026-10).
  Bulan berjalan tidak pernah ditawarkan.
- `POST /payouts` body `{user_id, period_month, note?, paid_at?}`, **satu payout per kreator per bulan**:
  - Kolom `payouts.period_month String NULL` (YYYY-MM) + unique index `uq_payouts_user_period (user_id, period_month)`, lewat
    `migrate_payouts.py` (aman diulang). Payout lama tetap NULL: tanpa periode, tidak menandai bulan mana pun sebagai dibayar.
  - `amount_usd` = `share_usd` dan `amount_idr` = `share_idr` bulan itu dari `creator_months`, **dihitung server**. Tidak ada input
    jumlah: field lain di body (termasuk `amount_usd`) ditolak 422.
  - Tolak 400: periode bukan YYYY-MM; bulan belum lengkap (bulan berjalan/depan); tidak ada pendapatan (share 0 atau di luar rentang);
    sudah dibayar (juga lewat unique index kalau dua pencatatan bersamaan).
  - Tetap: user harus kreator Active; tolak 400 jika kreator belum mengisi metode payout; jumlah ≤ `outstanding_usd` (bisa kena kalau
    masih ada payout lama tanpa periode); snapshot `method/details/idr_rate` dari keadaan saat itu; `created_by` = admin.
  - `outstanding_usd` tetap = total share − total dibayar (termasuk payout lama dan bulan berjalan).
- `DELETE /payouts/{id}` (koreksi salah input; bulannya bisa dicatat ulang).
- Email payout ke kreator: baris **Periode** (mis. "Oktober 2026") di atas Jumlah; payout lama tanpa periode tidak punya baris itu.
  Rupiah memakai `earnings.format_idr` (§5 Format angka).
- Riwayat payout (admin & kreator) menyertakan `period_month`.
- `GET /admin-reports/`: ganti perhitungan lama (`price × unit`) dengan `admin_overview`; tambahkan `net_usd`, `creators_share_usd`,
  `squareclouds_share_usd` per konten & per bulan. Bentuk respons lama yang dipakai tab Laporan boleh diubah, sesuaikan frontend-nya.

Kreator (role Creator, Active):
- `GET /me/payout` → `{payout_method, payout_details_masked}` (nomor rekening/HP dimask: 4 karakter terakhir terlihat; email PayPal: 2 karakter pertama + `***@` + domain, mis. `re***@gmail.com`).
- `PUT /me/payout` body `{payout_method, payout_details}` dengan validasi per metode (email valid; nomor rekening 6–20 digit;
  nomor HP Indonesia 10–13 digit; provider dari daftar; `account_name` wajib untuk bank/ewallet).
- `GET /creator-dashboard/`: ganti/lengkapi dengan `creator_summary(include_internal=False)`. Hapus field lama yang membocorkan
  harga/gross (mis. `price`, pendapatan kotor) — kreator hanya melihat unit dan bagian mereka.

## 5. Frontend

Kreator (`app/(portal)/creator/page.tsx`):
- Kartu ringkasan: **Total diperoleh**, **Sudah dibayar**, **Saldo tertunda** (USD; di bawahnya "≈ Rp …" jika metode ≠ PayPal, pakai `idr_rate`).
- Kartu **Metode payout**: tampilkan metode + data termask + tombol Ubah → form sesuai metode (select metode mengubah field). Keterangan:
  "Payout bank/e-wallet dikonversi dengan kurs Rp{idr_rate}/$ yang ditetapkan Squareclouds Studio."
- Tabel **Per konten**: nama, status, unit terjual, **pendapatan saya**. Tidak ada kolom harga/gross/net/split.
- Tabel **Per bulan**: bulan, unit terjual, pendapatan saya.
- Tabel **Riwayat payout**: periode, tanggal, jumlah USD, (IDR & kurs bila ada), metode, catatan.

Admin (`app/(portal)/admin/page.tsx`):
- Tab baru **Pengaturan**: dua input (fee PayPal %, kurs IDR) + Simpan.
- Tab **Kreator**: tombol **Pendapatan & Payout** per baris → panel/modal berisi ringkasan, data payout **penuh**, form
  **Catat pembayaran**, riwayat payout dengan tombol hapus (konfirmasi). Tampilkan peringatan jika kreator belum mengisi metode payout.
  - Form: dropdown **Periode** berisi bulan dari `months` yang belum dibayar (dan share > 0), label
    "Oktober 2026 — $123.45 (≈ Rp2.036.925,00)" (bagian rupiah hanya non-PayPal), default bulan tertua. Di bawah dropdown: ringkasan
    nominal yang akan dicatat (USD, plus IDR & kurs jika non-PayPal). **Tidak ada input jumlah.** Tanggal bayar & catatan tetap.
  - Bulan yang sudah dibayar tidak ada di dropdown; tampil di riwayat payout, yang punya kolom **Periode** (payout lama: "-").
- Tab **Konten**: tambah kolom Gross & Net (all-time).
- Tab **Laporan**: sesuaikan dengan respons baru; tampilkan baris total: gross, net, bagian kreator, bagian Squareclouds.

Format angka (admin, kreator, email):
- Rupiah selalu format Indonesia dua desimal: ribuan titik, desimal koma, selalu `,00`, mis. `Rp2.036.925,00`; kurs juga
  (`Rp16.500,00/$`). Satu helper per sisi: `formatIDR` di `frontend/src/lib/portal.ts`, `format_idr` di `backend/earnings.py`.
  Jangan memformat rupiah di tempat lain.
- USD tetap `$1,234.56` (`formatUsd`).

## 6. Tes (pytest) minimal
- Rumus: gross 100, fee 5 → net80 80, net 76; split 30 → share 22.8; `outstanding` berkurang setelah payout.
- `POST /payouts` melebihi saldo → 400; kreator tanpa metode → 400; non-admin → 403.
- `PUT /me/payout` validasi tiap metode; `GET /me/payout` termask.
- `GET /creator-dashboard/` sebagai kreator: respons **tidak mengandung** key `gross`, `net`, `net80`, `split`, `price` di level mana pun.
- `PUT /settings` validasi; perubahan fee langsung mengubah hasil `creator_summary`.

## 7. Urutan deploy (manual)
1. `git pull` → `venv/bin/python scripts/migrate_payouts.py`
2. `venv/bin/python pathway_bot.py --full` (mengisi `gross_usd`/`net80_usd` untuk semua baris lama)
3. `./deploy.sh`
4. Cek: admin → Pengaturan tersimpan; Kreator → Pendapatan & Payout menunjukkan angka Royal Mansion yang masuk akal
   (6.396 unit × 0,75 → gross ≈ 4.797; net ≈ 3.645,7; share 30% ≈ 1.093,7).
