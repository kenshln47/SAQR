"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(`saqr.${k}`)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(`saqr.${k}`, JSON.stringify(v)); } catch { /* private window */ } },
};
const RUNNING = ["queued", "recon", "analysing"];
const okLL = (lat, lon) => lat !== null && lon !== null && lat !== "" && lon !== "" &&
  Number.isFinite(+lat) && Number.isFinite(+lon) && Math.abs(+lat) <= 90;
const wrapLon = (lon) => ((((+lon + 180) % 360) + 360) % 360) - 180;

// ---------------------------------------------------------------- icons
const S = (p) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
const ICON = {
  logo: S('<path d="M12 2.5 21.5 12 12 21.5 2.5 12z"/><path d="M6.6 12c1.6-2.3 3.4-3.5 5.4-3.5s3.8 1.2 5.4 3.5c-1.6 2.3-3.4 3.5-5.4 3.5S8.2 14.3 6.6 12z"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/>'),
  folder: S('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
  search: S('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  clock: S('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  help: S('<circle cx="12" cy="12" r="9"/><path d="M9.6 9.2a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5M12 16.8h.01"/>'),
  panel: S('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>'),
  globe: S('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'),
  filter: S('<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>'),
  layers: S('<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>'),
  cube: S('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>'),
  board: S('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
  intel: S('<path d="M13 2 4.5 14H11l-1 8 8.5-12H12z"/>'),
  note: S('<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>'),
  x: S('<path d="M6 6l12 12M18 6 6 18"/>'),
  plus: S('<path d="M12 5v14M5 12h14"/>'),
  minus: S('<path d="M5 12h14"/>'),
  cursor: S('<path d="m5 4 6.5 16 2.3-6.7L20.5 11z"/>'),
  pin: S('<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>'),
  measure: S('<circle cx="5" cy="12" r="2.2"/><circle cx="19" cy="12" r="2.2"/><path d="M7.2 12h9.6"/>'),
  trash: S('<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>'),
  compass: '<svg viewBox="0 0 24 24"><path d="M12 2.5 16 12h-8z" fill="#ff453a"/><path d="M12 21.5 8 12h8z" fill="#8e8e93"/></svg>',
  map: S('<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>'),
  eye: S('<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
  eyeOff: S('<path d="M3 3l18 18M10.6 5.1Q11.3 5 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6C3.8 8.4 2 12 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6M9.9 9.9a3 3 0 0 0 4.2 4.2"/>'),
  chev: S('<path d="m6 9 6 6 6-6"/>'),
  shield: S('<path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z"/><path d="m9 12 2 2 4-4"/>'),
  car: S('<path d="M4 15.5V12l2-5h12l2 5v3.5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/><path d="M4 12h16M6.5 16.5V19M17.5 16.5V19"/><circle cx="8" cy="14.2" r=".6" fill="currentColor"/><circle cx="16" cy="14.2" r=".6" fill="currentColor"/>'),
  home: S('<path d="M4 11 12 4l8 7v9H4z"/><path d="M9.5 20v-6h5v6"/>'),
  user: S('<circle cx="12" cy="8" r="4"/><path d="M4.5 20c1.6-3.6 4.3-5.4 7.5-5.4s5.9 1.8 7.5 5.4"/>'),
  camera: S('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>'),
  upload: S('<path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>'),
  copy: S('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>'),
  ext: S('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
  target: S('<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>'),
  check: S('<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>'),
  ring: S('<circle cx="12" cy="12" r="8"/>'),
  stop: S('<rect x="6.5" y="6.5" width="11" height="11" rx="1.5"/>'),
  redo: S('<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v5h-5"/>'),
  gear: S('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
};
function icons(root = document) {
  $$("[data-i]", root).forEach((el) => {
    if (el.dataset.done) return;
    el.insertAdjacentHTML("afterbegin", ICON[el.dataset.i] || "");
    el.dataset.done = "1";
  });
}

// ---------------------------------------------------------------- vocabulary
const MODE_LABEL = { region: "تحديد المنطقة", street: "تحديد الشارع", private: "تحديد مكان خاص",
  verify: "التحقق من الصورة", car: "هوية السيارة", person: "من هذا الشخص؟", plate: "لوحة السيارة" };
const GROUPS = [
  { key: "geo", title: "تحديد الموقع", icon: "globe", modes: ["region", "street", "private"] },
  { key: "person", title: "الأشخاص", icon: "user", modes: ["person"] },
  { key: "plate", title: "اللوحات", icon: "car", modes: ["plate"] },
  { key: "verify", title: "التحقق من الصور", icon: "shield", modes: ["verify"] },
  { key: "car", title: "هوية السيارة", icon: "car", modes: ["car"] },
];
const PIN_KIND = { place: { label: "مكان", icon: "pin" }, camera: { label: "نقطة تصوير", icon: "camera" }, note: { label: "ملاحظة", icon: "note" } };
const CONF_AR = { high: "ثقة عالية", medium: "ثقة متوسطة", low: "ثقة ضعيفة" };
const CONF_POP = { high: "مؤكد", medium: "مرجّح", low: "تقريبي" };
const LEVEL_AR = { country: "مستوى الدولة", region: "مستوى المنطقة", city: "مستوى المدينة", street: "مستوى الشارع", point: "نقطة الكاميرا" };
const ASSESS_AR = { likely_genuine: "غالباً أصلية", possibly_manipulated: "ممكن معدلة", likely_manipulated: "غالباً معدلة",
  possibly_ai_generated: "ممكن مولدة بالذكاء الاصطناعي", likely_ai_generated: "غالباً مولدة بالذكاء الاصطناعي", inconclusive: "غير حاسم" };
const STATUS_AR = { queued: "بالانتظار", recon: "فحص أولي", analysing: "يحلل", done: "خلص", stopped: "انوقف", error: "خطأ" };
const TOOL_AR = { view_photo: "فحص الصورة", streetview_near: "Street View · أقرب بانوراما", streetview_views: "Street View · عرض",
  streetview_sweep: "Street View · مسح المنطقة", satellite: "قمر صناعي", terrain_view: "مقارنة التضاريس", geocode: "بحث عن مكان",
  osm_query: "OpenStreetMap", pin_candidate: "تثبيت مرشح", final_answer: "الإجابة النهائية", web_search: "بحث ويب",
  listing_search: "بحث في الإعلانات", web_lookup: "بحث ويب (بدون مفتاح)", gravatar_lookup: "Gravatar",
  file_person: "الجواب النهائي", file_plate: "الجواب النهائي" };
const COLOR = { high: "#30d158", medium: "#ff9f0a", low: "#8e8e93", cand: "#ff9f0a", model: "#8e8e93" };
const cls = (v) => String(v ?? "").replace(/[^a-z_]/gi, "");   // model text used as a class name

const state = {
  mode: "region", file: null, blob: null, uploading: false, cases: [], sig: "", active: null, es: null, openTok: 0,
  hidden: new Set(store.get("hidden", [])), filters: { geo: true, person: true, plate: true, verify: true, car: true, pins: true, ...store.get("filters", {}) },
  closed: new Set(store.get("closed", [])),
  board: { pins: [], notes: "" }, boardLoaded: false, savePending: false,
  tool: "select", lines: [], drawing: false,
  caseMarkers: [], activeMarkers: [], pinMarkers: [], measureMarkers: [], tempMarker: null,
  cands: [], final: null, feedN: 0, evN: 0, stage: "recon", sideOpen: true, replaying: false,
  show3d: store.get("3d", true), showRadius: true, base: store.get("base", "dark"), tilt: true,
};

let toastT;
function toast(msg, kind = "") {
  const t = $("#toast");
  t.textContent = msg; t.className = `toast ${kind}`;
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.add("hidden"), 4200);
}

// ---------------------------------------------------------------- map
// joins and orders Arabic letters in map labels; without it they draw unjoined and left-to-right
maplibregl.setRTLTextPlugin(new URL("vendor/mapbox-gl-rtl-text.js", location.href).href, false)?.catch?.(() => {});
const map = new maplibregl.Map({
  container: "map", style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  center: [30, 24], zoom: 1.7, maxPitch: 75, attributionControl: { compact: true }, dragRotate: true,
});
let ready = false;
new ResizeObserver(() => map.resize()).observe(document.body);
// a zoom "step" must stay the top-level expression, so the Arabic name goes into each of its outputs
const arabicFirst = (tf) => (tf[0] === "step" && Array.isArray(tf[1]) && tf[1][0] === "zoom"
  ? tf.map((v, i) => (i >= 2 && i % 2 === 0 ? ["coalesce", ["get", "name:ar"], v] : v))
  : ["coalesce", ["get", "name:ar"], tf]);
map.on("error", () => {
  if (ready) return;   // a missing tile later is normal; only a style that never loads needs a word
  $("#mapErr").textContent = "الخريطة ما تحملت: تحتاج إنترنت (CARTO و Esri). باقي صقر يشتغل عادي.";
  $("#mapErr").classList.remove("hidden");
});
map.on("load", () => {
  map.resize();
  $("#mapErr").classList.add("hidden");
  const layers = map.getStyle().layers;
  const firstSym = layers.find((l) => l.type === "symbol")?.id;
  map.addSource("sat", { type: "raster", tileSize: 256, maxzoom: 19, attribution: "Esri, Maxar, Earthstar Geographics",
    tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"] });
  map.addLayer({ id: "sat", type: "raster", source: "sat", layout: { visibility: "none" }, paint: { "raster-brightness-max": 0.85 } }, firstSym);
  const b = layers.find((l) => l["source-layer"] === "buildings" || l["source-layer"] === "building");
  state.flatBuildings = layers.filter((l) => l["source-layer"] === b?.["source-layer"] && l.type === "fill").map((l) => l.id);
  if (b) {
    map.addLayer({ id: "bld3d", type: "fill-extrusion", source: b.source, "source-layer": b["source-layer"], minzoom: 13,
      paint: {
        "fill-extrusion-color": ["interpolate", ["linear"], ["coalesce", ["get", "height"], 8], 0, "#2a2b2f", 40, "#34353a", 150, "#414247"],
        "fill-extrusion-height": ["interpolate", ["linear"], ["zoom"], 13, 0, 14.5,
          ["coalesce", ["get", "height"], ["*", ["coalesce", ["get", "building:levels"], 3], 3.4]]],
        "fill-extrusion-base": ["coalesce", ["get", "min_height"], 0],
        "fill-extrusion-opacity": 0.92,
      } }, firstSym);
  }
  map.addSource("radii", { type: "geojson", data: fc([]) });
  map.addLayer({ id: "radii-fill", type: "fill", source: "radii", paint: { "fill-color": ["get", "color"], "fill-opacity": 0.07 } });
  map.addLayer({ id: "radii-line", type: "line", source: "radii",
    paint: { "line-color": ["get", "color"], "line-width": 1.3, "line-opacity": 0.85, "line-dasharray": [3, 2] } });
  map.addSource("measure", { type: "geojson", data: fc([]) });
  map.addLayer({ id: "measure-line", type: "line", source: "measure",
    paint: { "line-color": "#0a84ff", "line-width": 2.5, "line-opacity": 0.95, "line-dasharray": [2, 1.2] } });
  for (const l of layers) {          // lift Dark Matter to neutral graphite land and deep blue water, so the map never reads as a black screen
    try {
      if (l.type === "background") map.setPaintProperty(l.id, "background-color", "#1d1e21");
      else if (l.type === "fill" && /water/.test(l.id)) map.setPaintProperty(l.id, "fill-color", "#0e1924");
      else if (l.type === "line" && /boundar|admin/.test(l.id)) map.setPaintProperty(l.id, "line-color", "#55565c");
      // Arabic place names first, the style's own (local / English) name where OSM has no Arabic one
      if (l.type === "symbol" && Array.isArray(l.layout?.["text-field"])) map.setLayoutProperty(l.id, "text-field", arabicFirst(l.layout["text-field"]));
    } catch { /* layer uses an expression we leave alone */ }
  }
  ready = true;
  applyLayers();
  renderRadii();
  renderMeasure();
});
map.on("mousemove", (e) => { $("#coordbar").textContent = `${e.lngLat.lat.toFixed(5)}, ${e.lngLat.wrap().lng.toFixed(5)}  ·  z${map.getZoom().toFixed(1)}`; });
map.on("rotate", () => { $("#compass svg").style.transform = `rotate(${-map.getBearing()}deg)`; });
map.on("pitchend", () => { $("#tiltLabel").textContent = map.getPitch() > 5 ? "منظور علوي" : "ثلاثي الأبعاد"; });
map.on("click", (e) => {
  if (state.tool === "pin") { const ll = e.lngLat.wrap(); addPin(ll.lat, ll.lng); }
  else if (state.tool === "measure") {
    if (!state.drawing) { state.lines.push([]); state.drawing = true; }
    state.lines[state.lines.length - 1].push([e.lngLat.lng, e.lngLat.lat]);
    renderMeasure();
  }
});

const fc = (features) => ({ type: "FeatureCollection", features });
function circle(lat, lon, km, color) {
  const pts = [], R = 6371, d = km / R, la = (lat * Math.PI) / 180, lo = (lon * Math.PI) / 180;
  for (let i = 0; i <= 72; i++) {
    const b = (i / 72) * 2 * Math.PI;
    const la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(b));
    const lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2));
    pts.push([(lo2 * 180) / Math.PI, (la2 * 180) / Math.PI]);
  }
  return { type: "Feature", properties: { color }, geometry: { type: "Polygon", coordinates: [pts] } };
}
function km(a, b) {
  const r = Math.PI / 180, dLa = (b[1] - a[1]) * r, dLo = (b[0] - a[0]) * r;
  const h = Math.sin(dLa / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dLo / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}
const fmtKm = (k) => (k < 1 ? `${Math.round(k * 1000)} م` : `${k.toFixed(k < 10 ? 2 : 1)} كم`);
function zoomFor(r) {
  r = +r || 50;
  for (const [lim, z] of [[0.15, 17], [0.5, 15.6], [1, 14.6], [3, 13], [10, 11.2], [30, 9.6], [100, 8], [300, 6.3]]) if (r <= lim) return z;
  return 4.6;
}
const shown = (el) => !el.classList.contains("hidden") && getComputedStyle(el).display !== "none";
function pad() {
  if (innerWidth <= 860) {   // phones: the open sheet covers the lower half, so centre the target above it
    const h = Math.max(0, ...$$(".panel").filter(shown).map((p) => p.getBoundingClientRect().height));
    return { top: 64, bottom: Math.min(h + 80, innerHeight - 170), left: 20, right: 20 };
  }
  const side = state.sideOpen && shown($("#sidePanel")) ? innerWidth - $("#sidePanel").getBoundingClientRect().left + 12 : 72;
  const intel = shown($("#intel")) ? $("#intel").getBoundingClientRect().right + 12 : 60;
  return { top: 70, bottom: 30, right: side, left: intel };
}
function flyTo(lat, lon, r) {
  if (!okLL(lat, lon)) return;
  const z = zoomFor(r), deep = z >= 12.5 && state.tilt;
  map.flyTo({ center: [+lon, +lat], zoom: z, pitch: deep ? 58 : 0, bearing: deep ? -20 : 0, padding: pad(), duration: 1900, essential: true });
}

function applyLayers() {
  if (!ready) return;
  const sat = state.base === "sat";
  map.setLayoutProperty("sat", "visibility", sat ? "visible" : "none");
  if (map.getLayer("bld3d")) map.setLayoutProperty("bld3d", "visibility", state.show3d && !sat ? "visible" : "none");
  (state.flatBuildings || []).forEach((id) => map.setLayoutProperty(id, "visibility", state.show3d || sat ? "none" : "visible"));
  const labels = $("#lLabels").checked;
  map.getStyle().layers.filter((l) => l.type === "symbol").forEach((l) => map.setLayoutProperty(l.id, "visibility", labels ? "visible" : "none"));
  ["radii-fill", "radii-line"].forEach((id) => map.setLayoutProperty(id, "visibility", state.showRadius ? "visible" : "none"));
  $(`input[name=base][value=${state.base}]`).checked = true;
  $("#l3d").checked = state.show3d;
  $("#baseToggle").classList.toggle("on", sat);
}

// ---------------------------------------------------------------- markers
function mkEl(klass, inner, label) {
  const d = document.createElement("div");
  d.className = `mk ${klass}`;
  d.innerHTML = `<div class="halo"></div><div class="core">${inner}</div>`;
  if (label) d.title = label;
  return d;
}
function marker(el, lat, lon, html) {
  const m = new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat([+lon, +lat]);
  if (html) m.setPopup(new maplibregl.Popup({ offset: 20, closeButton: false, maxWidth: "300px", className: "hud-pop" }).setHTML(html));
  return m.addTo(map);
}
const clear = (arr) => { arr.forEach((m) => m.remove()); arr.length = 0; };
function closePopups() {   // through the API: removing the DOM would leave MapLibre thinking they are still open
  [...state.caseMarkers, ...state.activeMarkers, ...state.pinMarkers].forEach((m) => { const p = m.getPopup(); if (p?.isOpen()) p.remove(); });
}

function geoCases() {
  return state.cases.filter((c) => ["region", "street", "private"].includes(c.mode)).slice().sort((a, b) => (a.created < b.created ? -1 : 1));
}
const caseNo = (id) => geoCases().findIndex((c) => c.id === id) + 1;

function renderCaseMarkers() {
  clear(state.caseMarkers);
  if (!state.filters.geo) return;
  geoCases().forEach((c, i) => {
    const f = c.final;
    if (!f || !okLL(f.lat, f.lon) || state.hidden.has(c.id)) return;
    const place = [f.country, f.region, f.city].filter(Boolean).join(" · ");
    const el = mkEl(`final ${cls(f.confidence) || "low"} ${state.active && state.active !== c.id ? "dimmed" : ""}`, i + 1, place);
    el.addEventListener("click", () => { if (state.active !== c.id) openCase(c.id); });
    state.caseMarkers.push(marker(el, f.lat, f.lon, `<div class="pop" dir="rtl"><b>${esc(place)}</b>
      <div class="c">${(+f.lat).toFixed(5)}, ${(+f.lon).toFixed(5)}</div>
      <div class="st ${cls(f.confidence)}"><i></i>${esc(CONF_POP[f.confidence] || "")} · ± ${esc(f.radius_km)} كم · ${esc(LEVEL_AR[f.level] || "")}</div>
      <div class="why">${esc(c.filename)}</div></div>`));
  });
}

function renderActiveMarkers() {
  clear(state.activeMarkers);
  state.cands.filter((c) => okLL(c.lat, c.lon)).forEach((c) => {
    const model = c.source === "model";
    const el = mkEl(model ? "cand model" : "cand", model ? ICON.ring : esc(c.n), c.label);
    state.activeMarkers.push(marker(el, c.lat, c.lon, `<div class="pop" dir="rtl"><b>${esc(c.label)}</b>
      <div class="c">${(+c.lat).toFixed(5)}, ${(+c.lon).toFixed(5)}</div>
      <div class="st ${model ? "low" : "medium"}"><i></i>${model ? "تخمين نماذج محلية" : "مرشح"} · ${Math.round((+c.confidence || 0) * 100)}% · ± ${esc(c.radius_km)} كم</div>
      <div class="why">${esc(c.reason)}</div></div>`));
  });
  renderRadii();
}

function renderRadii() {
  if (!ready) return;
  const feats = state.cands.filter((c) => okLL(c.lat, c.lon))
    .map((c) => circle(+c.lat, +c.lon, Math.max(+c.radius_km || 1, 0.02), c.source === "model" ? COLOR.model : COLOR.cand));
  const f = state.final;
  if (f && okLL(f.lat, f.lon)) feats.push(circle(+f.lat, +f.lon, Math.max(+f.radius_km || 1, 0.02), COLOR[f.confidence] || COLOR.low));
  map.getSource("radii").setData(fc(feats));
}

// ---------------------------------------------------------------- user pins + measure
function renderPins() {
  clear(state.pinMarkers);
  if (!state.filters.pins) return;
  state.board.pins.forEach((p) => {
    const k = PIN_KIND[p.kind] || PIN_KIND.place;
    const el = mkEl(`u-${cls(p.kind)}`, ICON[k.icon], p.label);
    const m = marker(el, p.lat, p.lon, " ");
    m.getPopup().on("open", () => fillPinPopup(m.getPopup(), p));
    p._m = m;
    state.pinMarkers.push(m);
  });
}
function fillPinPopup(pop, p) {
  pop.setHTML(`<div class="pop" dir="rtl"><b>دبوس</b><div class="c">${(+p.lat).toFixed(5)}, ${(+p.lon).toFixed(5)}</div>
    <input value="${esc(p.label)}" maxlength="120">
    <div class="kinds">${Object.entries(PIN_KIND).map(([k, v]) => `<button data-k="${k}" class="${k === p.kind ? "on" : ""}">${v.label}</button>`).join("")}</div>
    <div class="row"><button class="save">حفظ</button><button class="del">حذف</button></div></div>`);
  const root = pop.getElement();
  let kind = p.kind;
  $$(".kinds button", root).forEach((b) => (b.onclick = () => { kind = b.dataset.k; $$(".kinds button", root).forEach((x) => x.classList.toggle("on", x === b)); }));
  const inp = $("input", root);
  inp.focus(); inp.select();
  const save = () => { p.label = inp.value.trim() || p.label; p.kind = kind; pop.remove(); saveBoard(); renderPins(); renderSources(); };
  inp.onkeydown = (e) => { if (e.key === "Enter") save(); };
  $(".save", root).onclick = save;
  $(".del", root).onclick = () => { state.board.pins = state.board.pins.filter((x) => x !== p); pop.remove(); saveBoard(); renderPins(); renderSources(); };
}
function addPin(lat, lon) {
  const p = { id: Date.now().toString(36), lat, lon: wrapLon(lon), label: `دبوس ${state.board.pins.length + 1}`, kind: "place", created: new Date().toISOString() };
  state.board.pins.push(p);
  saveBoard(); renderPins(); renderSources();
  setTool("select");
  p._m?.togglePopup();
}
let saveT;
function saveBoard() {
  clearTimeout(saveT);
  if (!state.boardLoaded) { $("#notesState").textContent = "ما انحفظ: اللوحة ما تحملت من الخادم"; return; }
  state.savePending = true;
  $("#notesState").textContent = "…";
  saveT = setTimeout(async () => {
    const body = { notes: state.board.notes, pins: state.board.pins.map(({ _m, ...p }) => p) };
    try {
      const r = await fetch("/api/board", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const saved = r.ok ? await r.json() : null;
      $("#notesState").textContent = !saved ? "ما انحفظ" : saved.notes.length < body.notes.length ? "انحفظ بس انقص: الحد 20000 حرف" : "محفوظ";
    } catch { $("#notesState").textContent = "ما انحفظ: صقر مو شغال؟"; }
    state.savePending = false;
  }, 400);
}
async function loadBoard() {
  try {
    const r = await fetch("/api/board");
    if (!r.ok) throw new Error(r.status);
    const b = await r.json();
    state.board.pins.forEach((p) => p._m?.remove());
    state.board = { pins: (b.pins || []).filter((p) => okLL(p.lat, p.lon)), notes: b.notes || "" };
    state.boardLoaded = true;
    if (document.activeElement !== $("#notes")) $("#notes").value = state.board.notes;
    if (b.recovered) toast(`ملف اللوحة كان خربان: انحفظت نسخة منه في ${b.recovered} وبدأت لوحة جديدة`, "warn");
    renderPins(); renderSources();
  } catch {
    if (!state.boardLoaded) $("#notesState").textContent = "ما قدرت أقرا اللوحة: التعديلات ما بتنحفظ لين يرجع الخادم";
  }
}

function renderMeasure() {
  clear(state.measureMarkers);
  const lines = state.lines.filter((l) => l.length);
  if (ready) map.getSource("measure").setData(fc(lines.filter((l) => l.length > 1)
    .map((l) => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: l } }))));
  lines.forEach((pts) => {
    let total = 0;
    pts.forEach((p, i) => {
      const d = document.createElement("div"); d.className = "mdot";
      state.measureMarkers.push(new maplibregl.Marker({ element: d }).setLngLat(p).addTo(map));
      if (i) {
        const seg = km(pts[i - 1], p); total += seg;
        const l = document.createElement("div"); l.className = "mlabel"; l.textContent = fmtKm(seg);
        state.measureMarkers.push(new maplibregl.Marker({ element: l }).setLngLat([(pts[i - 1][0] + p[0]) / 2, (pts[i - 1][1] + p[1]) / 2]).addTo(map));
      }
    });
    if (pts.length > 2) {
      const l = document.createElement("div"); l.className = "mlabel total"; l.textContent = `المجموع ${fmtKm(total)}`;
      state.measureMarkers.push(new maplibregl.Marker({ element: l, offset: [0, -20] }).setLngLat(pts[pts.length - 1]).addTo(map));
    }
  });
}
function endLine() {   // a new click with the measure tool starts a separate line instead of extending the old one
  state.drawing = false;
  state.lines = state.lines.filter((l) => l.length > 1);
  renderMeasure();
}

function setTool(t) {
  if (t !== "measure" || state.tool !== "measure") endLine();
  state.tool = t;
  $$(".tl[data-tool]").forEach((b) => b.classList.toggle("active", b.dataset.tool === t));
  document.body.classList.toggle("measuring", t === "measure");
  document.body.classList.toggle("pinning", t === "pin");
  const hint = { pin: "اضغط على الخريطة عشان تحط دبوس", measure: "اضغط نقاط على الخريطة لقياس المسافة · Esc للإنهاء" }[t];
  $("#hint").textContent = hint || "";
  $("#hint").classList.toggle("hidden", !hint);
}

// ---------------------------------------------------------------- sources panel
function caseSummary(c) {
  const f = c.final;
  if (c.status === "error") return { text: c.error ? `خطأ: ${c.error}` : "صار خطأ", cls: "r" };
  if (RUNNING.includes(c.status)) return { text: `${STATUS_AR[c.status] || c.status}…`, cls: "run" };
  if (!f) return { text: c.status === "stopped" ? "انوقف قبل الجواب" : "ما طلع جواب", cls: "" };
  if ("found" in f) return { text: f.found ? `${f.name || "شخص"}${f.role ? " · " + f.role : ""}` : "ما تحدد شخص", cls: f.found ? (f.confidence === "high" ? "g" : "a") : "r" };
  if (f.plate) return { text: `${f.plate}${f.vehicle ? " · " + f.vehicle : ""}`, cls: "a" };
  if (f.country) return { text: [f.country, f.region, f.city].filter(Boolean).join(" · "), cls: { high: "g", medium: "a" }[f.confidence] || "r" };
  if (f.assessment) return { text: ASSESS_AR[f.assessment] || f.assessment, cls: f.assessment === "likely_genuine" ? "g" : f.assessment === "inconclusive" ? "" : "a" };
  if (f.make) return { text: `${f.make} ${f.model} ${f.year_range || ""}`, cls: (+f.confidence || 0) >= 0.7 ? "g" : "a" };
  return { text: "—", cls: "" };
}
function srcItem(c) {
  const s = caseSummary(c), f = c.final || {}, n = caseNo(c.id), geo = okLL(f.lat, f.lon);
  const cands = (c.candidates || []).filter((x) => x.source !== "model").length;
  const stats = [
    s.cls === "run" ? `<span><i class="spin"></i>${esc(STATUS_AR[c.status] || c.status)}</span>` : "",
    f.confidence && f.country ? `<span class="${s.cls}">${ICON.check}${esc(CONF_POP[f.confidence])}</span>` : "",
    f.radius_km ? `<span>± ${esc(f.radius_km)} كم</span>` : "",
    cands ? `<span class="a">${ICON.target}${cands}</span>` : "",
    n && geo ? `<span>#${n}</span>` : "",
    c.rerun_of ? `<span title="إعادة تحليل">${ICON.redo}</span>` : "",
  ].join("");
  const off = state.hidden.has(c.id);
  return `<div class="src ${state.active === c.id ? "active" : ""} ${off ? "off" : ""}" data-id="${esc(c.id)}">
    <img src="/api/cases/${esc(c.id)}/photo" loading="lazy" alt="">
    <div class="t"><b>${esc(c.filename)}</b><small class="${s.cls === "r" ? "r" : ""}">${esc(s.text)}</small><div class="stats">${stats}</div></div>
    <div class="acts">${geo ? `<button data-eye title="${off ? "إظهار" : "إخفاء"} على الخريطة">${off ? ICON.eyeOff : ICON.eye}</button>` : ""}
      ${s.cls !== "run" ? `<button data-del title="حذف المصدر (ينتقل لمجلد _saqr_trash)">${ICON.trash}</button>` : ""}</div></div>`;
}
function renderSources() {
  const q = $("#srcSearch").value.trim().toLowerCase();
  const match = (c) => !q || `${c.filename} ${caseSummary(c).text}`.toLowerCase().includes(q);
  let total = 0, html = "";
  for (const g of GROUPS) {
    if (!state.filters[g.key]) continue;
    const items = state.cases.filter((c) => g.modes.includes(c.mode) && match(c));
    if (!items.length) continue;
    total += items.length;
    html += `<div class="group ${state.closed.has(g.key) ? "closed" : ""}" data-g="${g.key}">
      <button class="ghead"><span class="ico">${ICON[g.icon]}</span>${g.title} <span class="n">(${items.length})</span><span class="chev">${ICON.chev}</span></button>
      <div class="items">${items.map(srcItem).join("")}</div></div>`;
  }
  const pins = state.filters.pins ? state.board.pins.filter((p) => !q || p.label.toLowerCase().includes(q)) : [];
  if (pins.length) {
    total += pins.length;
    html += `<div class="group ${state.closed.has("pins") ? "closed" : ""}" data-g="pins">
      <button class="ghead"><span class="ico">${ICON.pin}</span>دبابيس المستخدم <span class="n">(${pins.length})</span><span class="chev">${ICON.chev}</span></button>
      <div class="items">${pins.map((p) => {
        const k = PIN_KIND[p.kind] || PIN_KIND.place;
        return `<div class="src upin" data-pin="${esc(p.id)}"><div class="dot mk u-${cls(p.kind)}"><div class="core">${ICON[k.icon]}</div></div>
          <div class="t"><b>${esc(p.label)}</b><small>${(+p.lat).toFixed(4)}, ${(+p.lon).toFixed(4)}</small></div><div class="acts"></div></div>`;
      }).join("")}</div></div>`;
  }
  $("#groups").innerHTML = html || `<p class="dim empty">ما فيه مصادر للحين. أضف صورة عشان تبدأ.</p>`;
  $("#srcCount").textContent = `${total} مصادر`;
  $("#caseCount").textContent = `· ${state.cases.length}`;
  $$(".ghead").forEach((h) => (h.onclick = () => {
    const g = h.parentElement.dataset.g;
    state.closed.has(g) ? state.closed.delete(g) : state.closed.add(g);
    store.set("closed", [...state.closed]); h.parentElement.classList.toggle("closed");
  }));
  $$(".src[data-id]").forEach((el) => (el.onclick = (e) => {
    const id = el.dataset.id;
    if (e.target.closest("[data-eye]")) {
      state.hidden.has(id) ? state.hidden.delete(id) : state.hidden.add(id);
      store.set("hidden", [...state.hidden]); renderSources(); renderCaseMarkers(); return;
    }
    const del = e.target.closest("[data-del]");
    if (del) {
      if (!del.classList.contains("armed")) {   // two clicks, like "delete all pins"
        del.classList.add("armed"); del.title = "اضغط مرة ثانية للتأكيد";
        setTimeout(() => { del.classList.remove("armed"); del.title = "حذف المصدر"; }, 3500);
        return;
      }
      deleteCase(id); return;
    }
    openCase(id);
  }));
  $$(".src[data-pin]").forEach((el) => (el.onclick = () => {
    const p = state.board.pins.find((x) => x.id === el.dataset.pin);
    if (!p) return;
    map.flyTo({ center: [p.lon, p.lat], zoom: Math.max(map.getZoom(), 14), padding: pad() });
    if (p._m && !p._m.getPopup().isOpen()) p._m.togglePopup();
  }));
  renderActivity();
}
async function deleteCase(id) {
  try {
    const r = await fetch(`/api/cases/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "ما انحذف");
  } catch (e) { toast(e instanceof TypeError ? "ما قدرت أوصل لصقر" : e.message, "err"); return; }
  if (state.active === id) closeIntel();
  state.cases = state.cases.filter((c) => c.id !== id);
  state.sig = "";
  renderSources(); renderCaseMarkers(); renderWelcome();
  toast("انتقل المصدر لمجلد _saqr_trash");
}
function renderActivity() {
  const rows = state.cases.slice().sort((a, b) => (a.updated < b.updated ? 1 : -1)).slice(0, 60);
  $("#activity").innerHTML = rows.map((c) => {
    const s = caseSummary(c);
    return `<div class="act" data-id="${esc(c.id)}"><i class="${s.cls === "run" ? "a" : s.cls}"></i><div>
      <b>${esc(MODE_LABEL[c.mode])}</b> · ${esc(s.text)}<small>${esc(c.filename)} · ${esc((c.updated || "").slice(0, 16).replace("T", " "))}</small></div></div>`;
  }).join("") || `<p class="dim">ما فيه نشاط.</p>`;
  $$(".act").forEach((a) => (a.onclick = () => openCase(a.dataset.id)));
}

function showSide(tab) {
  state.sideOpen = true;
  document.body.classList.add("side-open");
  if (innerWidth <= 860) document.body.classList.add("side-front");   // phones: one sheet at a time, this one on top
  $("#sidePanel").classList.remove("hidden");
  $$(".pt").forEach((b) => b.classList.toggle("active", b.dataset.pt === tab));
  $$(".pbody").forEach((b) => b.classList.toggle("hidden", b.dataset.pb !== tab));
  $$(".ri[data-panel]").forEach((b) => b.classList.toggle("active", b.dataset.panel === tab || (tab === "notes" && b.dataset.panel === "sources")));
  if (tab === "search") $("#placeSearch").focus();
}
function hideSide() {
  state.sideOpen = false;
  document.body.classList.remove("side-open", "side-front");
  $("#sidePanel").classList.add("hidden");
  $$(".ri[data-panel]").forEach((b) => b.classList.remove("active"));
}

async function refreshCases(force = false) {
  let cs;
  try { const r = await fetch("/api/cases"); if (!r.ok) return; cs = await r.json(); } catch { return; }
  const sig = JSON.stringify(cs.map((c) => [c.id, c.status, c.updated, !!c.final, (c.candidates || []).length]));
  state.cases = cs;
  syncActive();
  if (!force && sig === state.sig) return;   // nothing changed: keep open popups and armed delete buttons
  state.sig = sig;
  renderSources();
  renderCaseMarkers();
  renderWelcome();
}
function syncActive() {
  const c = state.cases.find((x) => x.id === state.active);
  if (!c) return;
  const run = RUNNING.includes(c.status);
  $("#iStop").classList.toggle("hidden", !run || !!c.cancel);
  $("#iRerun").classList.toggle("hidden", run);
}

function renderWelcome() {
  const w = $("#welcome");
  w.classList.toggle("hidden", !!state.active);
  w.classList.toggle("compact", state.cases.length > 0);
}

// ---------------------------------------------------------------- settings
const PROV_NAME = { openrouter: "OpenRouter", anthropic: "Anthropic" };
const ai = { status: {}, prov: "openrouter", model: "", models: null };

function updateEngine(s) {
  ai.status = s;
  state.claude = s.ready;
  if (!ai.model) ai.model = s.or_model || "";
  const short = (s.model || "").split("/").pop();
  $("#engine span").textContent = s.ready ? `${PROV_NAME[s.provider]} · ${short}` : "بدون ذكاء اصطناعي · أضف مفتاح API";
  $("#engine").classList.toggle("off", !s.ready);
  $("#engineDot").textContent = s.ready ? "AI" : "LO";
  $("#engineDot").classList.toggle("on", s.ready);
  $("#engineDot").title = s.ready ? `${s.label} شغال` : "النماذج المحلية بس";
  $("#keyState").className = `keystate ${s.ready ? "on" : ""}`;
  $("#keyState").innerHTML = s.ready
    ? `<i></i><span>شغال عبر ${PROV_NAME[s.provider]} · <span class="mono">${esc(s.model)}</span> · المفتاح ينتهي بـ <span class="mono">${esc(s.key_hint || "")}</span></span>`
    : `<i></i><span>ما فيه مفتاح: صقر يشتغل بالنماذج المحلية بس</span>`;
  $("#wkey").className = `wkey ${s.ready ? "on" : ""}`;
  $("#wkey").innerHTML = s.ready
    ? `<i></i>التحليل الكامل شغال (${esc(short)})`
    : `<i></i>وضع بدون ذكاء اصطناعي: نتائج تقريبية بس <button class="link" data-open-settings>أضف مفتاح API للتحليل الكامل</button>`;
  setProv(s.provider || ai.prov);
  $$("#wkey [data-open-settings]").forEach((b) => (b.onclick = () => $("#settingsBtn").click()));
  const car = $('.mode[data-mode="car"]');
  car.classList.toggle("needkey", !s.claude);
  $("small", car).textContent = s.claude ? "الماركة · الموديل · السنة" : "يحتاج مفتاح API";
  $('.mode[data-mode="street"] small').textContent = s.claude ? "تحليل عميق · Street View" : "بدون مفتاح: نفس تحديد المنطقة";
  if (!s.claude && state.mode === "car") $('.mode[data-mode="region"]').click();
  $("#modeHint").classList.toggle("hidden", s.claude);
  $('#rerunMenu [data-mode="car"]').disabled = !s.claude;
  [["person", "صورة · إيميل · جوال · اسم"], ["plate", "قراءة اللوحة · المركبة"]].forEach(([m, t]) => {
    const b = $(`.mode[data-mode="${m}"]`); b.classList.toggle("needkey", !s.claude); $("small", b).textContent = s.claude ? t : "يحتاج مفتاح API";
    $(`#rerunMenu [data-mode="${m}"]`).disabled = !s.claude;
  });
  $("#rerunEng").textContent = s.ready ? `بيستخدم ${s.label}` : "بدون مفتاح: النماذج المحلية بس";
  if (s.cases_dir) {
    $("#helpDir").textContent = s.cases_dir;
    $("#notes").placeholder = `ملاحظات عامة للتحقيق… (تنحفظ تلقائياً في ${s.cases_dir}\\saqr_board.json)`;
  }
  const warn = [];
  if (s.geoint_ok === false) warn.push(`مهارة geoint مو موجودة في <span class="mono" dir="ltr">${esc(s.geoint_path)}</span>: الفحص الأولي وأدوات Street View والقمر الصناعي ما بتشتغل. شوف README.`);
  if (s.uv_ok === false) warn.push(`برنامج <span class="mono">uv</span> مو مثبت: النماذج المحلية ما بتشتغل. ثبته من <span class="mono">docs.astral.sh/uv</span>`);
  $("#wwarn").innerHTML = warn.map((w) => `<p>${w}</p>`).join("");
  $("#wwarn").classList.toggle("hidden", !warn.length);
}
function setProv(p) {
  ai.prov = p;
  $$("#provSeg button").forEach((b) => b.classList.toggle("active", b.dataset.prov === p));
  $("#provOR").classList.toggle("hidden", p !== "openrouter");
  $("#provAN").classList.toggle("hidden", p !== "anthropic");
  const saved = (ai.status.keys || {})[p];
  $("#keyInput").placeholder = saved ? `المفتاح المحفوظ ينتهي بـ ${saved} · الصق مفتاح جديد لو تبي تغيره`
    : p === "openrouter" ? "sk-or-v1-…" : "sk-ant-api03-…";
  $("#keySave").textContent = saved ? "حفظ" : "حفظ وتحقق";
  $("#keyRemove").classList.toggle("hidden", !saved);
  $("#keyRemove").classList.remove("armed");
  $("#keyRemove").textContent = `حذف مفتاح ${PROV_NAME[p]} من الجهاز`;
  if (p === "openrouter" && !ai.models) loadModels();
}
async function loadModels() {
  ai.models = { recommended: [], all: [] };
  try {
    const r = await fetch("/api/models");
    const body = await r.json();
    if (!r.ok) throw new Error(body.detail || `خطأ ${r.status}`);
    ai.models = body;
    $("#modelSrc").textContent = `الترتيب حسب ${body.source}`;
    $("#modelAll").innerHTML = body.all.map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join("");
    renderModels();
  } catch (e) {
    ai.models = null;
    $("#modelList").innerHTML = `<div class="keymsg err" style="padding:10px 12px">${esc(e.message)}</div>`;
  }
}
function renderModels() {
  const rec = ai.models?.recommended || [];
  const custom = !rec.some((m) => m.id === ai.model);
  $("#modelCustom").value = custom ? ai.model : "";
  $("#modelList").innerHTML = rec.map((m) => {
    const pr = m.price ? `$${esc(m.price.in)} / $${esc(m.price.out)}<i>لكل مليون توكن</i>` : "—";
    const tag = m.tag ? `<span class="tag ${m.tag === "الأرخص" ? "cheap" : ""}">${esc(m.tag)}</span>` : "";
    return `<button class="mrow ${m.id === ai.model ? "on" : ""} ${m.available ? "" : "off"}" data-model="${esc(m.id)}">
      <span class="dot"></span>
      <span><span class="nm">${esc(m.label)} ${tag}</span><span class="note">${esc(m.available ? m.note : "مو متوفر حالياً في OpenRouter")}</span></span>
      <span class="pr">${pr}</span></button>`;
  }).join("");
}
async function saveAI(remove = false) {
  const msg = $("#keyMsg");
  const key = $("#keyInput").value.trim();
  const model = ($("#modelCustom").value.trim() || ai.model).trim();
  msg.className = "keymsg";
  msg.textContent = remove ? "جاري الحذف…" : key ? `جاري التحقق من المفتاح مع ${PROV_NAME[ai.prov]}…` : "جاري الحفظ…";
  $("#keySave").disabled = true;
  try {
    const r = await fetch("/api/settings/ai", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: ai.prov, key, model: ai.prov === "openrouter" ? model : undefined, remove }) });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : `خطأ ${r.status}`);
    if (ai.prov === "openrouter" && !remove) ai.model = body.or_model;
    updateEngine(body);
    if (ai.models) renderModels();
    $("#keyInput").value = "";
    msg.className = "keymsg ok";
    msg.textContent = remove ? (body.ready ? `انحذف المفتاح. صقر الحين يستخدم ${PROV_NAME[body.provider]}.` : "انحذف المفتاح. صقر رجع لوضع بدون ذكاء اصطناعي.")
      : `تمام: التحليلات الجاية بتستخدم ${body.label}.`;
  } catch (e) {
    msg.className = "keymsg err"; msg.textContent = e instanceof TypeError ? "ما قدرت أوصل لصقر" : e.message;
  } finally { $("#keySave").disabled = false; }
}
function closeSettings() {
  $("#setModal").classList.add("hidden");
  // a model clicked without a saved key was never stored: show what the server will really use
  if (ai.status.or_model && ai.model !== ai.status.or_model) { ai.model = ai.status.or_model; if (ai.models) renderModels(); }
}

