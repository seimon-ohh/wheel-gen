import { useState } from "react";

export type SegmentRow = {
  id: string;
  text: string;
  answer: string;
};

type Props = {
  rows: SegmentRow[];
  onChange: (rows: SegmentRow[]) => void;
  onRerollOne?: (index: number) => void;
  rerollDisabled?: boolean;
};

export function SegmentList({
  rows,
  onChange,
  onRerollOne,
  rerollDisabled,
}: Props) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

  const update = (i: number, patch: Partial<SegmentRow>) => {
    const next = rows.slice();
    next[i] = { ...next[i], ...patch };
    onChange(next);
  };

  const move = (from: number, to: number) => {
    if (from === to || from < 0 || to < 0 || from >= rows.length || to >= rows.length) {
      return;
    }
    const next = rows.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };

  return (
    <ol className="space-y-1.5">
      {rows.map((row, i) => {
        const isDragging = dragIndex === i;
        const isOver = overIndex === i && dragIndex !== null && dragIndex !== i;
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
            onDragLeave={() => setOverIndex((cur) => (cur === i ? null : cur))}
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
              "group flex items-center gap-2 rounded-lg ring-1 transition",
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
            <input
              type="text"
              className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none px-1 py-2 text-sm"
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
            {row.text && (
              <button
                type="button"
                className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition px-2 py-2 text-slate-400 hover:text-slate-700"
                title="Leeren"
                onClick={() => update(i, { text: "", answer: "" })}
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
  );
}
