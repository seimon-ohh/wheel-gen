import { useEffect, useMemo, useRef, useState } from "react";
import {
  downloadFile,
  fetchEmojiCatalog,
  fetchExerciseTypes,
  generateItems,
  renderWheel,
  type EmojiCatalog,
  type ExerciseType,
  type Item,
  type ParamSpec,
  type RenderRequest,
  type RenderResponse,
  type SegmentFillMode,
  type SizeMode,
  type TextOrientation,
} from "./api";
import { HelpModal } from "./HelpModal";
import { SegmentList, type SegmentRow } from "./SegmentList";

type ParamValues = Record<string, unknown>;

function defaultParamsFor(t: ExerciseType): ParamValues {
  const out: ParamValues = {};
  for (const p of t.params) out[p.key] = p.default;
  return out;
}

function makeBlankRow(): SegmentRow {
  return { id: cryptoRandomId(), text: "", answer: "", emoji: "" };
}

function cryptoRandomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
}

function itemsToRows(items: Item[]): SegmentRow[] {
  return items.map((it) => ({
    id: cryptoRandomId(),
    text: it.text,
    answer: it.answer,
    emoji: it.emoji ?? "",
  }));
}

function rowsToItems(rows: SegmentRow[]): Item[] {
  return rows.map((r) => ({
    text: r.text,
    answer: r.answer,
    emoji: r.emoji,
    meta: {},
  }));
}

function resizeRows(rows: SegmentRow[], n: number): SegmentRow[] {
  if (rows.length === n) return rows;
  if (rows.length > n) return rows.slice(0, n);
  return rows.concat(
    Array.from({ length: n - rows.length }, () => makeBlankRow()),
  );
}

