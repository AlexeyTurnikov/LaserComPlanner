const token = localStorage.getItem("access_token");

if (!token) {
  window.location.href = "/login";
}

const authHeaders = {
  Authorization: `Bearer ${token}`,
};

const statusColors = {
  available: "#15803d",
  limited: "#ca8a04",
  unavailable: "#dc2626",
  nodata: "#6b7280",
};

const map = L.map("dashboard-map").setView([55.75, 37.62], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
const linkLayer = L.layerGroup().addTo(map);
const terminalList = document.querySelector("#terminal-list");

function logout() {
  localStorage.removeItem("access_token");
}

document.querySelector("#logout-link")?.addEventListener("click", logout);

async function apiGet(url) {
  const response = await fetch(url, {headers: authHeaders});
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  }
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatValue(value, suffix = "") {
  if (value === null || value === undefined) {
    return "No data";
  }
  return `${value}${suffix}`;
}

function popupHtml(item) {
  const status = item.availability_status || "no data";
  return `
    <strong>${item.name}</strong>
    <dl class="details">
      <dt>Status</dt><dd>${status}</dd>
      <dt>Score</dt><dd>${formatValue(item.availability_score)}</dd>
      <dt>Cloud</dt><dd>${formatValue(item.cloud_cover_percent, "%")}</dd>
      <dt>Visibility</dt><dd>${formatValue(item.visibility_m, " m")}</dd>
      <dt>Precipitation</dt><dd>${formatValue(item.precipitation_mm, " mm")}</dd>
      <dt>Wind</dt><dd>${formatValue(item.wind_speed_kmh, " km/h")}</dd>
    </dl>
    <p><a href="/terminals/${item.terminal_id}/view">Open terminal</a></p>
  `;
}

function renderTerminalList(items) {
  terminalList.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("a");
    row.className = "list-item";
    row.href = `/terminals/${item.terminal_id}/view`;
    row.innerHTML = `
      <strong>${item.name}</strong>
      <span class="meta">${item.availability_status || "no data"} · ${formatValue(item.availability_score)}</span>
    `;
    terminalList.appendChild(row);
  }
}

function renderTerminals(items) {
  markerLayer.clearLayers();
  const bounds = [];
  for (const item of items) {
    const status = item.availability_status || "nodata";
    const marker = L.circleMarker([item.latitude, item.longitude], {
      radius: 8,
      color: "#ffffff",
      weight: 2,
      fillColor: statusColors[status],
      fillOpacity: 0.9,
    });
    marker.bindPopup(popupHtml(item));
    marker.addTo(markerLayer);
    bounds.push([item.latitude, item.longitude]);
  }
  if (bounds.length > 0) {
    map.fitBounds(bounds, {padding: [30, 30]});
  }
  renderTerminalList(items);
}

function renderLinks(links) {
  linkLayer.clearLayers();
  for (const link of links) {
    const color = link.is_active ? "#2563eb" : "#9ca3af";
    L.polyline(
      [
        [link.source_latitude, link.source_longitude],
        [link.target_latitude, link.target_longitude],
      ],
      {
        color,
        weight: 3,
        opacity: link.is_active ? 0.65 : 0.35,
      },
    ).addTo(linkLayer);
  }
}

async function loadDashboard() {
  const [availabilityItems, links] = await Promise.all([
    apiGet("/api/v1/availability-map"),
    apiGet("/api/v1/fiber-links/map"),
  ]);
  renderLinks(links);
  renderTerminals(availabilityItems);
}

document.querySelector("#refresh-dashboard").addEventListener("click", loadDashboard);

loadDashboard().catch((error) => {
  terminalList.innerHTML = `<div class="list-item">${error.message}</div>`;
});
