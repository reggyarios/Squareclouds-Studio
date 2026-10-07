import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# Muat environment variables dari file .env
load_dotenv()

# Ambil kunci dari .env, sediakan fallback default jika gagal terbaca
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_rahasia_aman_123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

# Mesin pengacak password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fungsi untuk membandingkan password saat login
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Fungsi untuk mengacak password baru
def get_password_hash(password):
    return pwd_context.hash(password)

# Fungsi untuk membuat JWT Token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) # <-- Ini yang dibaca frontend untuk Auto-Kick!
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt