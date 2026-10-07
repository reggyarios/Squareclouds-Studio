"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const STATUS_OPTIONS = ["Development", "Packaging", "MS Review", "Ingestion", "Published"];
const TYPE_OPTIONS = [
  "Survival Spawn",
  "Skin Pack",
  "Adventure Map",
  "Add-On",
  "Mash-Up",
  "Mini Game",
];
const JOB_OPTIONS = ["Builder", "Skin Artist", "Developer", "Keyart Artist", "Other"];
const TIER_OPTIONS = [
  { tier: 1, price: 0.37 },
  { tier: 2, price: 0.74 },
  { tier: 3, price: 1.12 },
  { tier: 4, price: 1.49 },
  { tier: 5, price: 1.87 },
  { tier: 6, price: 2.24 },
  { tier: 7, price: 2.62 },
  { tier: 8, price: 2.99 },
  { tier: 9, price: 3.37 },
  { tier: 10, price: 3.74 },
  { tier: 11, price: 4.12 },
  { tier: 12, price: 4.49 },
  { tier: 13, price: 4.87 },
  { tier: 14, price: 5.24 },
  { tier: 15, price: 5.62 },
  { tier: 16, price: 5.99 },
  { tier: 17, price: 6.37 },
  { tier: 18, price: 6.74 },
  { tier: 19, price: 7.12 },
];

