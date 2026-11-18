import base64
import gc
import io
import json
import math
import os
import random
import re
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, PngImagePlugin

BASIS = Path(os.environ.get("BW_BASIS", Path(__file__).resolve().parent.parent))
MODELL_ORDNER = Path(os.environ.get("BW_MODELLE", BASIS / "Modelle"))
BILDER_ORDNER = Path(os.environ.get("BW_BILDER", BASIS / "Bilder"))
EINSTELLUNGEN = BASIS / "einstellungen.json"
SAMMLUNGEN = BASIS / "sammlungen.json"
EXPORT_ORDNER = BILDER_ORDNER / "Export"
TESTMODELL = os.environ.get("BW_TESTMODELL")

MODELL_ORDNER.mkdir(parents=True, exist_ok=True)
BILDER_ORDNER.mkdir(parents=True, exist_ok=True)

MODELLE = {
    "juggernaut": {
        "name": "Juggernaut XL",
        "titel": "Lumen Foto",
        "beschreibung": "Fotorealistisch – Menschen, Tiere, Landschaften, Produkte",
        "repo": "RunDiffusion/Juggernaut-XL-v9",
        "variante": "fp16",
        "schritte": {"schnell": 20, "normal": 30, "hoch": 45},
        "cfg": 5.0,
        "sampler": "dpmpp_karras",
    },
    "lightning": {
        "name": "DreamShaper XL Lightning",
        "titel": "Lumen Turbo",
        "beschreibung": "Turbo – sehr schnell (wenige Sekunden), vielseitig",
        "repo": "Lykon/dreamshaper-xl-lightning",
        "variante": "fp16",
        "schritte": {"schnell": 4, "normal": 6, "hoch": 8},
        "cfg": 2.0,
        "sampler": "dpmpp",
    },
    "sdxl": {
        "name": "Stable Diffusion XL 1.0",
        "titel": "Lumen Vision",
        "beschreibung": "Allrounder – Kunst, Illustration, Konzepte",
        "repo": "stabilityai/stable-diffusion-xl-base-1.0",
        "variante": "fp16",
        "schritte": {"schnell": 20, "normal": 30, "hoch": 45},
        "cfg": 7.0,
        "sampler": "dpmpp_karras",
    },
    "anime": {
        "name": "Animagine XL 3.1",
        "titel": "Lumen Anime",
        "beschreibung": "Anime & Manga",
        "repo": "cagliostrolab/animagine-xl-3.1",
        "variante": None,
        "schritte": {"schnell": 20, "normal": 28, "hoch": 40},
        "cfg": 6.0,
        "sampler": "euler_a",
        "prompt_zusatz": "masterpiece, best quality, very aesthetic, absurdres",
        "negativ_zusatz": "nsfw, lowres, (bad), text, error, fewer, extra, missing, worst quality, jpeg artifacts, low quality, watermark, unfinished, displeasing, oldest, early, chromatic aberration, signature, extra digits, artistic error, username, scan, [abstract]",
    },
    "flux": {
        "name": "FLUX.1 schnell",
        "titel": "Lumen Präzise",
        "beschreibung": "Am genauesten – bekannte Figuren, mehrere Figuren, Text (ca. 30 s pro Bild)",
        "typ": "flux",
        "repo": "unsloth/FLUX.1-schnell",
        "gguf": ("city96/FLUX.1-schnell-gguf", "flux1-schnell-Q6_K.gguf"),
        "groesse_gb": 19.4,
        "variante": None,
        "schritte": {"schnell": 3, "normal": 4, "hoch": 6},
        "cfg": 1.0,
        "sampler": None,
    },
}
STANDARD_MODELL = "lightning"
_IMPORT_LOCK = threading.Lock()
VAE_REPO = "madebyollin/sdxl-vae-fp16-fix"
UEBERSETZER_REPO = "Helsinki-NLP/opus-mt-de-en"
PROMPT_KI_REPO = "Qwen/Qwen3-4B-Instruct-2507"
PROMPT_KI_GB = 8.1
NAMEN = json.loads((Path(__file__).resolve().parent / "namen.json").read_text("utf-8"))
_NAMEN_MUSTER = re.compile(r"\b(" + "|".join(sorted(map(re.escape, NAMEN), key=len, reverse=True)) + r")(s)?\b", re.IGNORECASE)
_NAMEN_KLEIN = {k.lower(): v for k, v in NAMEN.items()}

PROMPT_KI_REGELN = (
    "You turn a user's image wish (often German, casual, maybe with typos) into one English prompt for Stable Diffusion XL. "
    "Output ONLY the prompt: no quotes, no explanation, no 'I want'. "
    "Replace every German or localized name of a known character, creature, brand, place or franchise with its official English name "
    "plus its franchise (e.g. 'Squirtle (Pokemon)', 'Mickey Mouse (Disney)'). "
    "The image model already knows famous characters by name: never describe their body, colors or features yourself. "
    "Never write color, tone or shade words (gray, monochrome, pastel, muted ...) unless the user wrote that color; a mood like sad is not a color. "
    "Keep every subject, action, count, color and place the user asked for and never add new subjects. "
    "Do not add art-style or medium words (realistic, photo, anime, painting, 3d) unless the user asked for a style. "
)
PROMPT_KI_BILD = PROMPT_KI_REGELN + "Add helpful visual details (composition, lighting, setting). Comma-separated phrases, at most 60 words."
PROMPT_KI_GRAFIK = PROMPT_KI_REGELN + (
    "This becomes a single emote or sticker on a plain background: describe only the subject, its pose and expression; "
    "no background, no scenery. Comma-separated phrases, at most 30 words."
)

