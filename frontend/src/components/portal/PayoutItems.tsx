"use client";

// Rincian payout per konten: preview sebelum dicatat (admin, form Catat
// pembayaran). Angka dari backend; di sini hanya format tampilan.
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
