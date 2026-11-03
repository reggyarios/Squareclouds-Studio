"use client";

import { useState } from "react";
import Link from "next/link";
import { apiErrorMessage, apiUrl } from "@/lib/api";
import { JOB_OPTIONS } from "@/lib/portal";

const MIN_PASSWORD_LENGTH = 8;

const inputClass =
  "mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-blue-500 sm:text-sm";

export default function RegisterPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    job_title: JOB_OPTIONS[0],
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => setForm({ ...form, [field]: e.target.value });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password minimal ${MIN_PASSWORD_LENGTH} karakter.`);
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Konfirmasi password tidak sama.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(apiUrl("/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          password: form.password,
          job_title: form.job_title,
        }),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(apiErrorMessage(data, "Pendaftaran gagal. Coba lagi."));
      }

      setSuccess(data?.message || "Pendaftaran diterima. Tunggu persetujuan admin.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pendaftaran gagal. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-8 rounded-2xl bg-white p-10 shadow-xl">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">Squareclouds</h2>
          <p className="mt-2 text-sm text-gray-500">Daftar sebagai kreator</p>
        </div>

        {success ? (
          <div className="space-y-6 text-center">
            <div className="rounded-lg bg-green-50 p-4 text-sm font-medium text-green-700">
              {success}
            </div>
            <Link
              href="/login"
              className="inline-block text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Ke halaman masuk
            </Link>
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleRegister}>
            <div className="space-y-4 rounded-md shadow-sm">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nama</label>
                <input
                  type="text"
                  required
                  className={inputClass}
                  placeholder="Nama lengkap"
                  value={form.name}
                  onChange={update("name")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  required
                  className={inputClass}
                  placeholder="email@studio.com"
                  value={form.email}
                  onChange={update("email")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Password</label>
                <input
                  type="password"
                  required
                  minLength={MIN_PASSWORD_LENGTH}
                  className={inputClass}
                  placeholder="Minimal 8 karakter"
                  value={form.password}
                  onChange={update("password")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Konfirmasi Password
                </label>
                <input
                  type="password"
                  required
                  className={inputClass}
                  placeholder="••••••••"
                  value={form.confirmPassword}
                  onChange={update("confirmPassword")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Job Title</label>
                <select
                  required
                  className={`${inputClass} bg-white`}
                  value={form.job_title}
                  onChange={update("job_title")}
                >
                  {JOB_OPTIONS.map((j) => (
                    <option key={j} value={j}>
                      {j}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {error && <div className="text-sm text-red-500 text-center font-medium">{error}</div>}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative flex w-full justify-center rounded-lg border border-transparent bg-gradient-to-r from-cyan-500 to-blue-600 py-2.5 px-4 text-sm font-medium text-white hover:from-cyan-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {loading ? "Memproses..." : "Daftar"}
              </button>
            </div>
          </form>
        )}

        <p className="text-center text-sm text-gray-500">
          Sudah punya akun?{" "}
          <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700">
            Masuk
          </Link>
        </p>
      </div>
    </div>
  );
}
