// Helper autentikasi untuk halaman portal (admin & kreator).
import { apiErrorMessage, apiUrl } from "@/lib/api";

/** Header Authorization dari token login, digabung dengan header tambahan. */
export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = typeof window === "undefined" ? "" : (localStorage.getItem("token") ?? "");
  return { ...extra, Authorization: `Bearer ${token}` };
}

/** Hapus sesi lalu kembali ke halaman login. */
export function logout(redirectTo = "/login") {
  localStorage.clear();
  window.location.assign(redirectTo);
}

/**
 * Token kadaluarsa / ditolak (401/403) -> paksa login ulang.
 * `onUnauthorized` bisa diganti, mis. dengan router.push milik halaman.
 */
export function guard(res: Response, onUnauthorized: () => void = logout): Response {
  if (res.status === 401 || res.status === 403) {
    onUnauthorized();
    throw new Error("Sesi berakhir, silakan login ulang.");
  }
  return res;
}

/**
 * Panggil endpoint terproteksi dan kembalikan JSON-nya. 401/403 -> login ulang
 * (lihat `guard`), error lain -> Error berisi `detail` dari server.
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  onUnauthorized: () => void = logout
) {
  const headers = authHeaders(init.body ? { "Content-Type": "application/json" } : {});
  const res = guard(await fetch(apiUrl(path), { ...init, headers }), onUnauthorized);
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(apiErrorMessage(data, `Permintaan gagal (${res.status}).`));
  return data;
}
