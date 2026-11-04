// Konstanta bersama halaman portal. Harus sama dengan JOB_TITLES di backend/main.py.
export const JOB_OPTIONS = ["Builder", "Skin Artist", "Developer", "Keyart Artist", "Other"];

// Harus sama dengan USERNAME_RE di backend/main.py. Dipakai juga sebagai
// atribut `pattern` input (browser mencocokkan seluruh nilai).
export const USERNAME_PATTERN = "[a-z0-9_]{3,20}";
export const USERNAME_HINT = "3–20 karakter: huruf kecil, angka, dan underscore (_).";
