# Spek: Creator Portal v2.1 (undangan kreator + konten dari Pathway)

Dokumen acuan untuk implementasi. Kerjakan berurutan per bagian, commit kecil per bagian,
jalankan `python -m py_compile backend/*.py` dan `cd frontend && npm run build` sebelum tiap commit.
Jangan menyentuh: folder `backend/uploads/`, file `.env`, semua endpoint dan halaman CMS (`/cms/*`, `admin-cms`),
`backend/pathway_bot.py`, dan skrip di `backend/scripts/`.

## Latar

- Konten (`contents`) sekarang **diisi otomatis** oleh `backend/pathway_bot.py` dari Pathway (cron harian).
  Kolom yang diisi bot: `name, status, pack_type, world_type, tier, price, release_date, pathway_status,
  pathway_product_id, pathway_offer_id, last_synced_at`. Admin **tidak** lagi membuat/mengedit/menghapus konten.
- Penjualan harian (`daily_sales`) juga diisi bot. Unit disimpan apa adanya (tidak ada pembagian).
- Kreator **hanya bisa mendaftar lewat undangan**: admin memasukkan email → sistem mengirim email berisi link
  undangan → kreator membuka link, mengisi nama, password, dan job title → akun berstatus **Pending** →
  admin menyetujui. Tidak ada pendaftaran terbuka.
- Admin **tidak pernah tahu dan tidak bisa mengubah password** kreator. Admin hanya: mengundang,
  menyetujui/menolak, menonaktifkan, mengubah job title, dan **menautkan kreator ke konten beserta
  persentase split** (`creator_splits`).
- Halaman login: hapus subjudul "Masuk ke portal pendapatan kreator" di bawah logo.
- Kreator hanya melihat konten yang tertaut ke dirinya (sudah begitu di `/creator-dashboard/`, pertahankan).
- `backend/crawler.py` dan endpoint `/sync-pathway-daily/` sudah tidak dipakai → hapus.
  `backend/scripts/cleanup_uploads.py` masih memakai SQLite → hapus juga.

## 1. Database

Tambah ke `models.User`:

```python
account_status = Column(String, nullable=False, default="Pending", server_default="Pending")  # Pending | Active | Inactive
created_at     = Column(String, nullable=True)   # ISO timestamp UTC saat daftar
username       = Column(String, unique=True, nullable=True, index=True)  # 3–20 karakter [a-z0-9_], disimpan lowercase
```

`username` nullable karena akun lama dibuat sebelum ada username; akun itu tetap login pakai email.
Aturan username (dicek backend dan frontend, harus sama): 3–20 karakter, hanya huruf kecil, angka, dan underscore.
Karena tidak boleh mengandung `@`, username tidak pernah tertukar dengan email saat login.

Tabel baru `invitations` (model `Invitation`):

```python
id          Integer PK
email       String, nullable=False, index=True   # disimpan lowercase
token       String, unique=True, nullable=False, index=True   # secrets.token_urlsafe(32)
invited_by  Integer FK users.id
created_at  String (ISO UTC)
expires_at  String (ISO UTC)   # created_at + 7 hari
used_at     String, nullable=True   # diisi saat kreator selesai mendaftar
```

Buat `backend/scripts/migrate_add_user_status.py` dengan pola yang sama seperti
`scripts/migrate_add_pathway_columns.py` (ALTER TABLE ... ADD COLUMN IF NOT EXISTS untuk kolom users,
`CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)` — nama index sama dengan yang dibuat
`create_all` —, lalu `Base.metadata.create_all` untuk tabel `invitations`), dan di akhir:
`UPDATE users SET account_status='Active' WHERE role='Admin'`.
Catat di docstring bahwa skrip ini harus dijalankan di server sebelum deploy versi ini, dan dijalankan **lagi**
kalau sudah pernah dijalankan sebelum kolom `username` ditambahkan (skrip aman diulang).

## 2. Backend (`backend/main.py`, `backend/schemas.py`)

### 2.1 Undangan, pendaftaran & login

