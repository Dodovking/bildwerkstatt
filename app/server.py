import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import engine
from engine import BILDER_ORDNER, EXPORTE, FORMATE, MODELLE, STANDARD_MODELL, STILE, ZWECKE, Fehler, Werk

HOST = "127.0.0.1"
PORT = int(os.environ.get("BW_PORT", "7861"))
WEB = Path(__file__).resolve().parent / "web"
VERSION = (Path(__file__).resolve().parent / "VERSION").read_text("utf-8").strip() if (Path(__file__).resolve().parent / "VERSION").exists() else "dev"
LEERLAUF_ENDE_S = int(os.environ.get("BW_LEERLAUF_S", "120"))

app = FastAPI(title="Lumen Studio")
werk = Werk()
letzter_herzschlag = time.time()


@app.exception_handler(Fehler)
def _fehler(_, e):
    return JSONResponse({"fehler": str(e)}, status_code=400)


@app.get("/")
def startseite():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/info")
def info():
    return {
        "version": VERSION,
        "modelle": werk.modelle(),
        "standard_modell": STANDARD_MODELL,
        "stile": [{"id": k, "name": v[0]} for k, v in STILE.items()],
        "zwecke": [{"id": k, "name": v[0]} for k, v in ZWECKE.items()],
        "exporte": [{"id": k, "name": v[0], "groessen": v[1]} for k, v in EXPORTE.items()],
        "benutzer": _benutzer(),
        "formate": [{"id": k, "name": v[0], "breite": v[1], "hoehe": v[2]} for k, v in FORMATE.items()],
        "qualitaeten": {k: m["schritte"] for k, m in MODELLE.items()},
        "einstellungen": werk.einstellungen,
        "bilder_ordner": str(BILDER_ORDNER),
        "hardware": werk.hardware(),
    }


@app.get("/api/status")
def status():
    return werk.status()


@app.post("/api/herzschlag")
def herzschlag():
    global letzter_herzschlag
    letzter_herzschlag = time.time()
    return {"ok": True}


@app.post("/api/modell/{schluessel}/herunterladen")
def herunterladen(schluessel: str):
    werk.modell_herunterladen(schluessel)
    return {"ok": True}


@app.post("/api/erzeugen")
def erzeugen(daten: dict):
    return {"id": werk.auftrag(daten)}


@app.post("/api/abbrechen")
def abbrechen():
    werk.abbrechen_alle()
    return {"ok": True}


@app.post("/api/uebersetzen")
def uebersetzen(daten: dict):
    return {"text": werk.uebersetzen(daten.get("text", ""))}


@app.post("/api/einstellungen")
def einstellungen(daten: dict):
    werk.speichere_einstellungen(daten)
    return {"ok": True}


@app.get("/api/galerie")
def galerie():
    return {"bilder": werk.galerie(), "version": werk.galerie_version}


@app.delete("/api/galerie/{name:path}")
def loeschen(name: str):
    werk.loeschen(name)
    return {"ok": True}


@app.post("/api/freistellen")
def freistellen(daten: dict):
    return {"name": werk.freistellen_datei(daten.get("name", ""))}


@app.post("/api/export")
def exportieren(daten: dict):
    erg = werk.exportieren(daten.get("name", ""), daten.get("art", ""))
    if daten.get("zeigen", True):
        _im_explorer(Path(erg["zip"]))
    return erg


@app.get("/api/sammlungen")
def sammlungen():
    return werk.sammlungen()


@app.post("/api/sammlungen")
def sammlung_aendern(daten: dict):
    return werk.sammlung_aendern(daten)


@app.get("/bilder/{name:path}")
def bild(name: str):
    try:
        return FileResponse(werk.bildpfad(name))
    except Fehler:
        raise HTTPException(404)


@app.get("/vorschau/{name:path}")
def vorschau(name: str):
    try:
        pfad = werk.bildpfad(name)
    except Fehler:
        raise HTTPException(404)
    mini = BILDER_ORDNER / ".vorschau" / (name.rsplit(".", 1)[0] + ".webp")
    if not mini.exists() or mini.stat().st_mtime < pfad.stat().st_mtime:
        from PIL import Image

        mini.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(pfad) as im:
            im = im.convert("RGBA")
            im.thumbnail((480, 480))
            im.save(mini, "WEBP", quality=86)
    return FileResponse(mini, media_type="image/webp", headers={"Cache-Control": "max-age=86400"})


@app.post("/api/beenden")
def beenden():
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return {"ok": True}


@app.post("/api/ordner-oeffnen")
def ordner_oeffnen(daten: dict | None = None):
    ziel = BILDER_ORDNER
    name = (daten or {}).get("name")
    if name:
        _im_explorer(werk.bildpfad(name))
        return {"ok": True}
    if sys.platform == "win32":
        os.startfile(ziel)
    else:
        subprocess.Popen(["xdg-open", str(ziel)])
    return {"ok": True}


app.mount("/web", StaticFiles(directory=WEB), name="web")


def _benutzer():
    import getpass

    try:
        return getpass.getuser()
    except Exception:
        return ""


def _im_explorer(pfad):
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(pfad)])
    else:
        subprocess.Popen(["xdg-open", str(pfad.parent)])


def eltern_waechter():
    pid = int(os.environ.get("BW_ELTERN_PID") or 0)
    if not pid or sys.platform != "win32":
        return
    import ctypes

    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x00100000, False, pid)
    if h:
        k.WaitForSingleObject(h, 0xFFFFFFFF)
    os._exit(0)


def fenster_oeffnen():
    url = f"http://{HOST}:{PORT}/"
    if os.environ.get("BW_KEIN_FENSTER"):
        return
    kandidaten = []
    if sys.platform == "win32":
        for basis in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if basis:
                kandidaten += [
                    Path(basis) / "Microsoft/Edge/Application/msedge.exe",
                    Path(basis) / "Google/Chrome/Application/chrome.exe",
                    Path(basis) / "BraveSoftware/Brave-Browser/Application/brave.exe",
                ]
    profil = engine.BASIS / "fensterprofil"
    for exe in kandidaten:
        if exe.exists():
            subprocess.Popen([
                str(exe), f"--app={url}", f"--user-data-dir={profil}", "--window-size=1500,960",
                "--no-first-run", "--no-default-browser-check", "--disable-features=Translate",
            ])
            return
    webbrowser.open(url)


def leerlauf_waechter(server):
    while True:
        time.sleep(10)
        if LEERLAUF_ENDE_S <= 0:
            continue
        if werk.beschaeftigt():
            continue
        if time.time() - max(letzter_herzschlag, werk.letzte_aktivitaet) > LEERLAUF_ENDE_S:
            server.should_exit = True
            return


def laeuft_schon():
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/api/info", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    if laeuft_schon():
        if not os.environ.get("BW_KEIN_FENSTER"):
            fenster_oeffnen()
        return
    if sys.platform == "win32" and sys.stdout is None:
        log = open(engine.BASIS / "bildwerkstatt.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=leerlauf_waechter, args=(server,), daemon=True).start()
    threading.Thread(target=eltern_waechter, daemon=True).start()

    def nach_start():
        for _ in range(100):
            if server.started:
                fenster_oeffnen()
                return
            time.sleep(0.1)

    threading.Thread(target=nach_start, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
