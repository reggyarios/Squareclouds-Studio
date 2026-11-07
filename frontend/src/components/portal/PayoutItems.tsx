"use client";

// Rincian payout per konten: preview sebelum dicatat (admin) dan isi baris
// "Rincian" di riwayat payout (admin & kreator). Angka dari backend; di sini
// hanya format tampilan.
import { useEffect, useState } from "react";
import { type PayoutItem, formatIDR, formatUsd } from "@/lib/portal";

type TableProps = {
  items: PayoutItem[];
  totalUsd: number;
  // Hanya payout bank/e-wallet; null = tanpa baris rupiah.
  totalIdr?: number | null;
  idrRate?: number | null;
};

export function PayoutItemsTable({ items, totalUsd, totalIdr = null, idrRate = null }: TableProps) {
  const totalUnits = items.reduce((sum, item) => sum + item.units, 0);
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="text-xs font-bold uppercase text-gray-500">
          <th className="py-1.5 pr-4">Konten</th>
          <th className="py-1.5 pr-4 text-right">Unit</th>
          <th className="py-1.5 text-right">USD</th>
        </tr>
      </thead>
      <tbody>
        {items.length === 0 ? (
          <tr className="border-t border-gray-100">
            <td colSpan={3} className="py-2 font-bold text-gray-400">
              Rincian per konten tidak tersedia untuk payout ini.
            </td>
          </tr>
        ) : (
          items.map((item) => (
            <tr key={item.content_id} className="border-t border-gray-100">
              <td className="py-1.5 pr-4 text-gray-800">{item.name}</td>
              <td className="py-1.5 pr-4 text-right">{item.units.toLocaleString("id-ID")}</td>
              <td className="py-1.5 text-right">{formatUsd(item.share_usd)}</td>
            </tr>
          ))
        )}
      </tbody>
      <tfoot>
        <tr className="border-t-2 border-gray-300 font-black text-gray-900">
          <td className="py-1.5 pr-4">Total</td>
          <td className="py-1.5 pr-4 text-right">
            {items.length > 0 && totalUnits.toLocaleString("id-ID")}
          </td>
          <td className="py-1.5 text-right">{formatUsd(totalUsd)}</td>
        </tr>
        {totalIdr !== null && (
          <tr className="font-bold text-gray-700">
            <td colSpan={2} className="py-1 pr-4">
              Total (IDR)
              {idrRate !== null && (
                <span className="text-xs font-normal text-gray-500">
                  {" "}
                  · kurs {formatIDR(idrRate)}/$
                </span>
              )}
            </td>
            <td className="py-1 text-right">{formatIDR(totalIdr)}</td>
          </tr>
        )}
      </tfoot>
    </table>
  );
}

// Bagian respons GET /payouts/{id} yang dipakai di sini.
type PayoutDetail = {
  amount_usd: number;
  amount_idr: number | null;
  idr_rate: number | null;
  items: PayoutItem[];
};

/** Ambil GET /payouts/{id} lalu tampilkan rinciannya. `api` = apiFetch milik halaman. */
export function PayoutItemsDetail({
  payoutId,
  api,
}: {
  payoutId: number;
  api: (path: string) => Promise<PayoutDetail>;
}) {
  const [detail, setDetail] = useState<PayoutDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api(`/payouts/${payoutId}`)
      .then((data) => active && setDetail(data))
      .catch(
        (err) => active && setError(err instanceof Error ? err.message : "Gagal memuat rincian.")
      );
    return () => {
      active = false;
    };
  }, [api, payoutId]);

  if (error) return <p className="text-sm font-bold text-red-600">{error}</p>;
  if (!detail) return <p className="text-sm font-bold text-blue-600">Memuat rincian...</p>;
  return (
    <PayoutItemsTable
      items={detail.items}
      totalUsd={detail.amount_usd}
      totalIdr={detail.amount_idr}
      idrRate={detail.idr_rate}
    />
  );
}