Pengiriman email: buat `backend/mailer.py` dengan fungsi `send_mail(to, subject, html, text)` memakai
`smtplib` + STARTTLS, konfigurasi dari `.env`: `SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS,
MAIL_FROM (contoh: "Squareclouds Studio <contact@squarecloudsmc.com>"), PORTAL_URL (default https://creator.squarecloudsmc.com)`.
Jika `SMTP_HOST` kosong: jangan error, cukup `print` isi email ke log dan kembalikan `False` (mode dev).
Tambahkan contoh variabel ini ke `backend/.env.example` (buat file itu, tanpa nilai rahasia).

- `POST /invitations` (admin). Body `{"email"}`.
  - Validasi email; tolak jika email sudah terdaftar di `users`. Jika sudah ada undangan aktif (belum `used_at`,
    belum kedaluwarsa) untuk email itu, **kirim ulang** dengan token baru dan hapus yang lama.
  - Buat `Invitation`, kirim email: subjek "Undangan Creator Portal Squareclouds Studio", isi singkat dalam Bahasa
    Indonesia dengan tombol/link `{PORTAL_URL}/register?token={token}` dan catatan berlaku 7 hari.
  - Respons 201 `{"message": "Undangan terkirim ke ...", "sent": true|false}`.
- `GET /invitations` (admin): daftar undangan yang belum dipakai: `email, created_at, expires_at, expired (bool)`.
- `DELETE /invitations/{id}` (admin): batalkan undangan.
- `GET /register/{token}` (publik): validasi token → 200 `{"email": ...}` atau 404/410 dengan `detail`
  ("Undangan tidak ditemukan" / "Undangan sudah kedaluwarsa" / "Undangan sudah dipakai").
- `POST /register` (publik). Body: `token, username, name, password, job_title`.
  - Token harus valid (sama seperti GET). Email **diambil dari undangan**, bukan dari body.
  - Validasi: `username` wajib, di-`strip().lower()` lalu harus cocok dengan aturan username (400 kalau tidak),
    dan belum dipakai akun lain (400 `"Username sudah dipakai"`); nama wajib (nama tampilan); password ≥ 8;
    `job_title` salah satu dari `Builder, Skin Artist, Developer, Keyart Artist, Other`.
    Request tanpa field `username` → 422. Undangan **tidak** hangus kalau pendaftaran ditolak validasi.
  - Simpan user `role="Creator"`, `account_status="Pending"`, `created_at=now`, `username` (lowercase),
    password di-hash; set `used_at` undangan.
  - Respons 201 `{"message": "Pendaftaran diterima. Tunggu persetujuan admin."}`. Jangan kembalikan token.
  - Buat endpoint ini dalam satu transaksi (user + used_at), supaya token tidak bisa dipakai dua kali.
    Kalau commit gagal karena unique constraint (balapan dua pendaftaran), rollback dan kembalikan 400
    `"Username sudah dipakai"` atau `"Email sudah terdaftar!"` sesuai yang bentrok.
- `POST /login`: field `username` dari form OAuth2 boleh berisi **email atau username**. Input di-`strip().lower()`;
  kalau mengandung `@` dicocokkan ke `email`, selain itu ke `username` (keduanya case-insensitive, `func.lower` di kolom).
  User tidak ditemukan atau password salah → 401 `"Email/username atau password salah"` (generik, tidak membocorkan
  mana yang salah). Token JWT tetap memakai email sebagai `sub`.
- `POST /login`: setelah password cocok, jika `account_status != "Active"` → 403
  `{"detail": "Akun belum disetujui admin."}` (Pending) atau `"Akun dinonaktifkan."` (Inactive).
  Admin selalu boleh login.
- `get_current_user`: tolak (401) jika user `account_status != "Active"`. Semua token lama tetap valid untuk admin.

### 2.2 Manajemen kreator (semua admin-only, pakai `require_admin`)
- **Hapus** `POST /users/`.
- `GET /users/`: kembalikan `id, name, username, email, role, job_title, account_status, created_at`
  (`username` bisa `null` untuk akun lama), hanya `role="Creator"`,
  urut `account_status` (Pending dulu) lalu `created_at` terbaru.
- `PUT /users/{id}`: boleh ubah `name, job_title, account_status` (hanya nilai `Active|Inactive`).
  **Tidak ada field password** — admin tidak bisa mengubah password siapa pun. Tidak boleh mengubah akun Admin.
- `DELETE /users/{id}`: tetap ada (dipakai untuk **menolak** pendaftar Pending). Hapus juga split-nya. Tidak boleh untuk Admin.

