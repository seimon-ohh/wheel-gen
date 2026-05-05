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
            Wie drucke und schneide ich das?
          </h2>
          <button className="btn-ghost" onClick={onClose} aria-label="Schließen">
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4 text-sm leading-relaxed text-slate-700">
          <p className="font-semibold text-slate-900">
            Drei Download-Formate, je nach Workflow:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <span className="font-semibold">SVG / PNG</span> – für{" "}
              <span className="font-semibold">
                Cricut Print&nbsp;Then&nbsp;Cut
              </span>
              : Das Rad ist eine einzige gefüllte Fläche mit transparentem
              Nabenloch und transparentem Hintergrund. Außenkreis und Nabe
              sind zusätzlich als <span className="font-semibold">rote
              Schnittlinien</span> drin – Design Space erkennt sie
              automatisch als Schnitt. Die rote Farbe ist nur ein Hinweis
              auf der Leinwand und wird nicht gedruckt.
            </li>
            <li>
              <span className="font-semibold">PDF</span> – für den{" "}
              <span className="font-semibold">Heimdrucker</span> auf
              A4-Format: Das Rad sitzt mittig auf der Seite, exakt im
              gewählten Durchmesser. Außenkreis und Nabenloch sind als feine
              schwarze Schnittlinien sichtbar – mit Schere oder Cutter
              ausschneiden.
            </li>
          </ul>

          <div className="rounded-lg bg-emerald-50 ring-1 ring-emerald-200 p-3 text-emerald-900">
            <p className="font-semibold">Cricut-Workflow (SVG oder PNG)</p>
            <ol className="list-decimal pl-5 mt-1 space-y-1">
              <li>SVG oder PNG herunterladen.</li>
              <li>
                In <span className="font-semibold">Cricut Design Space</span> →{" "}
                <span className="font-semibold">Hochladen</span> → Datei
                auswählen und als{" "}
                <span className="font-semibold">
                  Print&nbsp;Then&nbsp;Cut
                </span>{" "}
                importieren.
              </li>
              <li>
                <span className="font-semibold">Make It</span> drücken. Cricut
                druckt das Rad auf dem Heimdrucker und schneidet entlang der
                roten Schnittlinien (Außenrand und Nabenloch). Die roten
                Linien selbst werden nicht aufs Papier gedruckt – sie
                steuern nur die Schneideklinge.
              </li>
            </ol>
          </div>

          <div className="rounded-lg bg-violet-50 ring-1 ring-violet-200 p-3 text-violet-900">
            <p className="font-semibold">Heimdrucker-Workflow (PDF)</p>
            <ol className="list-decimal pl-5 mt-1 space-y-1">
              <li>PDF herunterladen.</li>
              <li>
                Mit der Druckereinstellung{" "}
                <span className="font-semibold">Tatsächliche Größe</span> bzw.{" "}
                <span className="font-semibold">100 %</span> (nicht „An Seite
                anpassen") auf A4 drucken.
              </li>
              <li>
                Entlang der schwarzen Außenlinie und des Nabenkreises mit
                Schere oder Cutter ausschneiden.
              </li>
            </ol>
          </div>
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
                Druckereinstellung: <em>Tatsächliche Größe</em> bzw. 100 % –
                nicht „An Seite anpassen".
              </li>
              <li>
                Cricut Print-Then-Cut hat ein Limit von 17,1 × 23,5&nbsp;cm.
                Im Modus „Cricut" wird das Rad auf 17&nbsp;cm Durchmesser
                erzeugt – das passt in dieses Limit. Im Vollformat-Modus
                (18,8&nbsp;cm) druckst du das PDF auf A4 und schneidest von
                Hand aus.
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