export default function App() {
  // Catalog
  const [types, setTypes] = useState<ExerciseType[]>([]);
  const [typeId, setTypeId] = useState<string>("");
  const [params, setParams] = useState<ParamValues>({});

  // Wheel layout
  const [segments, setSegments] = useState<number>(12);

  // Print/output
  const [size, setSize] = useState<SizeMode>("cricut");
  const [hubDiameter, setHubDiameter] = useState<number>(19.0);
  const [hubClearance, setHubClearance] = useState<number>(0.4);
  const [textOrientation, setTextOrientation] =
    useState<TextOrientation>("horizontal");
  const [fillMode, setFillMode] = useState<SegmentFillMode>("none");

  // Content
  const [rows, setRows] = useState<SegmentRow[]>(() =>
    Array.from({ length: 12 }, () => makeBlankRow()),
  );

  // Render result
  const [render, setRender] = useState<RenderResponse | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  // UI: collapsible right-hand editor pane
  const [editorOpen, setEditorOpen] = useState(true);
  const openEditor = () => setEditorOpen(true);
  const toggleEditor = () => setEditorOpen((o) => !o);

  // Catalog used by the per-row emoji picker. Fetched once on mount;
  // a null value just means the picker shows a "Lade Bilder…" state
  // until it arrives.
  const [emojiCatalog, setEmojiCatalog] = useState<EmojiCatalog | null>(null);

  useEffect(() => {
    fetchExerciseTypes()
      .then((ts) => {
        setTypes(ts);
        if (ts.length > 0) {
          setTypeId(ts[0].id);
          setParams(defaultParamsFor(ts[0]));
        }
      })
      .catch((e) => setActionError(String(e)));
    fetchEmojiCatalog()
      .then(setEmojiCatalog)
      .catch((e) => setActionError(String(e)));
  }, []);

  const activeType = useMemo(
    () => types.find((t) => t.id === typeId) ?? null,
    [types, typeId],
  );

  // Keep rows length in sync with segments count.
  useEffect(() => {
    setRows((cur) => resizeRows(cur, segments));
  }, [segments]);

  const buildRenderRequest = (): RenderRequest => ({
    items: rowsToItems(rows),
    segments,
    size,
    hub_diameter_mm: hubDiameter,
    hub_clearance_mm: hubClearance,
    text_orientation: textOrientation,
    fill_mode: fillMode,
    title: activeType?.label ?? null,
  });

  // Live, debounced preview render.
  const renderTimer = useRef<number | null>(null);
  const renderAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    if (renderTimer.current) window.clearTimeout(renderTimer.current);
    renderTimer.current = window.setTimeout(() => {
      const ctrl = new AbortController();
      renderAbort.current?.abort();
      renderAbort.current = ctrl;
      setPreviewLoading(true);
      setRenderError(null);
      renderWheel(buildRenderRequest(), ctrl.signal)
        .then((r) => {
          setRender(r);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setRenderError(String(e));
        })
        .finally(() => {
          setPreviewLoading(false);
        });
    }, 250);
    return () => {
      if (renderTimer.current) window.clearTimeout(renderTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    rows,
    segments,
    size,
    hubDiameter,
    hubClearance,
    textOrientation,
    fillMode,
    typeId,
  ]);

  const onTypeChange = (id: string) => {
    setTypeId(id);
    const t = types.find((x) => x.id === id);
    if (t) setParams(defaultParamsFor(t));
  };

  const onParamChange = (key: string, value: unknown) => {
    setParams((p) => ({ ...p, [key]: value }));
  };

  const generateAll = async () => {
    if (!typeId) return;
    setGenerating(true);
    setActionError(null);
    try {
      const res = await generateItems({
        generator_id: typeId,
        params,
        count: segments,
      });
      setRows(itemsToRows(res.items));
    } catch (e) {
      setActionError(String(e));
    } finally {
      setGenerating(false);
    }
  };

  const rerollOne = async (index: number) => {
    if (!typeId) return;
    try {
      const res = await generateItems({
        generator_id: typeId,
        params,
        count: 1,
      });
      const it = res.items[0];
      if (!it) return;
      setRows((cur) => {
        const next = cur.slice();
        // Rerolling generates fresh text-based content, so we clear
        // any emoji that might have been on this segment.
        next[index] = {
          ...next[index],
          text: it.text,
          answer: it.answer,
          emoji: it.emoji ?? "",
        };
        return next;
      });
    } catch (e) {
      setActionError(String(e));
    }
  };

  const clearAll = () => {
    setRows((cur) => cur.map(() => makeBlankRow()));
  };

  const onDownload = async (kind: "svg" | "png" | "pdf") => {
    const filename = `gluecksrad-${segments}seg.${kind}`;
    try {
      await downloadFile(kind, buildRenderRequest(), filename);
    } catch (e) {
      setActionError(String(e));
    }
  };

  const filledCount = rows.filter(
    (r) => r.text.trim().length > 0 || r.emoji.length > 0,
  ).length;
  const blankCount = segments - filledCount;

  return (
    <div className="min-h-full">
      <header className="bg-white ring-1 ring-slate-200 sticky top-0 z-30">
        <div className="mx-auto max-w-[1500px] px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white font-bold">
              GR
            </div>
            <div>
              <h1 className="text-lg font-semibold leading-tight">
                Glücksrad Generator
              </h1>
              <p className="text-xs text-slate-500 leading-tight">
                Druckvorlagen für Cricut Print &amp; Cut
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {render && (
              <span className="hidden md:inline text-xs text-slate-500 font-mono">
                {render.diameter_mm.toFixed(1)} mm Ø ·{" "}
                {render.hub_cut_diameter_mm.toFixed(1)} mm Loch
              </span>
            )}
            <button
              className="btn-secondary text-sm"
              onClick={() => setHelpOpen(true)}
            >
              Wie drucke ich das?
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-6 py-6 grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <section className="space-y-6">
          {/* ---------- 1. INHALT ---------- */}
          <SectionCard
            number={1}
            title="Inhalt"
            subtitle="Was steht in den Segmenten?"
          >
            <div className="grid grid-cols-[1fr_auto] gap-2 items-end">
              <div>
                <label className="label" htmlFor="type">
                  Aufgabentyp
                </label>
                <select
                  id="type"
                  className="input mt-1"
                  value={typeId}
                  onChange={(e) => onTypeChange(e.target.value)}
                >
                  {types.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="btn-primary"
                onClick={generateAll}
                disabled={generating || !typeId}
                title="Alle Segmente neu zufällig befüllen"
              >
                {generating ? "Generiere…" : "Alle generieren"}
              </button>
            </div>
            {activeType?.description && (
              <p className="text-xs text-slate-500">
                {activeType.description}
              </p>
            )}
            {activeType && activeType.params.length > 0 && (
              <details className="rounded-lg ring-1 ring-slate-200 bg-slate-50/60">
                <summary className="cursor-pointer text-sm font-medium text-slate-700 px-3 py-2">
                  Optionen
                </summary>
                <div className="p-3 pt-0 space-y-3 border-t border-slate-200/70">
                  {activeType.params.map((p) => (
                    <ParamControl
                      key={p.key}
                      spec={p}
                      value={params[p.key]}
                      onChange={(v) => onParamChange(p.key, v)}
                    />
                  ))}
                </div>
              </details>
            )}

            <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-3">
              <div className="text-sm text-slate-700">
                <span className="font-semibold">{segments} Segmente</span>{" "}
                <span className="text-slate-500">
                  · {filledCount} befüllt
                  {blankCount > 0 && (
                    <span className="text-slate-400"> · {blankCount} leer</span>
                  )}
                </span>
              </div>
              <button
                className={`btn text-sm ${
                  editorOpen
                    ? "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    : "bg-brand-600 text-white hover:bg-brand-700"
                }`}
                onClick={editorOpen ? toggleEditor : openEditor}
                aria-pressed={editorOpen}
                title={
                  editorOpen
                    ? "Segmenteditor verbergen"
                    : "Segmenteditor rechts öffnen"
                }
              >
                {editorOpen ? "Editor verbergen" : "Bearbeiten"}
              </button>
            </div>
          </SectionCard>

          {/* ---------- 2. RAD ---------- */}
          <SectionCard
            number={2}
            title="Rad"
            subtitle="Layout und Maße deines Glücksrads."
          >
            <div>
              <div className="flex items-center justify-between">
                <label className="label" htmlFor="segments">
                  Anzahl Segmente
                </label>
                <span className="text-sm font-mono text-slate-700">
                  {segments}
                </span>
              </div>
              <input
                id="segments"
                type="range"
                min={2}
                max={24}
                step={1}
                value={segments}
                onChange={(e) => setSegments(Number(e.target.value))}
                className="mt-2 w-full accent-brand-600"
              />
              <p className="text-xs text-slate-500 mt-1">
                Wie viele Felder hat dein Rad? Standard: 12.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
              <div>
                <label className="label" htmlFor="hub-d">
                  Nabe Ø (mm)
                </label>
                <input
                  id="hub-d"
                  type="number"
                  step="0.1"
                  min="5"
                  max="60"
                  className="input mt-1"
                  value={hubDiameter}
                  onChange={(e) => setHubDiameter(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="label" htmlFor="hub-c">
                  Spiel (mm)
                </label>
                <input
                  id="hub-c"
                  type="number"
                  step="0.1"
                  min="0"
                  max="5"
                  className="input mt-1"
                  value={hubClearance}
                  onChange={(e) => setHubClearance(Number(e.target.value))}
                />
              </div>
            </div>
            <p className="text-xs text-slate-500">
              Loch wird mit{" "}
              <span className="font-mono">
                {(hubDiameter + hubClearance).toFixed(1)} mm
              </span>{" "}
              Durchmesser geschnitten.
            </p>

            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="label">Textausrichtung</span>
              </div>
              <div
                role="radiogroup"
                aria-label="Textausrichtung"
                className="mt-1 grid grid-cols-2 gap-2"
              >
                <OrientationOption
                  checked={textOrientation === "horizontal"}
                  onChange={() => setTextOrientation("horizontal")}
                  label="Horizontal"
                  desc="Text entlang des Bogens"
                  axis="horizontal"
                />
                <OrientationOption
                  checked={textOrientation === "vertical"}
                  onChange={() => setTextOrientation("vertical")}
                  label="Vertikal"
                  desc="Text entlang des Radius"
                  axis="vertical"
                />
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Vertikal hilft, wenn die Aufgaben lang sind und quer nicht
                mehr lesbar passen.
              </p>
            </div>

            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="label">Segmentfarben</span>
              </div>
              <div
                role="radiogroup"
                aria-label="Segmentfarben"
                className="mt-1 flex flex-wrap gap-2"
              >
                <FillOption
                  checked={fillMode === "none"}
                  onChange={() => setFillMode("none")}
                  label="Keine"
                  swatch="none"
                />
                <FillOption
                  checked={fillMode === "rainbow"}
                  onChange={() => setFillMode("rainbow")}
                  label="Regenbogen"
                  swatch="rainbow"
                />
                <FillOption
                  checked={fillMode === "blue"}
                  onChange={() => setFillMode("blue")}
                  label="Blau"
                  swatch="blue"
                />
                <FillOption
                  checked={fillMode === "green"}
                  onChange={() => setFillMode("green")}
                  label="Grün"
                  swatch="green"
                />
                <FillOption
                  checked={fillMode === "red"}
                  onChange={() => setFillMode("red")}
                  label="Rot"
                  swatch="red"
                />
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Farbige Segmente werden mitgedruckt – mehr Tinte, dafür
                deutlich auffälliger.
              </p>
            </div>
          </SectionCard>

          {/* ---------- 3. DRUCK & FORMAT ---------- */}
          <SectionCard
            number={3}
            title="Druck & Format"
            subtitle="Wie soll das Rad ausgegeben werden?"
          >
            <div className="space-y-2">
              <SizeOption
                checked={size === "cricut"}
                onChange={() => setSize("cricut")}
                title="Cricut Print &amp; Cut (17,0 cm)"
                desc="Passt in Cricuts Print-Then-Cut Limit. Der Cricut schneidet automatisch."
              />
              <SizeOption
                checked={size === "full"}
                onChange={() => setSize("full")}
                title="Vollformat (18,8 cm)"
                desc="Originalgröße des Rads. Als PDF drucken und manuell ausschneiden."
              />
            </div>

            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100">
              <button
                className="btn-secondary text-sm"
                onClick={() => onDownload("svg")}
              >
                SVG
              </button>
              <button
                className="btn-secondary text-sm"
                onClick={() => onDownload("png")}
              >
                PNG
              </button>
              <button
                className="btn-secondary text-sm"
                onClick={() => onDownload("pdf")}
              >
                PDF
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Für Cricut: SVG verwenden – das Druckmotiv ist als ein Bild
              eingebettet, sodass Cricut nur die zwei roten Kreise
              schneidet. Für manuellen Druck: PDF.
            </p>
            {actionError && (
              <p className="text-sm text-rose-600">{actionError}</p>
            )}
          </SectionCard>
        </section>

        {/* ---------- PREVIEW + EDITOR (flex row, in-flow) ---------- */}
        <div className="flex flex-col lg:flex-row gap-6 min-w-0">
          {/* Preview */}
          <section className="flex-1 min-w-0 space-y-4">
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
                <h2 className="text-base font-semibold text-slate-800">
                  Vorschau
                </h2>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <Legend swatch="bg-slate-900" label="Druck" />
                  <Legend swatch="bg-rose-500" label="Schnitt" />
                  {previewLoading && (
                    <span className="text-slate-400">aktualisiere…</span>
                  )}
                  <button
                    className="btn-ghost text-xs px-2 py-1"
                    onClick={toggleEditor}
                    aria-pressed={editorOpen}
                    title={
                      editorOpen
                        ? "Segmenteditor verbergen"
                        : "Segmenteditor rechts öffnen"
                    }
                  >
                    {editorOpen ? "Editor ›" : "‹ Segmente bearbeiten"}
                  </button>
                </div>
              </div>
              <div
                role={editorOpen ? undefined : "button"}
                tabIndex={editorOpen ? -1 : 0}
                onClick={editorOpen ? undefined : openEditor}
                onKeyDown={(e) => {
                  if (
                    !editorOpen &&
                    (e.key === "Enter" || e.key === " ")
                  ) {
                    e.preventDefault();
                    openEditor();
                  }
                }}
                title={
                  editorOpen
                    ? undefined
                    : "Klicken, um die Segmente zu bearbeiten"
                }
                className={[
                  "aspect-square w-full max-w-[720px] mx-auto",
                  "bg-[radial-gradient(ellipse_at_center,_#f8fafc_0%,_#eef2f7_100%)]",
                  "rounded-xl ring-1 ring-slate-200 grid place-items-center overflow-hidden",
                  "transition",
                  editorOpen
                    ? ""
                    : "cursor-pointer hover:ring-brand-300 hover:ring-2 focus:outline-none focus:ring-2 focus:ring-brand-500",
                ].join(" ")}
              >
                {render ? (
                  <div
                    className="w-full h-full p-6 [&>svg]:w-full [&>svg]:h-full"
                    dangerouslySetInnerHTML={{ __html: render.svg }}
                  />
                ) : (
                  <div className="text-center text-slate-400 p-8">
                    <p className="text-sm">
                      Klicke auf{" "}
                      <span className="font-semibold">Alle generieren</span> um
                      Aufgaben zu würfeln.
                    </p>
                  </div>
                )}
              </div>
              {!editorOpen && (
                <p className="mt-2 text-center text-xs text-slate-400">
                  Klicke auf das Rad, um die Segmente zu bearbeiten.
                </p>
              )}
              {renderError && (
                <p className="text-sm text-rose-600 mt-2">{renderError}</p>
              )}
            </div>

            {render && filledCount > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-slate-800 mb-3">
                  Lösungen (für die Lehrkraft)
                </h3>
                <ol className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1 text-sm text-slate-700 list-decimal pl-5">
                  {rows.map((r, i) => {
                    const isEmpty = !r.text && !r.emoji;
                    return (
                      <li
                        key={r.id}
                        className={isEmpty ? "text-slate-300 italic" : ""}
                      >
                        {isEmpty ? (
                          <>(leer)</>
                        ) : r.emoji ? (
                          <>
                            <span
                              className="text-base align-middle"
                              aria-hidden="true"
                            >
                              {r.emoji}
                            </span>
                            {r.answer && (
                              <span className="text-slate-500">
                                {" "}
                                = {r.answer}
                              </span>
                            )}
                          </>
                        ) : (
                          <>
                            <span className="font-mono">{r.text}</span>
                            {r.answer && (
                              <span className="text-slate-500">
                                {" "}
                                = {r.answer}
                              </span>
                            )}
                          </>
                        )}
                        <span className="sr-only"> #{i + 1}</span>
                      </li>
                    );
                  })}
                </ol>
              </div>
            )}
          </section>

          {/* Collapsible right-hand segment editor (in-flow, not overlay) */}
          <aside
            className={[
              "shrink-0 overflow-hidden",
              "transition-[max-width,opacity] duration-200 ease-out",
              editorOpen
                ? "max-w-full lg:max-w-[360px] opacity-100"
                : "max-w-0 opacity-0 pointer-events-none",
            ].join(" ")}
            aria-hidden={!editorOpen}
          >
            <div className="w-full lg:w-[360px]">
              <div className="card p-5 space-y-4 lg:sticky lg:top-[88px]">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold text-slate-800 leading-tight">
                      Segmente
                    </h2>
                    <p className="text-xs text-slate-500 leading-tight mt-0.5">
                      {filledCount} befüllt
                      {blankCount > 0 && ` · ${blankCount} leer`}
                    </p>
                  </div>
                  <button
                    className="btn-ghost text-sm"
                    onClick={toggleEditor}
                    aria-label="Editor schließen"
                    title="Editor schließen"
                  >
                    ✕
                  </button>
                </div>

                <button
                  className="btn-primary w-full"
                  onClick={generateAll}
                  disabled={generating || !typeId}
                  title="Alle Segmente neu zufällig befüllen"
                >
                  {generating ? "Generiere…" : "Alle generieren"}
                </button>

                <SegmentList
                  rows={rows}
                  onChange={setRows}
                  onRerollOne={rerollOne}
                  rerollDisabled={generating || !typeId}
                  emojiCatalog={emojiCatalog}
                />
                <div className="flex items-center justify-between text-xs">
                  <button
                    className="text-slate-500 hover:text-slate-700 underline underline-offset-2"
                    onClick={clearAll}
                  >
                    Alle leeren
                  </button>
                  <span className="text-slate-400">
                    Ziehen zum Sortieren
                  </span>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <footer className="mx-auto max-w-[1500px] px-6 pb-8 text-center text-xs text-slate-400">
        Glücksrad Generator · läuft nur im Heimnetz
      </footer>

      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}

// ---------- helpers ----------

function SectionCard({
  number,
  title,
  subtitle,
  children,
}: {
  number: number;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="grid place-items-center h-7 w-7 rounded-full bg-brand-100 text-brand-700 text-sm font-semibold shrink-0">
          {number}
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-800 leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-slate-500 leading-tight mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}

function SizeOption({
  checked,
  onChange,
  title,
  desc,
}: {
  checked: boolean;
  onChange: () => void;
  title: string;
  desc: string;
}) {
  return (
    <label
      className={`flex cursor-pointer gap-3 rounded-lg p-3 ring-1 transition ${
        checked
          ? "bg-brand-50 ring-brand-500"
          : "bg-white ring-slate-200 hover:bg-slate-50"
      }`}
    >
      <input
        type="radio"
        className="mt-1 accent-brand-600"
        checked={checked}
        onChange={onChange}
      />
      <span>
        <span
          className="block text-sm font-medium text-slate-800"
          dangerouslySetInnerHTML={{ __html: title }}
        />
        <span className="block text-xs text-slate-500 mt-0.5">{desc}</span>
      </span>
    </label>
  );
}

function OrientationOption({
  checked,
  onChange,
  label,
  desc,
  axis,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  desc: string;
  axis: "horizontal" | "vertical";
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-2 rounded-lg p-2.5 ring-1 transition ${
        checked
          ? "bg-brand-50 ring-brand-500"
          : "bg-white ring-slate-200 hover:bg-slate-50"
      }`}
    >
      <input
        type="radio"
        name="text-orientation"
        className="accent-brand-600"
        checked={checked}
        onChange={onChange}
      />
      <span className="flex items-center gap-2 min-w-0">
        <OrientationIcon axis={axis} active={checked} />
        <span className="min-w-0">
          <span className="block text-sm font-medium text-slate-800 leading-tight">
            {label}
          </span>
          <span className="block text-xs text-slate-500 leading-tight mt-0.5 truncate">
            {desc}
          </span>
        </span>
      </span>
    </label>
  );
}

function OrientationIcon({
  axis,
  active,
}: {
  axis: "horizontal" | "vertical";
  active: boolean;
}) {
  const stroke = active ? "#2563eb" : "#64748b";
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle
        cx="11"
        cy="11"
        r="9"
        fill="none"
        stroke={stroke}
        strokeWidth="1.2"
        opacity="0.5"
      />
      {axis === "horizontal" ? (
        <text
          x="11"
          y="11"
          fontSize="7"
          fontWeight="700"
          textAnchor="middle"
          dominantBaseline="central"
          fill={stroke}
        >
          Abc
        </text>
      ) : (
        <text
          x="11"
          y="11"
          fontSize="7"
          fontWeight="700"
          textAnchor="middle"
          dominantBaseline="central"
          fill={stroke}
          transform="rotate(-90 11 11)"
        >
          Abc
        </text>
      )}
    </svg>
  );
}

function FillOption({
  checked,
  onChange,
  label,
  swatch,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  swatch: SegmentFillMode;
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 ring-1 transition ${
        checked
          ? "bg-brand-50 ring-brand-500"
          : "bg-white ring-slate-200 hover:bg-slate-50"
      }`}
    >
      <input
        type="radio"
        name="fill-mode"
        className="sr-only"
        checked={checked}
        onChange={onChange}
      />
      <FillSwatch mode={swatch} />
      <span className="text-sm text-slate-800">{label}</span>
    </label>
  );
}

function FillSwatch({ mode }: { mode: SegmentFillMode }) {
  const baseClass =
    "inline-block h-4 w-4 rounded-full ring-1 ring-slate-300 shrink-0";
  if (mode === "none") {
    return (
      <span
        className={`${baseClass} bg-white relative overflow-hidden`}
        aria-hidden="true"
      >
        <span
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(45deg, transparent 45%, #cbd5e1 45%, #cbd5e1 55%, transparent 55%)",
          }}
        />
      </span>
    );
  }
  if (mode === "rainbow") {
    return (
      <span
        className={baseClass}
        style={{
          background:
            "conic-gradient(#f87171, #fbbf24, #facc15, #84cc16, #34d399, #38bdf8, #818cf8, #c084fc, #f472b6, #f87171)",
        }}
        aria-hidden="true"
      />
    );
  }
  const familyGradient: Record<string, string> = {
    blue: "linear-gradient(135deg, #93c5fd, #60a5fa, #6366f1)",
    green: "linear-gradient(135deg, #bef264, #86efac, #4ade80)",
    red: "linear-gradient(135deg, #fda4af, #fb7185, #fb923c)",
  };
  return (
    <span
      className={baseClass}
      style={{ background: familyGradient[mode] ?? "#cbd5e1" }}
      aria-hidden="true"
    />
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2.5 w-2.5 rounded-full ${swatch}`} />
      {label}
    </span>
  );
}

function ParamControl({
  spec,
  value,
  onChange,
}: {
  spec: ParamSpec;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (spec.type === "bool") {
    return (
      <label className="flex items-start gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          className="mt-0.5 accent-brand-600"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span>{spec.label}</span>
      </label>
    );
  }
  if (spec.type === "int" || spec.type === "number") {
    return (
      <div>
        <label className="label" htmlFor={`p-${spec.key}`}>
          {spec.label}
        </label>
        <input
          id={`p-${spec.key}`}
          type="number"
          className="input mt-1"
          value={String(value ?? "")}
          min={spec.min ?? undefined}
          max={spec.max ?? undefined}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        {spec.help && (
          <p className="mt-1 text-xs text-slate-500">{spec.help}</p>
        )}
      </div>
    );
  }
  return (
    <div>
      <label className="label" htmlFor={`p-${spec.key}`}>
        {spec.label}
      </label>
      <input
        id={`p-${spec.key}`}
        type="text"
        className="input mt-1"
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
