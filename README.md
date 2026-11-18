# Lumen Studio (BildWerkstatt)

Kostenloser KI-Bildgenerator für Windows – läuft komplett lokal auf der eigenen NVIDIA-Grafikkarte (Stable Diffusion XL). Keine API, keine Kosten, kein Konto. Erstellt auch **Emotes, Abzeichen und Sticker für Twitch, YouTube und Discord** mit transparentem Hintergrund.

## Download

**[Lumen.exe herunterladen](https://github.com/Dodovking/bildwerkstatt/releases/latest/download/Lumen.exe)** und starten.

Beim ersten Start installiert sich Lumen nach `E:\KI\BildWerkstatt` (ohne Laufwerk E: nach `%LOCALAPPDATA%\Lumen`), legt die Verknüpfung „Lumen Studio“ auf dem Desktop an und richtet Python/PyTorch ein (einmalig ca. 3 GB). Updates gibt es über den Knopf **⟳ Update** unten links – Modelle, Bilder und Einstellungen bleiben erhalten.

## Funktionen

- Beschreibung auf Deutsch – wird lokal ins Englische übersetzt (Helsinki-NLP opus-mt-de-en)
- Modelle: Lumen Turbo (DreamShaper XL Lightning), Lumen Foto (Juggernaut XL), Lumen Vision (SDXL 1.0), Lumen Anime (Animagine XL 3.1) – je ~7 GB, Download beim ersten Gebrauch
- Stile, Formate, Qualitätsstufen, 1–4 Varianten, Prompt-Stärke, Seed, Negativ-Beschreibung
- Bild → Bild, Variationen, Hochskalieren 2×, Hintergrund entfernen (lokal, ONNX)
- **Emotes & Sticker:** Emote-, Sticker- und Abzeichen-Modus, automatischer transparenter Hintergrund, Sticker mit weißem Rand, Export als ZIP:

| Export | Größen |
| --- | --- |
| Twitch Emote | 112, 56, 28 px |
| Twitch Abzeichen | 72, 36, 18 px |
| YouTube Emoji | 288, 48, 24 px |
| Discord Emoji | 128 px |
| Sticker | 512, 320 px |

- Meine Kreationen (Filter, Suche), Favoriten & Sammlungen, Vorlagen

## Ordner

| Ordner | Inhalt |
| --- | --- |
| `Lumen.exe` | Programm (Fenster, Einrichtung, Updates) |
| `app` | KI-Engine (FastAPI-Server + Oberfläche), wird von Lumen.exe entpackt |
| `umgebung` | Python-Umgebung mit PyTorch (CUDA 12.8) |
| `Modelle` | heruntergeladene KI-Modelle |
| `Bilder` | erzeugte Bilder, `Bilder\Export` für Streamer-Exporte |

## Entwickeln

- `desktop/` – Windows-Host (.NET 8 WinForms + WebView2): `dotnet publish desktop -c Release` erzeugt eine einzelne `Lumen.exe` (Engine aus `app/` ist eingebettet).
- `app/` – Python-Engine; Version in `app/VERSION`. Release = Tag `vX.Y.Z` mit den Dateien `Lumen.exe` und `Lumen.exe.sha256`.