function updateClearMenu() {
  $("#mCount").textContent = state.lines.filter((l) => l.length > 1).length;
  $("#pCount").textContent = state.board.pins.length;
  $("#clearMeasure").disabled = !state.lines.length;
  $("#clearPins").disabled = !state.board.pins.length;
  $("#clearPins").classList.remove("armed");
  $("#clearPinsLabel").textContent = "حذف كل الدبابيس";
}

// ---------------------------------------------------------------- intel panel
function feed(kind, title, body, raw = false) {
  const box = $("#feed"), sc = box.parentElement;
  const stick = sc.scrollHeight - sc.scrollTop - sc.clientHeight < 80;   // only follow the stream when already at the bottom
  const d = document.createElement("div");
  d.className = `ev ${kind}`;
  d.innerHTML = `<span class="k">${esc(title)}</span>${raw ? body : `<div class="txt" dir="auto">${esc(body)}</div>`}`;
  box.appendChild(d);
  if (stick && !state.replaying) sc.scrollTop = sc.scrollHeight;
  $("#feedN").textContent = ++state.feedN;
  return d;
}
function addEvidence(path, caption) {
  const url = `/api/cases/${encodeURIComponent(state.active)}/file/${path.split("/").map(encodeURIComponent).join("/")}`;
  const d = document.createElement("div");
  d.className = "evi";
  d.innerHTML = `<img src="${esc(url)}" loading="lazy" alt=""><p>${esc(caption)}</p>`;
  d.onclick = () => lightbox(url, caption);
  $("#evidence").prepend(d);
  $("#evN").textContent = ++state.evN;
}
function lightbox(url, caption) {
  $("#lightbox img").src = url;
  $("#lightbox p").textContent = caption || "";
  $("#lightbox").classList.remove("hidden");
}
const STAGES = ["recon", "analysis", "done"];
function setStage(s) {
  s = { verify: "analysis" }[s] || s;
  if (s !== "done") state.stage = s;
  const idx = STAGES.indexOf(s);
  $$("#stages .stage").forEach((el) => {
    const i = STAGES.indexOf(el.dataset.s);
    el.classList.remove("failed", "stopped");
    el.classList.toggle("done", i < idx || s === "done");
    el.classList.toggle("active", i === idx && s !== "done");
  });
}
// a run that ended without an answer: stages before the one it ended in are done, that one is marked, later ones stay empty
function endStages(how) {
  const idx = STAGES.indexOf(state.stage);
  $$("#stages .stage").forEach((el) => {
    const i = STAGES.indexOf(el.dataset.s);
    el.classList.remove("active", "done", "failed", "stopped");
    if (i < idx) el.classList.add("done");
    else if (i === idx) el.classList.add(how);
  });
}
function itab(t) {
  $$(".it-tab").forEach((b) => b.classList.toggle("active", b.dataset.it === t));
  $$(".ibody").forEach((b) => b.classList.toggle("hidden", b.dataset.ib !== t));
  if (t === "feed") { const sc = $("#feed").parentElement; sc.scrollTop = sc.scrollHeight; }
}