export default function AdminDashboard() {
  const router = useRouter();
  const [adminName, setAdminName] = useState("");
  const [activeTab, setActiveTab] = useState("laporan");
  const [loading, setLoading] = useState(true);

  const [usersList, setUsersList] = useState<any[]>([]);
  const [contentsList, setContentsList] = useState<any[]>([]);
  const [reportsList, setReportsList] = useState<any[]>([]);

  // State untuk filter bulan laporan
  const [filterBulan, setFilterBulan] = useState<string>("");

  const [pesan, setPesan] = useState({ type: "", text: "" });
  const [isProcessing, setIsProcessing] = useState(false);

  const [formKreator, setFormKreator] = useState({
    name: "",
    email: "",
    job_title: JOB_OPTIONS[0],
    password: "",
  });
  const [formKonten, setFormKonten] = useState({
    name: "",
    price: TIER_OPTIONS[0].price,
    status: STATUS_OPTIONS[0],
    content_type: TYPE_OPTIONS[0],
  });

  // formSplits sekarang default kosong agar Squareclouds bisa 100% jika tidak ada kreator ditambahkan
  const [formSplits, setFormSplits] = useState<{ user_id: string; percentage: number }[]>([]);

  const [editingUser, setEditingUser] = useState<any>(null);
  const [editingContent, setEditingContent] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    if (!token || role !== "Admin") return router.push("/login");

    setAdminName(localStorage.getItem("name") || "Admin");
    fetchUsers();
    fetchContents();
    fetchReports();
    setLoading(false);
  }, [router]);

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  const fetchUsers = async () => {
    const res = await fetch("/users/");
    const data = await res.json();
    setUsersList(data.data.filter((u: any) => u.role === "Creator"));
  };

  const fetchContents = async () => {
    const res = await fetch("/contents/");
    const data = await res.json();
    setContentsList(data.data);
  };

  const fetchReports = async () => {
    const token = localStorage.getItem("token");
    const res = await fetch("/admin-reports/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (res.ok) {
      setReportsList(data.data);
      const months = Array.from(new Set(data.data.map((r: any) => r.bulan)))
        .sort()
        .reverse() as string[];
      if (months.length > 0) setFilterBulan(months[0]);
    }
  };

  const handleSubmitKreator = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setPesan({ type: "", text: "" });
    try {
      const res = await fetch("/users/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...formKreator, role: "Creator" }),
      });
      if (!res.ok) throw new Error("Gagal membuat kreator");
      setPesan({ type: "success", text: "Akun Kreator berhasil dibuat!" });
      setFormKreator({ name: "", email: "", job_title: JOB_OPTIONS[0], password: "" });
      fetchUsers();
    } catch (err: any) {
      setPesan({ type: "error", text: err.message });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAddSplitRow = () => {
    const currentTotal = formSplits.reduce((sum, item) => sum + Number(item.percentage), 0);
    const sisa = 80 - currentTotal;
    if (sisa <= 0) return alert("Batas alokasi kreator (80%) sudah penuh.");
    setFormSplits([...formSplits, { user_id: "", percentage: sisa }]);
  };

  const handleSubmitKonten = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setPesan({ type: "", text: "" });

    const totalPersen = formSplits.reduce((acc, curr) => acc + Number(curr.percentage), 0);
    if (totalPersen > 80) {
      setPesan({
        type: "error",
        text: "Total persentase kreator tidak boleh lebih dari 80% (Squareclouds memiliki minimal 20%).",
      });
      setIsProcessing(false);
      return;
    }

    try {
      const resKonten = await fetch("/contents/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formKonten),
      });
      const dataKonten = await resKonten.json();
      if (!resKonten.ok) throw new Error("Gagal membuat konten");

      for (const split of formSplits) {
        if (split.user_id && split.percentage > 0) {
          await fetch("/splits/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: Number(split.user_id),
              content_id: dataKonten.data.id,
              split_percentage: Number(split.percentage),
            }),
          });
        }
      }
      setPesan({ type: "success", text: "Konten dan Split berhasil disimpan!" });
      setFormKonten({
        name: "",
        price: TIER_OPTIONS[0].price,
        status: STATUS_OPTIONS[0],
        content_type: TYPE_OPTIONS[0],
      });
      setFormSplits([]);
      fetchContents();
    } catch (err: any) {
      setPesan({ type: "error", text: err.message });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    try {
      const res = await fetch(`/users/${editingUser.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editingUser.name,
          email: editingUser.email,
          job_title: editingUser.job_title,
          password: editingUser.newPassword || undefined,
        }),
      });
      if (!res.ok) throw new Error("Gagal update");
      setPesan({ type: "success", text: "Data kreator diupdate!" });
      setEditingUser(null);
      fetchUsers();
    } catch (err: any) {
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (!confirm("Hapus kreator ini permanen?")) return;
    await fetch(`/users/${id}`, { method: "DELETE" });
    fetchUsers();
  };

  const handleUpdateContent = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    const totalPersen = editingContent.splits.reduce(
      (acc: number, curr: any) => acc + Number(curr.percentage),
      0
    );
    if (totalPersen > 80) {
      setPesan({ type: "error", text: "Total split kreator melebihi 80%!" });
      setIsProcessing(false);
      return;
    }
    try {
      await fetch(`/contents/${editingContent.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editingContent.name,
          price: editingContent.price,
          status: editingContent.status,
          content_type: editingContent.content_type,
          splits: editingContent.splits,
        }),
      });
      setPesan({ type: "success", text: "Data konten diupdate!" });
      setEditingContent(null);
      fetchContents();
    } catch (err) {
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteContent = async (id: number) => {
    if (!confirm("Hapus konten permanen?")) return;
    await fetch(`/contents/${id}`, { method: "DELETE" });
    fetchContents();
    fetchReports();
  };

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

  const currentTotalSplit = formSplits.reduce((acc, curr) => acc + Number(curr.percentage), 0);
  const scShare = 100 - currentTotalSplit;

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center font-bold text-blue-600">
        Memuat...
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row relative">
      <div className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col z-10">
        <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500 mb-8">
          Admin Panel
        </h1>
        <nav className="flex flex-col gap-2 flex-grow">
          <button
            onClick={() => {
              setActiveTab("kreator");
              setPesan({ type: "", text: "" });
            }}
            className={`text-left px-4 py-3 rounded-xl font-medium ${activeTab === "kreator" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
          >
            Manajemen Kreator
          </button>
          <button
            onClick={() => {
              setActiveTab("konten");
              setPesan({ type: "", text: "" });
            }}
            className={`text-left px-4 py-3 rounded-xl font-medium ${activeTab === "konten" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
          >
            Manajemen Konten
          </button>
          <button
            onClick={() => {
              setActiveTab("laporan");
              fetchReports();
              setPesan({ type: "", text: "" });
            }}
            className={`text-left px-4 py-3 rounded-xl font-medium ${activeTab === "laporan" ? "bg-blue-50 text-blue-700" : "text-gray-600"}`}
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
            className={`mb-6 p-4 rounded-xl text-sm font-bold ${pesan.type === "error" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-700"}`}
          >
            {pesan.text}
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

        {/* TAB KONTEN */}
        {activeTab === "konten" && (
          <div className="max-w-5xl space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Tambah Konten Baru</h2>
              <form
                onSubmit={handleSubmitKonten}
                className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 space-y-8"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                  <div className="md:col-span-3">
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Nama Konten
                    </label>
                    <input
                      type="text"
                      required
                      value={formKonten.name}
                      onChange={(e) => setFormKonten({ ...formKonten, name: e.target.value })}
                      className="w-full rounded-xl border border-gray-300 px-4 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Harga</label>
                    <select
                      value={formKonten.price}
                      onChange={(e) =>
                        setFormKonten({ ...formKonten, price: Number(e.target.value) })
                      }
                      className="w-full rounded-xl border border-gray-300 px-4 py-2 bg-white"
                    >
                      {TIER_OPTIONS.map((t) => (
                        <option key={t.tier} value={t.price}>
                          Tier {t.tier} (${t.price.toFixed(2)})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Jenis Konten
                    </label>
                    <select
                      value={formKonten.content_type}
                      onChange={(e) =>
                        setFormKonten({ ...formKonten, content_type: e.target.value })
                      }
                      className="w-full rounded-xl border border-gray-300 px-4 py-2 bg-white"
                    >
                      {TYPE_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Status Konten
                    </label>
                    <select
                      value={formKonten.status}
                      onChange={(e) => setFormKonten({ ...formKonten, status: e.target.value })}
                      className="w-full rounded-xl border border-gray-300 px-4 py-2 bg-white"
                    >
                      {STATUS_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center border-b pb-2 mb-4">
                    <h3 className="text-lg font-bold text-gray-900">Alokasi Royalti</h3>
                    <button
                      type="button"
                      onClick={handleAddSplitRow}
                      className="text-sm font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg"
                    >
                      + Tambah Kreator
                    </button>
                  </div>

                  <div className="flex gap-3 bg-blue-50/50 p-4 rounded-xl border border-blue-100 mb-3">
                    <div className="flex-1">
                      <p className="text-sm font-bold text-blue-800 mt-2">
                        🏢 Squareclouds (Publisher)
                      </p>
                    </div>
                    <div className="w-32">
                      <input
                        type="text"
                        disabled
                        value={`${scShare}%`}
                        className="w-full rounded-lg border-blue-200 px-3 py-2 text-sm bg-blue-100 font-bold text-blue-800"
                      />
                    </div>
                  </div>

                  {formSplits.length === 0 && (
                    <div className="text-sm text-gray-500 font-bold p-4 text-center bg-gray-50 rounded-xl border border-gray-100">
                      Tidak ada kreator ditambahkan. Squareclouds mendapat full 100%.
                    </div>
                  )}

                  <div className="space-y-3">
                    {formSplits.map((split, index) => (
                      <div
                        key={index}
                        className="flex gap-3 items-end bg-gray-50 p-4 rounded-xl border border-gray-100"
                      >
                        <div className="flex-1">
                          <label className="block text-xs font-bold text-gray-500 mb-1">
                            Pilih Kreator
                          </label>
                          <select
                            required
                            value={split.user_id}
                            onChange={(e) => {
                              const newS = [...formSplits];
                              newS[index].user_id = e.target.value;
                              setFormSplits(newS);
                            }}
                            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
                          >
                            <option value="" disabled>
                              -- Pilih Kreator --
                            </option>
                            {usersList.map((u) => (
                              <option key={u.id} value={u.id}>
                                {u.name} ({u.job_title})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="w-32">
                          <label className="block text-xs font-bold text-gray-500 mb-1">
                            Persen (%)
                          </label>
                          <input
                            type="number"
                            step="0.1"
                            max="80"
                            required
                            value={split.percentage}
                            onChange={(e) => {
                              const newS = [...formSplits];
                              newS[index].percentage = Number(e.target.value);
                              setFormSplits(newS);
                            }}
                            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-bold text-green-600"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const newS = [...formSplits];
                            newS.splice(index, 1);
                            setFormSplits(newS);
                          }}
                          className="bg-red-100 text-red-600 px-3 py-2 rounded-lg text-sm font-bold"
                        >
                          X
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={isProcessing}
                  className="w-full bg-blue-600 text-white px-6 py-4 rounded-xl font-bold"
                >
                  Simpan Konten
                </button>
              </form>
            </div>

            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-4">Daftar Konten</h2>
              <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
                <table className="w-full text-left">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500">KONTEN</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500">TIPE</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500">HARGA</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 text-center">
                        STATUS
                      </th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 text-center">
                        AKSI
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {contentsList.map((c) => (
                      <tr
                        key={c.id}
                        className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors"
                      >
                        <td className="px-6 py-4 font-bold text-gray-800">{c.name}</td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-600">
                          {c.content_type}
                        </td>
                        <td className="px-6 py-4 text-sm font-bold text-gray-800">${c.price}</td>
                        <td className="px-6 py-4 text-center">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-extrabold ${
                              c.status === "Published"
                                ? "bg-green-100 text-green-600"
                                : "bg-amber-100 text-amber-700"
                            }`}
                          >
                            {c.status || "Development"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() =>
                              setEditingContent({ ...c, splits: c.splits.length ? c.splits : [] })
                            }
                            className="text-blue-600 font-bold text-sm bg-blue-50 hover:bg-blue-100 transition px-3 py-1.5 rounded-lg"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB KREATOR */}
        {activeTab === "kreator" && (
          <div className="max-w-4xl space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Tambah Kreator</h2>
              <form
                onSubmit={handleSubmitKreator}
                className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 grid grid-cols-2 gap-5"
              >
                <div className="col-span-2">
                  <label className="block text-sm font-bold mb-1">Nama</label>
                  <input
                    type="text"
                    required
                    value={formKreator.name}
                    onChange={(e) => setFormKreator({ ...formKreator, name: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1">Email</label>
                  <input
                    type="email"
                    required
                    value={formKreator.email}
                    onChange={(e) => setFormKreator({ ...formKreator, email: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1">Role / Job Title</label>
                  <select
                    value={formKreator.job_title}
                    onChange={(e) => setFormKreator({ ...formKreator, job_title: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 bg-white"
                  >
                    {JOB_OPTIONS.map((j) => (
                      <option key={j} value={j}>
                        {j}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-bold mb-1">Password</label>
                  <input
                    type="password"
                    required
                    value={formKreator.password}
                    onChange={(e) => setFormKreator({ ...formKreator, password: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2"
                  />
                </div>
                <div className="col-span-2">
                  <button
                    type="submit"
                    className="w-full bg-blue-600 text-white px-6 py-3 rounded-xl font-bold"
                  >
                    Daftarkan
                  </button>
                </div>
              </form>
            </div>
            <div>
              <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
                <table className="w-full text-left">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500">NAMA</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500">JOB TITLE</th>
                      <th className="px-6 py-4 text-xs font-bold text-gray-500 text-center">
                        AKSI
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList.map((u) => (
                      <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                        <td className="px-6 py-4 font-bold">{u.name}</td>
                        <td className="px-6 py-4 text-sm">{u.job_title}</td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => setEditingUser(u)}
                            className="text-blue-600 font-bold text-sm bg-blue-50 px-3 py-1 rounded-lg"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* POP-UP EDIT KREATOR */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-3xl max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Edit Kreator</h3>
            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-bold mb-1">Nama</label>
                <input
                  type="text"
                  value={editingUser.name}
                  onChange={(e) => setEditingUser({ ...editingUser, name: e.target.value })}
                  className="w-full rounded-xl border px-4 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-bold mb-1">Job Title</label>
                <select
                  value={editingUser.job_title}
                  onChange={(e) => setEditingUser({ ...editingUser, job_title: e.target.value })}
                  className="w-full rounded-xl border px-4 py-2 bg-white"
                >
                  {JOB_OPTIONS.map((j) => (
                    <option key={j} value={j}>
                      {j}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-4 border-t mt-6">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-bold"
                >
                  Simpan
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteUser(editingUser.id)}
                  className="px-4 py-2.5 rounded-xl font-bold bg-red-100 text-red-600"
                >
                  Hapus
                </button>
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2.5 rounded-xl font-bold bg-gray-100"
                >
                  Batal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* POP-UP EDIT KONTEN & SPLIT & STATUS */}
      {editingContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-3xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-4">Edit Konten & Split</h3>
            <form onSubmit={handleUpdateContent} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-500 mb-1">Nama Konten</label>
                <input
                  type="text"
                  value={editingContent.name}
                  onChange={(e) => setEditingContent({ ...editingContent, name: e.target.value })}
                  className="w-full rounded-xl border border-gray-300 px-4 py-2"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-500 mb-1">Harga ($)</label>
                  <select
                    value={editingContent.price}
                    onChange={(e) =>
                      setEditingContent({ ...editingContent, price: Number(e.target.value) })
                    }
                    className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm bg-white"
                  >
                    {TIER_OPTIONS.map((t) => (
                      <option key={t.tier} value={t.price}>
                        Tier {t.tier} (${t.price.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 mb-1">
                    Status Konten
                  </label>
                  <select
                    value={editingContent.status || "Development"}
                    onChange={(e) =>
                      setEditingContent({ ...editingContent, status: e.target.value })
                    }
                    className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm bg-white font-bold text-blue-600"
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2 border-t pt-4">
                <h4 className="text-sm font-bold text-gray-800">Kreator Splits (Max 80%)</h4>
                {editingContent.splits.map((split: any, index: number) => (
                  <div key={index} className="flex gap-2">
                    <select
                      value={split.user_id}
                      onChange={(e) => {
                        const s = [...editingContent.splits];
                        s[index].user_id = e.target.value;
                        setEditingContent({ ...editingContent, splits: s });
                      }}
                      className="flex-1 rounded-lg border border-gray-300 px-2 py-1 text-sm bg-white"
                    >
                      {usersList.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      step="0.1"
                      max="80"
                      value={split.percentage}
                      onChange={(e) => {
                        const s = [...editingContent.splits];
                        s[index].percentage = Number(e.target.value);
                        setEditingContent({ ...editingContent, splits: s });
                      }}
                      className="w-20 rounded-lg border border-gray-300 px-2 py-1 text-sm font-bold text-green-600"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const s = [...editingContent.splits];
                        s.splice(index, 1);
                        setEditingContent({ ...editingContent, splits: s });
                      }}
                      className="bg-red-100 text-red-600 px-2 rounded-lg text-xs font-bold"
                    >
                      X
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    setEditingContent({
                      ...editingContent,
                      splits: [...editingContent.splits, { user_id: "", percentage: 0 }],
                    })
                  }
                  className="text-xs font-bold text-blue-600"
                >
                  + Tambah Kreator
                </button>
              </div>

              <div className="flex gap-3 pt-4 border-t">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-bold hover:bg-blue-700 transition"
                >
                  Simpan
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteContent(editingContent.id)}
                  className="px-4 py-2.5 rounded-xl font-bold bg-red-100 text-red-600 hover:bg-red-200 transition"
                >
                  Hapus
                </button>
                <button
                  type="button"
                  onClick={() => setEditingContent(null)}
                  className="px-4 py-2.5 rounded-xl font-bold bg-gray-100 hover:bg-gray-200 transition"
                >
                  Batal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