### 2.3 Konten (read-only dari Pathway) & split
- **Hapus** `POST /contents/`, `DELETE /contents/{id}`, `POST /splits/`.
- `GET /contents/` (admin): tiap konten berisi semua kolom Pathway di atas + `units_total`
  (SUM `daily_sales.quantity`) + `splits: [{user_id, user_name, split_percentage}]`.
- `PUT /contents/{id}/splits` (admin): body `{"splits": [{"user_id": int, "split_percentage": float}]}`.
  Ganti seluruh split konten itu. Validasi: tiap persentase > 0, total ≤ 80, `user_id` harus kreator `Active`,
  tidak boleh duplikat. Respons: konten yang sudah diperbarui (format sama seperti `GET /contents/`).
- `PUT /contents/{id}` yang lama (edit nama/harga/status) **dihapus** — field itu milik Pathway.

### 2.4 Lainnya
- `/creator-dashboard/`: tambahkan ke tiap proyek aktif `status, pack_type, release_date, tier`. Logika uang tetap.
- `/admin-reports/`: tetap, tidak diubah.
- Hapus endpoint `/sync-pathway-daily/`, file `crawler.py`, `scripts/cleanup_uploads.py`, dan `import math` kalau sudah tak dipakai.
- Skema Pydantic baru: `InvitationCreate`, `UserRegister` (token, username, name, password, job_title), `UserStatusUpdate`
  (ganti `UserUpdate`), `SplitsReplace`. Hapus `UserCreate`, `ContentCreate`, `ContentUpdate`, `SplitCreate`, `SplitUpdate`.

## 3. Frontend (`frontend/src`)

Aturan umum: semua panggilan API lewat `apiUrl()` dari `lib/api.ts` (hapus URL hardcoded
`https://api.squarecloudsmc.com/...`), dan semua endpoint terproteksi memakai header `Authorization` seperti helper
`authHeaders()`/`guard()` yang sudah ada di `app/(portal)/admin/page.tsx` — pindahkan dua helper itu ke
`lib/auth.ts` supaya dipakai halaman lain juga.

### 3.1 Halaman daftar via undangan: `app/(portal)/register/page.tsx`
- Baca `token` dari query string. Saat dimuat, panggil `GET /register/{token}`:
  - gagal → tampilkan `detail` dari server (tidak ada form, hanya pesan + link ke `/login`);
  - sukses → tampilkan email (read-only) dan form: Username (dengan keterangan aturannya, langsung diubah ke
    lowercase saat diketik, dicek dengan `pattern` dan sebelum kirim), Nama, Password (+ konfirmasi),
    Job title (select). Tombol "Buat akun". Aturan username disimpan di `lib/portal.ts`
    (`USERNAME_PATTERN`, `USERNAME_HINT`) dan harus sama dengan `USERNAME_RE` di `backend/main.py`.
- Tanpa `token` di URL → tampilkan "Pendaftaran hanya lewat undangan. Hubungi admin Squareclouds Studio."
- Sukses → pesan dari server + link ke `/login`. Gagal → `detail` dari server.
- **Tidak ada** tautan "Daftar" di halaman login.
- Gaya mengikuti halaman login yang ada.

### 3.2 `app/(portal)/login/page.tsx`
- Hapus subjudul "Masuk ke portal pendapatan kreator".
- Label field pertama: **"Email atau username"**, input `type="text"` (bukan `email`, supaya username bisa diketik),
  dikirim sebagai field `username` form login.
- Jika respons 403, tampilkan `detail` apa adanya (pesan Pending/Inactive), bukan "email/password salah".

### 3.3 `proxy.ts`
- `creator.squarecloudsmc.com`: izinkan `/register` (sama seperti `/login`).
- `access.squarecloudsmc.com`: `/register` → redirect ke `/login`.
- `squarecloudsmc.com` & `www`: `/register` → redirect ke `/`.

### 3.4 Halaman admin: `app/(portal)/admin/page.tsx` (rombak)
Hapus: form "Tambah Kreator", form "Buat Konten", edit nama/harga/status konten, konstanta `STATUS_OPTIONS`,
`TYPE_OPTIONS`, `TIER_OPTIONS`. Pertahankan `JOB_OPTIONS` dan bagian Laporan.

