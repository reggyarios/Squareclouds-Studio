// Helper autentikasi untuk halaman portal (admin & kreator).

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