function dms(v, pos, neg) {
  const h = v >= 0 ? pos : neg; v = Math.abs(v);
  const d = Math.floor(v), m = Math.floor((v - d) * 60), s = ((v - d - m / 60) * 3600).toFixed(1);
  return `${d}°${String(m).padStart(2, "0")}'${s}"${h}`;
}
const list = (title, items) => (items && items.length ? `<h4>${title}</h4><ul>${items.map((x) => `<li dir="auto">${esc(String(x).replace(/^-\s+/, ""))}</li>`).join("")}</ul>` : "");
const errCard = (t) => `<div class="err-card"><b>صار خطأ</b><p dir="auto">${esc(t)}</p><small>تقدر تعيد التحليل من زر الإعادة بعد ما تصلح السبب.</small></div>`;
function noFinal(c) {
  if (c.status === "error") return errCard(c.error || "صار خطأ");
  if (c.status === "stopped") return `<div class="note-card"><b>انوقف التحليل</b><p>وقف بطلبك قبل الجواب النهائي. المرشحات على الخريطة باقية، وتقدر تعيد التحليل من زر الإعادة.</p></div>`;
  return `<div class="note-card"><b>ما طلع جواب نهائي</b><p>شوف تبويب "مباشر" لتفاصيل اللي صار، أو أعد التحليل.</p></div>`;
}

