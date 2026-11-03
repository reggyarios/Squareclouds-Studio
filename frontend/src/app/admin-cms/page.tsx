"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLandingCMS() {
  const router = useRouter();
  const [adminName, setAdminName] = useState("Admin");

  const [activeTab, setActiveTab] = useState("commission");
  const [loading, setLoading] = useState(true);
  const [pesan, setPesan] = useState({ type: "", text: "" });
  const [isUploading, setIsUploading] = useState(false);

  const [editingItem, setEditingItem] = useState<any>(null);
  const [editCategory, setEditCategory] = useState<string | null>(null);

  // --- STATE UNTUK SEMUA TABEL ---
  const [commissions, setCommissions] = useState<any[]>([]);
  const [marketplaces, setMarketplaces] = useState<any[]>([]);
  const [premades, setPremades] = useState<any[]>([]);
  const [exhibitions, setExhibitions] = useState<any[]>([]);
  const [teamMembers, setTeamMembers] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);

  // --- STATE UNTUK FORM INPUT BARU ---
  const currentYear = new Date().getFullYear().toString();
  const [newCommission, setNewCommission] = useState({
    title: "",
    description: "",
    thumbnail_url: "",
    gallery_urls: "",
    link: "",
    year: currentYear,
  });
  const [newMarketplace, setNewMarketplace] = useState({
    title: "",
    content_type: "",
    image_url: "",
    price_minecoin: 0,
    link: "",
  });
  const [newPremade, setNewPremade] = useState({
    title: "",
    category: "Worlds",
    description: "",
    image_url: "",
    price_usd: 0.0,
    link: "",
  });
  const [newExhibition, setNewExhibition] = useState({ image_url: "", link: "" });
  const [newClient, setNewClient] = useState({ img: "", link: "" });
  const [newTeam, setNewTeam] = useState({
    name: "",
    role: "",
    image_url: "",
    bio: "",
    link_x: "",
    link_linkedin: "",
    link_website: "",
    link_instagram: "",
  });

  // ==========================================================
  // SISTEM KEAMANAN & AUTO-LOGOUT
  // ==========================================================
  const getToken = () => localStorage.getItem("token");

  const handleLogout = (reason: string) => {
    alert(reason);
    localStorage.clear();
    router.push("/login");
  };

  // 1. Cek Validitas Token Awal & Hitung Mundur Kedaluwarsa JWT
  useEffect(() => {
    const token = getToken();
    if (!token || localStorage.getItem("role") !== "Admin") {
      router.push("/login");
      return;
    }

    setAdminName(localStorage.getItem("name") || "Web Admin");
    fetchAllCMSData();

    try {
      // Decode JWT Payload (bagian ke-2 dari struktur token)
      const payloadBase64 = token.split(".")[1];
      const payload = JSON.parse(atob(payloadBase64));

      const expTime = payload.exp * 1000; // Konversi ke millisecond
      const timeRemaining = expTime - Date.now();

      if (timeRemaining <= 0) {
        handleLogout("Sesi token telah kedaluwarsa. Silakan login kembali.");
      } else {
        // Pasang timer rahasia yang akan menendang user tepat saat token mati
        const expiryTimer = setTimeout(() => {
          handleLogout("Waktu login Anda telah habis. Silakan login kembali.");
        }, timeRemaining);
        return () => clearTimeout(expiryTimer);
      }
    } catch (error) {
      console.error("Token format tidak valid.");
      handleLogout("Terjadi kesalahan pada sesi Anda.");
    }
  }, [router]);

  // 2. Idle Timeout (AFK 30 Menit = Auto Logout)
  useEffect(() => {
    let idleTimer: NodeJS.Timeout;
    const idleTimeLimit = 30 * 60 * 1000; // 30 Menit

    const resetIdleTimer = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        handleLogout("Anda dikeluarkan karena tidak ada aktivitas (Idle 30 Menit).");
      }, idleTimeLimit);
    };

    // Dengarkan aktivitas fisik user
    const events = ["mousemove", "keydown", "scroll", "click"];
    events.forEach((event) => window.addEventListener(event, resetIdleTimer));

    resetIdleTimer(); // Mulai timer pertama kali

    return () => {
      clearTimeout(idleTimer);
      events.forEach((event) => window.removeEventListener(event, resetIdleTimer));
    };
  }, []);

  // 3. API 401 Interceptor (Pencegat Ditolak Server)
  const checkAPIUnauthorized = (res: Response) => {
    if (res.status === 401) {
      handleLogout("Sesi Anda ditolak oleh server. Silakan login kembali.");
      return true; // Berarti unauthorized
    }
    return false;
  };
  // ==========================================================

  const fetchAllCMSData = async () => {
    try {
      setLoading(true);
      const res = await Promise.all([
        fetch("https://api.squarecloudsmc.com/cms/commissions"),
        fetch("https://api.squarecloudsmc.com/cms/marketplaces"),
        fetch("https://api.squarecloudsmc.com/cms/premades"),
        fetch("https://api.squarecloudsmc.com/cms/exhibitions"),
        fetch("https://api.squarecloudsmc.com/cms/team"),
        fetch("https://api.squarecloudsmc.com/cms/clients"),
      ]);
      const data = await Promise.all(res.map((r) => r.json()));

      if (data[0].data) setCommissions(data[0].data);
      if (data[1].data) setMarketplaces(data[1].data);
      if (data[2].data) setPremades(data[2].data);
      if (data[3].data) setExhibitions(data[3].data);
      if (data[4].data) setTeamMembers(data[4].data);
      if (data[5].data) setClients(data[5].data);
    } catch (error) {
      setPesan({ type: "error", text: "Gagal terhubung ke server Backend." });
    } finally {
      setLoading(false);
    }
  };

  // --- FUNGSI UPLOAD GAMBAR UTAMA (AUTO-WEBP) ---
  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    onSuccess: (url: string) => void
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setPesan({ type: "info", text: "Mengunggah & Mengkonversi ke WebP..." });
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("https://api.squarecloudsmc.com/upload-image/", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      });
      if (checkAPIUnauthorized(res)) return; // Cek Auto-Logout

      const data = await res.json();
      if (res.ok) {
        onSuccess(data.url);
        setPesan({ type: "success", text: "Gambar berhasil diunggah!" });
      } else setPesan({ type: "error", text: "Gagal upload." });
    } catch (err) {
      setPesan({ type: "error", text: "Kesalahan jaringan saat upload." });
    } finally {
      setIsUploading(false);
    }
  };

  // --- FUNGSI UPLOAD GAMBAR GALERI MULTIPLE (KHUSUS COMMISSION) ---
  const handleGalleryUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    isEditMode: boolean = false
  ) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setPesan({ type: "info", text: `Mengunggah ${files.length} gambar ke galeri...` });
    try {
      let currentUrls = [];
      if (isEditMode) {
        currentUrls = editingItem.gallery_urls
          ? editingItem.gallery_urls.split(",").filter(Boolean)
          : [];
      } else {
        currentUrls = newCommission.gallery_urls
          ? newCommission.gallery_urls.split(",").filter(Boolean)
          : [];
      }

      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("file", files[i]);
        const res = await fetch("https://api.squarecloudsmc.com/upload-image/", {
          method: "POST",
          headers: { Authorization: `Bearer ${getToken()}` },
          body: formData,
        });
        if (checkAPIUnauthorized(res)) return;
        const data = await res.json();
        if (res.ok) {
          currentUrls.push(data.url);
        } else {
          throw new Error("Gagal mengunggah salah satu gambar.");
        }
      }

      if (isEditMode) {
        setEditingItem({ ...editingItem, gallery_urls: currentUrls.join(",") });
      } else {
        setNewCommission({ ...newCommission, gallery_urls: currentUrls.join(",") });
      }
      setPesan({ type: "success", text: "Semua gambar galeri berhasil ditambahkan!" });
    } catch (err) {
      setPesan({ type: "error", text: "Gagal upload beberapa gambar galeri." });
    } finally {
      setIsUploading(false);
    }
  };

  const removeGalleryUrl = (urlToRemove: string, isEditMode: boolean = false) => {
    if (isEditMode) {
      const urls = editingItem.gallery_urls.split(",").filter((u: string) => u !== urlToRemove);
      setEditingItem({ ...editingItem, gallery_urls: urls.join(",") });
    } else {
      const urls = newCommission.gallery_urls.split(",").filter((u: string) => u !== urlToRemove);
      setNewCommission({ ...newCommission, gallery_urls: urls.join(",") });
    }
  };

  // --- FUNGSI CRUD BERSAMA ---
  const handleAddItem = async (
    e: React.FormEvent,
    endpoint: string,
    payload: any,
    resetState: Function,
    emptyState: any
  ) => {
    e.preventDefault();
    const res = await fetch(`https://api.squarecloudsmc.com/cms/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify(payload),
    });
    if (checkAPIUnauthorized(res)) return; // Cek Auto-Logout

    if (res.ok) {
      setPesan({ type: "success", text: "Data berhasil ditambahkan!" });
      resetState(emptyState);
      fetchAllCMSData();
    } else {
      setPesan({ type: "error", text: "Gagal menambahkan data!" });
    }
  };

  const handleDeleteItem = async (endpoint: string, id: number) => {
    if (!confirm("Hapus data ini secara permanen?")) return;
    const res = await fetch(`https://api.squarecloudsmc.com/cms/${endpoint}/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (checkAPIUnauthorized(res)) return; // Cek Auto-Logout

    if (res.ok) {
      setPesan({ type: "success", text: "Data berhasil dihapus!" });
      fetchAllCMSData();
    }
  };

  const handleUpdateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !editCategory) return;
    const res = await fetch(`https://api.squarecloudsmc.com/cms/${editCategory}/${editingItem.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify(editingItem),
    });
    if (checkAPIUnauthorized(res)) return; // Cek Auto-Logout

    if (res.ok) {
      setPesan({ type: "success", text: "Data berhasil diperbarui!" });
      setEditingItem(null);
      setEditCategory(null);
      fetchAllCMSData();
    } else {
      setPesan({ type: "error", text: "Gagal memperbarui data!" });
    }
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center font-bold text-blue-600 bg-gray-50">
        Menarik Data Database...
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row relative font-sans text-slate-800">
      {/* SIDEBAR */}
      <div className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col z-10 shadow-sm min-h-screen">
        <div className="mb-8">
          <h1 className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">
            Website CMS
          </h1>
          <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-wider">
            squarecloudsmc.com
          </p>
        </div>
        <nav className="flex flex-col gap-2 flex-grow">
          {["commission", "marketplaces", "premades", "exhibitions", "team", "clients"].map(
            (tab) => (
              <button
                key={tab}
                onClick={() => {
                  setActiveTab(tab);
                  setPesan({ type: "", text: "" });
                }}
                className={`text-left px-4 py-3 rounded-xl font-bold text-sm uppercase transition-colors ${activeTab === tab ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-gray-50"}`}
              >
                {tab}
              </button>
            )
          )}
        </nav>
        <div className="mt-8 pt-6 border-t border-gray-100">
          <p className="font-bold text-gray-800 mb-4 text-sm">Hi, {adminName}</p>
          <button
            onClick={() => router.push("/admin")}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2.5 rounded-xl text-sm font-bold mb-2"
          >
            Portal Admin
          </button>
          <button
            onClick={() => handleLogout("Terima kasih telah menggunakan sistem.")}
            className="w-full bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2.5 rounded-xl text-sm font-bold"
          >
            Logout
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 p-6 md:p-10 overflow-y-auto">
        {pesan.text && (
          <div
            className={`mb-6 p-4 rounded-xl text-sm font-bold ${pesan.type === "error" ? "bg-red-50 text-red-600" : pesan.type === "info" ? "bg-blue-50 text-blue-700 animate-pulse" : "bg-green-50 text-green-700"}`}
          >
            {pesan.text}
          </div>
        )}

        {/* 1. TAB COMMISSION */}
        {activeTab === "commission" && (
          <div className="max-w-6xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Commission Projects</h2>
              <p className="text-sm text-gray-500 font-medium">
                Bento Box display dengan fitur carousel multi-gambar dan Auto-Curator.
              </p>
            </div>

            <form
              onSubmit={(e) =>
                handleAddItem(e, "commissions", newCommission, setNewCommission, {
                  title: "",
                  description: "",
                  thumbnail_url: "",
                  gallery_urls: "",
                  link: "",
                  year: currentYear,
                })
              }
              className="bg-white p-6 rounded-3xl shadow-sm border space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold block mb-1">Judul Project (Opsional)</label>
                  <input
                    type="text"
                    value={newCommission.title}
                    onChange={(e) => setNewCommission({ ...newCommission, title: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold block mb-1 text-blue-600">
                    Tahun (Penentu Chapter) *
                  </label>
                  <input
                    type="text"
                    required
                    value={newCommission.year}
                    onChange={(e) => setNewCommission({ ...newCommission, year: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm bg-blue-50"
                    placeholder="2024"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold block mb-1">Direct Link (Opsional)</label>
                  <input
                    type="text"
                    value={newCommission.link}
                    onChange={(e) => setNewCommission({ ...newCommission, link: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold block mb-1">Deskripsi (Opsional)</label>
                <textarea
                  rows={2}
                  value={newCommission.description}
                  onChange={(e) =>
                    setNewCommission({ ...newCommission, description: e.target.value })
                  }
                  className="w-full rounded-xl border px-4 py-2 text-sm"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 border rounded-xl">
                  <label className="text-xs font-bold block mb-2 text-blue-600">
                    Thumbnail Utama *
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    required={!newCommission.thumbnail_url}
                    onChange={(e) =>
                      handleFileUpload(e, (url) =>
                        setNewCommission({ ...newCommission, thumbnail_url: url })
                      )
                    }
                    className="text-xs"
                  />
                  {newCommission.thumbnail_url && (
                    <img src={newCommission.thumbnail_url} className="h-16 mt-2 rounded border" />
                  )}
                </div>

                <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
                  <label className="text-xs font-bold block mb-2 text-blue-700">
                    Tambah Gambar Galeri (Carousel)
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={(e) => handleGalleryUpload(e, false)}
                    className="text-xs"
                  />
                  <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                    {newCommission.gallery_urls &&
                      newCommission.gallery_urls
                        .split(",")
                        .filter(Boolean)
                        .map((url, i) => (
                          <div key={i} className="relative group flex-shrink-0">
                            <img src={url} className="h-14 w-14 object-cover rounded border" />
                            <button
                              type="button"
                              onClick={() => removeGalleryUrl(url, false)}
                              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-[10px] hidden group-hover:flex items-center justify-center font-bold"
                            >
                              X
                            </button>
                          </div>
                        ))}
                  </div>
                </div>
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold text-sm"
              >
                + Tambah Commission
              </button>
            </form>

            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">THUMBNAIL</th>
                    <th className="px-6 py-4 text-xs font-bold">INFO PROJECT</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {commissions.map((c) => (
                    <tr key={c.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <img
                          src={c.thumbnail_url}
                          className="w-20 h-14 object-cover rounded-lg border"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900">
                          {c.title || <span className="italic text-gray-400">Tanpa Judul</span>}{" "}
                          <span className="text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded text-xs ml-2">
                            {c.year}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {c.gallery_urls?.split(",").filter(Boolean).length || 0} Gambar Galeri
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(c);
                            setEditCategory("commissions");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("commissions", c.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 2. TAB MARKETPLACE */}
        {activeTab === "marketplaces" && (
          <div className="max-w-6xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Marketplace Catalog</h2>
              <p className="text-sm text-gray-500 font-medium">
                Katalog item official dengan harga Minecoin.
              </p>
            </div>

            <form
              onSubmit={(e) =>
                handleAddItem(e, "marketplaces", newMarketplace, setNewMarketplace, {
                  title: "",
                  content_type: "",
                  image_url: "",
                  price_minecoin: 0,
                  link: "",
                })
              }
              className="bg-white p-6 rounded-3xl shadow-sm border space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold block mb-1">Nama Item *</label>
                  <input
                    type="text"
                    required
                    value={newMarketplace.title}
                    onChange={(e) =>
                      setNewMarketplace({ ...newMarketplace, title: e.target.value })
                    }
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold block mb-1 text-emerald-600">
                    Harga (Minecoin) *
                  </label>
                  <input
                    type="number"
                    required
                    value={newMarketplace.price_minecoin}
                    onChange={(e) =>
                      setNewMarketplace({
                        ...newMarketplace,
                        price_minecoin: parseInt(e.target.value),
                      })
                    }
                    className="w-full rounded-xl border px-4 py-2 text-sm bg-emerald-50"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs font-bold block mb-1">
                    Content Type (Contoh: Skin Pack, Survival Spawn) *
                  </label>
                  <input
                    type="text"
                    required
                    value={newMarketplace.content_type}
                    onChange={(e) =>
                      setNewMarketplace({ ...newMarketplace, content_type: e.target.value })
                    }
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold block mb-1 text-blue-600">
                    Upload Banner Item *
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    required={!newMarketplace.image_url}
                    onChange={(e) =>
                      handleFileUpload(e, (url) =>
                        setNewMarketplace({ ...newMarketplace, image_url: url })
                      )
                    }
                    className="text-xs"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold block mb-1">
                    Link Eksternal Minecraft (Opsional)
                  </label>
                  <input
                    type="text"
                    value={newMarketplace.link}
                    onChange={(e) => setNewMarketplace({ ...newMarketplace, link: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                    placeholder="minecraft://..."
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="w-full bg-[#024e01] text-white py-3 rounded-xl font-bold text-sm"
              >
                + Tambah Marketplace Item
              </button>
            </form>

            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">BANNER</th>
                    <th className="px-6 py-4 text-xs font-bold">ITEM & INFO</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {marketplaces.map((m) => (
                    <tr key={m.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <img
                          src={m.image_url}
                          className="w-20 h-14 object-cover rounded-lg border"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900">{m.title}</div>
                        <div className="text-xs text-emerald-600 font-bold mt-1">
                          {m.content_type} • {m.price_minecoin} Minecoin
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(m);
                            setEditCategory("marketplaces");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("marketplaces", m.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 3. TAB PREMADE */}
        {activeTab === "premades" && (
          <div className="max-w-6xl space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">Premade Assets Showcase</h2>
              <p className="text-sm text-gray-500 font-medium">
                Showcase asset premium dengan fitur filter kategori Aardvark style.
              </p>
            </div>

            <form
              onSubmit={(e) =>
                handleAddItem(e, "premades", newPremade, setNewPremade, {
                  title: "",
                  category: "Worlds",
                  description: "",
                  image_url: "",
                  price_usd: 0.0,
                  link: "",
                })
              }
              className="bg-white p-6 rounded-3xl shadow-sm border space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold block mb-1">Nama Asset *</label>
                  <input
                    type="text"
                    required
                    value={newPremade.title}
                    onChange={(e) => setNewPremade({ ...newPremade, title: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold block mb-1">Kategori Filter *</label>
                  <select
                    required
                    value={newPremade.category}
                    onChange={(e) => setNewPremade({ ...newPremade, category: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm bg-white"
                  >
                    <option value="Worlds">Worlds / Maps</option>
                    <option value="Hubs">Hubs & Lobbies</option>
                    <option value="Arenas">Arenas</option>
                    <option value="Organics">Organics / Models</option>
                    <option value="Setups">Server Setups</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="text-xs font-bold block mb-1">Deskripsi Pendek *</label>
                  <textarea
                    required
                    rows={2}
                    value={newPremade.description}
                    onChange={(e) => setNewPremade({ ...newPremade, description: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold block mb-1 text-green-700">
                    Harga ($ USD) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={newPremade.price_usd}
                    onChange={(e) =>
                      setNewPremade({ ...newPremade, price_usd: parseFloat(e.target.value) })
                    }
                    className="w-full rounded-xl border px-4 py-2 text-sm bg-green-50"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold block mb-1 text-blue-600">
                    Upload Gambar Asset *
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    required={!newPremade.image_url}
                    onChange={(e) =>
                      handleFileUpload(e, (url) => setNewPremade({ ...newPremade, image_url: url }))
                    }
                    className="text-xs"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="text-xs font-bold block mb-1">
                    Direct Link (Beli/Download)
                  </label>
                  <input
                    type="text"
                    value={newPremade.link}
                    onChange={(e) => setNewPremade({ ...newPremade, link: e.target.value })}
                    className="w-full rounded-xl border px-4 py-2 text-sm"
                    placeholder="https://..."
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="w-full bg-[#412f1f] text-white py-3 rounded-xl font-bold text-sm"
              >
                + Tambah Premade Asset
              </button>
            </form>

            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">GAMBAR</th>
                    <th className="px-6 py-4 text-xs font-bold">ASSET INFO</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {premades.map((p) => (
                    <tr key={p.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <img
                          src={p.image_url}
                          className="w-20 h-14 object-cover rounded-lg border"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900">{p.title}</div>
                        <div className="text-xs font-bold mt-1 text-slate-500">
                          <span className="text-blue-600 uppercase mr-2">
                            {p.category || "Worlds"}
                          </span>{" "}
                          • <span className="text-green-700 ml-2">${p.price_usd}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(p);
                            setEditCategory("premades");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("premades", p.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 4. TAB EXHIBITION */}
        {activeTab === "exhibitions" && (
          <div className="max-w-5xl space-y-6">
            <h2 className="text-2xl font-bold">Exhibition Showcase (Marquee)</h2>
            <form
              onSubmit={(e) =>
                handleAddItem(e, "exhibitions", newExhibition, setNewExhibition, {
                  image_url: "",
                  link: "",
                })
              }
              className="bg-white p-6 rounded-2xl border flex flex-col md:flex-row gap-4 md:items-end"
            >
              <div className="flex-1">
                <label className="text-xs font-bold block mb-1">Upload Gambar</label>
                <input
                  type="file"
                  accept="image/*"
                  required={!newExhibition.image_url}
                  onChange={(e) =>
                    handleFileUpload(e, (url) =>
                      setNewExhibition({ ...newExhibition, image_url: url })
                    )
                  }
                />
              </div>
              <div className="flex-1">
                <label className="text-xs font-bold block mb-1">Link Redirect</label>
                <input
                  type="text"
                  value={newExhibition.link}
                  onChange={(e) => setNewExhibition({ ...newExhibition, link: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm"
              >
                Tambah Marquee
              </button>
            </form>
            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">GAMBAR</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {exhibitions.map((exh) => (
                    <tr key={exh.id} className="border-b">
                      <td className="px-6 py-4">
                        <img src={exh.image_url} className="w-24 h-14 object-cover rounded" />
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(exh);
                            setEditCategory("exhibitions");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("exhibitions", exh.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. TAB TEAM */}
        {activeTab === "team" && (
          <div className="max-w-5xl space-y-6">
            <h2 className="text-2xl font-bold">Team Members</h2>
            <form
              onSubmit={(e) =>
                handleAddItem(e, "team", newTeam, setNewTeam, {
                  name: "",
                  role: "",
                  image_url: "",
                  bio: "",
                  link_x: "",
                  link_linkedin: "",
                  link_website: "",
                  link_instagram: "",
                })
              }
              className="bg-white p-6 rounded-2xl border grid grid-cols-2 gap-4"
            >
              <div>
                <label className="text-xs font-bold block mb-1">Nama Lengkap</label>
                <input
                  type="text"
                  required
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">Jabatan</label>
                <input
                  type="text"
                  required
                  value={newTeam.role}
                  onChange={(e) => setNewTeam({ ...newTeam, role: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-bold block mb-1">Bio Deskripsi</label>
                <textarea
                  rows={2}
                  value={newTeam.bio}
                  onChange={(e) => setNewTeam({ ...newTeam, bio: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm resize-none"
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-bold text-blue-600 block mb-1">
                  Upload Foto Profil
                </label>
                <input
                  type="file"
                  accept="image/*"
                  required={!newTeam.image_url}
                  onChange={(e) =>
                    handleFileUpload(e, (url) => setNewTeam({ ...newTeam, image_url: url }))
                  }
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">Link Website</label>
                <input
                  type="text"
                  value={newTeam.link_website}
                  onChange={(e) => setNewTeam({ ...newTeam, link_website: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">Link Twitter (X)</label>
                <input
                  type="text"
                  value={newTeam.link_x}
                  onChange={(e) => setNewTeam({ ...newTeam, link_x: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">Link LinkedIn</label>
                <input
                  type="text"
                  value={newTeam.link_linkedin}
                  onChange={(e) => setNewTeam({ ...newTeam, link_linkedin: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">Link Instagram</label>
                <input
                  type="text"
                  value={newTeam.link_instagram}
                  onChange={(e) => setNewTeam({ ...newTeam, link_instagram: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="col-span-2 bg-blue-600 text-white py-3 rounded-xl font-bold text-sm"
              >
                + Tambah Anggota Tim
              </button>
            </form>
            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">PROFIL</th>
                    <th className="px-6 py-4 text-xs font-bold">NAMA</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {teamMembers.map((member) => (
                    <tr key={member.id} className="border-b">
                      <td className="px-6 py-4">
                        <img
                          src={member.image_url}
                          className="w-10 h-10 rounded-full object-cover border"
                        />
                      </td>
                      <td className="px-6 py-4 font-bold">
                        {member.name}{" "}
                        <span className="block text-xs font-normal text-gray-500">
                          {member.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(member);
                            setEditCategory("team");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("team", member.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 6. TAB CLIENTS */}
        {activeTab === "clients" && (
          <div className="max-w-4xl space-y-6">
            <h2 className="text-2xl font-bold">Global Clients (Marquee)</h2>
            <form
              onSubmit={(e) =>
                handleAddItem(e, "clients", newClient, setNewClient, { img: "", link: "" })
              }
              className="bg-white p-6 rounded-2xl border space-y-4"
            >
              <div>
                <label className="text-xs font-bold block mb-1 text-blue-600">
                  Upload Logo Client *
                </label>
                <input
                  type="file"
                  accept="image/*"
                  required={!newClient.img}
                  onChange={(e) =>
                    handleFileUpload(e, (url) => setNewClient({ ...newClient, img: url }))
                  }
                />
                {newClient.img && (
                  <img
                    src={newClient.img}
                    className="h-14 mt-2 object-contain bg-gray-50 p-2 rounded border"
                  />
                )}
              </div>
              <div>
                <label className="text-xs font-bold block mb-1">
                  Link Website Client (Opsional)
                </label>
                <input
                  type="text"
                  value={newClient.link}
                  onChange={(e) => setNewClient({ ...newClient, link: e.target.value })}
                  className="w-full border rounded-xl px-4 py-2"
                  placeholder="https://..."
                />
              </div>
              <button
                type="submit"
                disabled={isUploading}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold"
              >
                + Tambah Client
              </button>
            </form>

            <div className="bg-white rounded-3xl border overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-4 text-xs font-bold">LOGO</th>
                    <th className="px-6 py-4 text-xs font-bold">LINK TUJUAN</th>
                    <th className="px-6 py-4 text-xs font-bold text-center">AKSI</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((c) => (
                    <tr key={c.id} className="border-b hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <img src={c.img} className="h-10 object-contain" />
                      </td>
                      <td className="px-6 py-4 text-sm text-blue-600 truncate max-w-xs">
                        {c.link || "-"}
                      </td>
                      <td className="px-6 py-4 text-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingItem(c);
                            setEditCategory("clients");
                          }}
                          className="text-blue-600 font-bold text-xs bg-blue-50 px-3 py-1.5 rounded-lg"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteItem("clients", c.id)}
                          className="text-red-600 font-bold text-xs bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ==============================================
          POPUP MODAL EDIT DATA BERSAMA
      ============================================== */}
      {editingItem && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 cursor-pointer"
          onClick={() => {
            setEditingItem(null);
            setEditCategory(null);
          }}
        >
          <div
            className="bg-white rounded-3xl p-8 max-w-2xl w-full space-y-4 max-h-[90vh] overflow-y-auto cursor-default shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-black text-gray-900 border-b pb-2">
              Edit Data {editCategory?.toUpperCase()}
            </h3>

            <form onSubmit={handleUpdateItem} className="space-y-4">
              <div className="p-4 bg-gray-50 border rounded-xl">
                <label className="text-xs font-bold block mb-2 text-blue-700">
                  Ganti Gambar/Thumbnail Utama
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) =>
                    handleFileUpload(e, (url) =>
                      setEditingItem({ ...editingItem, image_url: url, thumbnail_url: url })
                    )
                  }
                  className="text-xs"
                />
                {(editingItem.image_url || editingItem.thumbnail_url) && (
                  <img
                    src={editingItem.image_url || editingItem.thumbnail_url}
                    className="h-16 mt-3 object-cover rounded border shadow-sm"
                  />
                )}
              </div>

              {editCategory === "commissions" && (
                <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
                  <label className="text-xs font-bold block mb-2 text-blue-700">
                    Tambah Gambar Galeri (Carousel)
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={(e) => handleGalleryUpload(e, true)}
                    className="text-xs"
                  />
                  <div className="flex gap-2 mt-3 overflow-x-auto pb-2">
                    {editingItem.gallery_urls &&
                      editingItem.gallery_urls
                        .split(",")
                        .filter(Boolean)
                        .map((url: string, i: number) => (
                          <div key={i} className="relative group flex-shrink-0">
                            <img src={url} className="h-14 w-14 object-cover rounded border" />
                            <button
                              type="button"
                              onClick={() => removeGalleryUrl(url, true)}
                              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-[10px] hidden group-hover:flex items-center justify-center font-bold"
                            >
                              X
                            </button>
                          </div>
                        ))}
                  </div>
                </div>
              )}

              {/* INPUT TEKS & TAHUN/KATEGORI */}
              {(editCategory === "commissions" ||
                editCategory === "marketplaces" ||
                editCategory === "premades") && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold block mb-1">Judul Project/Item</label>
                    <input
                      type="text"
                      value={editingItem.title || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, title: e.target.value })}
                      className="w-full border rounded-xl px-4 py-2"
                    />
                  </div>

                  {editCategory === "commissions" && (
                    <div>
                      <label className="text-xs font-bold block mb-1 text-blue-600">
                        Tahun Project
                      </label>
                      <input
                        type="text"
                        value={editingItem.year || ""}
                        onChange={(e) => setEditingItem({ ...editingItem, year: e.target.value })}
                        className="w-full border rounded-xl px-4 py-2 bg-blue-50"
                      />
                    </div>
                  )}

                  {editCategory === "premades" && (
                    <div>
                      <label className="text-xs font-bold block mb-1 text-blue-600">
                        Kategori Filter
                      </label>
                      <select
                        value={editingItem.category || "Worlds"}
                        onChange={(e) =>
                          setEditingItem({ ...editingItem, category: e.target.value })
                        }
                        className="w-full rounded-xl border px-4 py-2 bg-white"
                      >
                        <option value="Worlds">Worlds / Maps</option>
                        <option value="Hubs">Hubs & Lobbies</option>
                        <option value="Arenas">Arenas</option>
                        <option value="Organics">Organics / Models</option>
                        <option value="Setups">Server Setups</option>
                      </select>
                    </div>
                  )}
                </div>
              )}

              {(editCategory === "commissions" || editCategory === "premades") && (
                <div>
                  <label className="text-xs font-bold block mb-1">Deskripsi</label>
                  <textarea
                    rows={3}
                    value={editingItem.description || ""}
                    onChange={(e) =>
                      setEditingItem({ ...editingItem, description: e.target.value })
                    }
                    className="w-full border rounded-xl px-4 py-2 resize-none"
                  />
                </div>
              )}

              {editCategory === "marketplaces" && (
                <>
                  <div>
                    <label className="text-xs font-bold block mb-1">
                      Content Type (Skin Pack, World, dll)
                    </label>
                    <input
                      type="text"
                      value={editingItem.content_type || ""}
                      onChange={(e) =>
                        setEditingItem({ ...editingItem, content_type: e.target.value })
                      }
                      className="w-full border rounded-xl px-4 py-2"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1 text-emerald-600">
                      Harga (Minecoin)
                    </label>
                    <input
                      type="number"
                      value={editingItem.price_minecoin || 0}
                      onChange={(e) =>
                        setEditingItem({ ...editingItem, price_minecoin: parseInt(e.target.value) })
                      }
                      className="w-full border rounded-xl px-4 py-2 bg-emerald-50"
                    />
                  </div>
                </>
              )}

              {editCategory === "premades" && (
                <div>
                  <label className="text-xs font-bold block mb-1 text-green-700">
                    Harga ($ USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={editingItem.price_usd || 0}
                    onChange={(e) =>
                      setEditingItem({ ...editingItem, price_usd: parseFloat(e.target.value) })
                    }
                    className="w-full border rounded-xl px-4 py-2 bg-green-50"
                  />
                </div>
              )}

              {editCategory === "team" && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold block mb-1">Nama</label>
                    <input
                      type="text"
                      value={editingItem.name || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, name: e.target.value })}
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1">Jabatan</label>
                    <input
                      type="text"
                      value={editingItem.role || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, role: e.target.value })}
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs font-bold block mb-1">Bio</label>
                    <textarea
                      rows={2}
                      value={editingItem.bio || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, bio: e.target.value })}
                      className="w-full border rounded-xl px-4 py-2 text-sm resize-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1">Link Web</label>
                    <input
                      type="text"
                      value={editingItem.link_website || ""}
                      onChange={(e) =>
                        setEditingItem({ ...editingItem, link_website: e.target.value })
                      }
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1">Link Twitter</label>
                    <input
                      type="text"
                      value={editingItem.link_x || ""}
                      onChange={(e) => setEditingItem({ ...editingItem, link_x: e.target.value })}
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1">Link LinkedIn</label>
                    <input
                      type="text"
                      value={editingItem.link_linkedin || ""}
                      onChange={(e) =>
                        setEditingItem({ ...editingItem, link_linkedin: e.target.value })
                      }
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold block mb-1">Link Instagram</label>
                    <input
                      type="text"
                      value={editingItem.link_instagram || ""}
                      onChange={(e) =>
                        setEditingItem({ ...editingItem, link_instagram: e.target.value })
                      }
                      className="w-full border rounded-xl px-4 py-2 text-sm"
                    />
                  </div>
                </div>
              )}

              {editCategory === "clients" && (
                <div>
                  <label className="text-xs font-bold block mb-1">Nama Perusahaan</label>
                  <input
                    type="text"
                    value={editingItem.name || ""}
                    onChange={(e) => setEditingItem({ ...editingItem, name: e.target.value })}
                    className="w-full border rounded-xl px-4 py-2"
                  />
                </div>
              )}

              {(editCategory === "commissions" ||
                editCategory === "marketplaces" ||
                editCategory === "premades" ||
                editCategory === "exhibitions") && (
                <div>
                  <label className="text-xs font-bold block mb-1">Link Tujuan / Redirect</label>
                  <input
                    type="text"
                    value={editingItem.link || ""}
                    onChange={(e) => setEditingItem({ ...editingItem, link: e.target.value })}
                    className="w-full border rounded-xl px-4 py-2"
                  />
                </div>
              )}

              <div className="flex gap-3 pt-6 border-t mt-4">
                <button
                  type="submit"
                  disabled={isUploading}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-xl font-bold text-sm"
                >
                  Simpan Perubahan
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditingItem(null);
                    setEditCategory(null);
                  }}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-3 rounded-xl font-bold text-sm"
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
