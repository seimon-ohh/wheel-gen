# Glücksrad Generator

Ein kleiner Heimnetz-Webdienst, der für ein selbstgebautes 12-Segment-Glücksrad
(18,8 cm Durchmesser, 19 mm Nabe) Cricut **Print-Then-Cut** Druckvorlagen mit
zufälligen Aufgaben (z. B. Kleines 1×1) erzeugt. Gedacht zum Einsatz im
Klassenzimmer als Gamification für Grundschüler:innen.

## Funktionsweise

1. Lehrkraft öffnet die Web-App im LAN.
2. Wählt einen Aufgabentyp (aktuell: **Kleines 1×1**, Faktor-Bereich
   einstellbar) und eine Größe (Cricut 17 cm oder Vollformat 18,8 cm).
3. Klickt **Generieren** – 12 zufällige, einzigartige Aufgaben werden auf
   die Segmente des Rads gedruckt.
4. Lädt die SVG (für Cricut), PNG (300 DPI) oder PDF herunter.
5. In Cricut Design Space hochladen → schwarze Druck-Elemente per
   *Flatten* zum Print-Then-Cut-Bild machen → die roten Kreise als Schnitt
   belassen → *Make It* – Cricut druckt und schneidet automatisch.

## Architektur

- **Backend**: FastAPI (Python 3.12), reine SVG-Erzeugung in
  [`backend/app/wheel.py`](backend/app/wheel.py), CairoSVG für PNG/PDF.
- **Frontend**: Vite + React + TypeScript + Tailwind, einseitige UI auf
  Deutsch, Live-Vorschau direkt aus dem zurückgegebenen SVG.
- **Deployment**: Single Docker-Image (Multi-Stage Build), läuft als
  einzelner Container per Docker Compose.

```
backend/
  app/
    api/generate.py     # Routen: /api/generate, /api/download.{svg,png,pdf}
    exercises/          # Aufgabengeneratoren (erweiterbar)
      base.py           # ExerciseGenerator ABC
      kleines_1x1.py    # Kleines 1×1
      registry.py
    wheel.py            # Cricut-fähiger SVG-Renderer
    main.py             # FastAPI-App + statische Auslieferung des Frontends
  requirements.txt
frontend/
  src/                  # React-App
  ...
Dockerfile              # Multi-stage: baut Frontend, packt Python-Runtime
docker-compose.yml
```

## Cricut Print-Then-Cut – wichtig zu wissen

| Eigenschaft | Wert |
|---|---|
| Maximale Druckfläche | 6,75″ × 9,25″ ≈ **17,14 × 23,5 cm** |
| Akzeptierte Formate | SVG, PNG, JPG, BMP, GIF, HEIC (kein PDF) |
| Empfohlene Auflösung | ≥ 300 DPI |
| Registrierungsmarken | werden von Design Space automatisch beim *Make It* hinzugefügt |

Da das Original-Rad 18,8 cm misst, würde es nicht in die Cricut-Druckfläche
passen. Diese App erzeugt im Cricut-Modus daher das Cover mit **17,0 cm**
Durchmesser. Es bleibt ein dünner Holzring (~9 mm) am Rand sichtbar, was
optisch unauffällig ist. Wer das volle Format will, nutzt den
**Vollformat-Modus (18,8 cm)** als PDF und schneidet manuell aus.

### Workflow in Cricut Design Space

1. **Hochladen → SVG** und die heruntergeladene Datei einfügen.
2. Auf der Leinwand alle schwarzen Elemente (Trennlinien + Aufgabentexte)
   selektieren → **Flatten/Abflachen** drücken. Das wird zu einem
   einzelnen Print-Then-Cut-Bild.
3. Die beiden roten Kreise (Außenkreis und 19 mm Nabe) als
   Schnitt-Operationen belassen und mit dem abgeflachten Bild **Attach /
   Anhängen**, damit alles in Position bleibt.
4. **Make It** klicken – Design Space erzeugt die Registrierungsmarken,
   schickt den Druckauftrag an deinen Drucker (immer mit „Tatsächliche
   Größe", nicht „An Seite anpassen") und der Cricut schneidet entlang
   der roten Linien.

## Lokale Entwicklung

Backend (in einem Terminal):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Frontend (in einem zweiten Terminal):

```bash
cd frontend
npm install
npm run dev
```

Vite proxyt `/api/*` an `http://localhost:8080`. Die App läuft dann auf
<http://localhost:5173>.

## Build & Deployment auf Proxmox

### 1. LXC anlegen

In der Proxmox-Web-UI einen neuen Container erstellen:

- Template: Debian 12 (`debian-12-standard`)
- Ressourcen: 1 vCPU, 512 MB RAM, 2 GB Disk reichen
- Netzwerk: an deine LAN-Bridge (z. B. `vmbr0`), DHCP oder feste IP
- **Optionen → Features**: `keyctl=1` und `nesting=1` (für Docker)

Alternativ als VM, falls Docker im LXC nicht gewünscht.

### 2. Docker installieren (im LXC)

```bash
apt update && apt install -y docker.io docker-compose-plugin git
systemctl enable --now docker
```

### 3. Repo klonen und starten

```bash
git clone <repo-url> /opt/wheel-gen
cd /opt/wheel-gen
docker compose up -d --build
```

App ist erreichbar unter `http://<lxc-ip>:8080`.

### 4. Auf das LAN beschränken

In `docker-compose.yml` das Port-Mapping auf die LAN-IP binden, z. B.:

```yaml
    ports:
      - "192.168.1.50:8080:8080"
```

…oder in der LXC/Firewall den Port nur intern erlauben.

### Updates

```bash
cd /opt/wheel-gen
git pull
docker compose up -d --build
```

## Erweiterung um neue Aufgabentypen

Neuen Generator anlegen, von `ExerciseGenerator` ableiten und in
`registry.py` registrieren:

```python
# backend/app/exercises/addition.py
from .base import Exercise, ExerciseGenerator, ParamSpec

class AdditionGenerator(ExerciseGenerator):
    id = "addition"
    label = "Addition"
    params = [
        ParamSpec("min", "Minimum", "int", 1, 0, 100),
        ParamSpec("max", "Maximum", "int", 20, 1, 1000),
    ]
    def generate(self, count=12, params=None, rng=None):
        ...
```

Dann in `backend/app/exercises/registry.py` zur Liste hinzufügen. Das
Frontend lädt die Generatoren dynamisch und rendert die Parameter-Felder
automatisch.

## Roadmap

- Großes 1×1, Addition, Subtraktion, Division als weitere Generatoren
- Optional Lösungen mit ausdrucken (Lehrer-PDF mit Antwort-Schlüssel)
- Speichern/Wiederverwenden früherer Sets

## Lizenz

MIT