Susunan tab/bagian:
1. **Undangan & Pendaftar**
   - Atas: input email + tombol **Kirim undangan** (`POST /invitations`). Tampilkan pesan sukses/gagal.
     Jika `sent: false`, tampilkan peringatan "Email belum terkirim (SMTP belum dikonfigurasi)".
   - Tengah: daftar undangan yang belum dipakai (`GET /invitations`): email, dikirim kapan, kedaluwarsa kapan,
     badge "Kedaluwarsa" bila perlu; tombol **Kirim ulang** (POST lagi dengan email yang sama) dan **Batalkan**.
   - Bawah: kreator `account_status=Pending` (sudah mengisi form): nama, username, email, job title, tanggal daftar.
     Tombol **Setujui** (`PUT /users/{id}` → `Active`) dan **Tolak** (konfirmasi, lalu `DELETE /users/{id}`).
   - Badge jumlah pending (undangan + pendaftar) di judul tab.
2. **Kreator** — `account_status` Active/Inactive: nama, username (`-` untuk akun lama), email, job title (editable select), status toggle
   Aktif/Nonaktif, jumlah konten tertaut. **Tidak ada** reset password.
3. **Konten** — tabel read-only dari Pathway: nama, badge status (`Published` hijau, `Pending Release`/`Submissions`
   kuning, `In Development`/`Review` abu), pack type, tier, harga, tanggal rilis, total unit, dan daftar kreator
   tertaut (nama + %). Tombol **Atur split** per baris → modal: daftar kreator Active dengan checkbox + input %,
   total kreator ≤ 80% (sisanya Squareclouds Studio), simpan via `PUT /contents/{id}/splits`.
   Tulis keterangan kecil: "Data konten disinkronkan otomatis dari Pathway setiap hari."
4. **Laporan** — bagian yang sudah ada, tidak diubah selain pemakaian `apiUrl()`/`authHeaders()`.

### 3.5 Halaman kreator: `app/(portal)/creator/page.tsx`
- Tampilkan `status`, `pack_type`, `release_date` di kartu proyek kalau field itu ada di respons. Tidak ada perubahan lain.

## 4. Pembersihan
- Hapus `backend/crawler.py`, `backend/scripts/cleanup_uploads.py`.
- Hapus `backend/scripts/audit_*.py` **hanya jika** keduanya memakai SQLite; kalau sudah pakai SQLAlchemy, biarkan.

## 5. Kriteria selesai (uji manual setelah deploy)
1. Admin kirim undangan ke email uji → email masuk (atau tercetak di log kalau SMTP belum diisi) berisi link `/register?token=...`.
   `POST /register` tanpa token / token salah → 404; token yang sudah dipakai → 410.
2. Buka link → form muncul dengan email terkunci → isi (termasuk username) → 201. Login akun Pending → 403 "belum disetujui";
   setelah admin Setujui → login sukses, masuk `/creator`, baik dengan email maupun username.
   Mendaftar dengan username yang sudah dipakai → 400 "Username sudah dipakai".
3. Admin: tab Undangan & Pendaftar menampilkan undangan lalu pendaftar; Setujui memindahkannya ke tab Kreator.
   `curl -X POST api/invitations` tanpa token → 401.
4. Admin: tab Konten menampilkan 18 konten dari Pathway dengan status & tier; Atur split untuk "Royal Mansion"
   ke kreator tersebut 30% → tersimpan; total > 80% ditolak dengan pesan.
5. Kreator yang tertaut melihat "Royal Mansion" di dashboard-nya dengan angka penjualan; kreator lain tidak.
6. `curl api/users/` tanpa token → 401; `curl -X POST api/contents/` → 405/404 (endpoint tidak ada).
7. `npm run build` bersih tanpa error TypeScript.

## 6. Urutan deploy (dikerjakan manusia, bukan Claude Code)
0. Isi `SMTP_*`, `MAIL_FROM`, `PORTAL_URL` di `backend/.env` server (lihat `.env.example`).
1. `git pull` di server, `venv/bin/python scripts/migrate_add_user_status.py`
   (jalankan lagi walau sudah pernah: menambah kolom `username` + index-nya; aman diulang)
2. `./deploy.sh local` (atau `./deploy.sh` kalau sudah push)
3. Jalankan kriteria 1–6.