function showFinal(f) {
  const r = $("#result");
  if ("country" in f && okLL(f.lat, f.lon)) {
    state.final = f;
    renderRadii();
    const lat = +f.lat, lon = +f.lon;
    const place = [f.country, f.region, f.city].filter(Boolean).join(" · ");
    const coords = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    r.innerHTML = `<div class="hudlbl ${cls(f.confidence)}"><span>الموقع</span>${esc(LEVEL_AR[f.level] || f.level || "")}</div>
      <h2>${esc(place)}</h2>
      <div class="coords"><span>${dms(lat, "N", "S")} ${dms(lon, "E", "W")}</span><span class="dim">${coords}</span>
        <span class="acts"><button id="copyc">${ICON.copy}نسخ</button>
        <a target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query=${lat},${lon}">${ICON.ext}Maps</a>
        <button id="goto">${ICON.target}انتقل</button></span></div>
      <div class="meta"><span class="tag ${cls(f.confidence)}"><i></i>${esc(CONF_AR[f.confidence] || f.confidence)}</span>
        <span class="tag">${esc(LEVEL_AR[f.level] || f.level || "")}</span><span class="tag">± ${esc(f.radius_km)} كم</span></div>
      <p dir="auto">${esc(f.summary)}</p>
      ${list("الأدلة الحاسمة", f.clues)}
      ${list("احتمالات ثانية", (f.alternatives || []).map((a) => `${a.place}: ${a.why}`))}
      ${list("ما تحقق منه", f.unverified)}`;
    $("#copyc").onclick = () => navigator.clipboard?.writeText(coords).then(() => toast("انسخت الإحداثيات"), () => toast("ما قدرت أنسخ", "err"));
    $("#goto").onclick = () => flyTo(lat, lon, f.radius_km);
  } else if ("assessment" in f) {
    const gen = Math.round((+f.ai_generation_likelihood || 0) * 100), mp = Math.round((+f.manipulation_likelihood || 0) * 100);
    r.innerHTML = `<div class="hudlbl"><span>سلامة الصورة</span></div><h2>${esc(ASSESS_AR[f.assessment] || f.assessment)}</h2>
      ${"ai_generation_likelihood" in f ? `<h4>احتمال التوليد بالذكاء الاصطناعي · ${gen}%</h4><div class="bar2 ${gen > 50 ? "warn" : ""}"><div style="width:${gen}%"></div></div>
      <h4>احتمال التعديل · ${mp}%</h4><div class="bar2 ${mp > 50 ? "warn" : ""}"><div style="width:${mp}%"></div></div>` : ""}
      <p dir="auto">${esc(f.summary_ar)}</p>
      ${list("المؤشرات", (f.signals || []).map((s) => `${s.name}: ${s.finding}`))}
      ${f.limits_ar ? `<h4>الحدود</h4><p dir="auto">${esc(f.limits_ar)}</p>` : ""}
      ${f.metadata ? `<h4>بيانات الملف</h4><pre class="meta-pre" dir="ltr">${esc(f.metadata)}</pre>` : ""}
      ${state.evN ? `<button class="link" id="seeEla">شوف صورة ELA في الأدلة</button>` : ""}`;
    $("#seeEla")?.addEventListener("click", () => itab("evidence"));
  } else if ("make" in f) {
    const c = Math.round((+f.confidence || 0) * 100);
    r.innerHTML = `<div class="hudlbl"><span>السيارة</span></div><h2>${esc(f.make)} ${esc(f.model)}</h2>
      <div class="meta"><span class="tag">${esc(f.year_range)}</span><span class="tag">${esc(f.body_type)}</span><span class="tag ${c >= 70 ? "high" : "medium"}"><i></i>${c}%</span></div>
      <p dir="auto">${esc(f.summary_ar)}</p>${list("العلامات", f.cues)}${list("سيارات تشبهها", f.alternatives)}`;
  } else if ("found" in f) {
    const acc = (f.accounts || []).map((a) => `${a.site}${a.handle ? " · " + a.handle : ""}: ${a.why}`);
    r.innerHTML = `<div class="hudlbl"><span>الشخص</span>${esc(CONF_AR[f.confidence] || "")}</div>
      <h2>${esc(f.found ? f.name : "ما تحدد شخص")}</h2>
      ${f.role ? `<div class="meta"><span class="tag">${esc(f.role)}</span>${f.place ? `<span class="tag">${esc(f.place)}</span>` : ""}</div>` : ""}
      <p dir="auto">${esc(f.summary)}</p>${list("حسابات مرجّحة", acc)}
      ${list("الأدلة", f.evidence)}${list("ما تحقق منه", f.unverified)}`;
  } else if ("plate" in f) {
    r.innerHTML = `<div class="hudlbl"><span>اللوحة</span>${esc(CONF_AR[f.confidence] || "")}</div>
      <h2 dir="ltr">${esc(f.plate)}</h2>
      <div class="meta">${f.country ? `<span class="tag">${esc(f.country)}</span>` : ""}${f.plate_type ? `<span class="tag">${esc(f.plate_type)}</span>` : ""}</div>
      <p dir="auto">${esc(f.summary)}</p>
      ${list("المركبة", [f.vehicle])}
      ${list("الموقع من شكل اللوحة", [f.region_hint])}
      ${list("المالك", [f.owner ? `${f.owner} — ${f.owner_note || ""}` : (f.owner_note || "غير متاح علناً")])}
      ${list("الأدلة", f.evidence)}${list("ما تحقق منه", f.unverified)}`;
  }
}

