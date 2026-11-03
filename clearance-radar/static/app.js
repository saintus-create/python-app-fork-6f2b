/* Clearance Radar front-end. Talks only to relative API URLs on this host. */
"use strict";

const state = {
  lat: null,
  lon: null,
  radius: 25,
  minScore: 60,
  meta: null,
  activeFilters: new Set(), // signal kinds; empty = show all
  stores: [],
};

const $ = (sel) => document.querySelector(sel);

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

function fmtMoney(v) {
  return "$" + Number(v).toFixed(2);
}

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/* ---------- location ---------- */
function setLocation(lat, lon, label) {
  state.lat = lat;
  state.lon = lon;
  $("#lat-input").value = lat.toFixed(4);
  $("#lon-input").value = lon.toFixed(4);
  $("#status-bar").textContent = `Scanning around ${label || lat.toFixed(4) + ", " + lon.toFixed(4)} — radius ${state.radius} km`;
}

function useBrowserLocation() {
  $("#status-bar").textContent = "Requesting your location…";
  if (!navigator.geolocation) {
    fallbackLocation("Geolocation unavailable — using default");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      setLocation(pos.coords.latitude, pos.coords.longitude, "your current position");
      scan();
    },
    () => {
      fallbackLocation("Location permission denied — using default");
      scan();
    },
    { timeout: 8000 }
  );
}

function fallbackLocation(msg) {
  const d = state.meta ? state.meta.default_location : { lat: 34.953, lon: -120.4357, label: "Santa Maria, CA" };
  setLocation(d.lat, d.lon, d.label);
  $("#status-bar").textContent = `${msg} (${d.label}) — radius ${state.radius} km`;
}

/* ---------- scanning ---------- */
async function scan() {
  if (state.lat == null) return;
  const q = `lat=${state.lat}&lon=${state.lon}&radius_km=${state.radius}`;
  try {
    const [nearby, alerts] = await Promise.all([
      api(`/api/nearby?${q}`),
      api(`/api/alerts?${q}&min_score=${state.minScore}`),
    ]);
    state.stores = nearby.stores;
    renderAlerts(alerts);
    await renderStores(q);
  } catch (e) {
    $("#status-bar").textContent = "Error: " + e.message;
  }
}

async function renderStores(q) {
  const host = $("#stores");
  host.innerHTML = "";
  if (!state.stores.length) {
    host.innerHTML = '<div class="empty">No stores found within this radius. Try widening it.</div>';
    return;
  }
  for (const store of state.stores) {
    const detail = await api(`/api/stores/${store.id}`);
    host.appendChild(storeCard(detail, store.distance_km));
  }
}

/* ---------- rendering ---------- */
function signalVisible(item) {
  if (!state.activeFilters.size) return true;
  return item.signals.some((s) => state.activeFilters.has(s.kind));
}

function storeCard(detail, distance) {
  const node = $("#store-card-tpl").content.firstElementChild.cloneNode(true);
  node.querySelector(".store-name").textContent = detail.name;
  node.querySelector(".store-meta").textContent =
    `${detail.address}, ${detail.city}, ${detail.state} · ${detail.chain}` + (detail.phone ? ` · ${detail.phone}` : "");
  node.querySelector(".distance").textContent = `${distance.toFixed(1)} km away`;
  const flagged = detail.items.filter((i) => i.signals.length);
  node.querySelector(".flagged").textContent =
    flagged.length ? `${flagged.length} liquidation item${flagged.length > 1 ? "s" : ""}` : "no flagged items";

  const chips = node.querySelector(".signal-chips");
  const kinds = new Set(flagged.flatMap((i) => i.signals.map((s) => s.kind)));
  for (const k of kinds) {
    const meta = (state.meta.signals.find((s) => s.kind === k) || { label: k, severity: "low" });
    const c = document.createElement("span");
    c.className = `schip ${meta.severity}`;
    c.textContent = meta.label;
    chips.appendChild(c);
  }

  const itemsHost = node.querySelector(".items");
  const visible = detail.items.filter(signalVisible);
  for (const item of visible) itemsHost.appendChild(itemRow(item, detail));
  if (!visible.length) {
    itemsHost.innerHTML = '<div class="empty">No items match the selected signal filters.</div>';
  }
  return node;
}