STILE = {
    "kein": ("Kein Stil", "{p}"),
    "foto": ("Foto", "{p}, professional photography, sharp focus, highly detailed, natural lighting, 8k uhd, dslr"),
    "kino": ("Kinofilm", "cinematic film still of {p}, shallow depth of field, dramatic lighting, film grain, color graded, epic"),
    "portrait": ("Porträt", "close-up portrait photo of {p}, 85mm lens, bokeh, soft studio lighting, detailed skin texture"),
    "fantasy": ("Fantasy-Kunst", "epic fantasy digital painting of {p}, intricate details, magical atmosphere, artstation, concept art"),
    "anime": ("Anime", "anime artwork of {p}, studio anime style, vibrant colors, highly detailed"),
    "comic": ("Comic", "comic book illustration of {p}, bold ink lines, vibrant colors, halftone shading"),
    "oel": ("Ölgemälde", "oil painting of {p}, visible brush strokes, classical masterpiece, rich colors, canvas texture"),
    "aquarell": ("Aquarell", "watercolor painting of {p}, soft pastel colors, paper texture, delicate washes"),
    "bleistift": ("Bleistiftzeichnung", "detailed pencil sketch of {p}, graphite, fine linework, monochrome, paper"),
    "3d": ("3D-Render", "3d render of {p}, pixar style, octane render, soft global illumination, cute, highly detailed"),
    "pixel": ("Pixel-Art", "pixel art of {p}, 16-bit, retro video game style, crisp pixels"),
    "neon": ("Cyberpunk/Neon", "cyberpunk scene of {p}, neon lights, rain, futuristic city, vivid magenta and cyan"),
    "logo": ("Logo/Icon", "minimalist flat vector logo of {p}, simple shapes, clean, centered, white background"),
    "sticker": ("Sticker", "die-cut sticker of {p}, cute, bold outline, white border, flat colors, simple background"),
}

FREISTELL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"

ZWECKE = {
    "bild": ("Bild", None),
    "emote": ("Emote", "twitch emote of {p}, cute expressive mascot character, big readable face, bold thick dark outline, "
              "flat vibrant cel shading, simple shapes, centered, single subject, isolated on plain white background, "
              "high contrast, clean vector art"),
    "sticker": ("Sticker", "die-cut sticker of {p}, bold outline, vibrant flat colors, cute, centered, single subject, "
                "isolated on plain white background, clean vector illustration"),
    "abzeichen": ("Abzeichen", "badge icon of {p}, simple emblem, bold thick outline, flat vibrant colors, centered, "
                  "isolated on plain white background, minimal details, clean vector icon"),
}
NEGATIV_GRAFIK = "photo, photorealistic, scenery, landscape background, multiple subjects, text, letters, watermark, blurry, gradient background, drop shadow, frame, cropped"

EXPORTE = {
    "twitch_emote": ("Twitch Emote", [112, 56, 28]),
    "twitch_abzeichen": ("Twitch Abzeichen", [72, 36, 18]),
    "youtube_emoji": ("YouTube Emoji", [288, 48, 24]),
    "discord": ("Discord Emoji", [128]),
    "sticker": ("Sticker", [512, 320]),
}

FORMATE = {
    "quadrat": ("Quadrat 1:1", 1024, 1024),
    "hoch": ("Hochformat 2:3", 832, 1216),
    "quer": ("Querformat 3:2", 1216, 832),
    "breit": ("Breitbild 16:9", 1344, 768),
    "handy": ("Handy 9:16", 768, 1344),
    "kino": ("Kino 21:9", 1536, 640),
}

STANDARD_NEGATIV = (
    "lowres, blurry, worst quality, low quality, jpeg artifacts, deformed, disfigured, bad anatomy, "
    "extra fingers, mutated hands, extra limbs, watermark, text, signature, logo, cropped"
)

SDXL_LATENT_RGB = [
    [0.3651, 0.4232, 0.4341],
    [-0.2533, -0.0042, 0.1068],
    [0.1076, 0.1111, -0.0362],
    [-0.3165, -0.2492, -0.2188],
]
SDXL_LATENT_BIAS = [0.1084, -0.0175, -0.0011]

ENGLISCH = set("the a an of and with in on at under over is are by for from to into wearing holding his her their its this that".split())
DEUTSCH = set("der die das den dem des ein eine einen einem einer und mit im in auf unter über ist sind von vom zum zur für aus bei als oder trägt hält".split())


def _jetzt():
    return time.time()


class Fehler(Exception):
    pass