function handle(ev, live) {
  switch (ev.kind) {
    case "stage":
      setStage(ev.stage);
      feed("stage", { recon: "فحص أولي", verify: "فحص الملف", analysis: "تحليل", done: "انتهى" }[ev.stage] || ev.stage, ev.text);
      if (ev.stage === "done" && live) afterRun(state.active);
      break;
    case "log": feed("log", "سجل", ev.text); break;
    case "thinking": feed("thinking", "تفكير", ev.text); break;
    case "say": feed("say", "المحلل", ev.text); break;
    case "tool": feed("tool", `أداة · ${TOOL_AR[ev.name] || ev.name}`, `<code>${esc(JSON.stringify(ev.input))}</code>`, true); break;
    case "result": {
      const d = feed(`result ${ev.error ? "err" : ""}`, `${ev.error ? "فشلت" : "رجعت"} · ${TOOL_AR[ev.name] || ev.name}`, ev.text || "(بدون نص)");
      d.title = "اضغط لعرض الكل"; d.onclick = () => d.classList.toggle("open");
      break;
    }
    case "progress": {
      const t = +ev.turn || 0, mx = +ev.max || 1;
      $("#turns").classList.remove("hidden", "done");
      $("#turnFill").style.width = `${Math.min(100, (t / mx) * 100)}%`;
      $("#turnTxt").textContent = `جولة ${t} من ${mx}`;
      break;
    }
    case "candidate":
      state.cands.push(ev.candidate); renderActiveMarkers();
      feed("candidate", `مرشح #${ev.candidate.n}`, `${ev.candidate.label} — ${ev.candidate.reason}`);
      if (live && !state.final) flyTo(ev.candidate.lat, ev.candidate.lon, ev.candidate.radius_km);
      break;
    case "evidence": addEvidence(ev.path, ev.caption); break;
    case "final": {
      showFinal(ev.final);
      const c = state.cases.find((x) => x.id === state.active);
      if (c) { c.final = ev.final; renderSources(); renderCaseMarkers(); }
      if (live && ev.final.lat !== undefined) flyTo(ev.final.lat, ev.final.lon, ev.final.radius_km);
      break;
    }
    case "error":
      feed("error", "خطأ", ev.text);
      if (!state.final) $("#result").innerHTML = errCard(ev.text);
      endStages("failed");
      if (live) afterRun(state.active);
      break;
  }
}
function finished(hasReport) {
  const url = `/api/cases/${encodeURIComponent(state.active)}/report`;
  ["#reportBtn", "#iReport"].forEach((s) => (hasReport ? $(s).setAttribute("href", url) : $(s).removeAttribute("href")));
  $("#iReport").classList.toggle("hidden", !hasReport);
  $("#reportBtn").setAttribute("aria-disabled", hasReport ? "false" : "true");
  $("#iStop").classList.add("hidden");
  $("#iRerun").classList.remove("hidden");
  $("#turns").classList.add("done");
}
function finalizeView(c) {
  finished(!!c.has_report);
  if (c.status !== "done") endStages(c.status === "stopped" ? "stopped" : "failed");
  if (!state.final && !$("#result h2")) $("#result").innerHTML = noFinal(c);
}
async function afterRun(id) {
  if (!id || state.active !== id) return;
  let c;
  try { c = await (await fetch(`/api/cases/${encodeURIComponent(id)}`)).json(); } catch { return; }
  if (state.active !== id || RUNNING.includes(c.status)) return;
  finalizeView(c);
  refreshCases();
  if (state.final || $("#result h2") || c.status === "error") itab("result");
}

