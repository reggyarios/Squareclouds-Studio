"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { apiFetch } from "@/lib/auth";
import {
  EWALLET_PROVIDERS,
  MASKED_PAYOUT_FIELDS,
  PAYOUT_FIELDS,
  PAYOUT_FIELD_LABEL,
  PAYOUT_METHOD_LABEL,
  type PayoutMethod,
  formatIdr,
  formatMonth,
  formatUsd,
} from "@/lib/portal";

type Payout = {
  id: number;
  paid_at: string;
  amount_usd: number;
  idr_rate: number | null;
  amount_idr: number | null;
  method: PayoutMethod;
  note: string | null;
};

// Respons /creator-dashboard/: hanya unit dan bagian kreator. Semua angka
// uang sudah dihitung backend (earnings.py).
type Dashboard = {
  nama: string;
  job_title: string | null;
  proyek: { name: string; status: string | null; pack_type: string | null; release_date: string | null }[];
  grafik_harian: { date: string; content_name: string; quantity: number }[];
  total_earned_usd: number;
  total_paid_usd: number;
  outstanding_usd: number;
  idr_rate: number;
  // null kalau metode payout PayPal atau belum diisi.
  total_earned_idr: number | null;
  total_paid_idr: number | null;
  outstanding_idr: number | null;
  by_content: { content_id: number; name: string; status: string | null; units: number; share_usd: number }[];
  by_month: { month: string; units: number; share_usd: number }[];
  payouts: Payout[];
};

type PayoutPreference = {
  payout_method: PayoutMethod | null;
  payout_details_masked: Record<string, string> | null;
};

type PayoutForm = { method: PayoutMethod; details: Record<string, string> };

const errMsg = (err: unknown) => (err instanceof Error ? err.message : "Terjadi kesalahan.");

const formatDate = (value: string) => {
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};

const statusBadge = (status: string | null) =>
  status === "Published" ? "bg-green-100 text-green-600" : "bg-amber-100 text-amber-700";

const inputClass =
  "w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";