class Werk:
    def __init__(self):
        self.torch = None
        self.geraet = "cpu"
        self.gpu_name = None
        self.vram_gb = None
        self.pipe = None
        self.pipe_i2i = None
        self.pipe_offload = False
        self.aktuelles_modell = None
        self.vae = None
        self.lock = threading.Lock()
        self.uebersetzer = None
        self.uebersetzer_lock = threading.Lock()
        self.prompt_ki = None
        self.prompt_ki_lock = threading.Lock()
        self.prompt_cache = {}
        self.downloads = {}
        self.auftraege = []
        self.aktiv = None
        self.abbrechen = False
        self.galerie_version = 0
        self.zuletzt = None
        self.letzte_aktivitaet = _jetzt()
        self.bedingung = threading.Condition()
        self.einstellungen = self._lade_einstellungen()
        self._metadaten_cache = {}
        self.freisteller = None
        self.freisteller_lock = threading.Lock()
        self.freisteller_dl_lock = threading.Lock()
        threading.Thread(target=self._arbeiter, daemon=True).start()
        threading.Thread(target=self._vorbereiten, daemon=True).start()

    # ---------- Einstellungen ----------
    def _lade_einstellungen(self):
        try:
            return json.loads(EINSTELLUNGEN.read_text("utf-8"))
        except Exception:
            return {}

    def speichere_einstellungen(self, daten):
        self.einstellungen.update(daten or {})
        EINSTELLUNGEN.write_text(json.dumps(self.einstellungen, ensure_ascii=False, indent=2), "utf-8")

    # ---------- Hardware ----------
    def _vorbereiten(self):
        import torch

        self.torch = torch
        if torch.cuda.is_available():
            self.geraet = "cuda"
            self.gpu_name = torch.cuda.get_device_name(0)
            self.vram_gb = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        if not self._uebersetzer_vorhanden():
            self.modell_herunterladen("_uebersetzer")
        if self._prompt_ki_moeglich() and not self._ist_installiert("_prompt_ki"):
            self.modell_herunterladen("_prompt_ki")
        if not self._freisteller_pfad().exists():
            threading.Thread(target=self._freisteller_vorladen, daemon=True).start()

    def hardware(self):
        return {
            "geraet": self.geraet,
            "gpu": self.gpu_name,
            "vram_gb": self.vram_gb,
            "bereit": self.torch is not None,
        }

    # ---------- Modelle & Downloads ----------
    def _ordner(self, schluessel):
        return MODELL_ORDNER / schluessel

    def _ist_installiert(self, schluessel):
        return (self._ordner(schluessel) / ".fertig").exists()

    def _uebersetzer_vorhanden(self):
        return self._ist_installiert("_uebersetzer")

    def _download_plan(self, schluessel):
        if schluessel == "_uebersetzer":
            return UEBERSETZER_REPO, [
                "config.json", "generation_config.json", "pytorch_model.bin",
                "source.spm", "target.spm", "tokenizer_config.json", "vocab.json",
            ]
        if schluessel == "_prompt_ki":
            return PROMPT_KI_REPO, [
                "config.json", "generation_config.json", "model*.safetensors", "model.safetensors.index.json",
                "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt",
            ]
        if schluessel == "_vae":
            return VAE_REPO, ["config.json", "diffusion_pytorch_model.safetensors"]
        m = MODELLE[schluessel]
        if TESTMODELL:
            return TESTMODELL, None
        if m.get("typ") == "flux":
            return m["repo"], [
                "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*", "text_encoder/*",
                "text_encoder_2/*", "vae/*", "transformer/config.json",
            ]
        v = f".{m['variante']}" if m["variante"] else ""
        muster = ["model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*"]
        for teil, datei in (("text_encoder", "model"), ("text_encoder_2", "model"), ("unet", "diffusion_pytorch_model"), ("vae", "diffusion_pytorch_model")):
            muster += [f"{teil}/config.json", f"{teil}/{datei}{v}.safetensors"]
        return m["repo"], muster

    def _download_plaene(self, schluessel):
        plaene = [self._download_plan(schluessel)]
        m = MODELLE.get(schluessel) or {}
        if m.get("gguf") and not TESTMODELL:
            plaene.append((m["gguf"][0], [m["gguf"][1]]))
        return plaene

    def _braucht_vae(self, schluessel):
        return MODELLE[schluessel].get("typ") != "flux"

    def _modell_installiert(self, schluessel):
        return self._ist_installiert(schluessel) and (not self._braucht_vae(schluessel) or self._ist_installiert("_vae"))

    def _flux_moeglich(self):
        return self.geraet == "cuda" and (self.vram_gb or 0) >= 11.5

    def modelle(self):
        liste = []
        for k, m in MODELLE.items():
            liste.append({
                "id": k, "name": m["name"], "titel": m["titel"], "beschreibung": m["beschreibung"], "cfg": m["cfg"],
                "installiert": self._modell_installiert(k),
                "download": self.downloads.get(k),
                "groesse_gb": m.get("groesse_gb", 7.0),
                "verfuegbar": m.get("typ") != "flux" or self._flux_moeglich(),
            })
        return liste

    def modell_herunterladen(self, schluessel):
        if schluessel not in MODELLE and schluessel not in ("_uebersetzer", "_vae", "_prompt_ki"):
            raise Fehler("Unbekanntes Modell")
        d = self.downloads.get(schluessel)
        if d and d["status"] == "laeuft":
            return
        self.downloads[schluessel] = {"status": "laeuft", "geladen": 0, "gesamt": 0, "fehler": None}
        threading.Thread(target=self._download, args=(schluessel,), daemon=True).start()

    def _download(self, schluessel):
        from huggingface_hub import HfApi, snapshot_download
        import fnmatch

        info = self.downloads[schluessel]
        try:
            teile = [schluessel]
            if schluessel in MODELLE and self._braucht_vae(schluessel) and not self._ist_installiert("_vae"):
                teile.append("_vae")
            plaene = []
            for t in teile:
                liste = self._download_plaene(t)
                for nr, (repo, muster) in enumerate(liste):
                    gesamt = 0
                    try:
                        mi = HfApi().model_info(repo, files_metadata=True)
                        for s in mi.siblings:
                            if muster is None or any(fnmatch.fnmatch(s.rfilename, p) for p in muster):
                                gesamt += s.size or 0
                    except Exception:
                        pass
                    plaene.append((t, repo, muster, gesamt, nr == len(liste) - 1))
            info["gesamt"] = sum(p[3] for p in plaene)
            ordner = sorted({p[0] for p in plaene})

            stop = threading.Event()

            def messen():
                while not stop.is_set():
                    info["geladen"] = sum(_ordnergroesse(self._ordner(t)) for t in ordner)
                    stop.wait(0.7)

            threading.Thread(target=messen, daemon=True).start()
            try:
                for t, repo, muster, _, letzter in plaene:
                    ziel = self._ordner(t)
                    ziel.mkdir(parents=True, exist_ok=True)
                    for versuch in range(4):
                        try:
                            snapshot_download(repo, local_dir=str(ziel), allow_patterns=muster, max_workers=4)
                            break
                        except Exception:
                            if versuch == 3:
                                raise
                            time.sleep(3 * (versuch + 1))
                    if letzter:
                        (ziel / ".fertig").write_text(datetime.now().isoformat(), "utf-8")
            finally:
                stop.set()
            info["geladen"] = info["gesamt"] or info["geladen"]
            info["status"] = "fertig"
        except Exception as e:
            traceback.print_exc()
            info["status"] = "fehler"
            info["fehler"] = f"Download fehlgeschlagen: {e}"

    def _lade_pipeline(self, schluessel):
        if self.aktuelles_modell == schluessel and self.pipe is not None:
            self._pipe_auf_gpu()
            return
        torch = self.torch
        from diffusers import AutoencoderKL, AutoPipelineForImage2Image, StableDiffusionXLPipeline

        self.pipe = None
        self.pipe_i2i = None
        self.pipe_offload = False
        self.aktuelles_modell = None
        gc.collect()
        if self.geraet == "cuda":
            torch.cuda.empty_cache()
        m = MODELLE[schluessel]
        if m.get("typ") == "flux" and not TESTMODELL:
            self._lade_flux(schluessel, m)
            return
        dtype = torch.float16 if self.geraet == "cuda" else torch.float32
        if self.vae is None and not TESTMODELL:
            self.vae = AutoencoderKL.from_pretrained(str(self._ordner("_vae")), torch_dtype=dtype)
        extra = {} if TESTMODELL else {"vae": self.vae}
        pipe = StableDiffusionXLPipeline.from_pretrained(
            str(self._ordner(schluessel)), torch_dtype=dtype, **extra,
            variant=None if TESTMODELL else m["variante"], use_safetensors=None if TESTMODELL else True,
        )
        pipe.scheduler = _scheduler(m["sampler"], pipe.scheduler.config)
        if self.geraet == "cuda":
            with self.prompt_ki_lock:
                self._ki_auslagern()
        pipe.to(self.geraet)
        pipe.set_progress_bar_config(disable=True)
        pipe.vae.enable_tiling()
        self.pipe = pipe
        self.pipe_i2i = AutoPipelineForImage2Image.from_pipe(pipe)
        self.pipe_i2i.set_progress_bar_config(disable=True)
        self.aktuelles_modell = schluessel

    def _lade_flux(self, schluessel, m):
        torch = self.torch
        from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig

        with self.prompt_ki_lock:
            self._ki_auslagern(ganz=True)
        ordner = self._ordner(schluessel)
        transformer = FluxTransformer2DModel.from_single_file(
            str(ordner / m["gguf"][1]), config=str(ordner), subfolder="transformer", torch_dtype=torch.bfloat16,
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        )
        pipe = FluxPipeline.from_pretrained(str(ordner), transformer=transformer, torch_dtype=torch.bfloat16)
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_tiling()
        pipe.set_progress_bar_config(disable=True)
        self.pipe = pipe
        self.pipe_offload = True
        self.aktuelles_modell = schluessel

    # ---------- Prompt-KI ----------
    def _prompt_ki_moeglich(self):
        return self.geraet == "cuda" and (self.vram_gb or 0) >= 10 and not TESTMODELL

    def prompt_ki_bereit(self):
        return self._prompt_ki_moeglich() and self._ist_installiert("_prompt_ki")

    def prompt_verbessern(self, text, zweck="bild", vorschau=False):
        text = _namen_ersetzen((text or "").strip())
        if not text:
            return text
        grafik = zweck not in (None, "bild")
        schluessel = (text, grafik)
        if schluessel in self.prompt_cache:
            return self.prompt_cache[schluessel]
        erg = None
        if self.prompt_ki_bereit() and not (vorschau and self.aktiv):
            try:
                erg = self._prompt_ki_fragen(text, grafik)
            except Exception:
                traceback.print_exc()
                self._ki_auslagern()
        if not erg:
            return self.uebersetzen(text)
        if len(self.prompt_cache) > 300:
            self.prompt_cache.clear()
        self.prompt_cache[schluessel] = erg
        return erg

    def _prompt_ki_fragen(self, text, grafik):
        torch = self.torch
        with self.lock, self.prompt_ki_lock:
            if self.prompt_ki is None:
                with _IMPORT_LOCK:
                    from transformers import AutoModelForCausalLM, AutoTokenizer

                pfad = str(self._ordner("_prompt_ki"))
                self.prompt_ki = (AutoTokenizer.from_pretrained(pfad), AutoModelForCausalLM.from_pretrained(pfad, dtype=torch.bfloat16).eval())
            tok, modell = self.prompt_ki
            if modell.device.type != "cuda":
                if _frei_gb(torch) < PROMPT_KI_GB + 0.8:
                    self._pipe_auslagern()
                modell.to("cuda")
            nachrichten = [
                {"role": "system", "content": PROMPT_KI_GRAFIK if grafik else PROMPT_KI_BILD},
                {"role": "user", "content": text},
            ]
            ein = tok.apply_chat_template(nachrichten, add_generation_prompt=True, return_tensors="pt", return_dict=True).to("cuda")
            with torch.inference_mode():
                aus = modell.generate(**ein, max_new_tokens=140, do_sample=False)
            antwort = tok.decode(aus[0][ein["input_ids"].shape[1]:], skip_special_tokens=True)
        zeile = next((z.strip() for z in antwort.splitlines() if z.strip()), "")
        zeile = zeile.strip().strip('"\'„“”`').rstrip(".").strip()
        return zeile if 3 <= len(zeile) <= 700 else None

    def _ki_auslagern(self, ganz=False):
        if not self.prompt_ki:
            return
        if ganz or self.pipe_offload:
            self.prompt_ki = None
            gc.collect()
        elif self.prompt_ki[1].device.type == "cuda":
            self.prompt_ki[1].to("cpu")
        else:
            return
        self.torch.cuda.empty_cache()

    def _pipe_auslagern(self):
        if self.pipe is not None and not self.pipe_offload and self.pipe.device.type == "cuda":
            self.pipe.to("cpu")
            self.torch.cuda.empty_cache()

    def _pipe_auf_gpu(self):
        if self.geraet != "cuda" or self.pipe is None:
            return
        with self.prompt_ki_lock:
            self._ki_auslagern()
        if not self.pipe_offload and self.pipe.device.type != "cuda":
            self.pipe.to("cuda")

    # ---------- Übersetzung ----------
    def uebersetzen(self, text):
        text = (text or "").strip()
        if not text or not _wirkt_deutsch(text):
            return text
        if not self._uebersetzer_vorhanden():
            return text
        with self.uebersetzer_lock:
            if self.uebersetzer is None:
                with _IMPORT_LOCK:
                    from transformers import MarianMTModel, MarianTokenizer

                pfad = str(self._ordner("_uebersetzer"))
                self.uebersetzer = (MarianTokenizer.from_pretrained(pfad), MarianMTModel.from_pretrained(pfad).eval())
            tok, modell = self.uebersetzer
            zeilen = [z.strip() for z in re.split(r"[\n]+", text) if z.strip()]
            import torch

            with torch.inference_mode():
                batch = tok(zeilen, return_tensors="pt", padding=True, truncation=True, max_length=400)
                aus = modell.generate(**batch, max_new_tokens=400, num_beams=4)
            return ", ".join(tok.decode(a, skip_special_tokens=True).strip().rstrip(".") for a in aus)

    # ---------- Aufträge ----------
    def auftrag(self, daten):
        modus = daten.get("modus", "text")
        modell = daten.get("modell") or STANDARD_MODELL
        if modell not in MODELLE:
            raise Fehler("Unbekanntes Modell")
        if MODELLE[modell].get("typ") == "flux":
            if not self._flux_moeglich():
                raise Fehler("Lumen Präzise (FLUX) braucht eine NVIDIA-Grafikkarte mit mindestens 12 GB Grafikspeicher.")
            if modus != "text":
                ersatz = next((k for k in MODELLE if self._braucht_vae(k) and self._modell_installiert(k)), None)
                if not ersatz:
                    raise Fehler("Bild → Bild, Variation und Hochskalieren gehen mit einem der anderen Modelle.")
                modell = daten["modell"] = ersatz
                daten.pop("cfg", None)
        if not self._modell_installiert(modell):
            raise Fehler("Dieses Modell ist noch nicht heruntergeladen.")
        if modus == "text" and not (daten.get("prompt") or "").strip():
            raise Fehler("Bitte beschreibe, was auf dem Bild zu sehen sein soll.")
        if modus in ("bild", "variation", "hochskalieren") and not (daten.get("eingabebild") or daten.get("quelle")):
            raise Fehler("Bitte wähle zuerst ein Ausgangsbild.")
        a = {
            "id": uuid.uuid4().hex[:10],
            "daten": daten,
            "status": "wartet",
            "bild_nr": 0,
            "anzahl": max(1, min(int(daten.get("anzahl") or 1), 8)) if modus != "hochskalieren" else 1,
            "schritt": 0,
            "schritte": 0,
            "vorschau": None,
            "ergebnisse": [],
            "fehler": None,
            "hinweis": "Wartet …",
            "erstellt": _jetzt(),
        }
        with self.bedingung:
            self.auftraege.append(a)
            self.bedingung.notify()
        return a["id"]

    def abbrechen_alle(self):
        with self.bedingung:
            for a in self.auftraege:
                if a["status"] == "wartet":
                    a["status"] = "abgebrochen"
            self.auftraege = [a for a in self.auftraege if a["status"] != "abgebrochen"]
        self.abbrechen = True

    def status(self):
        akt = self.aktiv
        return {
            "hardware": self.hardware(),
            "aktiv": _auftrag_info(akt) if akt else None,
            "wartend": len([a for a in self.auftraege if a["status"] == "wartet"]),
            "galerie_version": self.galerie_version,
            "zuletzt": self.zuletzt,
            "downloads": self.downloads,
            "modell_geladen": self.aktuelles_modell,
            "uebersetzer": self._uebersetzer_vorhanden() or self.prompt_ki_bereit(),
            "prompt_ki": self.prompt_ki_bereit(),
            "prompt_ki_moeglich": self._prompt_ki_moeglich(),
        }

    def beschaeftigt(self):
        return self.aktiv is not None or any(a["status"] == "wartet" for a in self.auftraege) or any(
            d["status"] == "laeuft" for d in self.downloads.values()
        )

    def _arbeiter(self):
        while True:
            with self.bedingung:
                while not self.auftraege:
                    self.bedingung.wait()
                a = self.auftraege.pop(0)
            if a["status"] == "abgebrochen":
                continue
            self.abbrechen = False
            self.aktiv = a
            a["status"] = "laeuft"
            try:
                while self.torch is None:
                    time.sleep(0.2)
                self._ausfuehren(a)
                a["status"] = "fertig"
            except Abbruch:
                a["status"] = "abgebrochen"
            except Fehler as e:
                a["status"] = "fehler"
                a["fehler"] = str(e)
            except Exception as e:
                traceback.print_exc()
                a["status"] = "fehler"
                msg = str(e)
                if "out of memory" in msg.lower():
                    msg = "Grafikspeicher voll – bitte kleineres Format oder weniger Bilder wählen."
                a["fehler"] = msg
                if self.geraet == "cuda":
                    self.torch.cuda.empty_cache()
            finally:
                self.letzte_aktivitaet = _jetzt()
                self.zuletzt = _auftrag_info(a)
                self.aktiv = None

    def _ausfuehren(self, a):
        d = a["daten"]
        modus = d.get("modus", "text")
        schluessel = d.get("modell") or STANDARD_MODELL
        m = MODELLE[schluessel]

        quelle_meta = {}
        eingabe = None
        if d.get("quelle"):
            pfad = self.bildpfad(d["quelle"])
            eingabe = _rgb(Image.open(pfad))
            quelle_meta = self.metadaten(pfad) or {}
        elif d.get("eingabebild"):
            roh = d["eingabebild"].split(",", 1)[-1]
            eingabe = _rgb(Image.open(io.BytesIO(base64.b64decode(roh))))

        prompt_original = (d.get("prompt") or "").strip()
        if not prompt_original and quelle_meta:
            prompt_original = quelle_meta.get("prompt_original", "")
        negativ_original = (d.get("negativ") or "").strip()
        uebersetzen = d.get("uebersetzen", True)
        stil = d.get("stil") or quelle_meta.get("stil") or "kein"
        zweck = d.get("zweck") or quelle_meta.get("zweck") or "bild"
        if zweck not in ZWECKE:
            zweck = "bild"
        prompt_ki = uebersetzen and bool(prompt_original) and self.prompt_ki_bereit()
        if uebersetzen and (prompt_original or negativ_original):
            a["hinweis"] = "Prompt-KI versteht deine Beschreibung …" if prompt_ki else "Übersetze Beschreibung …"
        prompt_en = self.prompt_verbessern(prompt_original, zweck) if uebersetzen else prompt_original
        negativ_en = self.uebersetzen(_namen_ersetzen(negativ_original)) if uebersetzen else negativ_original
        if not prompt_original and quelle_meta.get("prompt"):
            prompt_en = quelle_meta["prompt"]

        if self.aktuelles_modell != schluessel:
            a["hinweis"] = f"Lade {m['name']} in die Grafikkarte …"
        with self.lock:
            self._lade_pipeline(schluessel)
        vorlage = STILE.get(stil, STILE["kein"])[1]
        prompt = vorlage.replace("{p}", prompt_en or "") if prompt_en else vorlage.replace("{p}", "").strip(", ")
        if ZWECKE[zweck][1]:
            prompt = ZWECKE[zweck][1].replace("{p}", prompt)
        if m.get("prompt_zusatz"):
            prompt = f"{prompt}, {m['prompt_zusatz']}"
        grafik = NEGATIV_GRAFIK if zweck != "bild" else None
        negativ = ", ".join(x for x in [negativ_en, grafik, m.get("negativ_zusatz") or STANDARD_NEGATIV] if x)
        freistellen = zweck != "bild" if d.get("freistellen") is None else bool(d.get("freistellen"))

        qualitaet = d.get("qualitaet") or "normal"
        schritte = int(d.get("schritte") or m["schritte"].get(qualitaet, m["schritte"]["normal"]))
        cfg = float(d.get("cfg") or m["cfg"])
        seed = d.get("seed")
        seed = int(seed) if seed not in (None, "", -1, "-1") else random.randint(0, 2**32 - 1)

        if modus == "text":
            _, breite, hoehe = FORMATE.get(d.get("format") or "quadrat", FORMATE["quadrat"])
            if zweck != "bild":
                breite = hoehe = 1024
            elif d.get("breite") and d.get("hoehe"):
                breite, hoehe = _auf8(int(d["breite"])), _auf8(int(d["hoehe"]))
        else:
            staerke = float(d.get("staerke") or (0.3 if modus == "hochskalieren" else 0.55 if modus == "variation" else 0.6))
            staerke = max(0.05, min(staerke, 1.0))
            if modus == "hochskalieren":
                faktor = min(2.0, math.sqrt(4_300_000 / (eingabe.width * eingabe.height)))
                breite, hoehe = _auf8(eingabe.width * faktor), _auf8(eingabe.height * faktor)
            else:
                faktor = math.sqrt(1024 * 1024 / (eingabe.width * eingabe.height))
                breite, hoehe = _auf8(eingabe.width * faktor), _auf8(eingabe.height * faktor)
            eingabe = eingabe.resize((breite, hoehe), Image.LANCZOS)

        if TESTMODELL:
            breite, hoehe = min(breite, 128), min(hoehe, 128)
            if eingabe is not None:
                eingabe = eingabe.resize((breite, hoehe))

        for i in range(a["anzahl"]):
            if self.abbrechen:
                raise Abbruch()
            s = (seed + i) % (2**32)
            a["bild_nr"] = i + 1
            a["schritt"] = 0
            a["vorschau"] = None
            a["hinweis"] = f"Bild {i + 1} von {a['anzahl']} wird gemalt …"
            gen = self.torch.Generator(device="cpu").manual_seed(s)
            start = _jetzt()

            def rueckruf(pipe, schritt, t, kw):
                a["schritt"] = schritt + 1
                a["schritte"] = getattr(pipe, "num_timesteps", None) or a["schritte"]
                if self.abbrechen:
                    pipe._interrupt = True
                if schritt % 2 == 0 or schritt + 1 == a["schritte"]:
                    try:
                        a["vorschau"] = _vorschau(kw["latents"])
                    except Exception:
                        pass
                return kw

            with self.lock:
                if self.pipe_offload:
                    a["schritte"] = schritte
                    bild = self.pipe(
                        prompt=prompt, width=breite, height=hoehe, num_inference_steps=schritte, guidance_scale=0.0,
                        generator=gen, max_sequence_length=256, callback_on_step_end=rueckruf,
                    ).images[0]
                elif modus == "text":
                    a["schritte"] = schritte
                    bild = self.pipe(
                        prompt=prompt, negative_prompt=negativ, width=breite, height=hoehe,
                        num_inference_steps=schritte, guidance_scale=cfg, generator=gen,
                        callback_on_step_end=rueckruf,
                    ).images[0]
                else:
                    n = min(150, math.ceil(schritte / staerke))
                    a["schritte"] = int(n * staerke)
                    bild = self.pipe_i2i(
                        prompt=prompt, negative_prompt=negativ, image=eingabe, strength=staerke,
                        num_inference_steps=n, guidance_scale=cfg, generator=gen,
                        callback_on_step_end=rueckruf,
                    ).images[0]
            if self.abbrechen:
                raise Abbruch()
            if freistellen:
                a["hinweis"] = f"Bild {i + 1}: Hintergrund wird entfernt …"
                if not self._freisteller_pfad().exists():
                    a["hinweis"] = "Freistell-Modell wird einmalig geladen (ca. 180 MB) …"
                bild = self.freistellen(bild, rand=zweck == "sticker")
            meta = {
                "prompt_original": prompt_original, "prompt": prompt, "negativ_original": negativ_original,
                "negativ": negativ, "stil": stil, "modell": schluessel, "modell_name": m["name"],
                "seed": s, "schritte": schritte, "cfg": cfg, "breite": bild.width, "hoehe": bild.height,
                "modus": modus, "qualitaet": qualitaet, "format": d.get("format"), "zweck": zweck,
                "transparent": freistellen, "prompt_ki": prompt_ki, "cfg_prozent": d.get("cfg_prozent"), "gruppe": a["id"],
                "dauer_s": round(_jetzt() - start, 1), "erstellt": datetime.now().isoformat(timespec="seconds"),
            }
            if modus != "text":
                meta["staerke"] = staerke
                if d.get("quelle"):
                    meta["quelle"] = d["quelle"]
            name = self._speichern(bild, meta)
            a["ergebnisse"].append(name)
            self.galerie_version += 1

    def _speichern(self, bild, meta, zusatz=None):
        tag = datetime.now().strftime("%Y-%m-%d")
        ordner = BILDER_ORDNER / tag
        ordner.mkdir(parents=True, exist_ok=True)
        basis = datetime.now().strftime("%H%M%S") + f"_{meta['seed']}" + (f"_{zusatz}" if zusatz else "")
        pfad = ordner / f"{basis}.png"
        n = 1
        while pfad.exists():
            pfad = ordner / f"{basis}_{n}.png"
            n += 1
        info = PngImagePlugin.PngInfo()
        info.add_text("bildwerkstatt", json.dumps(meta, ensure_ascii=False))
        info.add_text(
            "parameters",
            f"{meta['prompt']}\nNegative prompt: {meta['negativ']}\nSteps: {meta['schritte']}, CFG scale: {meta['cfg']}, "
            f"Seed: {meta['seed']}, Size: {meta['breite']}x{meta['hoehe']}, Model: {meta['modell_name']}",
        )
        bild.save(pfad, pnginfo=info)
        return pfad.relative_to(BILDER_ORDNER).as_posix()

    # ---------- Freistellen & Export ----------
    def _lade_freisteller(self):
        if self.freisteller is not None:
            return self.freisteller
        import onnxruntime as ort

        ziel = self._freisteller_sichern()
        self.freisteller = ort.InferenceSession(str(ziel), providers=["CPUExecutionProvider"])
        return self.freisteller

    def _freisteller_pfad(self):
        return self._ordner("_freisteller") / "isnet-general-use.onnx"

    def _freisteller_sichern(self):
        ziel = self._freisteller_pfad()
        with self.freisteller_dl_lock:
            if not ziel.exists():
                self._datei_laden("_freisteller", FREISTELL_URL, ziel)
        return ziel

    def _freisteller_vorladen(self):
        try:
            self._freisteller_sichern()
        except Exception:
            traceback.print_exc()

    def _datei_laden(self, schluessel, url, ziel):
        import urllib.request

        info = {"status": "laeuft", "geladen": 0, "gesamt": 0, "fehler": None}
        self.downloads[schluessel] = info
        ziel.parent.mkdir(parents=True, exist_ok=True)
        tmp = ziel.with_suffix(".teil")
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
                info["gesamt"] = int(r.headers.get("Content-Length") or 0)
                while True:
                    block = r.read(1 << 20)
                    if not block:
                        break
                    f.write(block)
                    info["geladen"] += len(block)
            tmp.replace(ziel)
            info["status"] = "fertig"
        except Exception as e:
            info["status"] = "fehler"
            info["fehler"] = f"Download fehlgeschlagen: {e}"
            raise Fehler(info["fehler"])

    def freistellen(self, bild, rand=False):
        import numpy as np

        rgb = _rgb(bild)
        with self.freisteller_lock:
            sitzung = self._lade_freisteller()
            x = np.asarray(rgb.resize((1024, 1024), Image.BILINEAR), dtype=np.float32) / 255.0
            x = x - np.array([0.485, 0.456, 0.406], dtype=np.float32)
            x = x.transpose(2, 0, 1)[None]
            aus = sitzung.run(None, {sitzung.get_inputs()[0].name: x})[0][0, 0]
        aus = (aus - aus.min()) / max(float(aus.max() - aus.min()), 1e-6)
        maske = Image.fromarray((aus * 255).astype("uint8")).resize(rgb.size, Image.LANCZOS)
        maske = maske.point(lambda v: 0 if v < 18 else 255 if v > 235 else v)
        ergebnis = rgb.convert("RGBA")
        ergebnis.putalpha(maske)
        if rand:
            ergebnis = _stickerrand(ergebnis)
        return _zuschneiden(ergebnis)

    def freistellen_datei(self, name):
        pfad = self.bildpfad(name)
        meta = dict(self.metadaten(pfad) or {})
        with Image.open(pfad) as im:
            bild = self.freistellen(im.copy(), rand=meta.get("zweck") == "sticker")
        for k, v in (("prompt", ""), ("negativ", ""), ("schritte", 0), ("cfg", 0), ("modell_name", ""), ("seed", 0)):
            meta.setdefault(k, v)
        meta.update({"transparent": True, "quelle": name, "erstellt": datetime.now().isoformat(timespec="seconds")})
        meta["breite"], meta["hoehe"] = bild.size
        neu = self._speichern(bild, meta, zusatz="frei")
        self.galerie_version += 1
        return neu

    def exportieren(self, name, art):
        import zipfile
        from PIL import ImageFilter

        if art not in EXPORTE:
            raise Fehler("Unbekanntes Exportformat")
        titel, groessen = EXPORTE[art]
        pfad = self.bildpfad(name)
        with Image.open(pfad) as im:
            bild = _quadratisch(im.convert("RGBA"))
        stamm = pfad.stem
        ordner = EXPORT_ORDNER / f"{stamm}_{art}"
        ordner.mkdir(parents=True, exist_ok=True)
        dateien = []
        for g in groessen:
            klein = bild.resize((g, g), Image.LANCZOS)
            if g <= 56:
                klein = klein.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
            ziel = ordner / f"{stamm}_{g}x{g}.png"
            klein.save(ziel, optimize=True)
            dateien.append(ziel)
        zipdatei = EXPORT_ORDNER / f"{stamm}_{art}.zip"
        with zipfile.ZipFile(zipdatei, "w", zipfile.ZIP_DEFLATED) as z:
            for f in dateien:
                z.write(f, f.name)
        return {"titel": titel, "ordner": str(ordner), "zip": str(zipdatei),
                "dateien": [f.name for f in dateien], "groessen": groessen}

    # ---------- Sammlungen ----------
    def sammlungen(self):
        try:
            daten = json.loads(SAMMLUNGEN.read_text("utf-8"))
        except Exception:
            daten = {}
        daten.setdefault("Favoriten", [])
        return daten

    def sammlung_aendern(self, d):
        daten = self.sammlungen()
        aktion, name, bild = d.get("aktion"), (d.get("name") or "").strip(), d.get("bild")
        if not name:
            raise Fehler("Bitte gib der Sammlung einen Namen.")
        if aktion == "anlegen":
            daten.setdefault(name, [])
        elif aktion == "loeschen":
            daten.pop(name, None)
        elif aktion in ("hinzu", "entfernen", "umschalten"):
            liste = daten.setdefault(name, [])
            if aktion == "umschalten":
                aktion = "entfernen" if bild in liste else "hinzu"
            if aktion == "hinzu" and bild not in liste:
                liste.insert(0, bild)
            if aktion == "entfernen" and bild in liste:
                liste.remove(bild)
        else:
            raise Fehler("Unbekannte Aktion")
        SAMMLUNGEN.write_text(json.dumps(daten, ensure_ascii=False, indent=2), "utf-8")
        return daten

    # ---------- Galerie ----------
    def bildpfad(self, name):
        pfad = (BILDER_ORDNER / name).resolve()
        if BILDER_ORDNER.resolve() not in pfad.parents or not pfad.is_file():
            raise Fehler("Bild nicht gefunden")
        return pfad

    def metadaten(self, pfad):
        try:
            schl = (str(pfad), pfad.stat().st_mtime)
            if schl in self._metadaten_cache:
                return self._metadaten_cache[schl]
            with Image.open(pfad) as im:
                roh = im.info.get("bildwerkstatt")
                meta = json.loads(roh) if roh else {}
                meta.setdefault("breite", im.width)
                meta.setdefault("hoehe", im.height)
            self._metadaten_cache[schl] = meta
            return meta
        except Exception:
            return {}

    def galerie(self, anzahl=None):
        dateien = sorted((p for p in BILDER_ORDNER.rglob("*.png") if EXPORT_ORDNER not in p.parents), key=lambda p: p.stat().st_mtime, reverse=True)[:anzahl]
        return [{"name": p.relative_to(BILDER_ORDNER).as_posix(), **self.metadaten(p)} for p in dateien]

    def loeschen(self, name):
        pfad = self.bildpfad(name)
        pfad.unlink()
        self.galerie_version += 1


