// Konstanta bersama halaman portal. Harus sama dengan JOB_TITLES di backend/main.py.
export const JOB_OPTIONS = ["Builder", "Skin Artist", "Developer", "Keyart Artist", "Other"];

// Harus sama dengan USERNAME_RE di backend/main.py. Dipakai juga sebagai
// atribut `pattern` input (browser mencocokkan seluruh nilai).
export const USERNAME_PATTERN = "[a-z0-9_]{3,20}";
export const USERNAME_HINT = "3–20 karakter: huruf kecil, angka, dan underscore (_).";

// Metode payout & field-nya. Harus sama dengan validasi /me/payout di backend/main.py.
export type PayoutMethod = "paypal" | "bank" | "ewallet";
export const PAYOUT_METHOD_LABEL: Record<PayoutMethod, string> = {
  paypal: "PayPal",
  bank: "Transfer bank",
  ewallet: "E-wallet",
};
export const PAYOUT_FIELDS: Record<PayoutMethod, string[]> = {
  paypal: ["paypal_email"],
  bank: ["bank_name", "account_number", "account_name"],
  ewallet: ["provider", "phone", "account_name"],
};
export const PAYOUT_FIELD_LABEL: Record<string, string> = {
  paypal_email: "Email PayPal",
  bank_name: "Nama bank",
  account_number: "Nomor rekening",
  account_name: "Atas nama",
  provider: "Provider",
  phone: "Nomor HP",
};
// Sama dengan EWALLET_PROVIDERS di backend/main.py.
export const EWALLET_PROVIDERS = ["DANA", "GoPay", "OVO", "ShopeePay"];
// Sama dengan MASKED_PAYOUT_FIELDS di backend/main.py: kreator hanya melihat
// 4 karakter terakhirnya, jadi harus diisi ulang saat mengubah data payout.
export const MASKED_PAYOUT_FIELDS = ["paypal_email", "account_number", "phone"];

// Format tampilan saja; semua angka uang dihitung di backend/earnings.py.
export const formatUsd = (n: number) =>
  `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const formatIdr = (n: number) =>
  `Rp${n.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
export const formatMonth = (month: string) => {
  const [year, m] = month.split("-").map(Number);
  return year && m
    ? new Date(year, m - 1, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" })
    : month;
};