function resetIntel() {
  state.es?.close(); state.es = null;
  state.cands = []; state.final = null; state.feedN = 0; state.evN = 0; state.stage = "recon";
  clear(state.activeMarkers); renderRadii();
  $("#feed").innerHTML = ""; $("#evidence").innerHTML = "";
  $("#feedN").textContent = "0"; $("#evN").textContent = "0";
  $("#result").innerHTML = `<p class="dim scanning">التحليل شغال… النتيجة تطلع هنا.</p>`;
  $$("#stages .stage").forEach((e) => e.classList.remove("active", "done", "failed"));
  $("#reportBtn").setAttribute("aria-disabled", "true"); $("#reportBtn").removeAttribute("href");
  ["#iReport", "#iStop", "#iRerun", "#rerunMenu", "#turns"].forEach((s) => $(s).classList.add("hidden"));
  $("#iStop").disabled = false;
  $("#caseNotes").value = ""; $("#caseNotesState").textContent = "";
}

async function openCase(id) {
  const tok = ++state.openTok;
  let c;
  try {
    const res = await fetch(`/api/cases/${encodeURIComponent(id)}`);
    if (!res.ok) { if (res.status === 404) toast("القضية مو موجودة (يمكن انحذفت)", "err"); return; }
    c = await res.json();
  } catch { toast("ما قدرت أوصل لصقر", "err"); return; }
  if (tok !== state.openTok) return;   // another case was clicked while this one loaded
  resetIntel();
  state.active = id;
  history.replaceState(null, "", `#case=${id}`);
  $("#intel").classList.remove("hidden");
  document.body.classList.add("has-intel");
  document.body.classList.remove("side-front");
  renderWelcome();
  $("#boardBtn").disabled = false; $("#intelBtn").disabled = false;
  $("#iThumb").src = `/api/cases/${encodeURIComponent(id)}/photo`;
  $("#iName").textContent = c.filename;
  $("#iMode").textContent = MODE_LABEL[c.mode] || c.mode;
  $("#iTime").textContent = (c.created || "").slice(0, 16).replace("T", " ");
  $("#iEngine").textContent = c.engine ? `المحرك: ${c.engine}${c.rerun_of ? " · إعادة تحليل" : ""}` : "";
  $("#rerunRev").checked = c.rev !== false && ["region", "street", "private", "plate"].includes(c.mode);   // only a choice the user made carries over
  const { events = [], ...meta } = c;
  if (!state.cases.some((x) => x.id === id)) state.cases.unshift(meta);
  renderSources(); renderCaseMarkers();
  loadCaseNotes(id);
  itab("result");
  state.replaying = true;
  events.forEach((ev) => handle(ev, false));
  state.replaying = false;
  const sc = $("#feed").parentElement; sc.scrollTop = sc.scrollHeight;
  if (!RUNNING.includes(c.status)) {
    finalizeView(c);
    const f = state.final, last = state.cands[state.cands.length - 1];
    if (f) flyTo(f.lat, f.lon, f.radius_km); else if (last) flyTo(last.lat, last.lon, last.radius_km);
  } else {
    itab("feed");
    $("#iStop").classList.toggle("hidden", !!c.cancel);
    const last = state.cands[state.cands.length - 1];
    if (last) flyTo(last.lat, last.lon, last.radius_km);
    const es = new EventSource(`/api/cases/${encodeURIComponent(id)}/stream?from=${events.length}`);   // resume after what was replayed
    state.es = es;
    es.onmessage = (m) => { if (state.active === id) handle(JSON.parse(m.data), true); };
    es.addEventListener("end", () => { es.close(); afterRun(id); });
  }
}
function closeIntel() {
  resetIntel();
  state.active = null;
  history.replaceState(null, "", location.pathname);
  $("#intel").classList.add("hidden");
  document.body.classList.remove("has-intel");
  $("#boardBtn").disabled = true; $("#intelBtn").disabled = true;
  renderSources(); renderCaseMarkers(); renderWelcome();
}

