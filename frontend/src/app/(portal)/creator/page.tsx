"use client";

import { useEffect, useState } from "react";
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

export default function CreatorDashboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState<string>("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return router.push("/login");

    fetch("https://api.squarecloudsmc.com/creator-dashboard/", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Gagal");
        return res.json();
      })
      .then((data) => {
        setData(data);

        const months = Array.from(
          new Set(data.riwayat_bulanan.map((item: any) => item.month))
        ) as string[];
        if (months.length > 0) {
          const latestMonth = months.sort().reverse()[0];
          setSelectedMonth(latestMonth);
        }

        setLoading(false);
      })
      .catch(() => {
        localStorage.clear();
        router.push("/login");
      });
  }, [router]);

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center font-bold text-blue-600">
        Memuat Dashboard...
      </div>
    );

  const availableMonths = Array.from(new Set(data.riwayat_bulanan.map((item: any) => item.month)));

  const filteredRiwayat = data.riwayat_bulanan.filter((item: any) => item.month === selectedMonth);
  const pendapatanPilihan = filteredRiwayat.reduce(
    (sum: number, item: any) => sum + item.earned,
    0
  );

  // LOGIKA STATUS PROYEK: Sembunyikan jika Published DAN sudah ada penjualannya
  const activeProjects = (data.proyek || []).filter((p: any) => {
    if (p.status !== "Published") return true;
    const hasSales = data.riwayat_bulanan.some((r: any) => r.content_name === p.name);
    return !hasSales;
  });

  // ============================================================================
  // LOGIKA GRAFIK GARIS (ANTI-PUTUS & PAKSA TITIK 0)
  // ============================================================================
  const dailyDataObj: any = {};
  const contentNamesSet = new Set<string>();

  data.grafik_harian.forEach((item: any) => {
    if (selectedMonth !== "Semua" && !item.date.includes(selectedMonth)) return;
    contentNamesSet.add(item.content_name);
  });
  const contentNamesArray = Array.from(contentNamesSet);

  if (selectedMonth && selectedMonth !== "Semua") {
    const [yearStr, monthStr] = selectedMonth.split("-");
    if (yearStr && monthStr) {
      const year = parseInt(yearStr);
      const month = parseInt(monthStr);
      const daysInMonth = new Date(year, month, 0).getDate();

      for (let i = 1; i <= daysInMonth; i++) {
        const dayStr = i.toString().padStart(2, "0");
        const fullDateStr = `${selectedMonth}-${dayStr}`;
        dailyDataObj[fullDateStr] = { date: fullDateStr };
        contentNamesArray.forEach((cName) => {
          dailyDataObj[fullDateStr][cName] = 0;
        });
      }
    }
  }

  data.grafik_harian.forEach((item: any) => {
    if (selectedMonth !== "Semua" && !item.date.includes(selectedMonth)) return;
    if (!dailyDataObj[item.date]) {
      dailyDataObj[item.date] = { date: item.date };
      contentNamesArray.forEach((cName) => {
        dailyDataObj[item.date][cName] = 0;
      });
    }
    dailyDataObj[item.date][item.content_name] = item.quantity;
  });

  const lineChartData = Object.values(dailyDataObj).sort(
    (a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );
  const colors = ["#3B82F6", "#F97316", "#10B981", "#8B5CF6", "#EC4899", "#EF4444"];

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

      <div className="max-w-6xl mx-auto px-6 mt-8">
        {/* KARTU PENDAPATAN & STATUS PROYEK */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-600 to-cyan-500 p-8 rounded-3xl shadow-lg text-white">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-blue-100 text-sm font-bold uppercase mt-2">Total Pendapatan</h2>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="bg-white/20 border border-white/30 text-white text-sm rounded-lg p-2 font-bold cursor-pointer outline-none focus:bg-blue-600 backdrop-blur-sm"
              >
                {availableMonths.map((m: any) => (
                  <option key={m} value={m} className="text-gray-900 bg-white">
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-5xl font-black mb-2">${pendapatanPilihan.toFixed(2)}</div>
            <p className="text-sm font-medium text-blue-100">
              Penghasilan bersih dari royalti di bulan {selectedMonth || "ini"}.
            </p>
          </div>

          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 flex flex-col">
            <h3 className="text-lg font-extrabold text-gray-900 mb-4">Status Proyek</h3>
            {activeProjects.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-center text-sm font-bold text-gray-400 bg-gray-50 rounded-xl p-4">
                Semua proyek Anda sudah rilis dan mencetak penjualan.
              </div>
            ) : (
              <div className="space-y-3 flex-1 overflow-y-auto pr-2" style={{ maxHeight: "130px" }}>
                {activeProjects.map((p: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center bg-gray-50 p-3 rounded-xl border border-gray-100"
                  >
                    <span className="font-bold text-gray-700 text-sm">{p.name}</span>
                    <span
                      className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider ${p.status === "Published" ? "bg-green-100 text-green-600" : "bg-amber-100 text-amber-700"}`}
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
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-extrabold text-gray-900 mb-6">
            Grafik Penjualan Unit Harian
          </h3>
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

        {/* TABEL RINCIAN PER BULAN */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-8 py-6 border-b border-gray-50 bg-gray-50/30">
            <h3 className="font-extrabold text-gray-800 text-lg">Rincian Performa Konten</h3>
            <p className="text-sm text-gray-500 font-medium">
              Berdasarkan bulan yang kamu pilih di atas.
            </p>
          </div>
          {filteredRiwayat.length === 0 ? (
            <div className="p-10 text-center text-gray-400 font-bold">
              Tidak ada catatan penjualan di bulan ini.
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="bg-white border-b border-gray-100">
                <tr>
                  <th className="px-8 py-4 text-xs font-bold text-gray-400 uppercase">Bulan</th>
                  <th className="px-8 py-4 text-xs font-bold text-gray-400 uppercase">
                    Konten Terjual
                  </th>
                  <th className="px-8 py-4 text-xs font-bold text-gray-400 uppercase text-center">
                    Unit Terjual
                  </th>
                  <th className="px-8 py-4 text-xs font-bold text-gray-400 uppercase text-right">
                    Pendapatan Bersih ($)
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRiwayat.map((item: any, index: number) => (
                  <tr key={index} className="border-b border-gray-50 hover:bg-blue-50/30">
                    <td className="px-8 py-4 text-sm font-bold text-gray-600">{item.month}</td>
                    <td className="px-8 py-4 text-sm font-bold text-gray-900">
                      {item.content_name}
                    </td>
                    <td className="px-8 py-4 text-sm font-bold text-gray-700 text-center">
                      {item.qty}
                    </td>
                    <td className="px-8 py-4 text-sm text-right font-black text-green-500">
                      + ${item.earned.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
