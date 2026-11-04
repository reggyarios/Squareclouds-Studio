"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiErrorMessage, apiUrl } from "@/lib/api";
import { authHeaders, guard } from "@/lib/auth";
import { JOB_OPTIONS } from "@/lib/portal";

type Tab = "undangan" | "kreator" | "konten" | "laporan";

type Invitation = {
  id: number;
  email: string;
  created_at: string;
  expires_at: string;
  expired: boolean;
};

type Creator = {
  id: number;
  name: string;
  email: string;
  role: string;
  job_title: string | null;
  account_status: "Pending" | "Active" | "Inactive";
  created_at: string | null;
};

type ContentSplit = { user_id: number; user_name: string; split_percentage: number };

type Content = {
  id: number;
  name: string;
  status: string | null;
  pack_type: string | null;
  world_type: string | null;
  tier: number | null;
  price: number | null;
  release_date: string | null;
  pathway_status: string | null;
  last_synced_at: string | null;
  units_total: number;
  splits: ContentSplit[];
};

type SplitRow = { user_id: number; name: string; checked: boolean; percentage: string };

const MAX_CREATOR_SPLIT = 80;

const PESAN_CLASS: Record<string, string> = {
  error: "bg-red-50 text-red-600",
  warning: "bg-amber-50 text-amber-700",
  success: "bg-green-50 text-green-700",
};

const STATUS_BADGE: Record<string, string> = {
  Published: "bg-green-100 text-green-700",
  "Pending Release": "bg-amber-100 text-amber-700",
  Submissions: "bg-amber-100 text-amber-700",
  "In Development": "bg-gray-100 text-gray-600",
  Review: "bg-gray-100 text-gray-600",
};

const errMsg = (err: unknown) => (err instanceof Error ? err.message : "Terjadi kesalahan.");

const formatDate = (value: string | null) => {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};

const formatDateTime = (value: string | null) => {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
};

const roundPct = (n: number) => Math.round(n * 1e6) / 1e6;