async function loadCaseNotes(id) {
  try {
    const n = await (await fetch(`/api/cases/${encodeURIComponent(id)}/notes`)).json();
    if (state.active === id && document.activeElement !== $("#caseNotes")) $("#caseNotes").value = n.notes || "";
  } catch { /* notes are optional */ }
}
const noteTimers = {};
function saveCaseNotes(id, text) {   // keyed by case, so typing in case B never cancels a pending save of case A
  clearTimeout(noteTimers[id]);
  $("#caseNotesState").textContent = "…";
  noteTimers[id] = setTimeout(async () => {
    let ok = false;
    try {
      ok = (await fetch(`/api/cases/${encodeURIComponent(id)}/notes`, { method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: text }) })).ok;
    } catch { /* shown below */ }
    if (state.active === id) $("#caseNotesState").textContent = ok ? "محفوظ · تدخل التقرير" : "ما انحفظ";
  }, 600);
}

// ---------------------------------------------------------------- add source
const IMG_EXT = /\.(jpe?g|jfif|png|webp|gif|bmp|tiff?|heic|heif|avif)$/i;
const NO_PREVIEW = /\.(heic|heif|tiff?)$/i;   // Chromium can't draw these; the server makes a JPEG copy
function openAdd(file) {
  $("#addModal").classList.remove("hidden");
  $("#runMsg").classList.add("hidden");
  if (file) pickFile(file);
}
function pickFile(f) {
  if (!f) return;
  const msg = $("#dropMsg");
  if (!(f.type ? f.type.startsWith("image/") : IMG_EXT.test(f.name)) || f.type === "image/svg+xml") {
    msg.textContent = `"${f.name}" مو صورة يقدر صقر يحللها. الأنواع: JPG · PNG · WEBP · HEIC · TIFF`;
    msg.classList.remove("hidden");
    return;
  }
  msg.classList.add("hidden");
  $("#runMsg").classList.add("hidden");
  state.file = f;
  if (state.blob) URL.revokeObjectURL(state.blob);
  state.blob = URL.createObjectURL(f);
  const drop = $("#drop"), pv = $("#preview");
  drop.classList.add("has");
  drop.classList.remove("noprev");
  $("#dropFile").textContent = `${f.name} · ${f.size < 1048576 ? `${Math.max(1, Math.round(f.size / 1024))} KB` : `${(f.size / 1048576).toFixed(1)} MB`}`;
  pv.onerror = () => drop.classList.add("noprev");
  if (NO_PREVIEW.test(f.name) || /heic|heif|tiff/.test(f.type)) { pv.removeAttribute("src"); drop.classList.add("noprev"); }
  else pv.src = state.blob;
  updateRun();
}
function updateRun() {
  const person = state.mode === "person";
  $("#queryRow").classList.toggle("hidden", !person);
  const typed = person && $("#queryInput").value.trim();
  $("#run").disabled = (!state.file && !typed) || state.uploading;
  $("#runLabel").textContent = state.uploading ? "جاري الرفع…"
    : state.file ? `ابدأ · ${MODE_LABEL[state.mode]}` : typed ? `ابدأ · ${MODE_LABEL.person}` : "اختر صورة";
  $("#revRow").classList.toggle("hidden", !["region", "street", "private", "plate"].includes(state.mode));
}
async function runCase() {
  if ((!state.file && !(state.mode === "person" && $("#queryInput").value.trim())) || state.uploading) return;
  state.uploading = true; updateRun();
  $("#runMsg").classList.add("hidden");
  const fd = new FormData();
  if (state.file) fd.append("photo", state.file, state.file.name);
  fd.append("mode", state.mode);
  fd.append("query", state.mode === "person" ? $("#queryInput").value.trim() : "");
  fd.append("rev", $("#revOpt").checked ? "true" : "false");
  try {
    const res = await fetch("/api/cases", { method: "POST", body: fd });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : res.status === 413 ? "الصورة أكبر من 40 MB" : `ما انرفعت الصورة (خطأ ${res.status})`);
    $("#addModal").classList.add("hidden");
    state.file = null; $("#drop").classList.remove("has", "noprev"); $("#file").value = "";
    if (state.blob) { URL.revokeObjectURL(state.blob); state.blob = null; }
    await refreshCases(true);
    openCase(body.id);
  } catch (e) {
    $("#runMsg").textContent = e instanceof TypeError ? "ما قدرت أوصل لصقر: تأكد إن run.bat شغال" : e.message;
    $("#runMsg").classList.remove("hidden");
  } finally { state.uploading = false; updateRun(); }
}

