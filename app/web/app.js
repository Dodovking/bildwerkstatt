"use strict";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const host = window.chrome && window.chrome.webview;

const STIL_FARBEN = {
  kein: ["#3a4160", "#252b40"], foto: ["#f3c58b", "#5b6b8c"], kino: ["#ffb36b", "#7c5cff"], portrait: ["#f6b8a0", "#8c5c7c"],
  fantasy: ["#9b7bff", "#2dd4bf"], anime: ["#ff8fc8", "#7aa8ff"], comic: ["#ffd23f", "#ff4f5e"], oel: ["#c58a4a", "#3d5a80"],
  aquarell: ["#9ee7e5", "#f5a3c7"], bleistift: ["#d9d9d9", "#5a5a5a"], "3d": ["#ffb86b", "#4fc3f7"], pixel: ["#5ee87d", "#3b82f6"],
  neon: ["#ff2fd0", "#22d3ee"], logo: ["#ffffff", "#7c5cff"], sticker: ["#fde047", "#f472b6"],
};
const FORMAT_KARTEN = [
  { id: "hoch", name: "Hochformat", w: 15, h: 21 },
  { id: "quer", name: "Querformat", w: 24, h: 16 },
  { id: "quadrat", name: "Quadrat", w: 19, h: 19 },
  { id: "breit", name: "16:9", w: 26, h: 15 },
];
const GRAFIK_ZWECKE = [["emote", "Emote"], ["sticker", "Sticker"], ["abzeichen", "Abzeichen"]];
const VORLAGEN = [
  { t: "Stadt im Abendlicht", p: "Eine futuristische Stadt bei Sonnenuntergang, die sich im Wasser spiegelt", s: "kino", f: "quer", i: "🌆" },
  { t: "Porträt im Studio", p: "Porträt einer jungen Frau mit Sommersprossen, weiches Fensterlicht", s: "portrait", f: "hoch", i: "📷" },
  { t: "Fantasy-Landschaft", p: "Schwebende Inseln mit Wasserfällen über einem Wolkenmeer, Drachen am Himmel", s: "fantasy", f: "breit", i: "🐉" },
  { t: "Produktfoto", p: "Eine elegante Parfümflasche auf nassem schwarzen Stein, Lichtreflexe", s: "foto", f: "quadrat", i: "✨" },
  { t: "Anime-Held", p: "Ein Anime-Mädchen mit Schwert auf einem Dach in einer Neon-Stadt bei Nacht", s: "anime", f: "hoch", i: "⚔️" },
  { t: "Gemütliches Zimmer", p: "Gemütliches Zimmer mit Bücherregal, Katze am Fenster, Regen draußen", s: "aquarell", f: "quer", i: "📚" },
  { t: "Cyberpunk-Gasse", p: "Eine enge Gasse im Regen mit Leuchtreklamen und Imbissständen", s: "neon", f: "hoch", i: "🌃" },
  { t: "Stream-Hintergrund", p: "Gemütliches Gaming-Zimmer mit RGB-Beleuchtung, unscharfer Hintergrund", s: "kino", f: "breit", i: "🎮" },
  { t: "Logo", p: "Ein Wolfskopf als Logo für einen Gaming-Kanal", s: "logo", f: "quadrat", i: "🐺" },
  { t: "Hype-Emote", p: "ein jubelnder Fuchs mit erhobenen Armen", z: "emote", i: "🦊" },
  { t: "Lach-Emote", p: "eine Katze, die Tränen lacht", z: "emote", i: "😹" },
  { t: "Herz-Emote", p: "ein niedlicher Panda, der ein rotes Herz hält", z: "emote", i: "🐼" },
  { t: "GG-Emote", p: "ein kleiner Roboter, der Daumen hoch zeigt", z: "emote", i: "🤖" },
  { t: "Sub-Abzeichen", p: "ein leuchtender lila Kristall", z: "abzeichen", i: "💎" },
  { t: "Sticker", p: "ein Corgi mit Sonnenbrille auf einem Skateboard", z: "sticker", i: "🛹" },
  { t: "Kaffee-Sticker", p: "eine lächelnde Kaffeetasse mit Dampf", z: "sticker", i: "☕" },
];
const ANSICHTEN = {
  bild: ["BILDERSTUDIO", "Bildgenerator", "Verwandle deine Ideen in Bilder. Passe Stil, Format und Details an."],
  grafik: ["STREAMER-STUDIO", "Emotes & Sticker", "Emotes, Abzeichen und Sticker für Twitch, YouTube und Discord – mit transparentem Hintergrund."],
  kreationen: ["MEINE KREATIONEN", "Meine Kreationen", "Alle deine Bilder – lokal auf deinem PC gespeichert."],
  sammlungen: ["SAMMLUNGEN", "Sammlungen", "Ordne deine Lieblingsbilder in eigene Sammlungen."],
  vorlagen: ["VORLAGEN", "Vorlagen", "Starte mit einer fertigen Idee und passe sie an."],
};

const z = {
  ansicht: "generator", grafik: false, grafikZweck: "emote", stil: "kino", grafikStil: "kein", format: "hoch",
  qualitaet: "normal", anzahl: 4, cfg: 50, staerke: 60, modell: null, seed: "", prompt: "", negativ: "", uebersetzen: true, freistellen: true,
  eingabebild: null, quelle: null, info: null, galerie: [], galerieVersion: -1, auswahl: null, auftrag: null,
  zoom: 1, verschiebung: [0, 0], filter: "alle", suche: "", sammlungen: {}, sammlungOffen: null, update: null, status: null,
};