export default function AdminDashboard() {
  const router = useRouter();
  const [adminName, setAdminName] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("undangan");
  const [loading, setLoading] = useState(true);

  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  // "new" = form kirim undangan, angka = id undangan yang sedang diproses.
  const [busyInvite, setBusyInvite] = useState<number | "new" | null>(null);

  const [usersList, setUsersList] = useState<Creator[]>([]);
  const [contentsList, setContentsList] = useState<Content[]>([]);
  const [reportsList, setReportsList] = useState<any[]>([]);

  // State untuk filter bulan laporan
  const [filterBulan, setFilterBulan] = useState<string>("");

  const [pesan, setPesan] = useState({ type: "", text: "" });
  const [busyId, setBusyId] = useState<number | null>(null);

  const [splitEditor, setSplitEditor] = useState<{ content: Content; rows: SplitRow[] } | null>(
    null
  );
  const [savingSplits, setSavingSplits] = useState(false);
  const [splitError, setSplitError] = useState("");

  const handleLogout = useCallback(() => {
    localStorage.clear();
    router.push("/login");
  }, [router]);

  // Semua endpoint admin wajib membawa token. 401/403 -> login ulang,
  // error lain -> Error berisi `detail` dari server.
  const api = useCallback(
    async (path: string, init: RequestInit = {}) => {
      const headers = authHeaders(init.body ? { "Content-Type": "application/json" } : {});
      const res = guard(await fetch(apiUrl(path), { ...init, headers }), handleLogout);
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(apiErrorMessage(data, `Permintaan gagal (${res.status}).`));
      return data;
    },
    [handleLogout]
  );

  const fetchInvitations = async () => {
    const data = await api("/invitations");
    setInvitations(data.data);
  };

  const fetchUsers = async () => {
    const data = await api("/users/");
    setUsersList(data.data);
  };

  const fetchContents = async () => {
    const data = await api("/contents/");
    setContentsList(data.data);
  };

  const fetchReports = async () => {
    const res = guard(
      await fetch(apiUrl("/admin-reports/"), { headers: authHeaders() }),
      handleLogout
    );
    const data = await res.json();
    if (res.ok) {
      setReportsList(data.data);
      const months = Array.from(new Set(data.data.map((r: any) => r.bulan)))
        .sort()
        .reverse() as string[];
      if (months.length > 0) setFilterBulan(months[0]);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    if (!token || role !== "Admin") {
      router.push("/login");
      return;
    }

    setAdminName(localStorage.getItem("name") || "Admin");
    Promise.all([fetchInvitations(), fetchUsers(), fetchContents(), fetchReports()])
      .catch((err) => setPesan({ type: "error", text: errMsg(err) }))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const switchTab = (tab: Tab) => {
    setActiveTab(tab);
    setPesan({ type: "", text: "" });
  };

  // ==========================================================================
  // UNDANGAN
  // ==========================================================================

  // Kirim (atau kirim ulang) undangan. sent=false berarti SMTP belum diisi:
  // undangan tetap dibuat, link-nya hanya tercetak di log backend.
  const sendInvite = async (email: string) => {
    const data = await api("/invitations", { method: "POST", body: JSON.stringify({ email }) });
    setPesan(
      data.sent
        ? { type: "success", text: data.message }
        : {
            type: "warning",
            text: `${data.message} Email belum terkirim (SMTP belum dikonfigurasi).`,
          }
    );
  };

  const runInviteAction = async (busyKey: number | "new", action: () => Promise<void>) => {
    setBusyInvite(busyKey);
    setPesan({ type: "", text: "" });
    try {
      await action();
      return true;
    } catch (err) {
      setPesan({ type: "error", text: errMsg(err) });
      return false;
    } finally {
      // Juga setelah gagal: undangan bisa sudah tersimpan walau email gagal terkirim.
      await fetchInvitations().catch(() => {});
      setBusyInvite(null);
    }
  };

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (await runInviteAction("new", () => sendInvite(inviteEmail.trim()))) setInviteEmail("");
  };

  const handleResendInvite = (inv: Invitation) =>
    runInviteAction(inv.id, () => sendInvite(inv.email));

  const handleCancelInvite = (inv: Invitation) => {
    if (!confirm(`Batalkan undangan untuk ${inv.email}? Link di email tidak akan bisa dipakai lagi.`))
      return;
    runInviteAction(inv.id, async () => {
      const data = await api(`/invitations/${inv.id}`, { method: "DELETE" });
      setPesan({ type: "success", text: data.message });
    });
  };

  // ==========================================================================
  // KREATOR & PENDAFTAR
  // ==========================================================================

  const pendingUsers = usersList.filter((u) => u.account_status === "Pending");
  const pendingCount = invitations.length + pendingUsers.length;
  const creators = usersList.filter((u) => u.account_status !== "Pending");
  const activeCreators = usersList.filter((u) => u.account_status === "Active");

  const linkedCount: Record<number, number> = {};
  contentsList.forEach((c) =>
    c.splits.forEach((s) => {
      linkedCount[s.user_id] = (linkedCount[s.user_id] || 0) + 1;
    })
  );

  const updateUser = (id: number, body: Record<string, string>) =>
    api(`/users/${id}`, { method: "PUT", body: JSON.stringify(body) });

  const runUserAction = async (
    user: Creator,
    action: () => Promise<unknown>,
    successText: string
  ) => {
    setBusyId(user.id);
    setPesan({ type: "", text: "" });
    try {
      await action();
      setPesan({ type: "success", text: successText });
      await Promise.all([fetchUsers(), fetchContents()]);
    } catch (err) {
      setPesan({ type: "error", text: errMsg(err) });
    } finally {
      setBusyId(null);
    }
  };

  const handleApprove = (u: Creator) =>
    runUserAction(
      u,
      () => updateUser(u.id, { account_status: "Active" }),
      `${u.name} disetujui dan sekarang bisa login.`
    );

  const handleReject = (u: Creator) => {
    if (!confirm(`Tolak pendaftaran ${u.name} (${u.email})? Akun akan dihapus permanen.`)) return;
    runUserAction(
      u,
      () => api(`/users/${u.id}`, { method: "DELETE" }),
      `Pendaftaran ${u.name} ditolak.`
    );
  };

  const handleJobChange = (u: Creator, jobTitle: string) =>
    runUserAction(
      u,
      () => updateUser(u.id, { job_title: jobTitle }),
      `Job title ${u.name} diperbarui.`
    );

  const handleToggleStatus = (u: Creator) => {
    const next = u.account_status === "Active" ? "Inactive" : "Active";
    if (next === "Inactive" && !confirm(`Nonaktifkan ${u.name}? Kreator ini tidak akan bisa login.`))
      return;
    runUserAction(
      u,
      () => updateUser(u.id, { account_status: next }),
      next === "Active" ? `${u.name} diaktifkan.` : `${u.name} dinonaktifkan.`
    );
  };

  // ==========================================================================
  // KONTEN & SPLIT
  // ==========================================================================

  const lastSynced = contentsList.reduce<string | null>(
    (latest, c) => (c.last_synced_at && (!latest || c.last_synced_at > latest) ? c.last_synced_at : latest),
    null
  );

  const openSplitEditor = (content: Content) => {
    const current = new Map(content.splits.map((s) => [s.user_id, s.split_percentage]));
    setSplitError("");
    setSplitEditor({
      content,
      rows: activeCreators.map((u) => ({
        user_id: u.id,
        name: u.name,
        checked: current.has(u.id),
        percentage: current.has(u.id) ? String(current.get(u.id)) : "",
      })),
    });
  };

  const updateSplitRow = (userId: number, patch: Partial<SplitRow>) =>
    setSplitEditor((ed) =>
      ed && {
        ...ed,
        rows: ed.rows.map((r) => (r.user_id === userId ? { ...r, ...patch } : r)),
      }
    );

  const checkedRows = splitEditor ? splitEditor.rows.filter((r) => r.checked) : [];
  const splitTotal = roundPct(checkedRows.reduce((sum, r) => sum + (Number(r.percentage) || 0), 0));
  const hasEmptyPct = checkedRows.some((r) => !(Number(r.percentage) > 0));
  const overLimit = splitTotal > MAX_CREATOR_SPLIT;
  // Split ke kreator yang tidak Active tidak bisa dipertahankan (backend hanya
  // menerima kreator Active), jadi akan hilang saat disimpan.
  const droppedSplits = splitEditor
    ? splitEditor.content.splits.filter((s) => !activeCreators.some((u) => u.id === s.user_id))
    : [];

  const handleSaveSplits = async () => {
    if (!splitEditor) return;
    if (hasEmptyPct) {
      setSplitError("Isi persentase lebih dari 0 untuk setiap kreator yang dicentang.");
      return;
    }
    if (overLimit) {
      setSplitError(`Total kreator maksimal ${MAX_CREATOR_SPLIT}%.`);
      return;
    }
    setSavingSplits(true);
    setSplitError("");
    try {
      const data = await api(`/contents/${splitEditor.content.id}/splits`, {
        method: "PUT",
        body: JSON.stringify({
          splits: checkedRows.map((r) => ({
            user_id: r.user_id,
            split_percentage: Number(r.percentage),
          })),
        }),
      });
      setContentsList((list) => list.map((c) => (c.id === data.data.id ? data.data : c)));
      setPesan({ type: "success", text: `Split ${splitEditor.content.name} disimpan.` });
      setSplitEditor(null);
    } catch (err) {
      setSplitError(errMsg(err));
    } finally {
      setSavingSplits(false);
    }
  };

  // ==========================================================================
  // LAPORAN
  // ==========================================================================

  // --- LOGIKA GROUPING LAPORAN HARIAN JADI 1 BARIS PER BULAN ---
  const availableMonths = Array.from(new Set(reportsList.map((r) => r.bulan)));
  const filteredReportsList = filterBulan
    ? reportsList.filter((tx) => tx.bulan === filterBulan)
    : reportsList;

  const groupedReportsMap: { [key: string]: any } = {};

  filteredReportsList.forEach((tx) => {
    const bulanKey = tx.bulan;
    if (!groupedReportsMap[bulanKey]) {
      groupedReportsMap[bulanKey] = {
        bulan: bulanKey,
        items: [],
        totalGross: 0,
        totalSqRevenue: 0,
        creatorBreakdownsMap: {},
      };
    }

    groupedReportsMap[bulanKey].items.push({
      nama_konten: tx.nama_konten,
      total_qty: tx.total_qty,
    });

    groupedReportsMap[bulanKey].totalGross += tx.gross;
    groupedReportsMap[bulanKey].totalSqRevenue += tx.sq_revenue;

    tx.creator_breakdown.forEach((cb: string) => {
      const match = cb.match(/^(.+?)\s*\((.+?)\):\s*\$(.+)$/);
      if (match) {
        const [, cName, cPercent, cAmt] = match;
        const key = `${cName} (${cPercent})`;
        const val = parseFloat(cAmt);
        groupedReportsMap[bulanKey].creatorBreakdownsMap[key] =
          (groupedReportsMap[bulanKey].creatorBreakdownsMap[key] || 0) + val;
      } else {
        groupedReportsMap[bulanKey].creatorBreakdownsMap[cb] =
          groupedReportsMap[bulanKey].creatorBreakdownsMap[cb] || 0;
      }
    });
  });

  const groupedReportsList = Object.values(groupedReportsMap).sort((a: any, b: any) =>
    b.bulan.localeCompare(a.bulan)
  );

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center font-bold text-blue-600">
        Memuat...
      </div>
    );

  const navClass = (tab: Tab) =>
    `text-left px-4 py-3 rounded-xl font-medium flex items-center justify-between ${activeTab === tab ? "bg-blue-50 text-blue-700" : "text-gray-600"}`;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row relative">
      <div className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col z-10">
        <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500 mb-8">
          Admin Panel
        </h1>
        <nav className="flex flex-col gap-2 flex-grow">
          <button onClick={() => switchTab("undangan")} className={navClass("undangan")}>
            <span>Undangan & Pendaftar</span>
            {pendingCount > 0 && (
              <span className="ml-2 rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-white">
                {pendingCount}
              </span>
            )}
          </button>
          <button onClick={() => switchTab("kreator")} className={navClass("kreator")}>
            Kreator
          </button>
          <button onClick={() => switchTab("konten")} className={navClass("konten")}>
            Konten
          </button>
          <button
            onClick={() => {
              switchTab("laporan");
              fetchReports().catch((err) => setPesan({ type: "error", text: errMsg(err) }));
            }}
            className={navClass("laporan")}
          >
            Laporan Penjualan
          </button>
        </nav>
        <div className="mt-8 pt-6 border-t border-gray-100">
          <p className="font-bold text-gray-800 mb-4">{adminName}</p>
          <button
            onClick={handleLogout}
            className="w-full bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-bold"
          >
            Keluar
          </button>
        </div>
      </div>

      <div className="flex-1 p-6 md:p-10 overflow-y-auto">
        {pesan.text && (
          <div
            className={`mb-6 p-4 rounded-xl text-sm font-bold ${PESAN_CLASS[pesan.type] || PESAN_CLASS.success}`}
          >
            {pesan.text}
          </div>
        )}

        {/* TAB UNDANGAN & PENDAFTAR */}
        {activeTab === "undangan" && (
          <div className="max-w-5xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Undangan & Pendaftar</h2>
              <p className="text-sm text-gray-500 font-medium">
                Kreator hanya bisa mendaftar lewat link undangan yang berlaku 7 hari.
              </p>
            </div>

            <form
              onSubmit={handleInviteSubmit}
              className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 flex flex-col sm:flex-row gap-3"
            >
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="email@kreator.com"
                className="flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={busyInvite !== null}
                className="bg-blue-600 text-white px-5 py-2 rounded-xl text-sm font-bold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {busyInvite === "new" ? "Mengirim..." : "Kirim undangan"}
              </button>
            </form>

            <h3 className="text-lg font-bold text-gray-800">Undangan belum dipakai</h3>
            <div className="bg-white rounded-3xl border border-gray-100 overflow-x-auto shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Dikirim</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Kedaluwarsa
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="text-center py-8 text-gray-400 font-bold">
                        Tidak ada undangan yang belum dipakai.
                      </td>
                    </tr>
                  ) : (
                    invitations.map((inv) => (
                      <tr key={inv.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                        <td className="px-6 py-4 text-sm font-bold text-gray-900">{inv.email}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          {formatDateTime(inv.created_at)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          <div className="flex flex-wrap items-center gap-2">
                            {formatDateTime(inv.expires_at)}
                            {inv.expired && (
                              <span className="whitespace-nowrap px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider bg-red-100 text-red-600">
                                Kedaluwarsa
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => handleResendInvite(inv)}
                              disabled={busyInvite !== null}
                              className="whitespace-nowrap text-blue-600 bg-blue-50 px-4 py-1.5 rounded-lg text-sm font-bold disabled:opacity-50"
                            >
                              {busyInvite === inv.id ? "Memproses..." : "Kirim ulang"}
                            </button>
                            <button
                              onClick={() => handleCancelInvite(inv)}
                              disabled={busyInvite !== null}
                              className="bg-red-50 text-red-600 px-4 py-1.5 rounded-lg text-sm font-bold disabled:opacity-50"
                            >
                              Batalkan
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div>
              <h3 className="text-lg font-bold text-gray-800">Pendaftar menunggu persetujuan</h3>
              <p className="text-sm text-gray-500 font-medium">
                Kreator yang sudah mengisi form undangan. Setujui agar bisa login.
              </p>
            </div>
            <div className="bg-white rounded-3xl border border-gray-100 overflow-x-auto shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Nama</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Job Title
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Tanggal Daftar
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pendingUsers.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-gray-400 font-bold">
                        Tidak ada pendaftar yang menunggu persetujuan.
                      </td>
                    </tr>
                  ) : (
                    pendingUsers.map((u) => (
                      <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                        <td className="px-6 py-4 font-bold text-gray-900">{u.name}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">{u.email}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">{u.job_title || "-"}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          {formatDate(u.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => handleApprove(u)}
                              disabled={busyId === u.id}
                              className="bg-green-600 text-white px-4 py-1.5 rounded-lg text-sm font-bold disabled:opacity-50"
                            >
                              Setujui
                            </button>
                            <button
                              onClick={() => handleReject(u)}
                              disabled={busyId === u.id}
                              className="bg-red-50 text-red-600 px-4 py-1.5 rounded-lg text-sm font-bold disabled:opacity-50"
                            >
                              Tolak
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB KREATOR */}
        {activeTab === "kreator" && (
          <div className="max-w-6xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Kreator</h2>
              <p className="text-sm text-gray-500 font-medium">
                Kreator nonaktif tidak bisa login dan tidak bisa ditautkan ke konten baru.
              </p>
            </div>
            <div className="bg-white rounded-3xl border border-gray-100 overflow-x-auto shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Nama</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Job Title
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Konten
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {creators.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-gray-400 font-bold">
                        Belum ada kreator yang disetujui.
                      </td>
                    </tr>
                  ) : (
                    creators.map((u) => {
                      const isActive = u.account_status === "Active";
                      return (
                        <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                          <td className="px-6 py-4 font-bold text-gray-900">{u.name}</td>
                          <td className="px-6 py-4 text-sm text-gray-700">{u.email}</td>
                          <td className="px-6 py-4">
                            <select
                              value={u.job_title || ""}
                              disabled={busyId === u.id}
                              onChange={(e) => handleJobChange(u, e.target.value)}
                              className="rounded-lg border border-gray-300 px-2 py-1 text-sm bg-white disabled:opacity-50"
                            >
                              {!JOB_OPTIONS.includes(u.job_title || "") && (
                                <option value={u.job_title || ""} disabled>
                                  {u.job_title || "-"}
                                </option>
                              )}
                              {JOB_OPTIONS.map((j) => (
                                <option key={j} value={j}>
                                  {j}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => handleToggleStatus(u)}
                              disabled={busyId === u.id}
                              title={isActive ? "Klik untuk menonaktifkan" : "Klik untuk mengaktifkan"}
                              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-bold disabled:opacity-50 ${isActive ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-600"}`}
                            >
                              <span
                                className={`h-2 w-2 rounded-full ${isActive ? "bg-green-500" : "bg-gray-400"}`}
                              />
                              {isActive ? "Aktif" : "Nonaktif"}
                            </button>
                          </td>
                          <td className="px-6 py-4 text-center text-sm font-bold text-gray-700">
                            {linkedCount[u.id] || 0}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB KONTEN (READ-ONLY DARI PATHWAY) */}
        {activeTab === "konten" && (
          <div className="max-w-7xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Konten</h2>
              <p className="text-sm text-gray-500 font-medium">
                Data konten disinkronkan otomatis dari Pathway setiap hari.
                {lastSynced && ` Terakhir sinkron: ${formatDateTime(lastSynced)}.`}
              </p>
            </div>
            <div className="bg-white rounded-3xl border border-gray-100 overflow-x-auto shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Nama</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">
                      Pack Type
                    </th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Tier</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Harga</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Rilis</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Total Unit
                    </th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase">Kreator</th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {contentsList.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-gray-400 font-bold">
                        Belum ada konten dari Pathway.
                      </td>
                    </tr>
                  ) : (
                    contentsList.map((c) => (
                      <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50/50 align-top">
                        <td className="px-4 py-4 font-bold text-gray-900 text-sm">{c.name}</td>
                        <td className="px-4 py-4">
                          <span
                            className={`whitespace-nowrap px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${STATUS_BADGE[c.status || ""] || "bg-gray-100 text-gray-600"}`}
                          >
                            {c.status || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-sm text-gray-700">{c.pack_type || "-"}</td>
                        <td className="px-4 py-4 text-sm text-gray-700">{c.tier ?? "-"}</td>
                        <td className="px-4 py-4 text-sm text-gray-700">
                          {c.price != null ? `$${c.price.toFixed(2)}` : "-"}
                        </td>
                        <td className="px-4 py-4 text-sm text-gray-700 whitespace-nowrap">
                          {c.release_date || "-"}
                        </td>
                        <td className="px-4 py-4 text-sm font-bold text-gray-800 text-right">
                          {c.units_total.toLocaleString("id-ID")}
                        </td>
                        <td className="px-4 py-4">
                          {c.splits.length === 0 ? (
                            <span className="text-xs text-gray-400 font-bold">Belum ditautkan</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {c.splits.map((s) => (
                                <span
                                  key={s.user_id}
                                  className="whitespace-nowrap text-xs bg-green-50 px-2 py-1 rounded-lg text-green-700 font-bold"
                                >
                                  {s.user_name} ({s.split_percentage}%)
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 text-center">
                          <button
                            onClick={() => openSplitEditor(c)}
                            className="whitespace-nowrap text-blue-600 font-bold text-sm bg-blue-50 px-3 py-1 rounded-lg"
                          >
                            Atur split
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB LAPORAN (DIGROUPING 1 BARIS PER BULAN) */}
        {activeTab === "laporan" && (
          <div className="max-w-6xl space-y-6">
            <div className="flex justify-between items-end mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">
                  Rekapitulasi Penjualan Bulanan
                </h2>
                <p className="text-sm text-gray-500 font-medium">
                  Data terkelompokkan per bulan. Silakan filter bulan yang ingin dilihat.
                </p>
              </div>
              <select
                value={filterBulan}
                onChange={(e) => setFilterBulan(e.target.value)}
                className="bg-white border border-gray-200 text-gray-800 rounded-lg p-2 px-4 font-bold shadow-sm outline-none cursor-pointer"
              >
                <option value="">-- Semua Bulan --</option>
                {availableMonths.map((m: any) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Bulan</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Rincian Konten & Qty
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Total Gross ($)
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Squareclouds (20%)
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Rincian Kreator
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {groupedReportsList.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-gray-400 font-bold">
                        Tidak ada data untuk bulan ini.
                      </td>
                    </tr>
                  ) : (
                    groupedReportsList.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50 align-top">
                        <td className="px-6 py-4 font-bold text-gray-900 text-base">{row.bulan}</td>
                        <td className="px-6 py-4 space-y-2">
                          {row.items.map((item: any, idx: number) => (
                            <div key={idx} className="border-b border-gray-100 pb-1 last:border-0">
                              <p className="font-bold text-gray-800 text-sm">{item.nama_konten}</p>
                              <p className="text-xs text-gray-500 font-medium">
                                {item.total_qty} copy terjual
                              </p>
                            </div>
                          ))}
                        </td>
                        <td className="px-6 py-4 text-sm font-bold text-gray-800">
                          ${row.totalGross.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 text-sm font-black text-blue-600">
                          ${row.totalSqRevenue.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 text-sm space-y-1">
                          {Object.keys(row.creatorBreakdownsMap).length === 0 ? (
                            <div className="text-xs bg-gray-100 p-2 rounded-lg text-gray-600 font-bold">
                              Tidak ada kreator (100% SC)
                            </div>
                          ) : (
                            Object.entries(row.creatorBreakdownsMap).map(
                              ([cLabel, cVal]: [string, any], idx: number) => (
                                <div
                                  key={idx}
                                  className="text-xs bg-green-50 p-2 rounded-lg text-green-700 font-bold"
                                >
                                  {cLabel}: ${cVal.toFixed(2)}
                                </div>
                              )
                            )
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* MODAL ATUR SPLIT */}
      {splitEditor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-3xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-1">Atur Split</h3>
            <p className="text-sm text-gray-500 mb-6">{splitEditor.content.name}</p>

            {droppedSplits.length > 0 && (
              <div className="mb-4 rounded-xl bg-amber-50 p-3 text-xs font-bold text-amber-700">
                Split untuk kreator yang tidak aktif akan dihapus saat disimpan:{" "}
                {droppedSplits.map((s) => `${s.user_name} (${s.split_percentage}%)`).join(", ")}.
              </div>
            )}

            {splitEditor.rows.length === 0 ? (
              <p className="text-sm text-gray-400 font-bold">Belum ada kreator aktif.</p>
            ) : (
              <div className="space-y-2">
                {splitEditor.rows.map((r) => (
                  <label
                    key={r.user_id}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${r.checked ? "border-blue-200 bg-blue-50/50" : "border-gray-100"}`}
                  >
                    <input
                      type="checkbox"
                      checked={r.checked}
                      onChange={(e) => updateSplitRow(r.user_id, { checked: e.target.checked })}
                      className="h-4 w-4"
                    />
                    <span className="flex-1 text-sm font-bold text-gray-800">{r.name}</span>
                    <input
                      type="number"
                      min="0"
                      max={MAX_CREATOR_SPLIT}
                      step="0.1"
                      disabled={!r.checked}
                      value={r.percentage}
                      onChange={(e) => updateSplitRow(r.user_id, { percentage: e.target.value })}
                      className="w-20 rounded-lg border border-gray-300 px-2 py-1 text-sm font-bold text-green-600 disabled:bg-gray-50 disabled:text-gray-300"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </label>
                ))}
              </div>
            )}

            <div className="mt-6 space-y-1 border-t pt-4 text-sm">
              <div className="flex justify-between font-bold">
                <span className="text-gray-600">Total kreator</span>
                <span className={overLimit ? "text-red-600" : "text-gray-900"}>
                  {splitTotal}% / {MAX_CREATOR_SPLIT}%
                </span>
              </div>
              <div className="flex justify-between font-bold">
                <span className="text-gray-600">Squareclouds</span>
                <span className="text-blue-600">{roundPct(100 - splitTotal)}%</span>
              </div>
              {overLimit && (
                <p className="text-xs font-bold text-red-600">
                  Total kreator melebihi {MAX_CREATOR_SPLIT}%. Kurangi persentasenya.
                </p>
              )}
            </div>

            {splitError && (
              <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm font-bold text-red-600">
                {splitError}
              </div>
            )}

            <div className="flex gap-3 pt-4 border-t mt-6">
              <button
                type="button"
                onClick={handleSaveSplits}
                disabled={savingSplits || overLimit || hasEmptyPct}
                className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-bold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {savingSplits ? "Menyimpan..." : "Simpan"}
              </button>
              <button
                type="button"
                onClick={() => setSplitEditor(null)}
                className="px-4 py-2.5 rounded-xl font-bold bg-gray-100 hover:bg-gray-200 transition"
              >
                Batal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
