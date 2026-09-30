/* BRICS AIRWATCH — frontend runtime.
   Reusable UI components (MetricCard, MapPanel, HotspotCard, AlertCard, ForecastChart,
   ActivityFeed, AIAnalysisPanel, EvidencePanel, DataSourceBadge, ConfidenceBadge) + page controllers. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const params = new URLSearchParams(location.search);
  const KEY = "IN-GJ-0926-018";

  function csrf() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const i = document.querySelector("[name=csrfmiddlewaretoken]");
    return i ? i.value : "";
  }
  async function api(url, opts = {}) {
    const o = { method: opts.method || "GET", credentials: "same-origin", headers: { "X-CSRFToken": csrf(), Accept: "application/json" } };
    if (opts.body instanceof FormData) o.body = opts.body;
    else if (opts.body !== undefined) { o.body = JSON.stringify(opts.body); o.headers["Content-Type"] = "application/json"; }
    const r = await fetch(url, o);
    let data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (!r.ok) {
      const msg = data ? (data.detail || Object.values(data).flat().join(" ")) : `HTTP ${r.status}`;
      const err = new Error(msg); err.status = r.status; throw err;
    }
    return data;
  }
  function toast(msg, ms = 3200) {
    const t = document.createElement("div"); t.className = "toast"; t.textContent = msg;
    document.body.appendChild(t); setTimeout(() => t.remove(), ms);
  }
  const ago = (iso) => {
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return "now"; if (s < 3600) return `${Math.round(s / 60)}m`; if (s < 86400) return `${Math.round(s / 3600)}h`; return `${Math.round(s / 86400)}d`;
  };

  // ---------- colour scales ----------
  const C = { accent: "#FF6B00", warn: "#F59E0B", danger: "#EF4444", ok: "#22C55E", info: "#3B82F6", muted: "#A1A1AA", line: "#1f1f22", purple: "#c084fc" };
  const STATUS_COLOR = { CRITICAL: C.danger, HIGH: C.accent, MODERATE: C.warn, MEDIUM: C.warn, LOW: C.ok };
  const THRESH = { aqi: [100, 200, 300], pm25: [60, 90, 120], pm10: [100, 250, 350], no2: [80, 180, 280], so2: [60, 120, 380], co: [2, 4, 10] };
  const UNITS = { aqi: "", pm25: "μg/m³", pm10: "μg/m³", no2: "μg/m³", so2: "μg/m³", co: "mg/m³" };
  function colorFor(metric, v) {
    const t = THRESH[metric] || THRESH.aqi;
    if (v >= t[2]) return C.danger; if (v >= t[1]) return C.accent; if (v >= t[0]) return C.warn; return C.ok;
  }
  function intensity(metric, v) { const t = THRESH[metric] || THRESH.aqi; return Math.max(0.15, Math.min(1.4, v / t[2])); }

  // ---------- reusable components ----------
  const UI = {
    DataSourceBadge(label) {
      const l = String(label || "DEMO DATA").toUpperCase();
      const cls = l.includes("LIVE") || l.includes("GEMINI") && !l.includes("MOCK") ? "live" : l.includes("SIMULATED") || l.includes("MODEL") ? "sim" : l.includes("AI") ? "ai" : "demo";
      return `<span class="badge-src ${cls}">${esc(l)}</span>`;
    },
    ConfidenceBadge(v) { return `<span class="conf"><span class="bar"><i style="width:${Math.max(0, Math.min(100, v))}%"></i></span>${esc(v)}%</span>`; },
    Severity(s) { return `<span class="sev ${esc(s)}">${esc(s)}</span>`; },
    MetricCard(m) {
      const tone = { warning: C.warn, danger: C.danger, accent: C.accent, info: C.info, success: C.ok }[m.tone] || C.accent;
      return `<div class="metric" style="--tone:${tone}"><div class="eyebrow">${esc(m.label)}</div><div class="v" data-count="${esc(m.value)}">${esc(m.value)}</div><div class="s">${esc(m.sub || "")}</div></div>`;
    },
    HotspotCard(h) {
      const c = STATUS_COLOR[h.status] || C.accent;
      return `<div class="hcard" style="--c:${c}" data-code="${esc(h.code)}">
        <div class="row"><span class="code">#${esc(h.code)}</span>${UI.Severity(h.status)}</div>
        <div class="reg">${esc(h.region)}</div>
        <div class="dim" style="font-size:11.5px">${esc(h.country || "")} · ${esc(h.source_category)}</div>
        <div class="nums"><div><small>AQI</small>${esc(h.aqi)}</div><div><small>PM2.5</small>${esc(h.pm25)}</div><div><small>REPORTS</small>${esc(h.citizen_report_count)}</div></div>
        <div class="row">${UI.ConfidenceBadge(h.confidence)}${UI.DataSourceBadge(h.data_label)}</div></div>`;
    },
    EvidencePanel(items) {
      return `<div class="chain">${items.map((e, i) => `<div class="ev ${i === items.length - 1 ? "last" : ""}" style="animation-delay:${i * 0.12}s"><span class="n">${esc(e.n)}</span><div><b>${esc(e.title)}</b><div class="val">${esc(e.value)}</div><div class="det">${esc(e.detail)} · <span class="${e.label === "AI ASSESSMENT" ? "accent" : "c-warn"}">${esc(e.label)}</span></div></div></div>`).join("")}</div>`;
    },
    AlertCard(a, canAct) {
      const c = STATUS_COLOR[a.severity] || C.accent;
      const hs = a.hotspot ? encodeURIComponent(a.hotspot) : "";
      return `<div class="alert-card ${esc(a.status)}" style="--c:${c}" data-code="${esc(a.code)}">
        <div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">${UI.Severity(a.severity)}<b style="font-family:var(--display);letter-spacing:.04em">${esc(a.title)}</b><span class="mono dim" style="font-size:11px">${esc(a.code)}</span>${UI.DataSourceBadge(a.data_label)}</div>
          <div style="margin-top:6px"><span class="dim">Location:</span> ${esc(a.location)}</div>
          <div class="vals"><div><small>${esc(a.pollutant)} CURRENT</small><b>${esc(a.current_value)}</b> <span class="dim mono" style="font-size:11px">${esc(a.unit)}</span></div><div><small>PREDICTED</small><b class="accent">${esc(a.predicted_value)}</b> <span class="dim mono" style="font-size:11px">${esc(a.unit)}</span></div><div><small>CONFIDENCE</small><b>${esc(a.confidence)}%</b></div></div>
          <div class="ev-tags"><span class="dim" style="border:none;padding-left:0">Evidence:</span>${(a.evidence || []).map((e) => `<span>${esc(e)}</span>`).join("")}</div>
          <div class="mono dim" style="font-size:10.5px;margin-top:10px">${new Date(a.created_at).toLocaleString()} · ${esc(a.origin)} · STATUS: <span class="${a.status === "NEW" ? "c-warn" : a.status === "RESOLVED" ? "c-ok" : "c-info"}">${esc(a.status_label)}</span>${a.acknowledged_by ? " · ack " + esc(a.acknowledged_by) : ""}${a.resolved_by ? " · resolved " + esc(a.resolved_by) : ""}</div>
        </div>
        <div class="acts">
          ${hs ? `<a class="btn sm" href="/map/?hotspot=${hs}">View event</a><a class="btn sm" href="/investigate/?hotspot=${hs}">Investigate</a>` : ""}
          <button class="btn sm" data-act="acknowledge" ${a.status !== "NEW" ? "disabled" : ""} ${canAct ? "" : 'title="Authority sign-in required"'}>Acknowledge</button>
          <button class="btn sm primary" data-act="resolve" ${a.status === "RESOLVED" ? "disabled" : ""}>Mark resolved</button>
        </div></div>`;
    },
    ActivityFeed(items) {
      return items.map((f, i) => `<div class="feed-i" style="animation-delay:${i * 0.05}s"><i class="dot ${f.kind === "alert" ? (f.severity === "CRITICAL" ? "" : "a") : "w"}" style="${f.kind === "alert" && f.severity === "CRITICAL" ? "background:#EF4444;box-shadow:0 0 8px #EF4444" : f.kind === "report" ? "background:#3B82F6;box-shadow:0 0 8px #3B82F6" : ""}"></i><div><b>${esc(f.title)}</b><span>${esc(f.text)}</span></div><time>${ago(f.t)}</time></div>`).join("");
    },
    AIAnalysisPanel(res) {
      const a = res.assessment, img = res.image_analysis;
      return `<div class="result-box">
        <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap"><div class="eyebrow accent">AI ASSESSMENT</div>${UI.DataSourceBadge(img.source)}</div>
        <h2 style="font-size:26px;margin:10px 0 6px">${esc(a.label)}</h2>
        <div style="display:flex;gap:30px;flex-wrap:wrap;margin:12px 0">
          <div><div class="eyebrow">Confidence</div><div class="big-read">${esc(a.confidence)}<small>%</small></div></div>
          <div><div class="eyebrow">Status</div><div class="verify" style="margin-top:8px">${esc(a.status_label.toUpperCase())}</div></div>
        </div>
        <div class="eyebrow" style="margin-top:6px">Visual indicators</div>
        <ul style="margin:6px 0 12px 18px;font-size:13px;color:var(--muted)">${(img.indicators || []).map((i) => `<li>${esc(i)}</li>`).join("")}</ul>
        <div class="eyebrow">Cross-checks</div>
        <table class="tbl" style="margin:6px 0 10px">${a.checks.map((c) => `<tr><td>${c.ok ? '<span class="c-ok">✓</span>' : '<span class="dim">○</span>'} ${esc(c.label)}</td><td class="mono" style="text-align:right">${esc(c.value)}</td></tr>`).join("")}</table>
        <p class="dim" style="font-size:11.5px">${esc(a.disclaimer)}</p>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><span class="mono dim" style="font-size:11px">REPORT ${esc(res.report.code)}</span>${res.report.hotspot ? `<a class="btn sm" href="/investigate/?hotspot=${encodeURIComponent(res.report.hotspot)}">Investigate linked hotspot →</a><a class="btn sm" href="/map/?hotspot=${encodeURIComponent(res.report.hotspot)}">View on map</a>` : ""}</div>
      </div>`;
    },
    ForecastChart(canvas, labels, datasets, opts = {}) {
      if (!window.Chart || !canvas) return null;
      if (canvas._chart) canvas._chart.destroy();
      const ch = new Chart(canvas, {
        type: opts.type || "line",
        data: { labels, datasets },
        options: Object.assign({
          responsive: true, maintainAspectRatio: false, animation: { duration: 900, easing: "easeOutQuart" },
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { display: datasets.length > 1, labels: { boxWidth: 10, boxHeight: 2 } }, tooltip: { backgroundColor: "#0B0B0B", borderColor: "#27272A", borderWidth: 1, titleFont: { family: "JetBrains Mono" }, bodyFont: { family: "JetBrains Mono" } } },
          scales: opts.type === "doughnut" ? {} : { x: { grid: { color: "#141416" }, ticks: { maxTicksLimit: 8 } }, y: { grid: { color: "#141416" }, beginAtZero: !!opts.zero } },
        }, opts.options || {}),
      });
      canvas._chart = ch; return ch;
    },
    MapPanel(el, opts = {}) {
      if (!window.L || !el) return null;
      const m = L.map(el, Object.assign({ zoomControl: !opts.static, attributionControl: true, worldCopyJump: true, minZoom: 2 }, opts.static ? { dragging: false, scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false } : {}))
        .setView(opts.center || [22, 78], opts.zoom || 5);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { subdomains: "abcd", maxZoom: 18, attribution: '&copy; OpenStreetMap &copy; CARTO' }).addTo(m);
      return m;
    },
  };
  window.AirwatchUI = UI;

  function line(color, fill) { return { borderColor: color, backgroundColor: fill || "transparent", borderWidth: 1.6, pointRadius: 0, tension: 0.35, fill: !!fill }; }
  function grad(canvas, color) {
    const g = canvas.getContext("2d").createLinearGradient(0, 0, 0, canvas.clientHeight || 260);
    g.addColorStop(0, color + "55"); g.addColorStop(1, color + "00"); return g;
  }
  if (window.Chart) {
    Chart.defaults.color = "#71717A"; Chart.defaults.borderColor = "#1c1c1f";
    Chart.defaults.font.family = "JetBrains Mono"; Chart.defaults.font.size = 10;
  }
  const hsIcon = (h, metric = "aqi", key = false) => L.divIcon({ className: "", html: `<div class="hs-marker ${key ? "key" : ""}" style="--c:${colorFor(metric, h[metric])}"><i></i></div>`, iconSize: [18, 18], iconAnchor: [9, 9] });
  const divIcon = (cls, size = 10, html = "") => L.divIcon({ className: "", html: `<div class="${cls}">${html}</div>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });

  function destPoint(lat, lng, bearingDeg, km) {
    const b = (bearingDeg * Math.PI) / 180;
    return [lat + (km * Math.cos(b)) / 111, lng + (km * Math.sin(b)) / (111 * Math.max(0.2, Math.cos((lat * Math.PI) / 180)))];
  }
  function plume(h) {
    const b = (h.wind_deg + 180) % 360, len = Math.max(8, h.wind_speed * 1.6);
    const pts = [[h.lat, h.lng]];
    for (let a = -20; a <= 20; a += 5) pts.push(destPoint(h.lat, h.lng, b + a, len * (1 - Math.abs(a) / 90)));
    return L.polygon(pts, { stroke: false, fillColor: colorFor("aqi", h.aqi), fillOpacity: 0.16, interactive: false });
  }
  function arc(a, b, n = 40, lift = 0.22) {
    const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    const dx = b[1] - a[1], dy = b[0] - a[0];
    const ctrl = [mid[0] + dx * lift, mid[1] - dy * lift];
    const pts = [];
    for (let i = 0; i <= n; i++) { const t = i / n; pts.push([(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * ctrl[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * ctrl[1] + t * t * b[1]]); }
    return pts;
  }

  // ---------- global chrome ----------
  function initChrome() {
    const s = $("#global-search");
    if (s) s.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      const v = s.value.trim(); if (!v) return;
      location.href = /^[A-Z]{2}-[A-Z]{2}-\d{4}-\d{3}$/i.test(v) ? `/map/?hotspot=${encodeURIComponent(v.toUpperCase())}` : `/hotspots/?q=${encodeURIComponent(v)}`;
    });
    const clock = $("#clock");
    if (clock) setInterval(() => { clock.textContent = new Date().toLocaleString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }) + " IST"; }, 30000);
    const nc = $("#notif-count");
    if (nc) api("/api/alerts/").then((d) => { nc.textContent = (d.counts.CRITICAL || 0) + (d.counts.HIGH || 0); }).catch(() => { nc.textContent = "!"; });
    const st = $("#api-status");
    if (st) api("/api/status/").then((d) => {
      const live = d.services.filter((x) => x.mode === "LIVE").length;
      st.innerHTML = live ? `<i class="dot"></i> ${live} LIVE` : `<i class="dot w"></i> DEMO`;
    }).catch(() => {});
    const fab = $("#fab"), chat = $("#chat-float");
    if (fab && chat) { fab.addEventListener("click", () => chat.classList.toggle("open")); initChat(chat); }
  }

  // ---------- chat (AIRWATCH AI) ----------
  let lastAnswer = "";
  function initChat(root) {
    const log = $("[data-chat-log]", root), form = $("[data-chat-form]", root), input = $("[data-chat-input]", root), mode = $("[data-chat-mode]", root);
    async function ask(q) {
      if (!q) return;
      log.insertAdjacentHTML("beforeend", `<div class="msg u">${esc(q)}</div>`);
      const typing = document.createElement("div"); typing.className = "msg a typing"; typing.innerHTML = "<span></span><span></span><span></span>";
      log.appendChild(typing); log.scrollTop = log.scrollHeight;
      try {
        const r = await api("/api/assistant/", { method: "POST", body: { message: q } });
        await sleep(350);
        typing.remove(); lastAnswer = r.answer;
        log.insertAdjacentHTML("beforeend", `<div class="msg a">${esc(r.answer)}<span class="src">${UI.DataSourceBadge(r.source)}</span></div>`);
        if (mode) mode.textContent = r.source;
      } catch (e) { typing.remove(); log.insertAdjacentHTML("beforeend", `<div class="msg a c-danger">${esc(e.message)}</div>`); }
      log.scrollTop = log.scrollHeight;
    }
    form.addEventListener("submit", (e) => { e.preventDefault(); const q = input.value.trim(); input.value = ""; ask(q); });
    $$("[data-chat-sugg] .chip", root).forEach((c) => c.addEventListener("click", () => ask(c.textContent)));
  }

  // ---------- pages ----------
  const pages = {};

  pages.landing = async function () {
    const m = UI.MapPanel($("#hero-map"), { static: true, center: [18, 45], zoom: 2 });
    if (!m) return;
    let hs = [];
    try { hs = (await api("/api/hotspots/")).results; } catch (e) { return; }
    $("#ls-hot").textContent = hs.length;
    hs.forEach((h) => L.marker([h.lat, h.lng], { icon: hsIcon(h, "aqi", h.code === KEY), interactive: false }).addTo(m));
    const hubs = { IN: [21.6, 73.0], CN: [38.0, 114.5], RU: [55.7, 37.6], BR: [-23.5, -46.6], ZA: [-26.2, 28.0] };
    const links = [["IN", "CN"], ["IN", "RU"], ["CN", "RU"], ["IN", "ZA"], ["BR", "ZA"], ["IN", "BR"], ["CN", "ZA"]];
    links.forEach(([a, b], i) => {
      L.polyline(arc(hubs[a], hubs[b], 50, 0.18), { color: i % 2 ? C.accent : "#f59e0b", weight: 1, opacity: 0.55, className: "flow-line", interactive: false }).addTo(m);
    });
    let n = 0; const hud = $("#hero-count");
    setInterval(() => {
      const h = hs[Math.floor(Math.random() * hs.length)];
      const c = L.circleMarker([h.lat, h.lng], { radius: 4, color: colorFor("aqi", h.aqi), weight: 1, fillOpacity: 0.4, interactive: false }).addTo(m);
      let r = 4; const t = setInterval(() => { r += 1.4; c.setRadius(r); c.setStyle({ opacity: Math.max(0, 1 - r / 30), fillOpacity: Math.max(0, 0.4 - r / 60) }); if (r > 30) { clearInterval(t); m.removeLayer(c); } }, 40);
      n++; hud.textContent = `EVENTS STREAMED · ${String(n).padStart(4, "0")}`;
    }, 900);
  };

  pages.overview = async function () {
    const d = await api("/api/dashboard/");
    $("#metrics").innerHTML = d.metrics.map(UI.MetricCard).join("");
    $("#feed").innerHTML = UI.ActivityFeed(d.activity);
    $("#top-hotspots").innerHTML = d.top_hotspots.map(UI.HotspotCard).join("");
    $$("#top-hotspots .hcard").forEach((c) => c.addEventListener("click", () => (location.href = `/map/?hotspot=${encodeURIComponent(c.dataset.code)}`)));
    $("#countries").innerHTML = `<table class="tbl">${d.countries.map((c) => `<tr><td><b>${esc(c.name)}</b></td><td class="num">${c.hotspots} hotspots</td><td class="num" style="color:${colorFor("aqi", c.avg_aqi)}">AQI ${c.avg_aqi}</td></tr>`).join("")}</table>`;
    const cv = $("#ov-trend");
    UI.ForecastChart(cv, d.trend.aqi.map((p) => new Date(p.t).getHours() + ":00"), [
      Object.assign({ label: "AQI", data: d.trend.aqi.map((p) => p.v) }, line(C.accent, grad(cv, "#FF6B00"))),
      Object.assign({ label: "PM2.5", data: d.trend.pm25.map((p) => p.v) }, line(C.info)),
    ]);
    const m = UI.MapPanel($("#ov-map"), { center: [22, 60], zoom: 2 });
    if (m) {
      const layers = await api("/api/map/layers/");
      layers.hotspots.forEach((h) => L.marker([h.lat, h.lng], { icon: hsIcon(h, "aqi", h.code === KEY) }).bindTooltip(`${h.code} · AQI ${h.aqi}`).on("click", () => (location.href = `/map/?hotspot=${h.code}`)).addTo(m));
      layers.predictions.forEach((p) => L.polyline(p.path.map((q) => [q.lat, q.lng]), { color: C.accent, weight: 1.5, className: "flow-line" }).addTo(m));
    }
    // live-feeling metric refresh (re-polls API; values only change when data changes)
    setInterval(async () => { try { const x = await api("/api/dashboard/"); $("#feed").innerHTML = UI.ActivityFeed(x.activity); } catch (e) {} }, 30000);
  };

  pages.map = async function () {
    const m = UI.MapPanel($("#live-map"), { center: [22.5, 76], zoom: 5 });
    if (!m) return;
    const data = await api("/api/map/layers/");
    let metric = "aqi";
    const groups = {};
    ["heat", "fire", "industrial", "reports", "wind", "satellite", "forecast", "plume", "hotspots"].forEach((k) => (groups[k] = L.layerGroup()));
    const markers = {};
    function draw() {
      groups.heat.clearLayers(); groups.hotspots.clearLayers(); groups.plume.clearLayers();
      data.hotspots.forEach((h) => {
        const v = h[metric], col = colorFor(metric, v), k = intensity(metric, v);
        [3, 2, 1].forEach((ring) => L.circle([h.lat, h.lng], { radius: 9000 * k * ring, stroke: false, fillColor: col, fillOpacity: 0.07 * (4 - ring), interactive: false }).addTo(groups.heat));
        groups.plume.addLayer(plume(h));
        const mk = L.marker([h.lat, h.lng], { icon: hsIcon(h, metric, h.code === KEY), zIndexOffset: 1000 })
          .bindTooltip(`<b>${h.code}</b><br>${esc(h.region)}<br>${metric.toUpperCase()} ${v} ${UNITS[metric]}`, { direction: "top" })
          .on("click", () => openPanel(h.code));
        markers[h.code] = mk; groups.hotspots.addLayer(mk);
      });
    }
    data.fires.forEach((f) => L.marker([f.lat, f.lng], { icon: divIcon("fire-marker", 7) }).bindTooltip(`Fire detection · ${f.confidence}% · ${f.data_label}`).addTo(groups.fire));
    data.industrial.forEach((z) => L.marker([z.lat, z.lng], { icon: divIcon("ind-marker", 10) }).bindTooltip(`${esc(z.name)} · ${esc(z.sector)}`).addTo(groups.industrial));
    data.reports.forEach((r) => L.marker([r.lat, r.lng], { icon: divIcon("rep-marker", 6) }).bindTooltip(`${r.code} · ${r.type.replace("_", " ")}`).addTo(groups.reports));
    data.wind.forEach((w) => L.marker([w.lat, w.lng], { icon: L.divIcon({ className: "", html: `<div class="wind-arrow" style="transform:rotate(${(w.deg + 180 - 90) % 360}deg)">➤</div>`, iconSize: [14, 14], iconAnchor: [7, 7] }), interactive: false }).addTo(groups.wind));
    data.satellite.forEach((s) => L.marker([s.lat, s.lng], { icon: divIcon("sat-marker", 12) }).bindTooltip(`${esc(s.type_label)} · ${s.data_label}`).addTo(groups.satellite));
    data.predictions.forEach((p) => {
      L.polyline(p.path.map((q) => [q.lat, q.lng]), { color: C.accent, weight: 2, className: "flow-line" }).bindTooltip(`Predicted movement ${p.heading} · ${p.label}`).addTo(groups.forecast);
      p.path.slice(1).forEach((q) => L.circle([q.lat, q.lng], { radius: q.radius_km * 1000, color: C.accent, weight: 1, dashArray: "3 5", fillOpacity: 0.04 }).bindTooltip(`+${q.h} h · simulated`).addTo(groups.forecast));
    });
    draw();
    ["heat", "plume", "fire", "industrial", "reports", "wind", "forecast", "hotspots"].forEach((k) => groups[k].addTo(m));
    $$("[data-metric] .chip").forEach((c) => c.addEventListener("click", () => {
      $$("[data-metric] .chip").forEach((x) => x.classList.remove("on")); c.classList.add("on");
      metric = c.dataset.m; $("#legend-metric").textContent = c.textContent; draw();
    }));
    $$("[data-layers] .chip").forEach((c) => c.addEventListener("click", () => {
      c.classList.toggle("on"); const g = groups[c.dataset.l];
      if (c.classList.contains("on")) g.addTo(m); else m.removeLayer(g);
      if (c.dataset.l === "satellite") $("#scan").classList.toggle("on", c.classList.contains("on"));
    }));
    $("#more-layers").addEventListener("click", (e) => { e.preventDefault(); $("#layers").classList.toggle("expanded"); });

    const panel = $("#hot-panel");
    async function openPanel(code) {
      panel.classList.add("open");
      panel.innerHTML = `<div class="panel-b"><div class="skel" style="height:20px;width:60%"></div><div class="skel" style="height:60px;margin-top:14px"></div></div>`;
      const h = await api(`/api/hotspots/${encodeURIComponent(code)}/`);
      m.flyTo([h.lat, h.lng], Math.max(m.getZoom(), 9), { duration: 1.1 });
      panel.innerHTML = `<button class="close" aria-label="Close">×</button>
        <div class="panel-b" style="display:grid;gap:14px">
          <div><div class="eyebrow accent">HOTSPOT</div><h2 class="mono" style="font-size:17px;margin-top:4px">#${esc(h.code)}</h2></div>
          <dl class="kv"><dt>Location</dt><dd>${esc(h.region.split("—").pop().trim())}, ${esc(h.country)}</dd><dt>Region</dt><dd>${esc(h.city)}</dd><dt>Status</dt><dd>${UI.Severity(h.status)}</dd></dl>
          <div><div class="eyebrow">Current PM2.5</div><div class="big-read" style="color:${colorFor("pm25", h.pm25)}">${h.pm25}<small>μg/m³</small></div><div class="mono dim" style="font-size:11px;margin-top:4px">Predicted ${h.predicted_pm25} μg/m³ · AQI ${h.aqi}</div></div>
          <div><div class="eyebrow">AI Confidence</div><div style="margin-top:6px">${UI.ConfidenceBadge(h.confidence)}</div></div>
          <div><div class="eyebrow">Sources</div><div class="ev-tags" style="margin-top:6px">${h.sources.map((s) => `<span>${esc(s)}</span>`).join("")}</div></div>
          <div><div class="eyebrow" style="margin-bottom:6px">Evidence chain</div>${UI.EvidencePanel(h.evidence)}</div>
          <div class="chart-box sm"><canvas id="hp-chart"></canvas></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><a class="btn primary" href="/investigate/?hotspot=${encodeURIComponent(h.code)}">AI Investigate</a><a class="btn" href="/forecast/?hotspot=${encodeURIComponent(h.code)}">Forecast</a></div>
          <div>${UI.DataSourceBadge(h.data_label)} <span class="dim" style="font-size:11px">Assessment — requires verification.</span></div>
        </div>`;
      $(".close", panel).addEventListener("click", () => panel.classList.remove("open"));
      const cv = $("#hp-chart");
      UI.ForecastChart(cv, h.readings.map((r) => new Date(r.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), [Object.assign({ label: "PM2.5", data: h.readings.map((r) => r.pm25) }, line(C.accent, grad(cv, "#FF6B00")))], { options: { plugins: { legend: { display: false } } } });
      const mv = h.movement;
      if (mv) L.polyline(mv.path.map((q) => [q.lat, q.lng]), { color: "#fff", weight: 1.5, className: "flow-line" }).addTo(groups.forecast);
    }
    const focus = params.get("hotspot");
    if (focus) openPanel(focus);
  };

  pages.hotspots = async function () {
    let country = "", status = "";
    const q = params.get("q") || "";
    async function load() {
      const u = new URLSearchParams({ country, status, q });
      const d = await api(`/api/hotspots/?${u}`);
      $("#hs-count").textContent = d.count;
      $("#hs-list").innerHTML = d.results.map(UI.HotspotCard).join("") || '<p class="dim">No hotspots match.</p>';
      $$("#hs-list .hcard").forEach((c) => c.addEventListener("click", () => detail(c.dataset.code)));
      if (d.results[0]) detail(d.results.find((h) => h.code === KEY) ? KEY : d.results[0].code);
    }
    async function detail(code) {
      const h = await api(`/api/hotspots/${encodeURIComponent(code)}/`);
      $("#hs-detail").innerHTML = `<div class="panel-h"><h3>#${esc(h.code)}</h3>${UI.Severity(h.status)}</div>
        <div class="panel-b" style="display:grid;gap:14px"><div><b>${esc(h.region)}</b><div class="dim" style="font-size:12px">${esc(h.country)} · ${esc(h.source_category)}</div></div>
        <dl class="kv"><dt>PM2.5</dt><dd>${h.pm25} μg/m³</dd><dt>PM10</dt><dd>${h.pm10} μg/m³</dd><dt>NO2 / SO2</dt><dd>${h.no2} / ${h.so2}</dd><dt>Wind</dt><dd>${h.wind_dir} ${h.wind_speed} km/h</dd><dt>Projected heading</dt><dd>${h.movement.heading} → ${esc(h.movement.toward)}</dd><dt>Confidence</dt><dd>${UI.ConfidenceBadge(h.confidence)}</dd></dl>
        <div class="eyebrow">EVIDENCE CHAIN</div>${UI.EvidencePanel(h.evidence)}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><a class="btn primary" href="/investigate/?hotspot=${encodeURIComponent(h.code)}">Investigate</a><a class="btn" href="/map/?hotspot=${encodeURIComponent(h.code)}">On map</a></div></div>`;
    }
    $$("#hs-country .chip").forEach((c) => c.addEventListener("click", () => { $$("#hs-country .chip").forEach((x) => x.classList.remove("on")); c.classList.add("on"); country = c.dataset.c; load(); }));
    $$("#hs-status .chip").forEach((c) => c.addEventListener("click", () => { $$("#hs-status .chip").forEach((x) => x.classList.remove("on")); c.classList.add("on"); status = c.dataset.s; load(); }));
    load();
  };

  pages.investigate = async function () {
    const sel = $("#inv-target");
    const list = (await api("/api/hotspots/")).results;
    const want = params.get("hotspot") || KEY;
    sel.innerHTML = list.map((h) => `<option value="${esc(h.code)}" ${h.code === want ? "selected" : ""}>HOTSPOT #${esc(h.code)} — ${esc(h.region)}</option>`).join("");
    let invMap = null;
    $("#inv-run").addEventListener("click", run);
    async function run() {
      const btn = $("#inv-run"); btn.disabled = true;
      $("#inv-state").textContent = "RUNNING"; $("#inv-state").className = "eyebrow accent";
      $("#inv-result-panel").style.display = "none"; $("#inv-extra").style.display = "none";
      $("#inv-chain").innerHTML = '<p class="dim mono" style="font-size:12px">Gathering evidence…</p>';
      $("#agent").innerHTML = '<div class="step run"><span class="ck"></span><span>Initialising investigation agent…</span><span class="d"></span></div>';
      let r;
      try { r = await api("/api/ai/investigate/", { method: "POST", body: { hotspot: sel.value } }); }
      catch (e) { toast(e.message); btn.disabled = false; return; }
      $("#inv-engine").textContent = `AGENT · ${r.result.source}`;
      $("#agent").innerHTML = r.steps.map((s) => `<div class="step" data-i="${s.id}"><span class="ck"></span><span>${esc(s.label)}</span><span class="d">${esc(s.detail)}</span></div>`).join("");
      for (const s of r.steps) {
        const el = $(`.step[data-i="${s.id}"]`); el.classList.add("run"); await sleep(520);
        el.classList.remove("run"); el.classList.add("done"); $(".ck", el).textContent = "✓";
      }
      $("#inv-chain").innerHTML = UI.EvidencePanel(r.evidence);
      await sleep(400);
      const res = r.result;
      $("#inv-result").innerHTML = `<div class="result-box">
          <div class="eyebrow accent">AI INVESTIGATION RESULT</div>
          <h2 style="font-size:24px;margin:10px 0 12px">${esc(res.headline)}</h2>
          <div class="eyebrow">Evidence</div>
          <ul style="margin:8px 0 14px 18px;display:grid;gap:6px;font-size:13.5px">${res.findings.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
          <div style="display:flex;gap:30px;flex-wrap:wrap;align-items:flex-end"><div><div class="eyebrow">Confidence</div><div class="big-read">${esc(res.confidence)}<small>%</small></div></div><div class="verify">STATUS: ${esc(res.status)}</div></div>
          <div class="eyebrow" style="margin-top:16px">Possible source categories</div>
          <table class="tbl">${res.possible_sources.map((p) => `<tr><td>${esc(p.category)}</td><td class="dim" style="text-align:right">${esc(p.likelihood)}</td></tr>`).join("")}</table>
        </div>
        <div style="display:grid;gap:14px;align-content:start">
          <div><div class="eyebrow">Situation summary ${UI.DataSourceBadge(res.source)}</div><p style="margin-top:8px;font-size:13.5px;color:#d4d4d8">${esc(r.summary)}</p></div>
          <div><div class="eyebrow">Spike probability · ${UI.DataSourceBadge(r.spike.label)}</div>${r.spike.probabilities.slice(0, 3).map((p) => `<div class="prob"><span>${esc(p.horizon)}</span><div class="track"><i style="width:${p.probability}%"></i></div><b>${p.probability}%</b></div>`).join("")}</div>
          ${r.alert ? `<div class="panel" style="border-color:${STATUS_COLOR[r.alert.severity]}"><div class="panel-b"><div class="eyebrow">${r.alert.created_now ? "AUTHORITY ALERT GENERATED" : "LINKED AUTHORITY ALERT"}</div><div style="display:flex;gap:8px;align-items:center;margin-top:8px">${UI.Severity(r.alert.severity)}<span class="mono">${esc(r.alert.code)}</span><span class="dim">· ${esc(r.alert.status_label)}</span></div><a class="btn sm" style="margin-top:10px" href="/alerts/">Open Alert Center →</a></div></div>` : ""}
          <p class="dim" style="font-size:11.5px">${esc(r.disclaimer)}</p>
        </div>`;
      $("#inv-result-panel").style.display = ""; $("#inv-extra").style.display = "";
      const cv = $("#inv-chart");
      UI.ForecastChart(cv, r.readings.map((x) => new Date(x.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), [Object.assign({ label: "PM2.5 μg/m³", data: r.readings.map((x) => x.pm25) }, line(C.accent, grad(cv, "#FF6B00")))]);
      if (!invMap) invMap = UI.MapPanel($("#inv-map"), { center: [r.hotspot.lat, r.hotspot.lng], zoom: 10 });
      if (invMap) {
        invMap.eachLayer((l) => { if (!(l instanceof L.TileLayer)) invMap.removeLayer(l); });
        invMap.invalidateSize();
        const h = r.hotspot;
        L.marker([h.lat, h.lng], { icon: hsIcon(h, "aqi", true) }).addTo(invMap);
        const pts = r.movement.path.map((q) => [q.lat, q.lng]);
        L.polyline(pts, { color: C.accent, weight: 2.5, className: "flow-line" }).addTo(invMap);
        r.movement.path.slice(1).forEach((q) => L.circle([q.lat, q.lng], { radius: q.radius_km * 1000, color: C.accent, weight: 1, dashArray: "3 5", fillOpacity: 0.06 }).bindTooltip(`+${q.h} h`).addTo(invMap));
        invMap.fitBounds(L.latLngBounds(pts).pad(0.4));
      }
      $("#inv-state").textContent = "COMPLETE"; $("#inv-state").className = "eyebrow c-ok";
      btn.disabled = false;
      $("#inv-result-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (params.get("hotspot") || params.get("auto")) run();
  };

  pages.forecast = async function () {
    const sel = $("#fc-city");
    let first = true;
    async function load() {
      const city = sel.value;
      const hs = params.get("hotspot") || KEY;
      const d = await api(city ? `/api/forecast/?city=${encodeURIComponent(city)}` : `/api/forecast/?hotspot=${encodeURIComponent(hs)}`);
      if (first) { sel.innerHTML = `<option value="">${esc(d.hotspot || hs)} (hotspot)</option>` + d.cities.map((c) => `<option>${esc(c)}</option>`).join(""); first = false; }
      $("#fc-title").textContent = d.title;
      $("#fc-label").textContent = d.label;
      $("[data-model]").textContent = d.model_source;
      $("#horizons").innerHTML = d.horizons.map((h, i) => `<div><div class="eyebrow">${esc(h.label)}</div><b style="color:${i ? colorFor("aqi", h.aqi) : "#fff"}">${h.aqi}</b><div class="mono dim" style="font-size:11px">AQI · ${i ? "simulated" : "reference"}</div></div>`).join("");
      $("#spike").innerHTML = d.spike.probabilities.map((p) => `<div class="prob"><span>${esc(p.horizon)}</span><div class="track"><i data-w="${p.probability}"></i></div><b>${p.probability}%</b></div>`).join("") +
        `<div class="kv" style="margin-top:12px"><dt>Risk category</dt><dd>${UI.Severity(d.spike.risk)}</dd><dt>Model confidence</dt><dd>${d.spike.confidence}%</dd></div>`;
      requestAnimationFrame(() => $$("#spike .track i").forEach((i) => (i.style.width = i.dataset.w + "%")));
      $("#fc-features").innerHTML = d.features_used.map((f) => `<span>${esc(f)}</span>`).join("");
      const lbl = d.series.map((s) => `+${s.h}h`);
      const cv = $("#fc-main");
      UI.ForecastChart(cv, lbl, [
        Object.assign({ label: "AQI", data: d.series.map((s) => s.aqi) }, line(C.accent, grad(cv, "#FF6B00"))),
        Object.assign({ label: "PM2.5", data: d.series.map((s) => s.pm25) }, line(C.info)),
        Object.assign({ label: "PM10", data: d.series.map((s) => s.pm10) }, line(C.purple)),
      ]);
      const small = (id, key, col) => UI.ForecastChart($(id), lbl, [Object.assign({ label: key, data: d.series.map((s) => s[key]) }, line(col, grad($(id), col)))], { options: { plugins: { legend: { display: false } } } });
      small("#fc-temp", "temperature", "#F59E0B"); small("#fc-hum", "humidity", "#3B82F6"); small("#fc-wind", "wind_speed", "#22C55E");
    }
    sel.addEventListener("change", load);
    load();
  };

  pages["cross-border"] = async function () {
    const d = await api("/api/cross-border/");
    const m = UI.MapPanel($("#xb-map"), { center: [15, 60], zoom: 2 });
    if (m) {
      d.countries.forEach((c) => L.marker([c.lat, c.lng], { icon: L.divIcon({ className: "", html: `<div class="mono" style="font-size:10px;letter-spacing:.2em;color:#fff;white-space:nowrap;text-shadow:0 0 6px #000"><span class="accent">◆</span> ${esc(c.name.toUpperCase())}</div>`, iconSize: [120, 14], iconAnchor: [8, 7] }) }).addTo(m));
      d.events.forEach((e) => {
        const pts = arc([e.origin_lat, e.origin_lng], [e.affected_lat, e.affected_lng], 50, 0.2);
        L.polyline(pts, { color: C.accent, weight: 2, className: "flow-line" }).bindTooltip(`${e.code} · ${e.corridor}`).addTo(m);
        L.circleMarker([e.origin_lat, e.origin_lng], { radius: 6, color: C.danger, fillOpacity: 0.6 }).bindTooltip(`${e.origin} (origin)`).addTo(m);
        L.circleMarker([e.affected_lat, e.affected_lng], { radius: 6, color: C.warn, fillOpacity: 0.3, dashArray: "2 3" }).bindTooltip(`${e.affected} (potentially affected)`).addTo(m);
      });
    }
    $("#xb-events").innerHTML = d.events.map((e) => `<div style="border:1px solid var(--line);padding:14px;border-radius:3px;background:var(--bg1)">
      <div style="display:flex;justify-content:space-between;gap:8px"><span class="eyebrow accent">CROSS-BORDER EVENT · ${esc(e.code)}</span>${UI.Severity(e.risk)}</div>
      <dl class="kv" style="margin:10px 0"><dt>Origin</dt><dd>${esc(e.origin)} <span class="dim">(${esc(e.origin_country)})</span></dd><dt>Potentially affected</dt><dd>${esc(e.affected)} <span class="dim">(${esc(e.affected_country)})</span></dd><dt>Estimated movement</dt><dd>${esc(e.direction)}</dd><dt>Forecast window</dt><dd>${esc(e.window)}</dd><dt>Confidence</dt><dd>${e.confidence}%</dd></dl>
      <div class="traj"><span class="o">SOURCE REGION</span><i>→</i><span>Wind trajectory</span><i>→</i><span class="t">${esc(e.corridor)}</span><i>→</i><span>Affected region</span></div>
      <div style="margin-top:8px">${UI.DataSourceBadge(e.data_label)}</div></div>`).join("");
    $("#xb-table tbody").innerHTML = d.countries.map((c) => `<tr><td><b>${esc(c.name)}</b></td><td class="num">${c.active_events}</td><td class="num">${c.predicted_events}</td><td class="num" style="color:${colorFor("aqi", c.avg_aqi)}">${c.avg_aqi}</td><td class="mono" style="font-size:11px">${esc(c.shared_model_status)} · ${esc(c.model_version)}</td><td>${UI.Severity(c.cross_border_risk)}</td></tr>`).join("");
    $("#fed-nodes").innerHTML = d.countries.map((c) => `<div class="fed-node"><b>${esc(c.name.toUpperCase())} MODEL</b>${esc(c.model_version)}<div class="lock">RAW DATA STAYS IN-COUNTRY</div></div>`).join("");
  };

  pages.report = function () {
    let ptype = "unknown", file = null, lat = 21.628, lng = 73.02, transcript = "";
    const lm = UI.MapPanel($("#loc-map"), { center: [lat, lng], zoom: 12 });
    let pin = lm ? L.marker([lat, lng], { icon: hsIcon({ aqi: 250 }, "aqi", true) }).addTo(lm) : null;
    const setLoc = (a, b, label) => {
      lat = +a.toFixed(5); lng = +b.toFixed(5);
      $("#loc-coords").textContent = `${lat}, ${lng}${label ? " · " + label : ""}`;
      if (pin) pin.setLatLng([lat, lng]); if (lm) lm.setView([lat, lng], Math.max(lm.getZoom(), 12));
    };
    if (lm) lm.on("click", (e) => setLoc(e.latlng.lat, e.latlng.lng, "manually selected"));
    $("#geo-btn").addEventListener("click", () => {
      if (!navigator.geolocation) return toast("Geolocation not available");
      navigator.geolocation.getCurrentPosition((p) => { setLoc(p.coords.latitude, p.coords.longitude, "auto detected"); $("#loc-label").value = $("#loc-label").value || "Auto-detected location"; }, () => toast("Location permission denied — tap the map instead."));
    });
    $$("#ptype .chip").forEach((c) => c.addEventListener("click", () => { $$("#ptype .chip").forEach((x) => x.classList.remove("on")); c.classList.add("on"); ptype = c.dataset.v; }));
    const setType = (v) => { const c = $(`#ptype .chip[data-v="${v}"]`); if (c) c.click(); };
    function onFile(f, src) {
      if (!f) return;
      if (f.size > 5 * 1024 * 1024) return toast("Image exceeds 5 MB limit");
      if (!/^image\/(jpeg|png|webp)$/.test(f.type)) return toast("Use a JPG, PNG or WEBP image");
      file = f; $("#preview").style.display = "block"; $("#preview-img").src = URL.createObjectURL(f);
      $$(".cap-btn").forEach((b) => b.classList.remove("on")); $(src).classList.add("on");
    }
    $("#img-input").addEventListener("change", (e) => onFile(e.target.files[0], "#cap-upload"));
    $("#cam-input").addEventListener("change", (e) => onFile(e.target.files[0], "#cap-camera"));

    // voice pipeline
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const SAMPLE = { en: "Heavy smoke from crop burning near the highway, visibility is low", hi: "खेत में पराली जल रही है, बहुत धुआं है", gu: "ખેતરમાં પરાળ સળગે છે, ઘણો ધુમાડો છે", mr: "शेतात पराली जाळली जात आहे, खूप धूर आहे" };
    let rec = null, listening = false;
    $("#cap-voice").addEventListener("click", async () => {
      const langSel = $("#lang"), code = langSel.value, bcp = langSel.selectedOptions[0].dataset.bcp;
      $("#voice-box").style.display = "block";
      if (listening && rec) { rec.stop(); return; }
      if (SR) {
        rec = new SR(); rec.lang = bcp; rec.interimResults = true; rec.maxAlternatives = 1;
        listening = true; $("#voice-lbl").innerHTML = '<span class="rec"></span> Listening… tap to stop'; $("#voice-mode").textContent = `BROWSER SPEECH-TO-TEXT · ${bcp}`;
        rec.onresult = (e) => { transcript = Array.from(e.results).map((r) => r[0].transcript).join(" "); $("#voice-out").textContent = transcript; };
        rec.onerror = (e) => { toast(`Speech error: ${e.error}`); };
        rec.onend = () => { listening = false; $("#voice-lbl").textContent = "Speak Report"; if (transcript) processVoice(code); };
        rec.start();
      } else {
        transcript = SAMPLE[code] || SAMPLE.en;
        $("#voice-mode").textContent = "SIMULATED VOICE INPUT (browser speech API unavailable)";
        $("#voice-out").textContent = transcript; processVoice(code);
      }
    });
    async function processVoice(code) {
      const steps = $$("#voice-pipe span");
      steps.forEach((s) => s.classList.remove("t"));
      for (let i = 0; i < 2; i++) { steps[i].classList.add("t"); await sleep(250); }
      try {
        const r = await api("/api/voice/process/", { method: "POST", body: { transcript, language: code } });
        for (let i = 2; i < steps.length; i++) { steps[i].classList.add("t"); await sleep(250); }
        $("#voice-out").innerHTML = `<div>TRANSCRIPT: ${esc(r.transcript)}</div><div>EN: ${esc(r.translated)} <span class="dim">[${esc(r.translation_mode)}]</span></div><div class="accent">INTENT: ${esc(r.intent.intent)} · type=${esc(r.intent.pollution_type)}</div>`;
        $("#desc").value = r.translated && r.translation_mode === "LIVE" ? `${r.translated} (orig: ${r.transcript})` : r.transcript;
        if (r.intent.pollution_type !== "unknown") setType(r.intent.pollution_type);
      } catch (e) { toast(e.message); }
    }

    $("#report-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $("#submit-btn"); btn.disabled = true;
      const fd = new FormData();
      fd.append("pollution_type", ptype); fd.append("lat", lat); fd.append("lng", lng);
      fd.append("description", $("#desc").value.slice(0, 1000)); fd.append("location_label", $("#loc-label").value.slice(0, 128));
      fd.append("language", $("#lang").value); fd.append("voice_transcript", transcript.slice(0, 2000));
      if (file) fd.append("image", file, file.name);
      $("#proc-panel").style.display = "block"; $("#assessment").innerHTML = "";
      if (file) $("#preview").classList.add("scanning");
      const labels = ["ANALYZING IMAGE", "VERIFYING LOCATION", "CHECKING WEATHER", "CHECKING NEARBY OBSERVATIONS", "CROSS-REFERENCING SATELLITE DATA"];
      $("#proc").innerHTML = labels.map((l) => `<div>${l}</div>`).join("");
      $("#proc-panel").scrollIntoView({ behavior: "smooth", block: "center" });
      const req = api("/api/reports/", { method: "POST", body: fd });
      const rows = $$("#proc div");
      for (const r of rows) { r.classList.add("run"); await sleep(650); r.classList.remove("run"); r.classList.add("done"); }
      try {
        const res = await req;
        $("#assessment").innerHTML = UI.AIAnalysisPanel(res);
        $("#assessment").scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        $("#assessment").innerHTML = `<div class="banner" style="color:#fca5a5;border-color:rgba(239,68,68,.4)">Submission failed: ${esc(err.message)}</div>`;
      }
      $("#preview").classList.remove("scanning"); btn.disabled = false;
    });
  };

  pages.reports = async function () {
    const d = await api("/api/reports/");
    $("#rp-total").textContent = d.count.toLocaleString();
    $("#rp-rows").innerHTML = d.results.map((r) => `<tr><td class="mono" style="font-size:11px">${esc(r.code)}</td><td>${esc(r.pollution_type_label)}</td><td>${esc(r.location_label)}</td><td>${esc(r.ai_label || "—")} ${r.ai_confidence ? `<span class="dim mono">${r.ai_confidence}%</span>` : ""}</td><td><span class="mono" style="font-size:10.5px;color:${r.status === "CORROBORATED" ? C.ok : r.status === "DISMISSED" ? "#71717A" : C.warn}">${esc(r.status_label)}</span></td><td class="mono dim">${ago(r.created_at)}</td></tr>`).join("");
    const keys = Object.keys(d.by_type);
    UI.ForecastChart($("#rp-types"), keys.map((k) => k.replace("_", " ")), [{ data: keys.map((k) => d.by_type[k]), backgroundColor: [C.accent, C.warn, C.danger, C.info, C.purple, "#52525b"], borderColor: "#0B0B0B", borderWidth: 2 }], { type: "doughnut", options: { cutout: "68%", plugins: { legend: { display: true, position: "bottom" } } } });
  };

  pages.alerts = async function () {
    const canAct = ["authority", "admin"].includes(document.body.dataset.role);
    let filter = "";
    async function load() {
      const d = await api(`/api/alerts/${filter ? "?severity=" + filter : ""}`);
      $("#sev-sum").innerHTML = ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => `<div class="panel ${filter === s ? "on" : ""}" style="--c:${STATUS_COLOR[s]}" data-s="${s}"><span class="eyebrow">${s}</span><b>${d.counts[s]}</b><span class="dim mono" style="font-size:10.5px">open alerts</span></div>`).join("");
      $$("#sev-sum .panel").forEach((p) => p.addEventListener("click", () => { filter = filter === p.dataset.s ? "" : p.dataset.s; load(); }));
      $("#alert-list").innerHTML = d.results.map((a) => UI.AlertCard(a, canAct)).join("") || '<p class="dim">No alerts.</p>';
      $$("#alert-list [data-act]").forEach((b) => b.addEventListener("click", async () => {
        const code = b.closest(".alert-card").dataset.code;
        try { await api(`/api/alerts/${encodeURIComponent(code)}/${b.dataset.act}/`, { method: "POST", body: {} }); toast(`${code} ${b.dataset.act === "resolve" ? "marked resolved" : "acknowledged"} · audit logged`); load(); }
        catch (e) { toast(e.status === 403 ? "Authority sign-in required for this action." : e.message); }
      }));
    }
    load();
  };

  pages.data = async function () {
    const f = { country: $("#f-country"), city: $("#f-city"), days: $("#f-days"), pollutant: $("#f-pollutant"), source: $("#f-source"), confidence: $("#f-conf"), event_type: $("#f-event") };
    let populated = false;
    async function load() {
      const q = new URLSearchParams(Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value])));
      const d = await api(`/api/data/?${q}`);
      if (!populated) { f.country.innerHTML = d.options.countries.map((c) => `<option value="${c.code}" ${c.code === "IN" ? "selected" : ""}>${esc(c.name)}</option>`).join("") + '<option value="AL">All BRICS</option>'; populated = true; }
      const curCity = f.city.value;
      f.city.innerHTML = '<option value="">All cities</option>' + d.options.cities.map((c) => `<option ${c === curCity ? "selected" : ""}>${esc(c)}</option>`).join("");
      $("#dx-storage").textContent = `Storage: ${d.storage} · tables: ${d.tables.join(", ")}`;
      $("#dx-trend-title").textContent = `${f.pollutant.selectedOptions[0].text} Trends`;
      const names = Object.keys(d.trends), palette = [C.accent, C.info, C.warn, C.purple, C.ok, "#f472b6"];
      const labels = names.length ? d.trends[names[0]].map((p) => p.d.slice(5)) : [];
      UI.ForecastChart($("#dx-trend"), labels, names.map((n, i) => Object.assign({ label: n, data: d.trends[n].map((p) => p.v) }, line(palette[i % 6]))));
      UI.ForecastChart($("#dx-fires"), d.fires.map((p) => p.d.slice(5)), [{ label: "Fire events", data: d.fires.map((p) => p.v), backgroundColor: "#FF6B00aa", borderRadius: 1 }], { type: "bar", zero: true, options: { plugins: { legend: { display: false } } } });
      UI.ForecastChart($("#dx-reports"), d.reports_per_day.map((p) => p.d.slice(5)), [{ label: "Reports", data: d.reports_per_day.map((p) => p.v), backgroundColor: "#3B82F6aa", borderRadius: 1 }], { type: "bar", zero: true, options: { plugins: { legend: { display: false } } } });
      UI.ForecastChart($("#dx-scatter"), undefined, [{ label: "City-day", data: d.weather_correlation.map((p) => ({ x: p.x, y: p.y })), backgroundColor: "#FF6B0066", pointRadius: 2.5 }], { type: "scatter", options: { plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "Wind speed km/h" }, grid: { color: "#141416" } }, y: { title: { display: true, text: "AQI" }, grid: { color: "#141416" } } } } });
      $("#dx-count").textContent = `${d.events.length} events`;
      $("#dx-rows").innerHTML = d.events.map((h) => `<tr><td class="mono" style="font-size:11px"><a class="accent" href="/map/?hotspot=${encodeURIComponent(h.code)}">${esc(h.code)}</a></td><td>${esc(h.region)}</td><td>${esc(h.country)}</td><td class="num">${h.aqi}</td><td class="num">${h.pm25}</td><td>${esc(h.source_category)}</td><td>${UI.Severity(h.status)}</td><td>${UI.ConfidenceBadge(h.confidence)}</td></tr>`).join("");
    }
    Object.values(f).forEach((el) => el.addEventListener("change", (e) => { if (e.target === f.country) f.city.value = ""; load(); }));
    load();
  };

  pages.analytics = async function () {
    const codes = [["IN", "India"], ["BR", "Brazil"], ["RU", "Russia"], ["CN", "China"], ["ZA", "South Africa"]];
    const res = await Promise.all(codes.map(([c]) => api(`/api/data/?country=${c}&days=90`)));
    let labels = [];
    const ds = res.map((d, i) => {
      const names = Object.keys(d.trends);
      if (!names.length) return null;
      const n = d.trends[names[0]].length;
      if (!labels.length) labels = d.trends[names[0]].map((p) => p.d.slice(5));
      const mean = Array.from({ length: n }, (_, k) => Math.round(names.reduce((s, nm) => s + (d.trends[nm][k] ? d.trends[nm][k].v : 0), 0) / names.length));
      return Object.assign({ label: codes[i][1], data: mean }, line([C.accent, C.ok, C.info, C.danger, C.purple][i]));
    }).filter(Boolean);
    UI.ForecastChart($("#an-country"), labels, ds);
    const hs = (await api("/api/hotspots/")).results;
    const src = {}; hs.forEach((h) => (src[h.source_category] = (src[h.source_category] || 0) + 1));
    UI.ForecastChart($("#an-sources"), Object.keys(src), [{ data: Object.values(src), backgroundColor: "#FF6B00aa", borderRadius: 1 }], { type: "bar", zero: true, options: { indexAxis: "y", plugins: { legend: { display: false } } } });
    const dash = await api("/api/dashboard/");
    const sb = dash.status_breakdown;
    UI.ForecastChart($("#an-status"), Object.keys(sb), [{ data: Object.values(sb), backgroundColor: [C.danger, C.accent, C.warn, C.ok], borderColor: "#0B0B0B", borderWidth: 2 }], { type: "doughnut", options: { cutout: "65%", plugins: { legend: { display: true, position: "right" } } } });
    const ind = res[0];
    const names = Object.keys(ind.trends);
    const aqiMean = names.length ? ind.trends[names[0]].map((_, k) => Math.round(names.reduce((s, nm) => s + (ind.trends[nm][k] ? ind.trends[nm][k].v : 0), 0) / names.length)) : [];
    UI.ForecastChart($("#an-fire"), ind.fires.map((p) => p.d.slice(5)), [
      { type: "bar", label: "Fire events", data: ind.fires.map((p) => p.v), backgroundColor: "#EF444466", yAxisID: "y1" },
      Object.assign({ type: "line", label: "Mean AQI", data: aqiMean }, line(C.accent)),
    ], { options: { scales: { y: { grid: { color: "#141416" } }, y1: { position: "right", grid: { display: false } } } } });
  };

  pages.assistant = function () {
    initChat($("#chat-inline"));
    $("#tts-btn").addEventListener("click", () => {
      if (!lastAnswer) return toast("Ask a question first.");
      if (!("speechSynthesis" in window)) return toast("Text-to-Speech not supported in this browser.");
      speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(lastAnswer));
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    initChrome();
    const page = $("[data-landing]") ? "landing" : document.body.dataset.page;
    const fn = pages[page];
    if (fn) Promise.resolve(fn()).catch((e) => { console.error(e); toast(`Failed to load: ${e.message}`); });
  });
})();