// ---------- Hilfen ----------
async function api(pfad, opt = {}) {
  const r = await fetch(pfad, {
    method: opt.method || (opt.body ? "POST" : "GET"),
    headers: opt.body ? { "Content-Type": "application/json" } : {},
    body: opt.body ? JSON.stringify(opt.body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.fehler || d.detail || `Fehler ${r.status}`);
  return d;
}
let meldungTimer;
function meldung(text, ok = false) {
  const m = $("#meldung");
  m.textContent = text; m.className = "meldung" + (ok ? " ok" : ""); m.hidden = false;
  clearTimeout(meldungTimer); meldungTimer = setTimeout(() => (m.hidden = true), ok ? 3500 : 6000);
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const bildUrl = (n) => "/bilder/" + encodeURI(n);
const miniUrl = (n) => "/vorschau/" + encodeURI(n);
const verlauf = (id) => { const f = STIL_FARBEN[id] || STIL_FARBEN.kein; return `linear-gradient(135deg, ${f[0]}, ${f[1]})`; };
function zeitText(iso) {
  if (!iso) return "";
  const d = new Date(iso), h = new Date(); const g = new Date(h); g.setDate(h.getDate() - 1);
  const uhr = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === h.toDateString()) return `Heute · ${uhr}`;
  if (d.toDateString() === g.toDateString()) return `Gestern · ${uhr}`;
  return `${d.toLocaleDateString("de-DE", { day: "numeric", month: "short" })} · ${uhr}`;
}
const zweckAktuell = () => (z.grafik ? z.grafikZweck : "bild");
const stilAktuell = () => (z.grafik ? z.grafikStil : z.stil);
const istGrafik = (b) => b && b.zweck && b.zweck !== "bild";
const modellInfo = (id) => (z.info?.modelle || []).find((m) => m.id === id);

let speichernTimer;
function speichern() {
  clearTimeout(speichernTimer);
  speichernTimer = setTimeout(() => {
    const { stil, grafikStil, grafikZweck, format, qualitaet, anzahl, cfg, modell, uebersetzen, freistellen, negativ } = z;
    api("/api/einstellungen", { body: { ui: { stil, grafikStil, grafikZweck, format, qualitaet, anzahl, cfg, modell, uebersetzen, freistellen, negativ } } }).catch(() => {});
  }, 600);
}

function dialog(html, beimOeffnen) {
  $("#dialog").innerHTML = html; $("#dialog-hg").hidden = false;
  $$("#dialog [data-zu]").forEach((b) => (b.onclick = dialogZu));
  beimOeffnen && beimOeffnen($("#dialog"));
}
function dialogZu() { $("#dialog-hg").hidden = true; $("#dialog").innerHTML = ""; }

// ---------- Ansichten ----------
function ansicht(name, grafik) {
  z.ansicht = name;
  if (name === "generator" && grafik !== undefined) z.grafik = grafik;
  $$(".ansicht").forEach((s) => (s.hidden = s.id !== "ansicht-" + name));
  $$("#nav a").forEach((a) => a.classList.toggle("aktiv", a.dataset.ansicht === name && (name !== "generator" || (a.dataset.zweck !== "bild") === z.grafik)));
  const k = name === "generator" ? (z.grafik ? "grafik" : "bild") : name;
  const [pfad, titel, unter] = ANSICHTEN[k];
  $("#pfad").textContent = pfad; $("#titel").textContent = titel; $("#untertitel").textContent = unter;
  if (name === "generator") generatorZeichnen();
  if (name === "kreationen") rasterZeichnen();
  if (name === "sammlungen") sammlungenZeichnen();
  if (name === "vorlagen") vorlagenZeichnen();
}

function generatorZeichnen() {
  $("#zweck-block").hidden = !z.grafik;
  $("#format-block").hidden = z.grafik;
  $("#frei-schalter").hidden = !z.grafik;
  $("#prompt-etikett").textContent = z.grafik ? "DEIN EMOTE / STICKER" : "DEINE BILDPROMPT";
  $("#leer-titel").textContent = z.grafik ? "Emotes & Sticker für deinen Kanal" : "Dein nächstes Meisterwerk";
  $("#leer-text").innerHTML = z.grafik
    ? "Beschreibe eine Figur oder ein Motiv, z. B. <b>„ein jubelnder Fuchs“</b>.<br>Der Hintergrund wird automatisch entfernt – danach exportierst du mit einem Klick für Twitch, YouTube oder Discord."
    : "Beschreibe oben, was du sehen möchtest, und klicke auf <b>Generieren</b>.<br>Alles läuft lokal auf deiner Grafikkarte – ohne Kosten, ohne Cloud.";
  const zw = $("#zweck");
  zw.innerHTML = GRAFIK_ZWECKE.map(([id, n]) => `<button data-wert="${id}" class="${id === z.grafikZweck ? "an" : ""}">${n}</button>`).join("");
  zw.querySelectorAll("button").forEach((b) => (b.onclick = () => { z.grafikZweck = b.dataset.wert; speichern(); generatorZeichnen(); }));
  formateZeichnen(); stilZeichnen(); modellZeichnen(); reglerZeichnen(); promptZeichnen(); auswahlZeichnen();
  $$("#qualitaet button").forEach((b) => b.classList.toggle("an", b.dataset.wert === z.qualitaet));
  $("#uebersetzen").checked = z.uebersetzen; $("#freistellen").checked = z.freistellen;
  $("#negativ").value = z.negativ;
  $("#los-text").textContent = z.auswahl ? "Neu generieren" : "Generieren";
}

function formateZeichnen() {
  $("#formate").innerHTML = FORMAT_KARTEN.map((f) =>
    `<button class="format ${f.id === z.format ? "an" : ""}" data-id="${f.id}"><i style="width:${f.w}px;height:${f.h}px"></i>${f.name}</button>`).join("");
  $$("#formate .format").forEach((b) => (b.onclick = () => { z.format = b.dataset.id; speichern(); formateZeichnen(); }));
}

function stilZeichnen() {
  const stile = z.info?.stile || [];
  const aktuell = stile.find((s) => s.id === stilAktuell()) || stile[0];
  if (!aktuell) return;
  $("#stil-name").textContent = aktuell.id === "kein" ? (z.grafik ? "Automatisch (Emote-Stil)" : "Kein Stil") : aktuell.name;
  $("#stil-farbe").style.background = verlauf(aktuell.id);
  $("#stil-liste").innerHTML = stile.map((s) =>
    `<div class="option ${s.id === aktuell.id ? "an" : ""}" data-id="${s.id}"><span class="farbe" style="background:${verlauf(s.id)}"></span><div>${esc(s.id === "kein" && z.grafik ? "Automatisch (Emote-Stil)" : s.name)}</div></div>`).join("");
  $$("#stil-liste .option").forEach((o) => (o.onclick = () => {
    if (z.grafik) z.grafikStil = o.dataset.id; else z.stil = o.dataset.id;
    $("#stil-liste").hidden = true; speichern(); stilZeichnen();
  }));
}

function modellZeichnen() {
  const modelle = z.info?.modelle || [];
  const dl = z.status?.downloads || {};
  const m = modellInfo(z.modell) || modelle[0];
  if (!m) return;
  $("#modell-name").textContent = `${m.titel} · ${m.name.replace(/ XL.*$/, " XL")}`;
  $("#modell-liste").innerHTML = modelle.map((x) => {
    const d = dl[x.id];
    let zusatz = x.installiert ? '<span class="zusatz ok">✓ bereit</span>' : `<span class="zusatz">⇩ laden · ${x.groesse_gb} GB</span>`;
    if (d && d.status === "laeuft") zusatz = `<span class="zusatz">${prozent(d)} %</span>`;
    if (d && d.status === "fehler") zusatz = '<span class="zusatz" style="color:var(--rot)">Fehler – erneut</span>';
    return `<div class="option ${x.id === m.id ? "an" : ""}" data-id="${x.id}"><span class="ico">✦</span><div>${esc(x.titel)} <small>${esc(x.name)} – ${esc(x.beschreibung)}</small></div>${zusatz}</div>`;
  }).join("");
  $$("#modell-liste .option").forEach((o) => (o.onclick = async () => {
    z.modell = o.dataset.id; speichern(); $("#modell-liste").hidden = true;
    const x = modellInfo(z.modell);
    if (!x.installiert) await modellLaden(x.id);
    modellZeichnen(); losZeichnen();
  }));
  losZeichnen();
}
const prozent = (d) => (d.gesamt ? Math.min(99, Math.floor((d.geladen / d.gesamt) * 100)) : 0);
async function modellLaden(id) {
  try { await api(`/api/modell/${id}/herunterladen`, { method: "POST" }); meldung("Download gestartet – das Modell wird einmalig auf deinen PC geladen.", true); }
  catch (e) { meldung(e.message); }
}

function reglerZeichnen() {
  const setze = (id, wert, text) => { const el = $(id); el.value = wert; el.style.setProperty("--p", ((wert - el.min) / (el.max - el.min)) * 100 + "%"); return text; };
  $("#anzahl-wert").textContent = setze("#anzahl", z.anzahl, "") || (z.anzahl === 1 ? "1 Bild" : `${z.anzahl} Bilder`);
  $("#cfg-wert").textContent = setze("#cfg", z.cfg, "") || `${z.cfg}%`;
  $("#staerke-wert").textContent = setze("#staerke", z.staerke, "") || `${z.staerke}%`;
  $("#staerke-block").hidden = !(z.eingabebild || z.quelle);
  $("#seed-wert").textContent = z.seed === "" ? "Zufall" : Number(z.seed).toLocaleString("de-DE");
}

function promptZeichnen() {
  const t = $("#prompt-text");
  t.textContent = z.prompt || (z.grafik ? "Beschreibe dein Emote – z. B. „ein jubelnder Fuchs mit erhobenen Armen“" : "Beschreibe dein Bild – z. B. „Eine futuristische Stadt bei Sonnenuntergang, die sich im Wasser spiegelt“");
  t.classList.toggle("leer", !z.prompt);
  $("#prompt").value = z.prompt;
  const hatEingabe = z.eingabebild || z.quelle;
  $("#eingabe-chip").hidden = !hatEingabe;
  if (hatEingabe) $("#eingabe-bild").src = z.eingabebild || miniUrl(z.quelle);
}
function promptBearbeiten(an) {
  $("#prompt").hidden = !an; $("#prompt-text").hidden = an;
  $("#bearbeiten").textContent = an ? "✓ Fertig" : "✎ Bearbeiten";
  if (an) { const p = $("#prompt"); p.focus(); p.setSelectionRange(p.value.length, p.value.length); }
  else { $("#uebersetzung").hidden = true; promptZeichnen(); }
}

function losZeichnen() {
  const b = $("#generieren"); const m = modellInfo(z.modell);
  const d = z.status?.downloads?.[z.modell];
  const laeuft = z.status?.aktiv || z.status?.wartend;
  b.disabled = false;
  if (m && !m.installiert) {
    $("#los-text").textContent = d && d.status === "laeuft" ? `Modell wird geladen … ${prozent(d)} %` : `${m.titel} herunterladen (${m.groesse_gb} GB)`;
    b.disabled = !!(d && d.status === "laeuft");
  } else if (laeuft) {
    $("#los-text").textContent = "Weitere Bilder in Warteschlange";
  } else {
    $("#los-text").textContent = z.auswahl ? "Neu generieren" : "Generieren";
  }
}

// ---------- Auswahl / Bühne ----------
function variantenVon(b) {
  if (!b) return [];
  if (!b.gruppe) return [b];
  return z.galerie.filter((x) => x.gruppe === b.gruppe).sort((a, c) => a.name.localeCompare(c.name));
}
function auswaehlen(b) {
  z.auswahl = b; z.zoom = 1; z.verschiebung = [0, 0];
  if (z.ansicht !== "generator") ansicht("generator", istGrafik(b));
  else auswahlZeichnen();
}
function auswahlZeichnen() {
  const b = z.auswahl; const img = $("#hauptbild");
  $("#leer").hidden = !!b; img.hidden = !b;
  $$("#aktionen button, #exporte button, #werkzeuge button").forEach((x) => (x.disabled = !b));
  $("#werkzeuge").hidden = !b;
  const var_ = variantenVon(b);
  const slots = Math.max(4, var_.length);
  $("#varianten").innerHTML = Array.from({ length: slots }, (_, i) => {
    const v = var_[i];
    return v ? `<div class="variante ${v.name === b.name ? "an" : ""}" data-name="${esc(v.name)}"><img class="${v.transparent ? "transparent" : ""}" src="${miniUrl(v.name)}" alt=""></div>` : '<div class="variante leer"></div>';
  }).join("");
  $$("#varianten .variante[data-name]").forEach((el) => (el.onclick = () => auswaehlen(z.galerie.find((x) => x.name === el.dataset.name))));
  const abz = $("#bild-abzeichen");
  if (!b) { abz.hidden = true; $("#chat-vorschau").hidden = true; zoomAnwenden(); losZeichnen(); return; }
  img.classList.remove("vorschau"); img.classList.toggle("transparent", !!b.transparent);
  img.src = bildUrl(b.name);
  abz.hidden = false;
  abz.querySelector("span").textContent = (var_.length > 1 ? `Generiert · ${var_.length} Varianten` : b.transparent ? "Freigestellt" : "Generiert") + ` · ${b.breite}×${b.hoehe}`;
  const fav = (z.sammlungen.Favoriten || []).includes(b.name);
  $("#favorit-knopf").textContent = fav ? "♥" : "♡";
  $("#seed-wert").title = `Seed dieses Bildes: ${b.seed}`;
  chatVorschau(b);
  zoomAnwenden(); losZeichnen();
}
function chatVorschau(b) {
  const cv = $("#chat-vorschau");
  if (!b.transparent && !istGrafik(b)) { cv.hidden = true; return; }
  const name = esc(z.info?.benutzer || "Du"); const u = bildUrl(b.name);
  cv.innerHTML = `<div class="chat dunkel"><b>${name}:</b> GG <img src="${u}" width="28" height="28"> <img src="${u}" width="56" height="56"></div>` +
    `<div class="chat hell"><b>${name}:</b> <img src="${u}" width="28" height="28"> <img src="${u}" width="56" height="56"></div>`;
  cv.hidden = false;
}
function zoomAnwenden() {
  $("#zoom-wert").textContent = Math.round(z.zoom * 100) + "%";
  $("#hauptbild").style.transform = `translate(${z.verschiebung[0]}px, ${z.verschiebung[1]}px) scale(${z.zoom})`;
}
function zoomen(richtung) {
  const stufen = [0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
  let i = stufen.findIndex((s) => s >= z.zoom - 0.001);
  i = Math.max(0, Math.min(stufen.length - 1, i + richtung));
  z.zoom = stufen[i]; if (z.zoom <= 1) z.verschiebung = [0, 0];
  zoomAnwenden();
}

// ---------- Erzeugen ----------
function cfgWert(id) {
  const m = modellInfo(id); const basis = m?.cfg || 5;
  return Math.round(basis * (0.4 + (1.2 * z.cfg) / 100) * 10) / 10;
}
async function erzeugen(extra = {}) {
  const modell = z.modell;
  const m = modellInfo(modell);
  if (!m) return;
  if (!m.installiert) { await modellLaden(modell); return; }
  if (!$("#prompt").hidden) z.prompt = $("#prompt").value.trim();
  const daten = {
    modus: z.eingabebild || z.quelle ? "bild" : "text",
    prompt: z.prompt, negativ: z.negativ, stil: stilAktuell(), format: z.format, qualitaet: z.qualitaet,
    anzahl: z.anzahl, modell, seed: z.seed === "" ? null : Number(z.seed), uebersetzen: z.uebersetzen,
    zweck: zweckAktuell(), freistellen: z.grafik ? z.freistellen : false, cfg: cfgWert(modell), cfg_prozent: z.cfg,
    eingabebild: z.eingabebild, quelle: z.quelle, staerke: z.staerke / 100, ...extra,
  };
  if (daten.modus === "text" && !daten.prompt) { promptBearbeiten(true); meldung("Bitte beschreibe zuerst, was auf dem Bild zu sehen sein soll."); return; }
  try {
    const r = await api("/api/erzeugen", { body: daten });
    z.auftrag = r.id; promptBearbeiten(false);
    $("#fortschritt").hidden = false; $("#fs-text").textContent = "Wird vorbereitet …"; $("#fs-balken").style.width = "2%";
    planen(150);
  } catch (e) { meldung(e.message); }
}
function aufQuelle(b, modus, extra = {}) {
  return erzeugen({
    modus, quelle: b.name, eingabebild: null, prompt: "", negativ: "", stil: b.stil, zweck: b.zweck || "bild",
    freistellen: !!b.transparent, modell: z.modell, ...extra,
  });
}

// ---------- Status-Schleife ----------
let schleifenTimer;
function planen(ms) { clearTimeout(schleifenTimer); schleifenTimer = setTimeout(aktualisieren, ms); }
async function aktualisieren() {
  let s;
  try { s = await api("/api/status"); } catch { planen(2000); return; }
  const vorher = z.status; z.status = s;
  hardwareZeichnen(s.hardware);
  const a = s.aktiv;
  if (a && a.id === z.auftrag) {
    $("#fortschritt").hidden = false;
    const gesamt = a.schritte || 1;
    const p = ((a.bild_nr - 1) + Math.min(1, a.schritt / gesamt)) / a.anzahl;
    $("#fs-balken").style.width = Math.max(2, p * 100) + "%";
    $("#fs-text").textContent = a.schritt && a.anzahl ? `${a.hinweis} · Schritt ${a.schritt}/${gesamt}` : a.hinweis;
    if (a.vorschau) {
      const img = $("#hauptbild"); img.hidden = false; $("#leer").hidden = true;
      img.src = a.vorschau; img.classList.add("vorschau"); img.classList.remove("transparent");
    }
  } else if (z.auftrag && s.zuletzt && s.zuletzt.id === z.auftrag) {
    const fertig = s.zuletzt; z.auftrag = null; $("#fortschritt").hidden = true;
    await galerieLaden(true);
    if (fertig.status === "fehler") meldung(fertig.fehler || "Unbekannter Fehler");
    if (fertig.status === "abgebrochen") meldung("Abgebrochen.", true);
    const erstes = z.galerie.find((b) => b.name === fertig.ergebnisse[0]);
    if (erstes) auswaehlen(erstes); else auswahlZeichnen();
  }
  if (s.galerie_version !== z.galerieVersion && !z.auftrag) await galerieLaden();
  const dlAktiv = Object.values(s.downloads || {}).some((d) => d.status === "laeuft");
  const dlVorher = vorher && Object.values(vorher.downloads || {}).some((d) => d.status === "laeuft");
  if (dlAktiv || dlVorher) {
    if (dlVorher && !dlAktiv) z.info = await api("/api/info");
    modellZeichnen(); willkommenAktualisieren();
  } else losZeichnen();
  planen(a || z.auftrag || dlAktiv ? 600 : 2500);
}
function hardwareZeichnen(h) {
  const punkt = $("#status-punkt");
  punkt.classList.toggle("bereit", !!h?.bereit);
  let t = "Grafikkarte wird geprüft …";
  if (h?.bereit) t = h.gpu ? `${h.gpu} · ${h.vram_gb} GB` : "Keine NVIDIA-Grafikkarte gefunden – CPU-Modus (sehr langsam)";
  $("#gpu-text").textContent = t; $("#avatar").title = t;
}

// ---------- Galerie ----------
async function galerieLaden(erzwingen = false) {
  try {
    const [g, s] = await Promise.all([api("/api/galerie"), api("/api/sammlungen")]);
    if (!erzwingen && g.version === z.galerieVersion) return;
    z.galerie = g.bilder; z.galerieVersion = g.version; z.sammlungen = s;
    if (z.auswahl) z.auswahl = z.galerie.find((b) => b.name === z.auswahl.name) || null;
    zuletztZeichnen(); planZeichnen();
    if (z.ansicht === "kreationen") rasterZeichnen();
    if (z.ansicht === "sammlungen") sammlungenZeichnen();
    if (z.ansicht === "generator" && !z.auftrag) auswahlZeichnen();
  } catch (e) { console.error(e); }
}
function zuletztZeichnen() {
  const gesehen = new Set(); const liste = [];
  for (const b of z.galerie) {
    const k = b.gruppe || b.name;
    if (gesehen.has(k)) continue; gesehen.add(k); liste.push(b);
    if (liste.length === 3) break;
  }
  $("#zuletzt").innerHTML = liste.length ? liste.map((b) =>
    `<div class="zuletzt-eintrag" data-name="${esc(b.name)}"><img src="${miniUrl(b.name)}" alt=""><div><b>${esc(b.prompt_original || (istGrafik(b) ? "Emote" : "Ohne Beschreibung"))}</b><small>${zeitText(b.erstellt)}</small></div></div>`).join("")
    : '<div class="zuletzt-leer">Noch keine Bilder – leg los!</div>';
  $$(".zuletzt-eintrag").forEach((el) => (el.onclick = () => auswaehlen(z.galerie.find((x) => x.name === el.dataset.name))));
}
function planZeichnen() {
  const heute = new Date().toDateString();
  const n = z.galerie.filter((b) => b.erstellt && new Date(b.erstellt).toDateString() === heute).length;
  $("#plan-text").textContent = `Heute ${n} ${n === 1 ? "Bild" : "Bilder"} erstellt · unbegrenzt & ohne Kosten`;
  $("#plan-balken").style.width = Math.min(100, 8 + n * 3) + "%";
}
function kachel(b) {
  const fav = (z.sammlungen.Favoriten || []).includes(b.name);
  return `<div class="kachel" data-name="${esc(b.name)}"><img class="${b.transparent ? "transparent" : ""}" loading="lazy" src="${miniUrl(b.name)}" alt="">` +
    `${fav ? '<span class="marke-fav">♥</span>' : ""}<div class="unterschrift">${esc(b.prompt_original || "")}<br><span class="leise">${zeitText(b.erstellt)} · ${esc(b.modell_name || "")}</span></div></div>`;
}
function kachelnVerbinden(container) {
  container.querySelectorAll(".kachel[data-name]").forEach((el) => (el.onclick = () => auswaehlen(z.galerie.find((x) => x.name === el.dataset.name))));
}
function rasterZeichnen() {
  const favs = z.sammlungen.Favoriten || []; const q = z.suche.toLowerCase();
  const liste = z.galerie.filter((b) => {
    if (z.filter === "bild" && istGrafik(b)) return false;
    if (z.filter === "grafik" && !istGrafik(b) && !b.transparent) return false;
    if (z.filter === "favoriten" && !favs.includes(b.name)) return false;
    return !q || `${b.prompt_original || ""} ${b.prompt || ""}`.toLowerCase().includes(q);
  });
  const r = $("#raster");
  r.innerHTML = liste.length ? liste.map(kachel).join("") : '<div class="leer-hinweis">Hier ist noch nichts. Erstelle dein erstes Bild im Bildgenerator.</div>';
  kachelnVerbinden(r);
}

// ---------- Sammlungen ----------
function sammlungenZeichnen() {
  const r = $("#sammlungen-raster"); const offen = z.sammlungOffen;
  $("#sammlung-zurueck").hidden = !offen; $("#sammlung-loeschen").hidden = !offen || offen === "Favoriten";
  $("#sammlung-titel").textContent = offen || "";
  if (offen) {
    const namen = z.sammlungen[offen] || [];
    const liste = namen.map((n) => z.galerie.find((b) => b.name === n)).filter(Boolean);
    r.innerHTML = liste.length ? liste.map(kachel).join("") : '<div class="leer-hinweis">Diese Sammlung ist noch leer. Füge Bilder über „Zur Sammlung“ hinzu.</div>';
    kachelnVerbinden(r); return;
  }
  r.innerHTML = Object.entries(z.sammlungen).map(([name, namen]) => {
    const cover = namen.slice(0, 4).map((n) => `<img src="${miniUrl(n)}" alt="" onerror="this.replaceWith(document.createElement('span'))">`);
    while (cover.length < 4) cover.push("<span></span>");
    return `<div class="kachel sammlung-kachel" data-sammlung="${esc(name)}"><div class="cover">${cover.join("")}</div><div class="info"><b>${name === "Favoriten" ? "♥ " : ""}${esc(name)}</b><small>${namen.length} ${namen.length === 1 ? "Bild" : "Bilder"}</small></div></div>`;
  }).join("");
  $$("[data-sammlung]").forEach((el) => (el.onclick = () => { z.sammlungOffen = el.dataset.sammlung; sammlungenZeichnen(); }));
}
async function sammlung(aktion, name, bild) {
  z.sammlungen = await api("/api/sammlungen", { body: { aktion, name, bild } });
}
function sammlungDialog(b) {
  const namen = Object.keys(z.sammlungen);
  dialog(`<h2>Zur Sammlung hinzufügen</h2>
    ${namen.map((n) => `<label class="schalter"><input type="checkbox" data-n="${esc(n)}" ${(z.sammlungen[n] || []).includes(b.name) ? "checked" : ""}> ${esc(n)}</label>`).join("")}
    <p class="leise" style="margin-top:16px">Neue Sammlung</p><input type="text" id="neue-sammlung" placeholder="z. B. Twitch-Emotes">
    <div class="knoepfe"><button class="klein-knopf" data-zu>Schließen</button><button class="los" id="sammlung-ok">Speichern</button></div>`, (d) => {
    d.querySelector("#sammlung-ok").onclick = async () => {
      try {
        for (const cb of d.querySelectorAll("[data-n]")) {
          const drin = (z.sammlungen[cb.dataset.n] || []).includes(b.name);
          if (cb.checked !== drin) await sammlung(cb.checked ? "hinzu" : "entfernen", cb.dataset.n, b.name);
        }
        const neu = d.querySelector("#neue-sammlung").value.trim();
        if (neu) await sammlung("hinzu", neu, b.name);
        dialogZu(); meldung("Gespeichert.", true); auswahlZeichnen();
      } catch (e) { meldung(e.message); }
    };
  });
}

// ---------- Vorlagen ----------
function vorlagenZeichnen() {
  $("#vorlagen-raster").innerHTML = VORLAGEN.map((v, i) => {
    const farbe = v.z ? "linear-gradient(135deg,#ffb36b,#f0629a 55%,#7c5cff)" : verlauf(v.s);
    const art = v.z ? GRAFIK_ZWECKE.find((g) => g[0] === v.z)[1] + " · transparent" : `${(z.info?.stile || []).find((s) => s.id === v.s)?.name || ""} · ${FORMAT_KARTEN.find((f) => f.id === v.f)?.name || ""}`;
    return `<div class="vorlage" data-i="${i}"><div class="farbe" style="background:${farbe}">${v.i}</div><b>${esc(v.t)}</b><p>${esc(v.p)}</p><small>${esc(art)}</small></div>`;
  }).join("");
  $$(".vorlage").forEach((el) => (el.onclick = () => {
    const v = VORLAGEN[el.dataset.i];
    z.prompt = v.p; z.auswahl = null; z.eingabebild = null; z.quelle = null;
    if (v.z) { z.grafikZweck = v.z; ansicht("generator", true); }
    else { z.stil = v.s; z.format = v.f; ansicht("generator", false); }
    speichern(); meldung("Vorlage übernommen – passe den Text an oder klicke auf Generieren.", true);
  }));
}

// ---------- Aktionen ----------
async function aktion(name) {
  const b = z.auswahl; if (!b) return;
  try {
    if (name === "hochskalieren") await aufQuelle(b, "hochskalieren", { anzahl: 1 });
    if (name === "variationen") await aufQuelle(b, "variation", { anzahl: z.anzahl });
    if (name === "freistellen") {
      meldung("Hintergrund wird entfernt …", true);
      const r = await api("/api/freistellen", { body: { name: b.name } });
      await galerieLaden(true);
      const neu = z.galerie.find((x) => x.name === r.name); if (neu) auswaehlen(neu);
      meldung("Hintergrund entfernt – jetzt mit transparentem Hintergrund gespeichert.", true);
    }
    if (name === "teilen") {
      const blob = await (await fetch(bildUrl(b.name))).blob();
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      meldung("Bild in die Zwischenablage kopiert – füge es mit Strg + V in Discord, WhatsApp & Co. ein.", true);
    }
    if (name === "herunterladen") {
      const a = document.createElement("a"); a.href = bildUrl(b.name); a.download = "lumen_" + b.name.split("/").pop(); a.click();
    }
    if (name === "vorlage") {
      z.quelle = b.name; z.eingabebild = null; promptZeichnen(); reglerZeichnen();
      meldung("Bild als Vorlage gesetzt – beschreibe die Änderung und klicke auf Generieren.", true); promptBearbeiten(true);
    }
    if (name === "favorit") { await sammlung("umschalten", "Favoriten", b.name); auswahlZeichnen(); }
    if (name === "sammlung") sammlungDialog(b);
    if (name === "uebernehmen") {
      z.prompt = b.prompt_original || ""; z.seed = b.seed ?? "";
      if (b.modell && modellInfo(b.modell)) z.modell = b.modell;
      if (istGrafik(b)) { z.grafikZweck = b.zweck; z.grafikStil = b.stil || "kein"; z.grafik = true; }
      else { if (b.stil) z.stil = b.stil; if (b.format) z.format = b.format; z.grafik = false; }
      if (b.qualitaet) z.qualitaet = b.qualitaet;
      if (b.cfg_prozent != null) z.cfg = b.cfg_prozent;
      ansicht("generator", z.grafik); speichern(); meldung("Einstellungen inkl. Seed übernommen.", true);
    }
    if (name === "ordner") await api("/api/ordner-oeffnen", { body: { name: b.name } });
    if (name === "loeschen") {
      dialog(`<h2>Bild löschen?</h2><p>Das Bild wird endgültig von deinem PC gelöscht.</p><div class="knoepfe"><button class="klein-knopf" data-zu>Abbrechen</button><button class="los" id="ja">Löschen</button></div>`, (d) => {
        d.querySelector("#ja").onclick = async () => {
          dialogZu();
          const var_ = variantenVon(b).filter((x) => x.name !== b.name);
          await api("/api/galerie/" + encodeURI(b.name), { method: "DELETE" });
          z.auswahl = var_[0] || null; await galerieLaden(true); auswahlZeichnen();
        };
      });
    }
  } catch (e) { meldung(e.message); }
}
async function exportieren(art) {
  const b = z.auswahl; if (!b) return;
  try {
    if (!b.transparent && !istGrafik(b)) meldung("Tipp: Für Emotes vorher „Hintergrund entfernen“ nutzen.", true);
    const r = await api("/api/export", { body: { name: b.name, art } });
    meldung(`${r.titel} exportiert (${r.groessen.map((g) => g + " px").join(", ")}) – Ordner wurde geöffnet.`, true);
  } catch (e) { meldung(e.message); }
}

// ---------- Eingabebild ----------
function dateiLesen(datei) {
  if (!datei || !datei.type.startsWith("image/")) return;
  const r = new FileReader();
  r.onload = () => { z.eingabebild = r.result; z.quelle = null; promptZeichnen(); reglerZeichnen(); meldung("Ausgangsbild geladen – beschreibe die gewünschte Änderung.", true); };
  r.readAsDataURL(datei);
}

// ---------- Übersetzung ----------
let uebTimer;
function uebersetzungAnzeigen() {
  clearTimeout(uebTimer);
  const t = $("#prompt").value.trim(); const el = $("#uebersetzung");
  if (!t || !z.uebersetzen || !z.status?.uebersetzer) { el.hidden = true; return; }
  uebTimer = setTimeout(async () => {
    try {
      const r = await api("/api/uebersetzen", { body: { text: t } });
      if (r.text && r.text.toLowerCase() !== t.toLowerCase()) { el.textContent = "→ für die KI: " + r.text; el.hidden = false; } else el.hidden = true;
    } catch { el.hidden = true; }
  }, 900);
}

// ---------- Willkommen (erstes Modell) ----------
function willkommen() {
  const modelle = z.info.modelle;
  if (modelle.some((m) => m.installiert) || sessionStorage.getItem("willkommen-zu")) return;
  dialog(`<h2>Willkommen bei Lumen Studio ✦</h2>
    <p>Lumen erzeugt Bilder komplett auf deinem PC – ohne Abo, ohne API-Kosten. Lade dafür einmalig mindestens ein KI-Modell (je ca. 7 GB):</p>
    <div id="willkommen-liste"></div>
    <div class="knoepfe"><button class="klein-knopf" id="willkommen-zu">Später</button></div>`, (d) => {
    d.querySelector("#willkommen-zu").onclick = () => { sessionStorage.setItem("willkommen-zu", "1"); dialogZu(); };
    willkommenAktualisieren();
  });
}
function willkommenAktualisieren() {
  const liste = $("#willkommen-liste"); if (!liste) return;
  const dl = z.status?.downloads || {};
  liste.innerHTML = z.info.modelle.map((m) => {
    const d = dl[m.id]; const laeuft = d && d.status === "laeuft";
    const knopf = m.installiert ? '<span class="zusatz ok" style="color:var(--gruen)">✓ bereit</span>'
      : laeuft ? `<b>${prozent(d)} %</b>` : `<button class="klein-knopf" data-laden="${m.id}">${m.id === "lightning" ? "Empfohlen · " : ""}Laden</button>`;
    return `<div class="modell-zeile"><div><b>${esc(m.titel)}</b> <span class="leise">${esc(m.name)}</span><small>${esc(m.beschreibung)}</small>${laeuft ? `<div class="balken"><i style="width:${prozent(d)}%"></i></div>` : ""}${d?.status === "fehler" ? `<small style="color:var(--rot)">${esc(d.fehler)}</small>` : ""}</div>${knopf}</div>`;
  }).join("");
  liste.querySelectorAll("[data-laden]").forEach((b) => (b.onclick = async () => { z.modell = b.dataset.laden; speichern(); await modellLaden(b.dataset.laden); planen(100); }));
  if (z.info.modelle.some((m) => m.installiert) && !Object.values(dl).some((d) => d.status === "laeuft")) {
    liste.insertAdjacentHTML("beforeend", '<p style="color:var(--gruen)">Fertig! Du kannst jetzt loslegen.</p>');
  }
}

// ---------- Update (über die Lumen-App) ----------
function updateKlick() {
  if (!host) {
    dialog(`<h2>Updates</h2><p>Updates werden direkt in der <b>Lumen.exe</b> installiert. Du nutzt Lumen gerade im Browser.</p><p>Aktuelle Version: <b>${esc(z.info?.version)}</b></p><div class="knoepfe"><button class="los" data-zu>OK</button></div>`);
    return;
  }
  dialog(`<h2>Nach Updates suchen …</h2><p class="leise">Verbinde mit GitHub …</p>`);
  host.postMessage({ typ: "update-pruefen", zeigen: true });
}
function hostNachricht(n) {
  if (!n || typeof n !== "object") return;
  if (n.typ === "host") { z.host = n; }
  if (n.typ === "update-info") {
    z.update = n;
    const k = $("#update-knopf");
    k.classList.toggle("neu", !!n.verfuegbar);
    k.textContent = n.verfuegbar ? `⟳ Update ${n.neu}` : "⟳ Update";
    if (!n.zeigen) return;
    if (n.fehler) { dialog(`<h2>Update-Prüfung fehlgeschlagen</h2><p>${esc(n.fehler)}</p><div class="knoepfe"><button class="los" data-zu>OK</button></div>`); return; }
    if (!n.verfuegbar) { dialog(`<h2>Alles aktuell ✓</h2><p>Du nutzt die neueste Version <b>${esc(n.aktuell)}</b>.</p><div class="knoepfe"><button class="los" data-zu>OK</button></div>`); return; }
    dialog(`<h2>Update ${esc(n.neu)} verfügbar</h2><p>Installiert: ${esc(n.aktuell)} · Download: ${n.groesse_mb} MB</p>${n.notizen ? `<pre>${esc(n.notizen)}</pre>` : ""}
      <p class="leise">Deine Bilder, Modelle und Einstellungen bleiben erhalten. Lumen startet danach automatisch neu.</p>
      <div class="knoepfe"><button class="klein-knopf" data-zu>Später</button><button class="los" id="update-los">Jetzt aktualisieren</button></div>`, (d) => {
      d.querySelector("#update-los").onclick = () => {
        if (z.status?.aktiv) { meldung("Bitte warte, bis die aktuelle Generierung fertig ist."); return; }
        dialog(`<h2>Update wird installiert …</h2><p id="update-text" class="leise">Lade herunter …</p><div class="balken"><i id="update-balken"></i></div>`);
        host.postMessage({ typ: "update-installieren" });
      };
    });
  }
  if (n.typ === "update-fortschritt") {
    const b = $("#update-balken"); if (b) b.style.width = n.prozent + "%";
    const t = $("#update-text"); if (t) t.textContent = n.text;
  }
  if (n.typ === "update-fehler") dialog(`<h2>Update fehlgeschlagen</h2><p>${esc(n.text)}</p><div class="knoepfe"><button class="los" data-zu>OK</button></div>`);
}

// ---------- Einstellungen & Hilfe ----------
function einstellungenDialog() {
  const h = z.status?.hardware || {}; const inst = z.info.modelle.filter((m) => m.installiert).map((m) => m.titel).join(", ") || "keins";
  dialog(`<h2>Einstellungen</h2>
    <div class="tabelle">
      <span>Version</span><span>${esc(z.info.version)}${z.host ? "" : " (Browser)"}</span>
      <span>Grafikkarte</span><span>${esc(h.gpu || "keine – CPU")}${h.vram_gb ? ` · ${h.vram_gb} GB` : ""}</span>
      <span>Modelle</span><span>${esc(inst)}</span>
      <span>Bilder-Ordner</span><code>${esc(z.info.bilder_ordner)}</code>
      ${z.host ? `<span>Programm-Ordner</span><code>${esc(z.host.wurzel)}</code>` : ""}
    </div>
    <label class="schalter" style="margin-top:16px"><input type="checkbox" id="e-ueb" ${z.uebersetzen ? "checked" : ""}> Deutsche Eingaben lokal ins Englische übersetzen (bessere Ergebnisse)</label>
    <div class="knoepfe">
      ${z.host ? '<button class="klein-knopf" id="e-log">Protokoll öffnen</button>' : ""}
      <button class="klein-knopf" id="e-ordner">Bilder-Ordner öffnen</button>
      <button class="klein-knopf" id="e-update">Nach Updates suchen</button>
      <button class="los" data-zu>Fertig</button>
    </div>`, (d) => {
    d.querySelector("#e-ueb").onchange = (e) => { z.uebersetzen = e.target.checked; $("#uebersetzen").checked = z.uebersetzen; speichern(); };
    d.querySelector("#e-ordner").onclick = () => api("/api/ordner-oeffnen", { body: {} });
    d.querySelector("#e-update").onclick = updateKlick;
    const log = d.querySelector("#e-log"); if (log) log.onclick = () => host.postMessage({ typ: "protokoll" });
  });
}
function hilfeDialog() {
  dialog(`<h2>So funktioniert Lumen</h2>
    <p><b>Bild erstellen:</b> Beschreibung eingeben (Deutsch geht), Stil & Format wählen, <b>Generieren</b>. Mehrere Varianten werden nacheinander erzeugt.</p>
    <p><b>Prompt-Stärke:</b> höher = hält sich strenger an deinen Text, niedriger = freier und kreativer.</p>
    <p><b>Seed:</b> gleiche Zahl + gleiche Einstellungen = gleiches Bild. „Einstellungen übernehmen“ holt alles von einem Bild zurück.</p>
    <p><b>Bild → Bild:</b> Eigenes Bild über „⇪ Bild“ oder per Drag &amp; Drop laden oder „Als Vorlage“ nutzen, dann Änderung beschreiben.</p>
    <p><b>Emotes &amp; Sticker:</b> Links „Emotes &amp; Sticker“ wählen. Der Hintergrund wird automatisch entfernt. Unter <b>Export für Streamer</b> bekommst du fertige PNGs: Twitch 112/56/28 px, Abzeichen 72/36/18 px, YouTube 288/48/24 px, Discord 128 px, Sticker 512/320 px.</p>
    <p><b>Tastatur:</b> Strg + Enter generiert, ← / → wechselt zwischen Varianten, Doppelklick aufs Bild = Vollbild, Mausrad = Zoom.</p>
    <p class="leise">Alles läuft lokal auf deiner Grafikkarte. Es entstehen keine Kosten.</p>
    <div class="knoepfe"><button class="los" data-zu>Alles klar</button></div>`);
}

// ---------- Ereignisse ----------
function verbinden() {
  $$("#nav a").forEach((a) => (a.onclick = () => ansicht(a.dataset.ansicht, a.dataset.ansicht === "generator" ? a.dataset.zweck !== "bild" : undefined)));
  $$("[data-gehe]").forEach((b) => (b.onclick = () => ansicht(b.dataset.gehe)));
  $("#neu").onclick = () => {
    z.auswahl = null; z.prompt = ""; z.eingabebild = null; z.quelle = null; z.seed = "";
    ansicht("generator", z.ansicht === "generator" ? z.grafik : false); promptBearbeiten(true);
  };
  $("#bearbeiten").onclick = () => { if ($("#prompt").hidden) promptBearbeiten(true); else { z.prompt = $("#prompt").value.trim(); promptBearbeiten(false); } };
  $("#prompt-text").onclick = () => promptBearbeiten(true);
  $("#prompt").oninput = (e) => { z.prompt = e.target.value; uebersetzungAnzeigen(); };
  $("#prompt").onkeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); erzeugen(); }
    if (e.key === "Escape") { z.prompt = $("#prompt").value.trim(); promptBearbeiten(false); }
  };
  $("#datei").onchange = (e) => { dateiLesen(e.target.files[0]); e.target.value = ""; };
  $("#eingabe-weg").onclick = () => { z.eingabebild = null; z.quelle = null; promptZeichnen(); reglerZeichnen(); };
  for (const ziel of [$("#prompt-karte"), $("#buehne")]) {
    ziel.ondragover = (e) => { e.preventDefault(); $("#prompt-karte").classList.add("ziel"); };
    ziel.ondragleave = () => $("#prompt-karte").classList.remove("ziel");
    ziel.ondrop = (e) => { e.preventDefault(); $("#prompt-karte").classList.remove("ziel"); dateiLesen(e.dataTransfer.files[0]); };
  }
  const umschalten = (knopf, liste) => {
    $(knopf).onclick = (e) => { e.stopPropagation(); const l = $(liste); const war = l.hidden; $$(".auswahl-liste").forEach((x) => (x.hidden = true)); l.hidden = !war; };
  };
  umschalten("#modell-knopf", "#modell-liste"); umschalten("#stil-knopf", "#stil-liste");
  document.addEventListener("click", (e) => { if (!e.target.closest(".auswahl")) $$(".auswahl-liste").forEach((x) => (x.hidden = true)); });
  const regler = (id, schl) => ($(id).oninput = (e) => { z[schl] = Number(e.target.value); reglerZeichnen(); speichern(); });
  regler("#anzahl", "anzahl"); regler("#cfg", "cfg"); regler("#staerke", "staerke");
  $$("#qualitaet button").forEach((b) => (b.onclick = () => { z.qualitaet = b.dataset.wert; speichern(); generatorZeichnen(); }));
  $("#negativ").oninput = (e) => { z.negativ = e.target.value; speichern(); };
  $("#uebersetzen").onchange = (e) => { z.uebersetzen = e.target.checked; speichern(); };
  $("#freistellen").onchange = (e) => { z.freistellen = e.target.checked; speichern(); };
  $("#seed-aendern").onclick = () => {
    const inp = $("#seed");
    if (inp.hidden) { inp.hidden = false; inp.value = z.seed === "" ? (z.auswahl?.seed ?? "") : z.seed; inp.focus(); inp.select(); $("#seed-aendern").textContent = "Zufall"; $("#seed-wert").hidden = true; }
    else { z.seed = ""; seedZu(); }
  };
  const seedZu = () => { $("#seed").hidden = true; $("#seed-wert").hidden = false; $("#seed-aendern").textContent = "Ändern"; reglerZeichnen(); };
  $("#seed").onchange = (e) => { z.seed = e.target.value === "" ? "" : Math.max(0, Math.floor(Number(e.target.value))); seedZu(); };
  $("#seed").onkeydown = (e) => { if (e.key === "Enter") e.target.blur(); };
  $("#generieren").onclick = () => erzeugen();
  $("#abbrechen").onclick = () => api("/api/abbrechen", { method: "POST" }).catch(() => {});
  $$("#aktionen button, #werkzeuge button").forEach((b) => (b.onclick = () => aktion(b.dataset.aktion)));
  $$("[data-zoom]").forEach((b) => (b.onclick = () => zoomen(Number(b.dataset.zoom))));
  $("#vollbild").onclick = () => { if (z.auswahl) { $("#voll-bild").src = bildUrl(z.auswahl.name); $("#vollansicht").hidden = false; } };
  $("#vollansicht").onclick = () => ($("#vollansicht").hidden = true);
  const innen = $("#buehne-innen");
  innen.ondblclick = () => $("#vollbild").click();
  innen.onwheel = (e) => { if (!z.auswahl) return; e.preventDefault(); zoomen(e.deltaY < 0 ? 1 : -1); };
  let zug = null;
  innen.onmousedown = (e) => { if (z.zoom > 1) { zug = [e.clientX - z.verschiebung[0], e.clientY - z.verschiebung[1]]; innen.classList.add("zieht"); } };
  window.addEventListener("mousemove", (e) => { if (zug) { z.verschiebung = [e.clientX - zug[0], e.clientY - zug[1]]; zoomAnwenden(); } });
  window.addEventListener("mouseup", () => { zug = null; innen.classList.remove("zieht"); });
  $$("#filter button").forEach((b) => (b.onclick = () => { z.filter = b.dataset.wert; $$("#filter button").forEach((x) => x.classList.toggle("an", x === b)); rasterZeichnen(); }));
  $("#suche").oninput = (e) => { z.suche = e.target.value; rasterZeichnen(); };
  $("#ordner-oeffnen").onclick = () => api("/api/ordner-oeffnen", { body: {} });
  $("#sammlung-zurueck").onclick = () => { z.sammlungOffen = null; sammlungenZeichnen(); };
  $("#sammlung-neu").onclick = () => dialog(`<h2>Neue Sammlung</h2><input type="text" id="sn" placeholder="Name"><div class="knoepfe"><button class="klein-knopf" data-zu>Abbrechen</button><button class="los" id="sn-ok">Anlegen</button></div>`, (d) => {
    const inp = d.querySelector("#sn"); inp.focus();
    const ok = async () => { try { await sammlung("anlegen", inp.value, null); dialogZu(); sammlungenZeichnen(); } catch (e) { meldung(e.message); } };
    d.querySelector("#sn-ok").onclick = ok; inp.onkeydown = (e) => e.key === "Enter" && ok();
  });
  $("#sammlung-loeschen").onclick = async () => { await sammlung("loeschen", z.sammlungOffen, null); z.sammlungOffen = null; sammlungenZeichnen(); };
  $("#update-knopf").onclick = updateKlick;
  $("#einstellungen").onclick = einstellungenDialog;
  $("#hilfe").onclick = hilfeDialog;
  $("#dialog-hg").onclick = (e) => { if (e.target.id === "dialog-hg") dialogZu(); };
  document.addEventListener("keydown", (e) => {
    const tippt = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); erzeugen(); return; }
    if (e.key === "Escape") { $("#vollansicht").hidden = true; dialogZu(); }
    if (tippt || z.ansicht !== "generator" || !z.auswahl) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      const v = variantenVon(z.auswahl); const i = v.findIndex((x) => x.name === z.auswahl.name);
      const n = v[(i + (e.key === "ArrowRight" ? 1 : -1) + v.length) % v.length];
      if (n && n !== z.auswahl) { e.preventDefault(); auswaehlen(n); }
    }
  });
  if (host) host.addEventListener("message", (e) => hostNachricht(e.data));
}

async function start() {
  verbinden();
  try { z.info = await api("/api/info"); } catch { setTimeout(start, 1000); return; }
  const u = z.info.einstellungen?.ui || {};
  Object.assign(z, Object.fromEntries(Object.entries(u).filter(([k, v]) => v !== undefined && k in z)));
  if (!modellInfo(z.modell)) {
    const inst = z.info.modelle.find((m) => m.installiert);
    z.modell = inst ? inst.id : z.info.standard_modell;
  }
  $("#version").textContent = "v" + z.info.version;
  $("#avatar").firstChild.textContent = (z.info.benutzer || "L").charAt(0).toUpperCase();
  $("#exporte").innerHTML = z.info.exporte.map((x) => `<button data-export="${x.id}" title="${x.groessen.join(" / ")} px">${esc(x.name)}</button>`).join("");
  $$("[data-export]").forEach((b) => (b.onclick = () => exportieren(b.dataset.export)));
  await galerieLaden(true);
  ansicht("generator", false);
  await aktualisieren();
  willkommen();
  if (host) host.postMessage({ typ: "bereit" });
  setInterval(() => api("/api/herzschlag", { method: "POST" }).catch(() => {}), 30000);
}
start();
