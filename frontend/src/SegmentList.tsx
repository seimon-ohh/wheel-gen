import { useRef, useState } from "react";
import { EmojiPicker } from "./EmojiPicker";
import type { EmojiCatalog } from "./api";

export type SegmentRow = {
  id: string;
  text: string;
  answer: string;
  // Set by exercise generators that produce picture-based segments
  // (e.g. Bildwörter) and by the per-row picker. When non-empty, the
  // wheel renders this emoji and the row's text input is replaced by
  // the answer field — that's what the kid is supposed to spell.
  emoji: string;
};

type Props = {
  rows: SegmentRow[];
  onChange: (rows: SegmentRow[]) => void;
  onRerollOne?: (index: number) => void;
  rerollDisabled?: boolean;
  emojiCatalog: EmojiCatalog | null;
};

export function SegmentList({
  rows,
  onChange,
  onRerollOne,
  rerollDisabled,
  emojiCatalog,
}: Props) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const [pickerIndex, setPickerIndex] = useState<number | null>(null);
  // One ref per row, keyed by stable row id. Survives reorders so the
  // picker stays anchored to the right button after drag-and-drop.
  const anchorRefs = useRef<Map<string, HTMLButtonElement | null>>(new Map());

  const update = (i: number, patch: Partial<SegmentRow>) => {
    const next = rows.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };

  const move = (from: number, to: number) => {
    if (
      from === to ||
      from < 0 ||
      to < 0 ||
      from >= rows.length ||
      to >= rows.length
    ) {
      return;
    }
    const next = rows.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };

  const onPick = (i: number, emoji: string, word: string) => {
    const cur = rows[i];
    // Auto-fill the answer only if it's empty so we never clobber a
    // teacher's manual answer. The text field stays as-is — it's
    // hidden when an emoji is set anyway.
    const patch: Partial<SegmentRow> = { emoji };
    if (!cur.answer.trim()) patch.answer = word;
    update(i, patch);
  };

  const activeRow = pickerIndex != null ? rows[pickerIndex] : null;
  const activeAnchor = activeRow
    ? anchorRefs.current.get(activeRow.id) ?? null
    : null;

  return (
    <>
      <ol className="space-y-1.5">
        {rows.map((row, i) => {
          const isDragging = dragIndex === i;
          const isOver =
            overIndex === i && dragIndex !== null && dragIndex !== i;
          const hasEmoji = Boolean(row.emoji);
          return (
            <li
              key={row.id}
              draggable
              onDragStart={(e) => {
                setDragIndex(i);
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", String(i));
              }}
              onDragEnter={() => setOverIndex(i)}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
              }}
              onDragLeave={() =>
                setOverIndex((cur) => (cur === i ? null : cur))
              }
              onDrop={(e) => {
                e.preventDefault();
                const from = Number(e.dataTransfer.getData("text/plain"));
                if (Number.isFinite(from)) move(from, i);
                setDragIndex(null);
                setOverIndex(null);
              }}
              onDragEnd={() => {
                setDragIndex(null);
                setOverIndex(null);
              }}
              className={[
                "group flex items-center gap-1 rounded-lg ring-1 transition",
                isDragging
                  ? "opacity-40 ring-brand-500 bg-white"
                  : isOver
                  ? "ring-brand-500 bg-brand-50/40"
                  : "ring-slate-200 bg-white hover:ring-slate-300",
              ].join(" ")}
            >
              <span
                className="cursor-grab active:cursor-grabbing px-2 py-2 text-slate-400 select-none"
                title="Zum Verschieben ziehen"
                aria-label="Ziehen"
              >
                ⋮⋮
              </span>
              <span className="font-mono text-xs tabular-nums text-slate-400 w-5 text-right">
                {i + 1}
              </span>
              <button
                ref={(el) => {
                  anchorRefs.current.set(row.id, el);
                }}
                type="button"
                onClick={() => setPickerIndex(i)}
                title={
                  hasEmoji ? "Bild ändern oder entfernen" : "Bild auswählen"
                }
                aria-label={
                  hasEmoji ? `Bild: ${row.emoji}` : "Bild auswählen"
                }
                className={[
                  "h-8 w-8 grid place-items-center rounded-md ring-1 transition shrink-0",
                  hasEmoji
                    ? "bg-brand-50 ring-brand-300 text-xl leading-none"
                    : "bg-white ring-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-50 text-base leading-none",
                ].join(" ")}
              >
                <span aria-hidden="true">{row.emoji || "🖼"}</span>
              </button>
              {hasEmoji ? (
                <input
                  type="text"
                  className="flex-1 min-w-0 bg-transparent border-0 focus:ring-0 focus:outline-none px-1 py-2 text-sm"
                  placeholder="Lösungswort"
                  value={row.answer}
                  onChange={(e) => update(i, { answer: e.target.value })}
                />
              ) : (
                <>
                  <input
                    type="text"
                    className="flex-1 min-w-0 bg-transparent border-0 focus:ring-0 focus:outline-none px-1 py-2 text-sm"
                    placeholder="(leeres Feld)"
                    value={row.text}
                    onChange={(e) => update(i, { text: e.target.value })}
                  />
                  {row.answer && (
                    <span
                      className="hidden sm:inline text-xs text-slate-400 font-mono pr-1"
                      title="Lösung"
                    >
                      = {row.answer}
                    </span>
                  )}
                </>
              )}
              {(row.text || row.emoji || row.answer) && (
                <button
                  type="button"
                  className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition px-2 py-2 text-slate-400 hover:text-slate-700"
                  title="Leeren"
                  onClick={() =>
                    update(i, { text: "", answer: "", emoji: "" })
                  }
                  aria-label="Leeren"
                >
                  ⌫
                </button>
              )}
              {onRerollOne && (
                <button
                  type="button"
                  className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition px-2 py-2 text-slate-400 hover:text-brand-600 disabled:opacity-30 disabled:cursor-not-allowed"
                  title="Diese Aufgabe neu würfeln"
                  disabled={rerollDisabled}
                  onClick={() => onRerollOne(i)}
                  aria-label="Neu würfeln"
                >
                  ⟲
                </button>
              )}
            </li>
          );
        })}
      </ol>

      <EmojiPicker
        open={pickerIndex !== null}
        anchor={activeAnchor}
        catalog={emojiCatalog}
        current={activeRow?.emoji ?? ""}
        onPick={(entry) => {
          if (pickerIndex !== null) {
            onPick(pickerIndex, entry.emoji, entry.word);
          }
          setPickerIndex(null);
        }}
        onClear={() => {
          if (pickerIndex !== null) update(pickerIndex, { emoji: "" });
          setPickerIndex(null);
        }}
        onClose={() => setPickerIndex(null)}
      />
    </>
  );
}
