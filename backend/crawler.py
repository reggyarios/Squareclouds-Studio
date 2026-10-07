import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# ==============================================================================
# 1. KONFIGURASI BOT PATHWAY
# ==============================================================================
PATHWAY_LOGIN_PAGE = "https://creators.pathway.studio/login/main_login.php"
PATHWAY_LOGIN_POST = "https://creators.pathway.studio/login/checklogin.php" 
PATHWAY_DATA_URL_BASE = "https://creators.pathway.studio/login/generate.php"

# AMAN: Data sensitif disedot dari .env
PAYLOAD_LOGIN = {
    "myusername": os.getenv("PATHWAY_USERNAME"), 
    "mypassword": os.getenv("PATHWAY_PASSWORD") 
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# ==============================================================================
# 2. KONFIGURASI SQUARECLOUDS (AUTO-LOGIN TOKEN)
# ==============================================================================
# AMAN: URL disedot dari .env (Lebih mudah saat pindah ke VPS production)
SQUARECLOUDS_API_SYNC = os.getenv("SQ_API_SYNC", "http://127.0.0.1:8000/sync-pathway-daily/")
SQUARECLOUDS_API_LOGIN = os.getenv("SQ_API_LOGIN", "http://127.0.0.1:8000/login")

# AMAN: Kredensial disedot dari .env
SQ_ADMIN_EMAIL = os.getenv("SQ_ADMIN_EMAIL")
SQ_ADMIN_PASS = os.getenv("SQ_ADMIN_PASS") 

# Variabel token kosong (akan diisi otomatis oleh bot)
ADMIN_TOKEN = "" 

def login_to_squareclouds():
    """Fungsi untuk meminta Token segar dari backend Squareclouds secara otomatis"""
    global ADMIN_TOKEN
    print("\n[☁️] Menghubungkan bot ke database Squareclouds...")
    
    # Mencegah bot jalan jika .env belum diisi
    if not SQ_ADMIN_EMAIL or not SQ_ADMIN_PASS:
        print("[✖] ERROR: Email atau Password Admin tidak ditemukan di file .env!")
        exit()
        
    payload = {
        "username": SQ_ADMIN_EMAIL, 
        "password": SQ_ADMIN_PASS
    }
    
    try:
        resp = requests.post(SQUARECLOUDS_API_LOGIN, data=payload)
        
        if resp.status_code == 200:
            ADMIN_TOKEN = resp.json().get("access_token")
            print("[✔] Berhasil mendapatkan Token Akses Squareclouds!")
        else:
            print(f"[✖] GAGAL LOGIN KE SQUARECLOUDS! Status: {resp.status_code}")
            print(f"Detail: {resp.text}")
            print("Pastikan server Uvicorn menyala dan kredensial di .env benar.")
            exit()
    except requests.exceptions.ConnectionError:
        print("[✖] KONEKSI GAGAL! Pastikan server backend FastAPI (Uvicorn) sedang menyala.")
        exit()

def do_login(session):
    print("\n[🔑] Mengambil cookies dari halaman depan Pathway...")
    session.get(PATHWAY_LOGIN_PAGE, headers=HEADERS)
    
    if not PAYLOAD_LOGIN["myusername"] or not PAYLOAD_LOGIN["mypassword"]:
        print("[✖] ERROR: Kredensial Pathway tidak ditemukan di file .env!")
        exit()
        
    print("[🔑] Mengirim data login ke checklogin.php...")
    resp = session.post(PATHWAY_LOGIN_POST, data=PAYLOAD_LOGIN, headers=HEADERS)
    
    print(f"[ℹ️] URL terakhir setelah login: {resp.url}")
    if "main_login" in resp.url.lower() or "checklogin" in resp.url.lower():
        print("[⚠️] PERINGATAN: Sepertinya masih di halaman login. Mari kita coba tarik datanya dulu.")
    else:
        print("[✔] Login Pathway sukses! Teralihkan ke Dashboard.")

def fetch_and_sync(session, month_int, year_int):
    # Mengubah angka 1 jadi "01"
    month_str = str(month_int).zfill(2) 
    
    url = f"{PATHWAY_DATA_URL_BASE}?m={month_str}&y={year_int}"
    print(f"[*] Menarik data Bulan {month_str} Tahun {year_int}...")
    
    resp = session.get(url, headers=HEADERS)
    
    if resp.status_code == 404:
        print(f"    [✖] ERROR 404: URL tidak ditemukan.")
        return

    try:
        raw_json_data = resp.json()
        print(f"    [+] Berhasil ditarik! Ada {len(raw_json_data)} baris data mentah.")
        
        # Kirim ke backend Squareclouds pakai Token segar
        headers_api = {
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        }
        sq_resp = requests.post(SQUARECLOUDS_API_SYNC, json=raw_json_data, headers=headers_api)
        
        if sq_resp.status_code == 200:
            print(f"    [✔] Berhasil masuk DB Squareclouds: {sq_resp.json()['message']}")
        else:
            print(f"    [✖] Gagal simpan ke DB Squareclouds: {sq_resp.text}")
            
    except Exception as e:
        print(f"    [✖] GAGAL MEMBACA JSON!")
        print(f"    Alasan: Sesi ditolak. Pathway melempar kembali HTML.")
        print(f"    [Cuplikan]: {resp.text[:150].strip()}...\n")

def run_bot():
    print("="*50)
    print("🤖 SQUARECLOUDS CRAWLER BOT AKTIF!")
    print("="*50)
    
    # 1. Login ke Squareclouds dulu untuk ambil Token (Wajib sebelum tarik data)
    login_to_squareclouds()
    
    session = requests.Session()
    do_login(session)
    
    # --- FASE 1: SINKRONISASI SEJARAH (JANUARI - AGUSTUS 2026) ---
    print("\n>>> MEMULAI SINKRONISASI HISTORIS (JAN-AGU 2026) <<<")
    # Loop dari 1 sampai 8 (Januari hingga Agustus karena saat ini bulan Agustus 2026)
    for m in range(1, 9):
        fetch_and_sync(session, m, 2026)
        time.sleep(2) 
        
    print("\n>>> SINKRONISASI HISTORIS SELESAI! <<<")
    print("Bot sekarang masuk ke mode 'Standby'. Akan sinkronisasi otomatis tiap 24 Jam.")
    
    # --- FASE 2: SINKRONISASI OTOMATIS PER 24 JAM ---
    while True:
        time.sleep(86400) 
        
        print("\n" + "="*50)
        print(f"⏰ SINKRONISASI HARIAN DIMULAI ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("="*50)
        
        # Ambil ulang token Squareclouds agar tidak expired setelah ditinggal 24 jam
        login_to_squareclouds()
        
        daily_session = requests.Session()
        do_login(daily_session)
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        fetch_and_sync(daily_session, current_month, current_year)
        print("[zZz] Sinkronisasi harian selesai. Bot kembali tidur 24 jam...")

if __name__ == "__main__":
    run_bot()