export default function CreatorDashboard() {
  const router = useRouter();
  const [data, setData] = useState<Dashboard | null>(null);
  const [payoutPref, setPayoutPref] = useState<PayoutPreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  // Payout terbaru kalau tanggal bayarnya dalam 30 hari terakhir (untuk banner).
  const [recentPayout, setRecentPayout] = useState<Payout | null>(null);

  // null = tidak sedang mengubah metode payout.
  const [payoutForm, setPayoutForm] = useState<PayoutForm | null>(null);
  const [savingPayout, setSavingPayout] = useState(false);
  const [payoutError, setPayoutError] = useState("");
  const [payoutMessage, setPayoutMessage] = useState("");

  const handleLogout = useCallback(() => {
    localStorage.clear();
    router.push("/login");
  }, [router]);

  const api = useCallback(
    (path: string, init?: RequestInit) => apiFetch(path, init, handleLogout),
    [handleLogout]
  );

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.push("/login");
      return;
    }
    Promise.all([api("/creator-dashboard/"), api("/me/payout")])
      .then(([dashboard, pref]: [Dashboard, PayoutPreference]) => {
        setData(dashboard);
        setPayoutPref(pref);
        // by_month urut dari bulan terbaru.
        if (dashboard.by_month.length > 0) setSelectedMonth(dashboard.by_month[0].month);
        // payouts urut dari tanggal bayar terbaru; batasnya 30 hari sebelum
        // awal hari ini (zona waktu browser).
        const latest = dashboard.payouts[0];
        const cutoff = new Date();
        cutoff.setHours(0, 0, 0, 0);
        cutoff.setDate(cutoff.getDate() - 30);
        if (latest && new Date(`${latest.paid_at}T00:00:00`) >= cutoff) setRecentPayout(latest);
      })
      .catch((err) => setLoadError(errMsg(err)))
      .finally(() => setLoading(false));
  }, [router, api]);

  // ==========================================================================
  // METODE PAYOUT
  // ==========================================================================

  const startEditPayout = () => {
    const method = payoutPref?.payout_method ?? "paypal";
    const saved = payoutPref?.payout_details_masked ?? {};
    // Field termask harus diisi ulang; sisanya diisi dari data tersimpan.
    const details = Object.fromEntries(
      PAYOUT_FIELDS[method].map((f) => [f, MASKED_PAYOUT_FIELDS.includes(f) ? "" : saved[f] || ""])
    );
    setPayoutError("");
    setPayoutMessage("");
    setPayoutForm({ method, details });
  };

  const updatePayoutForm = (patch: Partial<PayoutForm>) =>
    setPayoutForm((form) => form && { ...form, ...patch });

  const handleSavePayout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!payoutForm) return;
    setSavingPayout(true);
    setPayoutError("");
    try {
      const details = Object.fromEntries(
        PAYOUT_FIELDS[payoutForm.method].map((f) => [f, (payoutForm.details[f] || "").trim()])
      );
      const res = await api("/me/payout", {
        method: "PUT",
        body: JSON.stringify({ payout_method: payoutForm.method, payout_details: details }),
      });
      setPayoutPref({
        payout_method: res.payout_method,
        payout_details_masked: res.payout_details_masked,
      });
      setPayoutForm(null);
      setPayoutMessage(res.message);
      // Perkiraan rupiah di kartu ringkasan tergantung metode payout.
      setData(await api("/creator-dashboard/"));
    } catch (err) {
      setPayoutError(errMsg(err));
    } finally {
      setSavingPayout(false);
    }
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center font-bold text-blue-600">
        Memuat Dashboard...
      </div>
    );

  if (!data)
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="font-bold text-red-600">{loadError || "Gagal memuat dashboard."}</p>
        <button
          onClick={handleLogout}
          className="bg-red-50 text-red-600 px-5 py-2.5 rounded-xl text-sm font-bold"
        >
          Keluar
        </button>
      </div>
    );

  const availableMonths = data.by_month.map((m) => m.month);

  // LOGIKA STATUS PROYEK: Sembunyikan jika Published DAN sudah ada penjualannya
  const activeProjects = data.proyek.filter((p) => {
    if (p.status !== "Published") return true;
    return !data.by_content.some((c) => c.name === p.name && c.units > 0);
  });

  const summaryCards = [
    {
      label: "Total diperoleh",
      usd: data.total_earned_usd,
      idr: data.total_earned_idr,
      hint: "Seluruh bagian Anda dari penjualan konten.",
    },
    {
      label: "Sudah dibayar",
      usd: data.total_paid_usd,
      idr: data.total_paid_idr,
      hint: "Total payout yang sudah dikirim ke Anda.",
    },
    {
      label: "Saldo tertunda",
      usd: data.outstanding_usd,
      idr: data.outstanding_idr,
      hint: "Akan dibayarkan pada payout berikutnya.",
    },
  ];

  // ============================================================================
  // LOGIKA GRAFIK GARIS (ANTI-PUTUS & PAKSA TITIK 0)
  // ============================================================================
  const dailyDataObj: Record<string, Record<string, number | string>> = {};
  const contentNamesSet = new Set<string>();

  data.grafik_harian.forEach((item) => {
    if (!item.date.startsWith(selectedMonth)) return;
    contentNamesSet.add(item.content_name);
  });
  const contentNamesArray = Array.from(contentNamesSet);

  if (selectedMonth) {
    const [yearStr, monthStr] = selectedMonth.split("-");
    if (yearStr && monthStr) {
      const daysInMonth = new Date(parseInt(yearStr), parseInt(monthStr), 0).getDate();

      for (let i = 1; i <= daysInMonth; i++) {
        const fullDateStr = `${selectedMonth}-${i.toString().padStart(2, "0")}`;
        dailyDataObj[fullDateStr] = { date: fullDateStr };
        contentNamesArray.forEach((cName) => {
          dailyDataObj[fullDateStr][cName] = 0;
        });
      }
    }
  }

  data.grafik_harian.forEach((item) => {
    if (!item.date.startsWith(selectedMonth)) return;
    if (!dailyDataObj[item.date]) {
      dailyDataObj[item.date] = { date: item.date };
      contentNamesArray.forEach((cName) => {
        dailyDataObj[item.date][cName] = 0;
      });
    }
    dailyDataObj[item.date][item.content_name] = item.quantity;
  });

  const lineChartData = Object.values(dailyDataObj).sort((a, b) =>
    String(a.date).localeCompare(String(b.date))
  );
  const colors = ["#3B82F6", "#F97316", "#10B981", "#8B5CF6", "#EC4899", "#EF4444"];

  const savedMethod = payoutPref?.payout_method ?? null;
  const savedDetails = payoutPref?.payout_details_masked ?? {};

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* HEADER */}
      <div className="bg-white border-b border-gray-200 px-6 md:px-12 py-4 flex justify-between items-center sticky top-0 z-10 shadow-sm">
        <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">
          Squareclouds Portal
        </h1>
        <div className="flex items-center gap-6">
          <div className="text-right hidden md:block">
            <p className="text-xs text-gray-400 uppercase font-bold">{data.job_title}</p>
            <p className="font-bold text-gray-800">{data.nama}</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-50 hover:bg-red-100 transition-colors text-red-600 px-5 py-2.5 rounded-xl text-sm font-bold"
          >
            Keluar
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 mt-8 space-y-8">
        {recentPayout && (
          <div className="rounded-2xl border border-green-100 bg-green-50 px-5 py-3 text-sm font-bold text-green-700">
            Payout terakhir: {formatUsd(recentPayout.amount_usd)} pada{" "}
            {formatDate(recentPayout.paid_at)}
          </div>
        )}

        {/* KARTU RINGKASAN */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {summaryCards.map((card, idx) => {
            const highlight = idx === summaryCards.length - 1;
            return (
              <div
                key={card.label}
                className={
                  highlight
                    ? "bg-gradient-to-br from-blue-600 to-cyan-500 p-6 rounded-3xl shadow-lg text-white"
                    : "bg-white p-6 rounded-3xl shadow-sm border border-gray-100"
                }
              >
                <h2
                  className={`text-sm font-bold uppercase mb-3 ${highlight ? "text-blue-100" : "text-gray-400"}`}
                >
                  {card.label}
                </h2>
                <div
                  className={`text-4xl font-black ${highlight ? "text-white" : "text-gray-900"}`}
                >
                  {formatUsd(card.usd)}
                </div>
                {card.idr !== null && (
                  <p
                    className={`mt-1 text-sm font-bold ${highlight ? "text-blue-50" : "text-gray-500"}`}
                  >
                    ≈ {formatIdr(card.idr)}
                  </p>
                )}
                <p
                  className={`mt-3 text-xs font-medium ${highlight ? "text-blue-100" : "text-gray-400"}`}
                >
                  {card.hint}
                </p>
              </div>
            );
          })}
        </div>

        {/* METODE PAYOUT & STATUS PROYEK */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
            <div className="flex justify-between items-start mb-4 gap-4">
              <h3 className="text-lg font-extrabold text-gray-900">Metode payout</h3>
              {!payoutForm && (
                <button
                  onClick={startEditPayout}
                  className="text-blue-600 bg-blue-50 px-4 py-1.5 rounded-lg text-sm font-bold"
                >
                  {savedMethod ? "Ubah" : "Atur"}
                </button>
              )}
            </div>

            {payoutMessage && !payoutForm && (
              <div className="mb-4 rounded-xl bg-green-50 p-3 text-sm font-bold text-green-700">
                {payoutMessage}
              </div>
            )}

            {payoutForm ? (
              <form onSubmit={handleSavePayout} className="space-y-3">
                <label className="block">
                  <span className="text-xs font-bold text-gray-500 uppercase">Metode</span>
                  <select
                    value={payoutForm.method}
                    onChange={(e) => updatePayoutForm({ method: e.target.value as PayoutMethod })}
                    className={`${inputClass} mt-1 bg-white`}
                  >
                    {(Object.keys(PAYOUT_METHOD_LABEL) as PayoutMethod[]).map((m) => (
                      <option key={m} value={m}>
                        {PAYOUT_METHOD_LABEL[m]}
                      </option>
                    ))}
                  </select>
                </label>

                {PAYOUT_FIELDS[payoutForm.method].map((field) => {
                  const value = payoutForm.details[field] || "";
                  const onChange = (v: string) =>
                    updatePayoutForm({ details: { ...payoutForm.details, [field]: v } });
                  return (
                    <label key={field} className="block">
                      <span className="text-xs font-bold text-gray-500 uppercase">
                        {PAYOUT_FIELD_LABEL[field]}
                      </span>
                      {field === "provider" ? (
                        <select
                          required
                          value={value}
                          onChange={(e) => onChange(e.target.value)}
                          className={`${inputClass} mt-1 bg-white`}
                        >
                          <option value="" disabled>
                            Pilih e-wallet
                          </option>
                          {EWALLET_PROVIDERS.map((p) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          required
                          type={
                            field === "paypal_email" ? "email" : field === "phone" ? "tel" : "text"
                          }
                          inputMode={field === "account_number" ? "numeric" : undefined}
                          value={value}
                          onChange={(e) => onChange(e.target.value)}
                          placeholder={
                            field === "phone"
                              ? "08xxxxxxxxxx"
                              : field === "account_number"
                                ? "6–20 digit"
                                : undefined
                          }
                          className={`${inputClass} mt-1`}
                        />
                      )}
                    </label>
                  );
                })}

                {payoutError && (
                  <div className="rounded-xl bg-red-50 p-3 text-sm font-bold text-red-600">
                    {payoutError}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={savingPayout}
                    className="flex-1 bg-blue-600 text-white py-2 rounded-xl text-sm font-bold hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {savingPayout ? "Menyimpan..." : "Simpan"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPayoutForm(null)}
                    className="px-4 py-2 rounded-xl text-sm font-bold bg-gray-100 hover:bg-gray-200 transition"
                  >
                    Batal
                  </button>
                </div>
              </form>
            ) : savedMethod ? (
              <div className="space-y-2">
                <p className="font-bold text-gray-800">{PAYOUT_METHOD_LABEL[savedMethod]}</p>
                {PAYOUT_FIELDS[savedMethod].map((field) => (
                  <div key={field} className="flex justify-between gap-4 text-sm">
                    <span className="text-gray-500">{PAYOUT_FIELD_LABEL[field]}</span>
                    <span className="font-bold text-gray-800 font-mono">
                      {savedDetails[field] || "-"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl bg-amber-50 p-4 text-sm font-bold text-amber-700">
                Anda belum mengisi metode payout. Isi dulu supaya pendapatan bisa dibayarkan.
              </div>
            )}

            <p className="mt-4 text-xs font-medium text-gray-400">
              Payout bank/e-wallet dikonversi dengan kurs {formatIdr(data.idr_rate)}/$ yang
              ditetapkan Squareclouds Studio.
            </p>
          </div>

          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 flex flex-col">
            <h3 className="text-lg font-extrabold text-gray-900 mb-4">Status Proyek</h3>
            {activeProjects.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-center text-sm font-bold text-gray-400 bg-gray-50 rounded-xl p-4">
                Semua proyek Anda sudah rilis dan mencetak penjualan.
              </div>
            ) : (
              <div className="space-y-3 flex-1 overflow-y-auto pr-2" style={{ maxHeight: "220px" }}>
                {activeProjects.map((p) => (
                  <div
                    key={p.name}
                    className="flex justify-between items-center bg-gray-50 p-3 rounded-xl border border-gray-100"
                  >
                    <div className="min-w-0">
                      <span className="font-bold text-gray-700 text-sm">{p.name}</span>
                      {(p.pack_type || p.release_date) && (
                        <p className="text-[11px] font-medium text-gray-400">
                          {[p.pack_type, p.release_date && `Rilis ${p.release_date}`]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      )}
                    </div>
                    <span
                      className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${statusBadge(p.status)}`}
                    >
                      {p.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* GRAFIK GARIS (UNIT) */}
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
          <div className="flex flex-wrap justify-between items-center gap-4 mb-6">
            <h3 className="text-lg font-extrabold text-gray-900">Grafik Penjualan Unit Harian</h3>
            {availableMonths.length > 0 && (
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="bg-white border border-gray-200 text-gray-800 rounded-lg p-2 px-4 text-sm font-bold shadow-sm outline-none cursor-pointer"
              >
                {availableMonths.map((m) => (
                  <option key={m} value={m}>
                    {formatMonth(m)}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="h-[350px] w-full">
            {lineChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={lineChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis
                    dataKey="date"
                    axisLine={true}
                    tickLine={true}
                    tick={{ fill: "#6B7280", fontSize: 11 }}
                    dy={10}
                  />
                  <YAxis
                    axisLine={true}
                    tickLine={true}
                    tick={{ fill: "#6B7280", fontSize: 11 }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "12px",
                      border: "none",
                      boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)",
                    }}
                  />
                  <Legend
                    iconType="circle"
                    wrapperStyle={{ fontSize: "12px", fontWeight: 600, paddingTop: "10px" }}
                  />
                  {contentNamesArray.map((cName, idx) => (
                    <Line
                      key={cName}
                      type="linear"
                      dataKey={cName}
                      stroke={colors[idx % colors.length]}
                      strokeWidth={2}
                      activeDot={{ r: 6 }}
                      dot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400 font-bold bg-gray-50 rounded-2xl">
                Tidak ada data harian untuk periode ini.
              </div>
            )}
          </div>
        </div>

        {/* TABEL PER KONTEN */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-8 py-6 border-b border-gray-50 bg-gray-50/30">
            <h3 className="font-extrabold text-gray-800 text-lg">Per konten</h3>
            <p className="text-sm text-gray-500 font-medium">
              Total sejak rilis untuk setiap konten yang tertaut ke Anda.
            </p>
          </div>
          {data.by_content.length === 0 ? (
            <div className="p-10 text-center text-gray-400 font-bold">
              Belum ada konten yang tertaut ke akun Anda.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-white border-b border-gray-100">
                  <tr>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Konten</th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Status</th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Unit Terjual
                    </th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Pendapatan Saya
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_content.map((c) => (
                    <tr key={c.content_id} className="border-b border-gray-50 hover:bg-blue-50/30">
                      <td className="px-4 md:px-8 py-4 text-sm font-bold text-gray-900">{c.name}</td>
                      <td className="px-4 md:px-8 py-4">
                        <span
                          className={`whitespace-nowrap px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${statusBadge(c.status)}`}
                        >
                          {c.status || "-"}
                        </span>
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm font-bold text-gray-700 text-right">
                        {c.units.toLocaleString("id-ID")}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm text-right font-black text-green-500">
                        {formatUsd(c.share_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* TABEL PER BULAN */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-8 py-6 border-b border-gray-50 bg-gray-50/30">
            <h3 className="font-extrabold text-gray-800 text-lg">Per bulan</h3>
          </div>
          {data.by_month.length === 0 ? (
            <div className="p-10 text-center text-gray-400 font-bold">
              Belum ada catatan penjualan.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-white border-b border-gray-100">
                  <tr>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Bulan</th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Unit Terjual
                    </th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Pendapatan Saya
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_month.map((m) => (
                    <tr key={m.month} className="border-b border-gray-50 hover:bg-blue-50/30">
                      <td className="px-4 md:px-8 py-4 text-sm font-bold text-gray-900">
                        {formatMonth(m.month)}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm font-bold text-gray-700 text-right">
                        {m.units.toLocaleString("id-ID")}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm text-right font-black text-green-500">
                        {formatUsd(m.share_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* RIWAYAT PAYOUT */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-8 py-6 border-b border-gray-50 bg-gray-50/30">
            <h3 className="font-extrabold text-gray-800 text-lg">Riwayat payout</h3>
          </div>
          {data.payouts.length === 0 ? (
            <div className="p-10 text-center text-gray-400 font-bold">Belum ada payout.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-white border-b border-gray-100">
                  <tr>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Tanggal</th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Jumlah
                    </th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                      Rupiah
                    </th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Metode</th>
                    <th className="px-4 md:px-8 py-4 text-xs font-bold text-gray-400 uppercase">Catatan</th>
                  </tr>
                </thead>
                <tbody>
                  {data.payouts.map((p) => (
                    <tr key={p.id} className="border-b border-gray-50 hover:bg-blue-50/30">
                      <td className="px-4 md:px-8 py-4 text-sm font-bold text-gray-700 whitespace-nowrap">
                        {formatDate(p.paid_at)}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm font-black text-gray-900 text-right">
                        {formatUsd(p.amount_usd)}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm text-gray-700 text-right whitespace-nowrap">
                        {p.amount_idr !== null ? (
                          <>
                            <span className="font-bold">{formatIdr(p.amount_idr)}</span>
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
                      <td className="px-4 md:px-8 py-4 text-sm text-gray-700">
                        {PAYOUT_METHOD_LABEL[p.method] || p.method}
                      </td>
                      <td className="px-4 md:px-8 py-4 text-sm text-gray-500">{p.note || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
