"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/auth";
import {
  JOB_OPTIONS,
  PAYOUT_FIELDS,
  PAYOUT_FIELD_LABEL,
  PAYOUT_METHOD_LABEL,
  type PayoutMethod,
  formatIdr,
  formatMonth,
  formatUsd,
} from "@/lib/portal";

type Tab = "undangan" | "kreator" | "konten" | "laporan" | "pengaturan";

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
  // null untuk akun lama yang dibuat sebelum ada username.
  username: string | null;
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
  // All-time, dihitung backend/earnings.py.
  gross_usd: number;
  net_usd: number;
  splits: ContentSplit[];
};

type SplitRow = { user_id: number; name: string; checked: boolean; percentage: string };

type Payout = {
  id: number;
  paid_at: string;
  amount_usd: number;
  idr_rate: number | null;
  amount_idr: number | null;
  method: PayoutMethod;
  note: string | null;
  // Snapshot data payout saat dibayar.
  details: Record<string, string> | null;
  created_at: string;
  // Waktu email notifikasi terkirim; null = gagal / belum terkirim.
  notified_at: string | null;
};

// Respons /users/{id}/earnings (creator_summary versi admin).
type CreatorEarnings = {
  total_earned_usd: number;
  total_paid_usd: number;
  outstanding_usd: number;
  idr_rate: number;
  total_earned_idr: number | null;
  total_paid_idr: number | null;
  outstanding_idr: number | null;
  by_content: {
    content_id: number;
    name: string;
    status: string | null;
    units: number;
    gross_usd: number;
    net_usd: number;
    split_pct: number;
    share_usd: number;
  }[];
  payouts: Payout[];
  payout_method: PayoutMethod | null;
  payout_details: Record<string, string> | null;
};

type PayoutForm = { amount: string; note: string; paid_at: string };

type MoneyTotals = {
  units: number;
  gross_usd: number;
  net80_usd: number;
  net_usd: number;
  creators_share_usd: number;
  squareclouds_share_usd: number;
};

type ReportContent = MoneyTotals & {
  content_id: number;
  name: string;
  status: string | null;
  creators: { user_id: number; name: string; split_pct: number; share_usd: number }[];
};

// Respons /admin-reports/ (earnings.admin_overview).
type Report = {
  paypal_fee_pct: number;
  totals: MoneyTotals;
  by_content: ReportContent[];
  by_month: (MoneyTotals & { month: string; by_content: ReportContent[] })[];
};

type SettingsForm = { paypal_fee_pct: string; idr_rate: string };

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

// YYYY-MM-DD hari ini (zona waktu browser), untuk default tanggal bayar.
const todayIso = () => new Date().toLocaleDateString("en-CA");

const payoutDetailsText = (method: PayoutMethod, details: Record<string, string> | null) =>
  (PAYOUT_FIELDS[method] || [])
    .map((f) => details?.[f])
    .filter(Boolean)
    .join(" · ") || "-";