class Abbruch(Exception):
    pass


def _auftrag_info(a):
    return {k: a[k] for k in ("id", "status", "bild_nr", "anzahl", "schritt", "schritte", "vorschau", "ergebnisse", "fehler", "hinweis")}


def _rgb(bild):
    if bild.mode in ("RGBA", "LA", "P", "PA"):
        bild = bild.convert("RGBA")
        grund = Image.new("RGBA", bild.size, (255, 255, 255, 255))
        grund.alpha_composite(bild)
        return grund.convert("RGB")
    return bild.convert("RGB")


def _stickerrand(bild):
    from PIL import ImageFilter

    staerke = max(9, (min(bild.size) // 40) | 1)
    alpha = bild.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    rand = alpha.filter(ImageFilter.MaxFilter(staerke)).filter(ImageFilter.GaussianBlur(1.2))
    weiss = Image.new("RGBA", bild.size, (255, 255, 255, 0))
    weiss.putalpha(rand)
    weiss.alpha_composite(bild)
    return weiss


def _zuschneiden(bild):
    box = bild.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        return bild
    return _quadratisch(bild.crop(box), rand=0.04)


def _quadratisch(bild, rand=0.0):
    if bild.width == bild.height and not rand:
        return bild
    seite = int(max(bild.size) * (1 + 2 * rand))
    grund = Image.new("RGBA", (seite, seite), (0, 0, 0, 0))
    grund.alpha_composite(bild.convert("RGBA"), ((seite - bild.width) // 2, (seite - bild.height) // 2))
    return grund


def _auf8(x):
    return max(256, int(round(x / 8)) * 8)


def _ordnergroesse(ordner):
    gesamt = 0
    if ordner.exists():
        for wurzel, _, dateien in os.walk(ordner):
            for f in dateien:
                try:
                    gesamt += os.path.getsize(os.path.join(wurzel, f))
                except OSError:
                    pass
    return gesamt


def _namen_ersetzen(text):
    return _NAMEN_MUSTER.sub(lambda t: _NAMEN_KLEIN[t.group(1).lower()], text or "")


def _frei_gb(torch):
    return torch.cuda.mem_get_info()[0] / 1024**3


def _wirkt_deutsch(text):
    if re.search(r"[äöüÄÖÜß]", text):
        return True
    woerter = re.findall(r"[a-zA-Z]+", text.lower())
    if not woerter:
        return False
    de = sum(w in DEUTSCH for w in woerter)
    en = sum(w in ENGLISCH for w in woerter)
    if de > en:
        return True
    if en > de:
        return False
    return True


def _scheduler(art, config):
    from diffusers import DPMSolverMultistepScheduler, EulerAncestralDiscreteScheduler

    if art == "euler_a":
        return EulerAncestralDiscreteScheduler.from_config(config)
    if art == "dpmpp_karras":
        return DPMSolverMultistepScheduler.from_config(config, use_karras_sigmas=True, algorithm_type="dpmsolver++")
    return DPMSolverMultistepScheduler.from_config(config)


def _vorschau(latents):
    import torch

    lat = latents[0].float()
    if lat.shape[0] != 4:
        return None
    faktoren = torch.tensor(SDXL_LATENT_RGB, device=lat.device)
    bias = torch.tensor(SDXL_LATENT_BIAS, device=lat.device)
    rgb = torch.einsum("chw,cr->hwr", lat, faktoren) + bias
    rgb = ((rgb + 1) / 2).clamp(0, 1).mul(255).byte().cpu().numpy()
    bild = Image.fromarray(rgb)
    if bild.width < 192:
        bild = bild.resize((bild.width * 2, bild.height * 2), Image.BILINEAR)
    puffer = io.BytesIO()
    bild.save(puffer, format="JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(puffer.getvalue()).decode()
