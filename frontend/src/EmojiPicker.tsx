import { useEffect, useMemo, useRef, useState } from "react";
import type { EmojiCatalog, EmojiCategory, EmojiEntry } from "./api";

type Props = {
  open: boolean;
  anchor: HTMLElement | null;
  catalog: EmojiCatalog | null;
  current: string;
  onPick: (entry: EmojiEntry) => void;
  onClear: () => void;
  onClose: () => void;
};

export function EmojiPicker({
  open,
  anchor,
  catalog,
  current,
  onPick,
  onClear,
  onClose,
}: Props) {
  const firstCatId = catalog?.categories[0]?.id ?? "";
  const [activeCat, setActiveCat] = useState<string>(firstCatId);
  const [query, setQuery] = useState("");
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({
    top: 0,
    left: 0,
  });

  // Re-sync the active tab when the catalog finishes loading after
  // the first render — without this the first tab stays empty until
  // the user clicks a category.
  useEffect(() => {
    if (!activeCat && firstCatId) setActiveCat(firstCatId);
  }, [activeCat, firstCatId]);

  // Position the popover next to the anchor without going off-screen.
  useEffect(() => {
    if (!open || !anchor) return;
    const r = anchor.getBoundingClientRect();
    const width = 360;
    const height = 380;
    const margin = 8;
    let left = r.right + margin;
    if (left + width > window.innerWidth - 8) {
      left = Math.max(8, r.left - width - margin);
    }
    let top = r.top;
    if (top + height > window.innerHeight - 8) {
      top = Math.max(8, window.innerHeight - height - 8);
    }
    setPos({ top, left });
  }, [open, anchor]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (popoverRef.current?.contains(target)) return;
      if (anchor?.contains(target)) return;
      onClose();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open, anchor, onClose]);

  const filtered: EmojiCategory[] = useMemo(() => {
    if (!catalog) return [];
    const q = query.trim().toLowerCase();
    if (!q) return catalog.categories;
    return catalog.categories
      .map((cat) => ({
        ...cat,
        emojis: cat.emojis.filter(
          (e) =>
            e.word.toLowerCase().includes(q) ||
            cat.label.toLowerCase().includes(q),
        ),
      }))
      .filter((cat) => cat.emojis.length > 0);
  }, [catalog, query]);

  if (!open) return null;

  const showCategoryTabs = query.trim() === "";
  const visible: EmojiCategory[] = showCategoryTabs
    ? filtered.filter((c) => c.id === activeCat)
    : filtered;

  return (
    <div
      ref={popoverRef}
      role="dialog"
      aria-label="Bild auswählen"
      className="fixed z-40 w-[360px] max-h-[380px] flex flex-col card overflow-hidden"
      style={{ top: pos.top, left: pos.left }}
    >
      <div className="px-3 pt-3 pb-2 border-b border-slate-100 space-y-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            autoFocus
            placeholder="Suchen (z.B. Hund, Auto)…"
            className="input text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="button"
            className="btn-ghost text-xs px-2 py-1 shrink-0"
            onClick={onClose}
            aria-label="Schließen"
            title="Schließen"
          >
            ✕
          </button>
        </div>
        {showCategoryTabs && catalog && (
          <div className="flex flex-wrap gap-1">
            {catalog.categories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                className={[
                  "text-xs rounded-full px-2.5 py-1 ring-1 transition",
                  activeCat === cat.id
                    ? "bg-brand-50 ring-brand-500 text-brand-700"
                    : "bg-white ring-slate-200 text-slate-600 hover:bg-slate-50",
                ].join(" ")}
                onClick={() => setActiveCat(cat.id)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="overflow-y-auto px-2 py-2 flex-1">
        {!catalog && (
          <p className="text-center text-sm text-slate-400 py-6">
            Lade Bilder…
          </p>
        )}
        {catalog && visible.length === 0 && (
          <p className="text-center text-sm text-slate-400 py-6">
            Keine Treffer.
          </p>
        )}
        {visible.map((cat) => (
          <div key={cat.id} className="mb-2 last:mb-0">
            {!showCategoryTabs && (
              <h4 className="text-[11px] uppercase tracking-wide text-slate-400 px-1 pb-1">
                {cat.label}
              </h4>
            )}
            <div className="grid grid-cols-8 gap-0.5">
              {cat.emojis.map((e) => {
                const active = current === e.emoji;
                return (
                  <button
                    key={e.emoji}
                    type="button"
                    title={e.word}
                    aria-label={e.word}
                    onClick={() => onPick(e)}
                    className={[
                      "h-9 w-9 rounded-md grid place-items-center text-xl leading-none transition",
                      active
                        ? "bg-brand-100 ring-1 ring-brand-500"
                        : "hover:bg-slate-100",
                    ].join(" ")}
                  >
                    <span aria-hidden="true">{e.emoji}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {current && (
        <div className="px-3 py-2 border-t border-slate-100 flex items-center justify-between gap-2">
          <span className="text-xs text-slate-500">
            Aktuell:{" "}
            <span className="text-base align-middle" aria-hidden="true">
              {current}
            </span>
          </span>
          <button
            type="button"
            className="text-xs text-rose-600 hover:text-rose-700 underline underline-offset-2"
            onClick={onClear}
          >
            Bild entfernen
          </button>
        </div>
      )}
    </div>
  );
}