// Sel Unit, Gross, Net, Bagian Kreator, Squareclouds di tabel laporan.
function MoneyCells({ totals, strong = false }: { totals: MoneyTotals; strong?: boolean }) {
  const cell = `px-6 py-3 text-sm text-right whitespace-nowrap ${strong ? "font-black" : "font-bold"}`;
  return (
    <>
      <td className={`${cell} text-gray-700`}>{totals.units.toLocaleString("id-ID")}</td>
      <td className={`${cell} text-gray-800`}>{formatUsd(totals.gross_usd)}</td>
      <td className={`${cell} text-gray-800`}>{formatUsd(totals.net_usd)}</td>
      <td className={`${cell} text-green-600`}>{formatUsd(totals.creators_share_usd)}</td>
      <td className={`${cell} text-blue-600`}>{formatUsd(totals.squareclouds_share_usd)}</td>
    </>
  );
}

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
  const [report, setReport] = useState<Report | null>(null);

  // State untuk filter bulan laporan
  const [filterBulan, setFilterBulan] = useState<string>("");

  const [settingsForm, setSettingsForm] = useState<SettingsForm>({ paypal_fee_pct: "", idr_rate: "" });
  const [savingSettings, setSavingSettings] = useState(false);

  // Panel Pendapatan & Payout satu kreator (data null = sedang dimuat).
  const [earningsPanel, setEarningsPanel] = useState<{
    user: Creator;
    data: CreatorEarnings | null;
    error: string;
  } | null>(null);
  const [payoutForm, setPayoutForm] = useState<PayoutForm>({ amount: "", note: "", paid_at: "" });
  const [savingPayout, setSavingPayout] = useState(false);
  const [deletingPayoutId, setDeletingPayoutId] = useState<number | null>(null);
  const [notifyingPayoutId, setNotifyingPayoutId] = useState<number | null>(null);
  const [payoutPesan, setPayoutPesan] = useState({ type: "", text: "" });

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
    (path: string, init?: RequestInit) => apiFetch(path, init, handleLogout),
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
    const data: { data: Report } = await api("/admin-reports/");
    setReport(data.data);
    // Default: bulan terbaru (by_month urut dari yang terbaru). Pilihan admin
    // dipertahankan selama bulan itu masih ada.
    const months = data.data.by_month.map((m) => m.month);
    setFilterBulan((current) =>
      current && months.includes(current) ? current : (months[0] ?? "")
    );
  };

  const fetchSettings = async () => {
    const data = await api("/settings");
    setSettingsForm({ paypal_fee_pct: String(data.paypal_fee_pct), idr_rate: String(data.idr_rate) });
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    if (!token || role !== "Admin") {
      router.push("/login");
      return;
    }

    setAdminName(localStorage.getItem("name") || "Admin");
    Promise.all([
      fetchInvitations(),
      fetchUsers(),
      fetchContents(),
      fetchReports(),
      fetchSettings(),
    ])
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

  // runUserAction memuat ulang daftar kreator dan konten: split kreator ini
  // ikut terhapus di backend.
  const handleDelete = (u: Creator) => {
    const linked = linkedCount[u.id] || 0;
    const linkedText =
      linked > 0
        ? `Tertaut ke ${linked} konten; split-nya di konten tersebut ikut dihapus.`
        : "Belum tertaut ke konten mana pun.";
    if (
      !confirm(
        `Hapus akun ${u.name} (${u.email}) secara permanen?\n\n${linkedText}\n` +
          "Riwayat payout kreator ini juga ikut dihapus. Tindakan ini tidak bisa dibatalkan."
      )
    )
      return;
    runUserAction(
      u,
      () => api(`/users/${u.id}`, { method: "DELETE" }),
      `Akun ${u.name} dihapus.`
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
  // PENDAPATAN & PAYOUT KREATOR
  // ==========================================================================

  const loadEarnings = async (u: Creator) => {
    try {
      const data: CreatorEarnings = await api(`/users/${u.id}/earnings`);
      // Abaikan respons kalau panel sudah ditutup / pindah ke kreator lain.
      setEarningsPanel((p) => (p && p.user.id === u.id ? { user: u, data, error: "" } : p));
      setPayoutForm({
        amount: data.outstanding_usd > 0 ? data.outstanding_usd.toFixed(2) : "",
        note: "",
        paid_at: todayIso(),
      });
    } catch (err) {
      setEarningsPanel((p) => (p && p.user.id === u.id ? { ...p, error: errMsg(err) } : p));
    }
  };

  const openEarnings = (u: Creator) => {
    setEarningsPanel({ user: u, data: null, error: "" });
    setPayoutPesan({ type: "", text: "" });
    loadEarnings(u);
  };

  const handleRecordPayout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!earningsPanel) return;
    const { user } = earningsPanel;
    setSavingPayout(true);
    setPayoutPesan({ type: "", text: "" });
    try {
      const data = await api("/payouts", {
        method: "POST",
        body: JSON.stringify({
          user_id: user.id,
          amount_usd: Number(payoutForm.amount),
          note: payoutForm.note.trim() || null,
          paid_at: payoutForm.paid_at || null,
        }),
      });
      // Payout tetap tercatat walau email notifikasinya gagal.
      setPayoutPesan({ type: data.notified ? "success" : "warning", text: data.message });
      await loadEarnings(user);
    } catch (err) {
      setPayoutPesan({ type: "error", text: errMsg(err) });
    } finally {
      setSavingPayout(false);
    }
  };

  const handleResendPayoutEmail = async (p: Payout) => {
    if (!earningsPanel) return;
    const { user } = earningsPanel;
    setNotifyingPayoutId(p.id);
    setPayoutPesan({ type: "", text: "" });
    try {
      const data = await api(`/payouts/${p.id}/notify`, { method: "POST" });
      setPayoutPesan({ type: "success", text: data.message });
      await loadEarnings(user);
    } catch (err) {
      setPayoutPesan({ type: "error", text: errMsg(err) });
    } finally {
      setNotifyingPayoutId(null);
    }
  };

  const handleDeletePayout = async (p: Payout) => {
    if (!earningsPanel) return;
    if (
      !confirm(
        `Hapus payout ${formatUsd(p.amount_usd)} tanggal ${formatDate(p.paid_at)}?\n\n` +
          "Gunakan hanya untuk koreksi salah input. Saldo tertunda kreator akan bertambah lagi."
      )
    )
      return;
    const { user } = earningsPanel;
    setDeletingPayoutId(p.id);
    setPayoutPesan({ type: "", text: "" });
    try {
      const data = await api(`/payouts/${p.id}`, { method: "DELETE" });
      setPayoutPesan({ type: "success", text: data.message });
      await loadEarnings(user);
    } catch (err) {
      setPayoutPesan({ type: "error", text: errMsg(err) });
    } finally {
      setDeletingPayoutId(null);
    }
  };

  // ==========================================================================
  // PENGATURAN
  // ==========================================================================

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setPesan({ type: "", text: "" });
    try {
      const data = await api("/settings", {
        method: "PUT",
        body: JSON.stringify({
          paypal_fee_pct: Number(settingsForm.paypal_fee_pct),
          idr_rate: Number(settingsForm.idr_rate),
        }),
      });
      setSettingsForm({
        paypal_fee_pct: String(data.data.paypal_fee_pct),
        idr_rate: String(data.data.idr_rate),
      });
      setPesan({ type: "success", text: data.message });
      // Gross/net konten dan laporan bergantung pada fee PayPal.
      await Promise.all([fetchContents(), fetchReports()]);
    } catch (err) {
      setPesan({ type: "error", text: errMsg(err) });
    } finally {
      setSavingSettings(false);
    }
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

  // Semua angka sudah dihitung backend (earnings.admin_overview): per bulan
  // (urut terbaru) dengan rincian per konten, plus total keseluruhan.
  const reportMonths = report?.by_month ?? [];
  const availableMonths = reportMonths.map((m) => m.month);
  const shownMonths = filterBulan
    ? reportMonths.filter((m) => m.month === filterBulan)
    : reportMonths;
  const shownTotals: MoneyTotals | null = filterBulan
    ? (shownMonths[0] ?? null)
    : (report?.totals ?? null);

  const earningsData = earningsPanel?.data ?? null;
  // Sama dengan syarat POST /payouts di backend.
  const canRecordPayout =
    !!earningsData?.payout_method &&
    earningsPanel?.user.account_status === "Active" &&
    earningsData.outstanding_usd > 0;

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
          <button onClick={() => switchTab("pengaturan")} className={navClass("pengaturan")}>
            Pengaturan
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
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Username
                    </th>
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
                      <td colSpan={6} className="text-center py-8 text-gray-400 font-bold">
                        Tidak ada pendaftar yang menunggu persetujuan.
                      </td>
                    </tr>
                  ) : (
                    pendingUsers.map((u) => (
                      <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                        <td className="px-6 py-4 font-bold text-gray-900">{u.name}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">{u.username || "-"}</td>
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
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Username
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Job Title
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Konten
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {creators.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-gray-400 font-bold">
                        Belum ada kreator yang disetujui.
                      </td>
                    </tr>
                  ) : (
                    creators.map((u) => {
                      const isActive = u.account_status === "Active";
                      return (
                        <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                          <td className="px-6 py-4 font-bold text-gray-900">{u.name}</td>
                          <td className="px-6 py-4 text-sm text-gray-700">{u.username || "-"}</td>
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
                          <td className="px-6 py-4">
                            <div className="flex justify-center gap-2">
                              <button
                                onClick={() => openEarnings(u)}
                                className="whitespace-nowrap text-blue-600 bg-blue-50 px-4 py-1.5 rounded-lg text-sm font-bold"
                              >
                                Pendapatan & Payout
                              </button>
                              <button
                                onClick={() => handleDelete(u)}
                                disabled={busyId === u.id}
                                className="bg-red-50 text-red-600 px-4 py-1.5 rounded-lg text-sm font-bold disabled:opacity-50"
                              >
                                Hapus
                              </button>
                            </div>
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
                {lastSynced && ` Terakhir sinkron: ${formatDateTime(lastSynced)}.`} Gross & Net
                dihitung sejak rilis; Net = 80% gross dikurangi fee PayPal.
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
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Gross
                    </th>
                    <th className="px-4 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Net
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
                      <td colSpan={11} className="text-center py-8 text-gray-400 font-bold">
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
                        <td className="px-4 py-4 text-sm text-gray-700 text-right whitespace-nowrap">
                          {formatUsd(c.gross_usd)}
                        </td>
                        <td className="px-4 py-4 text-sm font-bold text-gray-800 text-right whitespace-nowrap">
                          {formatUsd(c.net_usd)}
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

        {/* TAB LAPORAN (PER BULAN, RINCIAN PER KONTEN) */}
        {activeTab === "laporan" && (
          <div className="max-w-7xl space-y-6">
            <div className="flex flex-wrap justify-between items-end gap-4 mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">
                  Rekapitulasi Penjualan Bulanan
                </h2>
                <p className="text-sm text-gray-500 font-medium">
                  Net = 80% gross dari Pathway dikurangi fee PayPal{" "}
                  {report ? `${report.paypal_fee_pct}%` : "-"}. Bagian kreator = net × split;
                  sisanya bagian Squareclouds.
                </p>
              </div>
              <select
                value={filterBulan}
                onChange={(e) => setFilterBulan(e.target.value)}
                className="bg-white border border-gray-200 text-gray-800 rounded-lg p-2 px-4 font-bold shadow-sm outline-none cursor-pointer"
              >
                <option value="">-- Semua Bulan --</option>
                {availableMonths.map((m) => (
                  <option key={m} value={m}>
                    {formatMonth(m)}
                  </option>
                ))}
              </select>
            </div>

            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">
                      Bulan / Konten
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Unit
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Gross
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Net
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Bagian Kreator
                    </th>
                    <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">
                      Squareclouds
                    </th>
                  </tr>
                </thead>
                {shownMonths.length === 0 ? (
                  <tbody>
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-gray-400 font-bold">
                        Tidak ada data untuk bulan ini.
                      </td>
                    </tr>
                  </tbody>
                ) : (
                  shownMonths.map((m) => (
                    <tbody key={m.month} className="border-b border-gray-100">
                      <tr className="bg-blue-50/40">
                        <td className="px-6 py-3 font-black text-gray-900">
                          {formatMonth(m.month)}
                        </td>
                        <MoneyCells totals={m} strong />
                      </tr>
                      {m.by_content.map((c) => (
                        <tr key={c.content_id} className="border-t border-gray-50 align-top">
                          <td className="py-3 pl-10 pr-6">
                            <p className="text-sm font-bold text-gray-800">{c.name}</p>
                            {c.creators.length === 0 ? (
                              <p className="text-xs font-bold text-gray-400">
                                Tidak ada kreator (100% SC)
                              </p>
                            ) : (
                              <div className="mt-1 flex flex-wrap gap-1">
                                {c.creators.map((cr) => (
                                  <span
                                    key={cr.user_id}
                                    className="whitespace-nowrap text-xs bg-green-50 px-2 py-0.5 rounded-lg text-green-700 font-bold"
                                  >
                                    {cr.name} ({cr.split_pct}%): {formatUsd(cr.share_usd)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                          <MoneyCells totals={c} />
                        </tr>
                      ))}
                    </tbody>
                  ))
                )}
                {shownTotals && (
                  <tfoot className="bg-gray-50 border-t-2 border-gray-200">
                    <tr>
                      <td className="px-6 py-4 text-sm font-black uppercase text-gray-900">
                        Total {filterBulan ? formatMonth(filterBulan) : "semua bulan"}
                      </td>
                      <MoneyCells totals={shownTotals} strong />
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        )}

        {/* TAB PENGATURAN */}
        {activeTab === "pengaturan" && (
          <div className="max-w-2xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Pengaturan</h2>
              <p className="text-sm text-gray-500 font-medium">
                Berlaku langsung untuk semua perhitungan pendapatan kreator dan laporan.
              </p>
            </div>
            <form
              onSubmit={handleSaveSettings}
              className="bg-white rounded-3xl border border-gray-100 shadow-sm p-6 space-y-5"
            >
              <label className="block">
                <span className="text-sm font-bold text-gray-800">Fee PayPal (%)</span>
                <input
                  type="number"
                  required
                  min="0"
                  max="100"
                  step="any"
                  value={settingsForm.paypal_fee_pct}
                  onChange={(e) => setSettingsForm((s) => ({ ...s, paypal_fee_pct: e.target.value }))}
                  className="mt-1 w-full rounded-xl border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <span className="mt-1 block text-xs text-gray-500">
                  Dipotong saat Pathway membayar Squareclouds: net = 80% gross × (1 − fee).
                </span>
              </label>
              <label className="block">
                <span className="text-sm font-bold text-gray-800">Kurs IDR (Rp per $1)</span>
                <input
                  type="number"
                  required
                  min="0"
                  step="any"
                  value={settingsForm.idr_rate}
                  onChange={(e) => setSettingsForm((s) => ({ ...s, idr_rate: e.target.value }))}
                  className="mt-1 w-full rounded-xl border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <span className="mt-1 block text-xs text-gray-500">
                  Untuk payout bank/e-wallet. Kurs ikut disimpan di tiap payout saat dicatat, jadi
                  payout lama tidak berubah.
                </span>
              </label>
              <button
                type="submit"
                disabled={savingSettings}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {savingSettings ? "Menyimpan..." : "Simpan"}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* MODAL PENDAPATAN & PAYOUT */}
      {earningsPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 md:p-8 rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start gap-4 mb-6">
              <div>
                <h3 className="text-xl font-bold">Pendapatan & Payout</h3>
                <p className="text-sm text-gray-500">
                  {earningsPanel.user.name} · {earningsPanel.user.email}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEarningsPanel(null)}
                className="px-4 py-2 rounded-xl text-sm font-bold bg-gray-100 hover:bg-gray-200 transition"
              >
                Tutup
              </button>
            </div>

            {earningsPanel.error ? (
              <div className="rounded-xl bg-red-50 p-3 text-sm font-bold text-red-600">
                {earningsPanel.error}
              </div>
            ) : !earningsData ? (
              <p className="text-sm font-bold text-blue-600">Memuat...</p>
            ) : (
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {(
                    [
                      ["Total diperoleh", earningsData.total_earned_usd, earningsData.total_earned_idr],
                      ["Sudah dibayar", earningsData.total_paid_usd, earningsData.total_paid_idr],
                      ["Saldo tertunda", earningsData.outstanding_usd, earningsData.outstanding_idr],
                    ] as const
                  ).map(([label, usd, idr]) => (
                    <div key={label} className="rounded-2xl bg-gray-50 p-4">
                      <p className="text-xs font-bold uppercase text-gray-400">{label}</p>
                      <p className="text-2xl font-black text-gray-900">{formatUsd(usd)}</p>
                      {idr !== null && (
                        <p className="text-xs font-bold text-gray-500">≈ {formatIdr(idr)}</p>
                      )}
                    </div>
                  ))}
                </div>

                {!earningsData.payout_method && (
                  <div className="rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-700">
                    Kreator ini belum mengisi metode payout, jadi pembayaran belum bisa dicatat.
                    Minta kreator mengisinya di dashboard mereka.
                  </div>
                )}
                {earningsPanel.user.account_status !== "Active" && (
                  <div className="rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-700">
                    Kreator nonaktif: pembayaran hanya bisa dicatat untuk kreator berstatus Active.
                  </div>
                )}

                {earningsData.payout_method && (
                  <div className="rounded-2xl border border-gray-100 p-4">
                    <h4 className="text-sm font-bold text-gray-800 mb-2">Data payout</h4>
                    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
                      <dt className="text-gray-500">Metode</dt>
                      <dd className="font-bold text-gray-900">
                        {PAYOUT_METHOD_LABEL[earningsData.payout_method]}
                      </dd>
                      {PAYOUT_FIELDS[earningsData.payout_method].map((f) => (
                        <Fragment key={f}>
                          <dt className="text-gray-500">{PAYOUT_FIELD_LABEL[f]}</dt>
                          <dd className="font-mono font-bold text-gray-900 select-all break-all">
                            {earningsData.payout_details?.[f] || "-"}
                          </dd>
                        </Fragment>
                      ))}
                    </dl>
                  </div>
                )}

                <div>
                  <h4 className="text-sm font-bold text-gray-800 mb-2">Per konten (sejak rilis)</h4>
                  <div className="rounded-2xl border border-gray-100 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase">Konten</th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Unit
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Gross
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Net
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Split
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Bagian kreator
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {earningsData.by_content.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-4 text-center text-gray-400 font-bold">
                              Belum tertaut ke konten mana pun.
                            </td>
                          </tr>
                        ) : (
                          earningsData.by_content.map((c) => (
                            <tr key={c.content_id} className="border-t border-gray-50">
                              <td className="px-4 py-2 font-bold text-gray-800">{c.name}</td>
                              <td className="px-4 py-2 text-right">{c.units.toLocaleString("id-ID")}</td>
                              <td className="px-4 py-2 text-right">{formatUsd(c.gross_usd)}</td>
                              <td className="px-4 py-2 text-right">{formatUsd(c.net_usd)}</td>
                              <td className="px-4 py-2 text-right">{c.split_pct}%</td>
                              <td className="px-4 py-2 text-right font-black text-green-600">
                                {formatUsd(c.share_usd)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <form
                  onSubmit={handleRecordPayout}
                  className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4 space-y-3"
                >
                  <h4 className="text-sm font-bold text-gray-800">Catat pembayaran</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <label className="block">
                      <span className="text-xs font-bold text-gray-500 uppercase">Jumlah (USD)</span>
                      <input
                        type="number"
                        required
                        min="0.01"
                        max={earningsData.outstanding_usd > 0 ? earningsData.outstanding_usd : undefined}
                        step="0.01"
                        disabled={!canRecordPayout}
                        value={payoutForm.amount}
                        onChange={(e) => setPayoutForm((f) => ({ ...f, amount: e.target.value }))}
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-100"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold text-gray-500 uppercase">Tanggal bayar</span>
                      <input
                        type="date"
                        required
                        disabled={!canRecordPayout}
                        value={payoutForm.paid_at}
                        onChange={(e) => setPayoutForm((f) => ({ ...f, paid_at: e.target.value }))}
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-100"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold text-gray-500 uppercase">Catatan</span>
                      <input
                        type="text"
                        disabled={!canRecordPayout}
                        value={payoutForm.note}
                        onChange={(e) => setPayoutForm((f) => ({ ...f, note: e.target.value }))}
                        placeholder="Opsional, terlihat oleh kreator"
                        className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm bg-white disabled:bg-gray-100"
                      />
                    </label>
                  </div>
                  <p className="text-xs text-gray-500">
                    Default jumlah = saldo tertunda. Payout bank/e-wallet dicatat juga dalam rupiah
                    dengan kurs {formatIdr(earningsData.idr_rate)}/$.
                  </p>
                  {payoutPesan.text && (
                    <div
                      className={`rounded-xl p-3 text-sm font-bold ${PESAN_CLASS[payoutPesan.type] || PESAN_CLASS.success}`}
                    >
                      {payoutPesan.text}
                    </div>
                  )}
                  <button
                    type="submit"
                    disabled={!canRecordPayout || savingPayout}
                    className="bg-blue-600 text-white px-5 py-2 rounded-xl text-sm font-bold hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {savingPayout ? "Menyimpan..." : "Catat pembayaran"}
                  </button>
                </form>

                <div>
                  <h4 className="text-sm font-bold text-gray-800 mb-2">Riwayat payout</h4>
                  <div className="rounded-2xl border border-gray-100 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase">Tanggal</th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Jumlah
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase text-right">
                            Rupiah
                          </th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase">Tujuan</th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase">Catatan</th>
                          <th className="px-4 py-2 text-xs font-bold text-gray-500 uppercase">Email</th>
                          <th className="px-4 py-2" />
                        </tr>
                      </thead>
                      <tbody>
                        {earningsData.payouts.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="px-4 py-4 text-center text-gray-400 font-bold">
                              Belum ada payout.
                            </td>
                          </tr>
                        ) : (
                          earningsData.payouts.map((p) => (
                            <tr key={p.id} className="border-t border-gray-50 align-top">
                              <td className="px-4 py-2 whitespace-nowrap">{formatDate(p.paid_at)}</td>
                              <td className="px-4 py-2 text-right font-black text-gray-900">
                                {formatUsd(p.amount_usd)}
                              </td>
                              <td className="px-4 py-2 text-right whitespace-nowrap">
                                {p.amount_idr !== null ? (
                                  <>
                                    {formatIdr(p.amount_idr)}
                                    {p.idr_rate !== null && (
                                      <span className="block text-xs text-gray-400">
                                        kurs {formatIdr(p.idr_rate)}/$
                                      </span>
                                    )}
                                  </>
                                ) : (
                                  "-"
                                )}
                              </td>
                              <td className="px-4 py-2">
                                <span className="font-bold">
                                  {PAYOUT_METHOD_LABEL[p.method] || p.method}
                                </span>
                                <span className="block text-xs text-gray-500 break-all">
                                  {payoutDetailsText(p.method, p.details)}
                                </span>
                              </td>
                              <td className="px-4 py-2 text-gray-600">{p.note || "-"}</td>
                              <td className="px-4 py-2">
                                {p.notified_at ? (
                                  <span
                                    title={`Terkirim ${formatDateTime(p.notified_at)}`}
                                    className="whitespace-nowrap rounded bg-green-100 px-2 py-1 text-[10px] font-black uppercase tracking-wider text-green-700"
                                  >
                                    ✓ Email terkirim
                                  </span>
                                ) : (
                                  <div className="flex flex-col items-start gap-1">
                                    <span className="whitespace-nowrap rounded bg-red-100 px-2 py-1 text-[10px] font-black uppercase tracking-wider text-red-600">
                                      ✕ Email gagal
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => handleResendPayoutEmail(p)}
                                      disabled={notifyingPayoutId !== null}
                                      className="whitespace-nowrap text-xs font-bold text-blue-600 hover:underline disabled:opacity-50"
                                    >
                                      {notifyingPayoutId === p.id ? "Mengirim..." : "Kirim ulang email"}
                                    </button>
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-2 text-right">
                                <button
                                  type="button"
                                  onClick={() => handleDeletePayout(p)}
                                  disabled={deletingPayoutId !== null}
                                  className="bg-red-50 text-red-600 px-3 py-1 rounded-lg text-xs font-bold disabled:opacity-50"
                                >
                                  {deletingPayoutId === p.id ? "Menghapus..." : "Hapus"}
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