// ---------------------------------------------------------------- place search
let searchT, searchSeq = 0;
async function placeSearch(q) {
  const seq = ++searchSeq, box = $("#placeResults");
  const m = q.match(/^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$/);
  let html = "";
  if (m && okLL(m[1], m[2]) && Math.abs(+m[2]) <= 180) {
    const lat = +m[1], lon = +m[2];
    html = `<button class="res" data-ll="${lat},${lon}"><b>انتقل للإحداثيات</b><small>${lat}, ${lon}</small></button>`;
  } else if (q.trim().length > 2) {
    box.innerHTML = `<p class="dim">جاري البحث…</p>`;
    try {
      const r = await (await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=7&accept-language=ar,en&q=${encodeURIComponent(q)}`)).json();
      if (seq !== searchSeq) return;   // a newer query is on its way: don't show stale results
      html = r.filter((x) => okLL(x.lat, x.lon)).map((x) => {
        const bb = (x.boundingbox || []).map(Number);
        return `<button class="res" data-ll="${+x.lat},${+x.lon}" ${bb.length === 4 && bb.every(Number.isFinite) ? `data-bb="${bb.join(",")}"` : ""}>
        <b>${esc(String(x.display_name).split(",")[0])}</b><small>${esc(x.display_name)}</small></button>`;
      }).join("") || `<p class="dim">ما لقيت شي.</p>`;
    } catch { html = `<p class="dim">البحث ما اشتغل (الشبكة؟)</p>`; }
  }
  if (seq !== searchSeq) return;
  box.innerHTML = html;
  $$(".res", box).forEach((b) => (b.onclick = () => {
    const [lat, lon] = b.dataset.ll.split(",").map(Number);
    state.tempMarker?.remove();
    state.tempMarker = marker(mkEl("u-place", ICON.target), lat, lon);
    if (b.dataset.bb) {
      const [s, n, w, e] = b.dataset.bb.split(",").map(Number);
      map.fitBounds([[w, s], [e, n]], { padding: pad(), maxZoom: 16, duration: 1600 });
    } else map.flyTo({ center: [lon, lat], zoom: 15, padding: pad() });
  }));
}

// ---------------------------------------------------------------- wiring
function init() {
  icons();
  if (store.get("side", innerWidth > 860) === false || innerWidth <= 860) hideSide(); else showSide("sources");

  $$(".ri[data-panel]").forEach((b) => (b.onclick = () => {
    const t = b.dataset.panel;
    if (state.sideOpen && b.classList.contains("active")) { hideSide(); store.set("side", false); }
    else { showSide(t); store.set("side", true); }
  }));
  $$(".pt").forEach((b) => (b.onclick = () => showSide(b.dataset.pt)));
  $("#togglePanel").onclick = () => { state.sideOpen ? hideSide() : showSide("sources"); store.set("side", state.sideOpen); };
  $("#closeSide").onclick = () => { hideSide(); store.set("side", false); };
  $("#srcSearch").oninput = renderSources;
  $("#placeSearch").oninput = (e) => { clearTimeout(searchT); searchT = setTimeout(() => placeSearch(e.target.value), 450); };
  $("#notes").oninput = (e) => { state.board.notes = e.target.value; saveBoard(); };
  $("#caseNotes").oninput = (e) => { if (state.active) saveCaseNotes(state.active, e.target.value); };

  // top bar menus
  const menus = [["#filterBtn", "#filterMenu"], ["#layersBtn", "#layersMenu"], ["#iRerun", "#rerunMenu"]];
  menus.forEach(([b, m]) => ($(b).onclick = (e) => {
    e.stopPropagation();
    menus.forEach(([ob, o]) => { if (o !== m) { $(o).classList.add("hidden"); $(ob).classList.remove("on"); } });
    $(m).classList.toggle("hidden"); $(b).classList.toggle("on", !$(m).classList.contains("hidden"));
  }));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".drop-wrap")) menus.forEach(([b, m]) => { $(m).classList.add("hidden"); $(b).classList.remove("on"); });
  });
  $$("#filterMenu input").forEach((i) => {
    i.checked = state.filters[i.dataset.f] !== false;
    i.onchange = () => {
      state.filters[i.dataset.f] = i.checked; store.set("filters", state.filters);
      $("#filterN").textContent = Object.values(state.filters).filter(Boolean).length;
      renderSources(); renderCaseMarkers(); renderPins();
    };
  });
  $("#filterN").textContent = Object.values(state.filters).filter(Boolean).length;
  $$("input[name=base]").forEach((i) => (i.onchange = () => { state.base = i.value; store.set("base", state.base); applyLayers(); }));
  $("#l3d").onchange = (e) => { state.show3d = e.target.checked; store.set("3d", state.show3d); applyLayers(); };
  $("#lRadius").onchange = (e) => { state.showRadius = e.target.checked; applyLayers(); };
  $("#lLabels").onchange = applyLayers;
  $("#baseToggle").onclick = () => { state.base = state.base === "sat" ? "dark" : "sat"; store.set("base", state.base); applyLayers(); };
  $("#tiltBtn").onclick = () => {
    const flat = map.getPitch() < 5;
    state.tilt = flat;
    map.easeTo({ pitch: flat ? 60 : 0, bearing: flat ? -20 : 0, zoom: flat ? Math.max(map.getZoom(), 15) : map.getZoom(), duration: 1000 });
  };
  $("#boardBtn").onclick = () => itab("evidence");
  $("#intelBtn").onclick = () => itab("feed");

  // map tools
  $$(".tl[data-tool]").forEach((b) => (b.onclick = () => setTool(b.dataset.tool)));
  $("#clearBtn").onclick = (e) => {
    e.stopPropagation();
    updateClearMenu();
    $("#clearMenu").classList.toggle("hidden");
  };
  document.addEventListener("click", (e) => { if (!e.target.closest("#clearMenu, #clearBtn")) $("#clearMenu").classList.add("hidden"); });
  $("#clearMeasure").onclick = () => { state.lines = []; state.drawing = false; renderMeasure(); $("#clearMenu").classList.add("hidden"); };
  let armT;
  $("#clearPins").onclick = (e) => {
    const b = e.currentTarget;
    if (!b.classList.contains("armed")) {
      b.classList.add("armed"); $("#clearPinsLabel").textContent = "متأكد؟ اضغط مرة ثانية";
      clearTimeout(armT); armT = setTimeout(updateClearMenu, 3500);
      return;
    }
    state.board.pins.forEach((p) => p._m?.remove());
    state.board.pins = []; saveBoard(); renderPins(); renderSources();
    $("#clearMenu").classList.add("hidden");
  };
  $("#compass").onclick = () => map.easeTo({ bearing: 0, pitch: 0, duration: 700 });
  $("#zin").onclick = () => map.zoomIn();
  $("#zout").onclick = () => map.zoomOut();

  // intel
  $("#closeIntel").onclick = closeIntel;
  $$(".it-tab").forEach((b) => (b.onclick = () => itab(b.dataset.it)));
  $("#iThumb").onclick = () => lightbox($("#iThumb").src, $("#iName").textContent);
  $("#iStop").onclick = async () => {
    const id = state.active, b = $("#iStop");
    b.disabled = true;
    try {
      const r = await fetch(`/api/cases/${encodeURIComponent(id)}/cancel`, { method: "POST" });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : `خطأ ${r.status}`);
      b.classList.add("hidden");
      toast("طلبت الإيقاف: بيوقف بعد الخطوة الحالية");
    } catch (e) { toast(e instanceof TypeError ? "ما قدرت أوصل لصقر" : e.message, "err"); }
    b.disabled = false;
  };
  $$("#rerunMenu [data-mode]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation();
    $("#rerunMenu").classList.add("hidden"); $("#iRerun").classList.remove("on");
    try {
      const r = await fetch(`/api/cases/${encodeURIComponent(state.active)}/rerun`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: b.dataset.mode, rev: $("#rerunRev").checked }) });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : `خطأ ${r.status}`);
      await refreshCases(true);
      openCase(body.id);
      toast(`بدأت إعادة التحليل · ${MODE_LABEL[b.dataset.mode]}`);
    } catch (err) { toast(err instanceof TypeError ? "ما قدرت أوصل لصقر" : err.message, "err"); }
  }));

  // add source
  $("#addBtn").onclick = () => openAdd();
  $("#closeAdd").onclick = () => $("#addModal").classList.add("hidden");
  $("#addModal").onclick = (e) => { if (e.target.id === "addModal") $("#addModal").classList.add("hidden"); };
  const drop = $("#drop");
  drop.onclick = () => $("#file").click();
  $("#file").onchange = (e) => pickFile(e.target.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); e.stopPropagation(); drop.classList.remove("over"); pickFile(e.dataTransfer.files[0]); $("#dragOverlay").classList.add("hidden"); };
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("drop", (e) => { e.preventDefault(); const f = e.dataTransfer?.files?.[0]; if (f) openAdd(f); });
  document.addEventListener("paste", (e) => { const f = [...(e.clipboardData?.files || [])][0]; if (f) openAdd(f); });
  $$(".mode").forEach((b) => (b.onclick = () => {
    if (b.classList.contains("needkey")) return;
    state.mode = b.dataset.mode;
    $$(".mode").forEach((x) => x.classList.toggle("active", x === b)); updateRun();
  }));
  $("#revOpt").checked = store.get("rev", true);
  $("#revOpt").onchange = (e) => store.set("rev", e.target.checked);
  $("#queryInput").oninput = updateRun;
  $("#run").onclick = runCase;

  $("#helpBtn").onclick = () => $("#helpModal").classList.remove("hidden");
  $$("[data-close]").forEach((b) => (b.onclick = () => (b.dataset.close === "setModal" ? closeSettings() : $(`#${b.dataset.close}`).classList.add("hidden"))));
  $("#helpModal").onclick = (e) => { if (e.target.id === "helpModal") e.target.classList.add("hidden"); };
  $("#lightbox").onclick = () => $("#lightbox").classList.add("hidden");
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#lightbox").classList.contains("hidden")) return $("#lightbox").classList.add("hidden");
    if (!$("#addModal").classList.contains("hidden")) return $("#addModal").classList.add("hidden");
    if (!$("#setModal").classList.contains("hidden")) return closeSettings();
    $("#helpModal").classList.add("hidden"); $("#clearMenu").classList.add("hidden");
    menus.forEach(([b, m]) => { $(m).classList.add("hidden"); $(b).classList.remove("on"); });
    closePopups();
    setTool("select");
  });

  // settings
  const openSettings = () => { $("#setModal").classList.remove("hidden"); $("#keyMsg").textContent = ""; $("#keyInput").focus(); };
  $("#settingsBtn").onclick = openSettings;
  $("#engine").onclick = openSettings;
  $$("[data-open-settings]").forEach((b) => (b.onclick = () => { $("#addModal").classList.add("hidden"); openSettings(); }));
  $("#setModal").onclick = (e) => { if (e.target.id === "setModal") closeSettings(); };
  $("#keySave").onclick = () => saveAI();
  $("#keyInput").onkeydown = (e) => { if (e.key === "Enter") saveAI(); };
  $("#keyRemove").onclick = (e) => {
    const b = e.currentTarget;
    if (!b.classList.contains("armed")) {
      b.classList.add("armed"); b.textContent = "متأكد؟ اضغط مرة ثانية للحذف";
      setTimeout(() => { if (b.classList.contains("armed")) setProv(ai.prov); }, 3500);
      return;
    }
    saveAI(true);
  };
  $$("#provSeg button").forEach((b) => (b.onclick = () => { setProv(b.dataset.prov); $("#keyMsg").textContent = ""; $("#keyInput").value = ""; }));
  $("#modelList").onclick = (e) => {
    const row = e.target.closest("[data-model]");
    if (!row) return;
    ai.model = row.dataset.model; $("#modelCustom").value = ""; renderModels();
    // already running on OpenRouter with a saved key: a click is the choice, save it now
    if (ai.status.provider === "openrouter" && (ai.status.keys || {}).openrouter && !$("#keyInput").value.trim()) saveAI();
  };
  $("#modelCustom").oninput = (e) => { if (e.target.value.trim()) $$("#modelList .mrow").forEach((r) => r.classList.remove("on")); };

  // big "new photo" entry points + drop anywhere
  $("#newBtn").onclick = () => openAdd();
  $("#wdrop").onclick = () => openAdd();
  let dragDepth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
  document.addEventListener("dragenter", (e) => {
    if (!hasFiles(e) || !$("#addModal").classList.contains("hidden")) return;
    dragDepth++; $("#dragOverlay").classList.remove("hidden");
  });
  document.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#dragOverlay").classList.add("hidden"); } });
  document.addEventListener("drop", () => { dragDepth = 0; $("#dragOverlay").classList.add("hidden"); }, true);

  const tick = () => { $("#clock").textContent = `UTC ${new Date().toISOString().slice(11, 19)}`; };
  tick(); setInterval(tick, 1000);

  fetch("/api/status").then((r) => r.json()).then(updateEngine).catch(() => toast("ما قدرت أوصل لصقر: تأكد إن run.bat شغال", "err"));
  loadBoard();
  document.addEventListener("visibilitychange", () => {   // another tab may have changed the board meanwhile
    if (document.visibilityState === "visible" && !state.savePending) loadBoard();
  });

  const fromHash = () => {
    const m = location.hash.match(/case=([\w.-]+)/);
    if (m && m[1] !== state.active) openCase(m[1]);
    const v = location.hash.match(/view=(-?[\d.]+),(-?[\d.]+),([\d.]+)(?:,([\d.]+))?/);
    if (v) map.jumpTo({ center: [+v[2], +v[1]], zoom: +v[3], pitch: +(v[4] || 0), bearing: v[4] ? -20 : 0 });
  };
  window.addEventListener("hashchange", fromHash);
  refreshCases(true).then(fromHash);
  setInterval(() => { if (state.cases.some((c) => RUNNING.includes(c.status))) refreshCases(); }, 4000);
  updateRun();
  applyLayers();
}
init();
