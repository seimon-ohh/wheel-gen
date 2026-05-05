import { useEffect } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function HelpModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onClick={onClose}
    >
      <div
        className="card max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-xl font-semibold">
            Wie drucke ich das mit dem Cricut?
          </h2>
          <button className="btn-ghost" onClick={onClose} aria-label="Schließen">
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4 text-sm leading-relaxed text-slate-700">
          <p>
            Diese App erzeugt eine{" "}
            <span className="font-semibold">Cricut-fähige SVG</span> mit zwei
            Ebenen:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <span className="font-semibold">Druck-Ebene</span> (schwarz):
              Trennlinien und Aufgabentexte – wird gedruckt.
            </li>
            <li>
              <span className="font-semibold">Schnitt-Ebene</span> (rote
              Haarlinien): Außenkreis &amp; Loch für die Nabe (19&nbsp;mm) –
              wird vom Cricut geschnitten.
            </li>
          </ul>
          <ol className="list-decimal pl-5 space-y-2">
            <li>SVG herunterladen.</li>
            <li>
              In <span className="font-semibold">Cricut Design Space</span> auf{" "}
              <span className="font-semibold">Hochladen → SVG</span> klicken
              und die Datei einfügen.
            </li>
            <li>
              Auf der Leinwand die schwarzen Druck-Elemente (Linien + Text)
              auswählen und{" "}
              <span className="font-semibold">Abflachen (Flatten)</span>{" "}
              drücken. Damit werden sie zu einem{" "}
              <span className="font-semibold">Print-Then-Cut-Bild</span>.
            </li>
            <li>
              Die beiden roten Kreise als{" "}
              <span className="font-semibold">Schnitt-Ebenen</span> (Operation
              „Basic Cut") belassen und mit dem abgeflachten Bild{" "}
              <span className="font-semibold">Anhängen (Attach)</span>, damit
              die Position erhalten bleibt.
            </li>
            <li>
              <span className="font-semibold">Make It</span> klicken. Cricut
              fügt automatisch die Registrierungsmarken hinzu, du druckst auf
              dem Heimdrucker und der Cricut schneidet entlang der roten
              Linien.
            </li>
          </ol>
          <div className="rounded-lg bg-sky-50 ring-1 ring-sky-200 p-3 text-sky-900">
            <p className="font-semibold">Aufgabentyp „Bildwörter“</p>
            <p className="mt-1">
              Wenn du als Aufgabentyp{" "}
              <span className="font-semibold">Bildwörter</span> wählst,
              erscheinen auf den Segmenten Bilder (z.&nbsp;B. 🏠, 🐶, 🍎)
              statt Text. Das Kind sieht das Bild und schreibt das passende
              Wort auf. Die Lösungen siehst du als Lehrkraft unter dem Rad.
            </p>
            <p className="mt-1 text-sky-800">
              Die Bilder werden als Vektorpfade in die SVG eingebettet und
              funktionieren mit Cricut Print&nbsp;&amp;&nbsp;Cut genauso wie
              normaler Text.
            </p>
          </div>

          <div className="rounded-lg bg-amber-50 ring-1 ring-amber-200 p-3 text-amber-900">
            <p className="font-semibold">Wichtig</p>
            <ul className="list-disc pl-5 mt-1 space-y-1">
              <li>
                Druckereinstellung: <em>Tatsächliche Größe</em> – nicht „An
                Seite anpassen".
              </li>
              <li>
                Cricut Print-Then-Cut hat ein Limit von 17,1 × 23,5&nbsp;cm.
                Im Modus „Cricut" wird das Rad auf 17&nbsp;cm Durchmesser
                erzeugt – das passt in dieses Limit. Im Vollformat-Modus
                (18,8&nbsp;cm) kannst du als PDF drucken und manuell
                ausschneiden.
              </li>
              <li>
                Mindestens 300&nbsp;DPI Druckqualität wählen für scharfen
                Text.
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button className="btn-primary" onClick={onClose}>
            Verstanden
          </button>
        </div>
      </div>
    </div>
  );
}
