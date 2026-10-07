"use client";

import { useEffect, useRef, useState } from "react";

const MIN_THUMB_HEIGHT = 36;

export function CustomScrollbar() {
  const [scrollbar, setScrollbar] = useState({ top: 0, height: 0, visible: false });
  const draggingRef = useRef(false);
  const dragStartYRef = useRef(0);
  const dragStartScrollYRef = useRef(0);

  useEffect(() => {
    let frameId = 0;

    const measure = () => {
      cancelAnimationFrame(frameId);
      frameId = requestAnimationFrame(() => {
        const viewportHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        const maxScroll = Math.max(0, documentHeight - viewportHeight);
        const thumbHeight = Math.max(
          MIN_THUMB_HEIGHT,
          (viewportHeight / Math.max(documentHeight, viewportHeight)) * viewportHeight,
        );
        const maxThumbTop = Math.max(0, viewportHeight - thumbHeight);
        const top = maxScroll > 0 ? (window.scrollY / maxScroll) * maxThumbTop : 0;

        setScrollbar({
          top,
          height: thumbHeight,
          visible: maxScroll > 0,
        });
      });
    };

    const handleScroll = () => measure();
    const handleResize = () => measure();

    measure();
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    draggingRef.current = true;
    dragStartYRef.current = event.clientY;
    dragStartScrollYRef.current = window.scrollY;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;

    const viewportHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    const maxScroll = Math.max(0, documentHeight - viewportHeight);
    const maxThumbTop = Math.max(1, viewportHeight - scrollbar.height);
    const scrollDelta = ((event.clientY - dragStartYRef.current) / maxThumbTop) * maxScroll;

    window.scrollTo({
      top: dragStartScrollYRef.current + scrollDelta,
      behavior: "auto",
    });
  };

  const stopDragging = () => {
    draggingRef.current = false;
  };

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-y-0 right-1 z-[9999] w-2"
      style={{ opacity: scrollbar.visible ? 1 : 0, transition: "opacity 160ms ease" }}
    >
      <div
        className="pointer-events-auto absolute right-0 w-1.5 cursor-grab rounded-full bg-[#4ea8de] active:cursor-grabbing"
        style={{
          top: scrollbar.top,
          height: scrollbar.height,
          touchAction: "none",
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
      />
    </div>
  );
}
