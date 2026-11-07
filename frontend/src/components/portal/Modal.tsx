"use client";

// Modal bersama untuk halaman portal admin:
// - klik backdrop atau Escape menutup (klik di dalam jendela tidak);
// - header (judul + Tutup) tetap di atas, hanya isi yang scroll; tinggi maks 90vh;
// - scroll halaman di belakang dikunci selama modal terbuka;
// - isProcessing: backdrop, Escape, dan Tutup diabaikan selama form dikirim.
// useConfirmDialog di bawah adalah pengganti window.confirm yang memakai Modal ini.
import { type ReactNode, useCallback, useEffect, useId, useRef, useState } from "react";

// Modal yang sedang terbuka, urut buka. Escape hanya menutup yang paling atas
// (mis. konfirmasi hapus di atas modal Pendapatan & Payout), dan scroll body
// baru dibuka lagi setelah modal terakhir tertutup.
const openModals: string[] = [];
let savedBodyStyle: { overflow: string; paddingRight: string } | null = null;

function lockBodyScroll() {
  if (savedBodyStyle) return;
  const body = document.body;
  savedBodyStyle = { overflow: body.style.overflow, paddingRight: body.style.paddingRight };
  // Lebar scrollbar yang hilang diganti padding supaya halaman tidak bergeser.
  const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
  body.style.overflow = "hidden";
  if (scrollbarWidth > 0) body.style.paddingRight = `${scrollbarWidth}px`;
}

function unlockBodyScroll() {
  if (!savedBodyStyle) return;
  document.body.style.overflow = savedBodyStyle.overflow;
  document.body.style.paddingRight = savedBodyStyle.paddingRight;
  savedBodyStyle = null;
}

type ModalProps = {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  // Bagian bawah yang tidak ikut scroll (mis. tombol aksi).
  footer?: ReactNode;
  // true selama form di dalamnya dikirim: backdrop, Escape, dan Tutup diabaikan.
  isProcessing?: boolean;
  // Kelas lebar maksimum Tailwind, mis. "max-w-5xl".
  width?: string;
  // Modal yang ditumpuk di atas modal lain butuh z-index lebih tinggi.
  zIndex?: string;
  showCloseButton?: boolean;
};

export function Modal({
  title,
  subtitle,
  onClose,
  children,
  footer,
  isProcessing = false,
  width = "max-w-2xl",
  zIndex = "z-50",
  showCloseButton = true,
}: ModalProps) {
  const id = useId();
  const titleId = `${id}-title`;
  const panelRef = useRef<HTMLDivElement>(null);
  // Klik dihitung sebagai klik backdrop hanya kalau tekan dan lepas sama-sama
  // di backdrop, jadi seleksi teks yang diseret keluar jendela tidak menutup.
  const pressedOnBackdrop = useRef(false);
  // Nilai terbaru untuk listener Escape tanpa memasang ulang listener.
  const latest = useRef({ onClose, isProcessing });
  useEffect(() => {
    latest.current = { onClose, isProcessing };
  });

  useEffect(() => {
    openModals.push(id);
    lockBodyScroll();
    const previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    // Fokus pindah ke dalam modal (kecuali elemen di dalamnya sudah autoFocus).
    if (panelRef.current && !panelRef.current.contains(document.activeElement))
      panelRef.current.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || openModals[openModals.length - 1] !== id) return;
      e.preventDefault();
      if (!latest.current.isProcessing) latest.current.onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      const index = openModals.indexOf(id);
      if (index >= 0) openModals.splice(index, 1);
      if (openModals.length === 0) unlockBodyScroll();
      previousFocus?.focus();
    };
  }, [id]);

  const requestClose = () => {
    if (!isProcessing) onClose();
  };

  return (
    <div
      className={`fixed inset-0 ${zIndex} flex items-center justify-center bg-black/50 p-4`}
      onMouseDown={(e) => {
        pressedOnBackdrop.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        if (pressedOnBackdrop.current && e.target === e.currentTarget) requestClose();
        pressedOnBackdrop.current = false;
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={isProcessing || undefined}
        tabIndex={-1}
        className={`flex max-h-[90vh] w-full ${width} flex-col overflow-hidden rounded-3xl bg-white shadow-xl outline-none`}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-gray-100 px-6 py-5 md:px-8">
          <div className="min-w-0">
            <h3 id={titleId} className="text-xl font-bold">
              {title}
            </h3>
            {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
          </div>
          {showCloseButton && (
            <button
              type="button"
              onClick={requestClose}
              disabled={isProcessing}
              className="shrink-0 rounded-xl bg-gray-100 px-4 py-2 text-sm font-bold transition hover:bg-gray-200 disabled:opacity-50"
            >
              Tutup
            </button>
          )}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6 md:px-8">{children}</div>
        {footer && (
          <div className="shrink-0 border-t border-gray-100 px-6 py-4 md:px-8">{footer}</div>
        )}
      </div>
    </div>
  );
}

type ConfirmOptions = {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  // Tombol konfirmasi merah untuk tindakan yang menghapus/menonaktifkan.
  danger?: boolean;
};

type PendingConfirm = ConfirmOptions & { resolve: (confirmed: boolean) => void };

/**
 * Pengganti window.confirm memakai Modal:
 *   const [askConfirm, confirmDialog] = useConfirmDialog();
 *   if (!(await askConfirm({ title, message, danger: true }))) return;
 * dan render {confirmDialog} sekali di halaman. Backdrop, Escape, dan Batal = tidak.
 */
export function useConfirmDialog(): [(options: ConfirmOptions) => Promise<boolean>, ReactNode] {
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const askConfirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => setPending({ ...options, resolve })),
    []
  );

  const finish = (confirmed: boolean) => {
    pending?.resolve(confirmed);
    setPending(null);
  };

  const dialog = pending && (
    <Modal
      title={pending.title}
      onClose={() => finish(false)}
      width="max-w-md"
      zIndex="z-[60]"
      showCloseButton={false}
      footer={
        <div className="flex justify-end gap-2">
          {/* Fokus awal di Batal: Enter tidak langsung menjalankan tindakan berbahaya. */}
          <button
            type="button"
            autoFocus
            onClick={() => finish(false)}
            className="rounded-xl bg-gray-100 px-5 py-2 text-sm font-bold transition hover:bg-gray-200"
          >
            Batal
          </button>
          <button
            type="button"
            onClick={() => finish(true)}
            className={`rounded-xl px-5 py-2 text-sm font-bold text-white transition ${
              pending.danger ? "bg-red-600 hover:bg-red-700" : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {pending.confirmLabel ?? "Ya"}
          </button>
        </div>
      }
    >
      <div className="whitespace-pre-line text-sm text-gray-700">{pending.message}</div>
    </Modal>
  );

  return [askConfirm, dialog];
}
