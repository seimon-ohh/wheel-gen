export type ParamSpec = {
  key: string;
  label: string;
  type: "int" | "number" | "bool" | "string";
  default: unknown;
  min?: number | null;
  max?: number | null;
  help?: string | null;
};

export type ExerciseType = {
  id: string;
  label: string;
  description: string;
  params: ParamSpec[];
};

export type Item = {
  text: string;
  answer: string;
  emoji: string;
  meta: Record<string, unknown>;
};

export type SizeMode = "cricut" | "full";

export type TextOrientation = "horizontal" | "vertical";

export type SegmentFillMode = "none" | "rainbow" | "blue" | "green" | "red";

// ---- /api/items ----
export type ItemsRequest = {
  generator_id: string;
  params: Record<string, unknown>;
  count: number;
  seed?: number | null;
};

export type ItemsResponse = {
  seed: number;
  items: Item[];
};

// ---- /api/render & /api/download.* ----
export type RenderRequest = {
  items: Item[];
  segments: number;
  size: SizeMode;
  hub_diameter_mm: number;
  hub_clearance_mm: number;
  text_orientation: TextOrientation;
  fill_mode: SegmentFillMode;
  title?: string | null;
};

export type RenderResponse = {
  segments: number;
  size: SizeMode;
  diameter_mm: number;
  hub_diameter_mm: number;
  hub_clearance_mm: number;
  hub_cut_diameter_mm: number;
  svg: string;
};

// ---- /api/emoji-catalog ----
export type EmojiEntry = {
  emoji: string;
  word: string;
};

export type EmojiCategory = {
  id: string;
  label: string;
  emojis: EmojiEntry[];
};

export type EmojiCatalog = {
  categories: EmojiCategory[];
};

const jsonHeaders = { "Content-Type": "application/json" };

export async function fetchExerciseTypes(): Promise<ExerciseType[]> {
  const res = await fetch("/api/exercise-types");
  if (!res.ok) throw new Error("Konnte Aufgabentypen nicht laden");
  return res.json();
}

export async function fetchEmojiCatalog(): Promise<EmojiCatalog> {
  const res = await fetch("/api/emoji-catalog");
  if (!res.ok) throw new Error("Konnte Bilderkatalog nicht laden");
  return res.json();
}

export function findEmojiWord(
  catalog: EmojiCatalog | null,
  emoji: string,
): string | null {
  if (!catalog) return null;
  for (const cat of catalog.categories) {
    for (const e of cat.emojis) {
      if (e.emoji === emoji) return e.word;
    }
  }
  return null;
}

export async function generateItems(req: ItemsRequest): Promise<ItemsResponse> {
  const res = await fetch("/api/items", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Aufgaben generieren fehlgeschlagen");
  return res.json();
}

export async function renderWheel(
  req: RenderRequest,
  signal?: AbortSignal,
): Promise<RenderResponse> {
  const res = await fetch("/api/render", {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) throw new Error("Vorschau fehlgeschlagen");
  return res.json();
}

export async function downloadFile(
  kind: "svg" | "png" | "pdf",
  req: RenderRequest,
  filename: string,
): Promise<void> {
  const res = await fetch(`/api/download.${kind}`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Download fehlgeschlagen");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