function itemRow(item, store) {
  const node = $("#item-row-tpl").content.firstElementChild.cloneNode(true);
  node.querySelector(".item-title").textContent = item.name;
  node.querySelector(".item-sub").textContent =
    `${item.category} · SKU ${item.sku} · ${item.quantity} in stock · on shelf ${item.days_on_shelf}d` +
    (item.clearance ? " · clearance" : "") + (item.discontinued ? " · discontinued" : "");

  const badges = node.querySelector(".badges");
  for (const s of item.signals) {
    const b = document.createElement("span");
    b.className = `badge ${s.severity}`;
    b.textContent = s.label;
    b.title = s.detail;
    badges.appendChild(b);
  }

  const priceBlock = node.querySelector(".price-block");
  const penny = item.current_price <= 0.011;
  priceBlock.innerHTML =
    `<span class="price-now ${penny ? "penny" : ""}">${fmtMoney(item.current_price)}</span>` +
    `<span class="price-was">${fmtMoney(item.original_price)}</span>` +
    `<span class="price-off">-${Math.round(item.markdown_pct)}%</span>`;

  node.querySelector(".score-fill").style.width = item.liquidation_score + "%";
  node.querySelector(".score-num").textContent = `${item.liquidation_score} / 100`;

  drawSparkline(node.querySelector(".spark"), item);

  const pred = node.querySelector(".prediction");
  const t = item.trajectory;
  const bits = [];
  if (t.projected_penny_date) {
    const days = Math.round((new Date(t.projected_penny_date) - new Date(t.today)) / 86400000);
    bits.push(`<span class="urgent">purge ~${fmtDate(t.projected_penny_date)} (${days}d)</span>`);
  } else if (t.price_trend === "falling") {
    bits.push(`price falling ${Math.abs(t.price_slope_per_day).toFixed(2)}/day (conf ${Math.round(t.confidence * 100)}%)`);
  }
  if (t.days_until_sold_out != null) {
    bits.push(`sells out in ~${Math.round(t.days_until_sold_out)}d`);
  }
  pred.innerHTML = bits.join(" · ") || "no projection";
  return node;
}

function drawSparkline(canvas, item) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const hist = item.price_history.map((p) => ({ d: new Date(p.date), v: p.price }));
  const proj = (item.trajectory.projection_points || []).map((p) => ({ d: new Date(p.date), v: p.price }));
  const all = hist.concat(proj);
  if (!all.length) return;
  const minV = 0.01, maxV = Math.max(...all.map((p) => p.v), item.original_price) * 1.05;
  const t0 = all[0].d.getTime(), t1 = all[all.length - 1].d.getTime() || t0 + 1;
  const X = (d) => 4 + ((d.getTime() - t0) / (t1 - t0)) * (W - 8);
  const Y = (v) => H - 6 - ((v - minV) / (maxV - minV)) * (H - 12);

  // $0.01 penny line
  ctx.strokeStyle = "rgba(255,92,92,.55)";
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(0, Y(0.01));
  ctx.lineTo(W, Y(0.01));
  ctx.stroke();
  ctx.setLineDash([]);

  // history (solid)
  ctx.strokeStyle = "#ffb020";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  hist.forEach((p, i) => (i ? ctx.lineTo(X(p.d), Y(p.v)) : ctx.moveTo(X(p.d), Y(p.v))));
  ctx.stroke();

  // projection (dashed)
  if (proj.length) {
    ctx.strokeStyle = "rgba(255,92,92,.9)";
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    const start = hist[hist.length - 1];
    ctx.moveTo(X(start.d), Y(start.v));
    proj.forEach((p) => ctx.lineTo(X(p.d), Y(p.v)));
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function renderAlerts(alerts) {
  const panel = $("#alerts-panel");
  const list = $("#alerts-list");
  $("#alerts-count").textContent = alerts.count ? `(${alerts.count})` : "";
  panel.classList.toggle("hidden", !alerts.count);
  list.innerHTML = "";
  for (const a of alerts.alerts.slice(0, 12)) {
    const row = document.createElement("div");
    row.className = "alert-row";
    const kinds = a.signals.map((s) => s.label).join(", ");
    row.innerHTML =
      `<div><strong>${a.name}</strong> <span class="a-store">@ ${a.store.name}, ${a.distance_km.toFixed(1)} km — ${kinds}</span></div>` +
      `<div>${fmtMoney(a.current_price)} <span class="a-store">(was ${fmtMoney(a.original_price)})</span> · <span class="a-score">${a.liquidation_score}</span></div>`;
    list.appendChild(row);
  }
}

function renderFilters() {
  const host = $("#filter-chips");
  host.innerHTML = "";
  for (const s of state.meta.signals) {
    const c = document.createElement("span");
    c.className = "chip" + (state.activeFilters.has(s.kind) ? " active" : "");
    c.textContent = s.label;
    c.onclick = () => {
      if (state.activeFilters.has(s.kind)) state.activeFilters.delete(s.kind);
      else state.activeFilters.add(s.kind);
      renderFilters();
      const q = `lat=${state.lat}&lon=${state.lon}&radius_km=${state.radius}`;
      renderStores(q);
    };
    host.appendChild(c);
  }
}

/* ---------- init ---------- */
(async function init() {
  state.meta = await api("/api/meta");
  renderFilters();
  $("#radius-input").value = state.meta.default_radius_km;
  state.radius = state.meta.default_radius_km;
  $("#radius-label").textContent = state.radius + " km";
  $("#radius-input").oninput = (e) => {
    state.radius = Number(e.target.value);
    $("#radius-label").textContent = state.radius + " km";
  };
  $("#scan-btn").onclick = () => {
    const lat = parseFloat($("#lat-input").value);
    const lon = parseFloat($("#lon-input").value);
    if (!isNaN(lat) && !isNaN(lon)) setLocation(lat, lon, "manual coordinates");
    scan();
  };
  $("#locate-btn").onclick = useBrowserLocation;
  useBrowserLocation();
})();
