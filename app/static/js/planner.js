const token = localStorage.getItem("access_token");

if (!token) {
  window.location.href = "/login";
}

const authHeaders = {
  Authorization: `Bearer ${token}`,
};

const jsonHeaders = {
  ...authHeaders,
  "Content-Type": "application/json",
};

const map = L.map("planner-map").setView([55.75, 37.62], 6);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
const linkLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);
const form = document.querySelector("#planner-form");
const sourceSelect = document.querySelector("#source-terminal");
const message = document.querySelector("#planner-message");
const result = document.querySelector("#plan-result");
let terminals = [];
let fiberLinks = [];

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

async function apiPost(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  }
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    throw new Error(errorPayload?.detail || "Planning failed");
  }
  return response.json();
}

function terminalById(id) {
  return terminals.find((terminal) => terminal.id === id);
}

function renderTerminals() {
  markerLayer.clearLayers();
  sourceSelect.innerHTML = "";
  const bounds = [];
  for (const terminal of terminals) {
    const option = document.createElement("option");
    option.value = terminal.id;
    option.textContent = terminal.name;
    sourceSelect.appendChild(option);

    L.circleMarker([terminal.latitude, terminal.longitude], {
      radius: 7,
      color: "#ffffff",
      weight: 2,
      fillColor: "#0f766e",
      fillOpacity: 0.85,
    })
      .bindPopup(`<strong>${terminal.name}</strong>`)
      .addTo(markerLayer);
    bounds.push([terminal.latitude, terminal.longitude]);
  }
  if (bounds.length > 0) {
    map.fitBounds(bounds, {padding: [30, 30]});
  }
}

function renderLinks() {
  linkLayer.clearLayers();
  for (const link of fiberLinks) {
    L.polyline(
      [
        [link.source_latitude, link.source_longitude],
        [link.target_latitude, link.target_longitude],
      ],
      {
        color: link.is_active ? "#94a3b8" : "#d1d5db",
        weight: 2,
        opacity: link.is_active ? 0.55 : 0.25,
      },
    ).addTo(linkLayer);
  }
}

function renderRoute(route) {
  routeLayer.clearLayers();
  const points = route
    .map((terminalId) => terminalById(terminalId))
    .filter(Boolean)
    .map((terminal) => [terminal.latitude, terminal.longitude]);
  if (points.length === 0) {
    return;
  }
  if (points.length === 1) {
    L.circleMarker(points[0], {
      radius: 12,
      color: "#0f766e",
      weight: 4,
      fillOpacity: 0.2,
    }).addTo(routeLayer);
    map.setView(points[0], 8);
    return;
  }
  L.polyline(points, {
    color: "#dc2626",
    weight: 5,
    opacity: 0.9,
  }).addTo(routeLayer);
  map.fitBounds(points, {padding: [40, 40]});
}

function renderResult(plan) {
  result.innerHTML = `
    <dt>Direct access</dt><dd>${plan.direct_satellite_access}</dd>
    <dt>Recommended terminal</dt><dd>${plan.recommended_terminal_id}</dd>
    <dt>Route</dt><dd>${plan.route.join(" -> ")}</dd>
    <dt>Distance</dt><dd>${plan.route_distance_km} km</dd>
    <dt>Latency</dt><dd>${plan.estimated_latency_ms} ms</dd>
    <dt>Transfer time</dt><dd>${plan.estimated_transfer_time_sec} s</dd>
    <dt>Final score</dt><dd>${plan.final_score}</dd>
    <dt>Reason</dt><dd>${plan.decision_reason.join("; ")}</dd>
  `;
}

async function loadPlanner() {
  [terminals, fiberLinks] = await Promise.all([
    apiGet("/api/v1/terminals"),
    apiGet("/api/v1/fiber-links/map"),
  ]);
  renderLinks();
  renderTerminals();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";
  result.innerHTML = "";
  const payload = {
    source_terminal_id: Number(form.source_terminal_id.value),
    data_volume_gb: Number(form.data_volume_gb.value),
    priority: form.priority.value,
    min_availability_score: Number(form.min_availability_score.value),
  };
  try {
    const plan = await apiPost("/api/v1/routing/transmission-plan", payload);
    renderResult(plan);
    renderRoute(plan.route);
  } catch (error) {
    message.textContent = error.message;
  }
});

loadPlanner().catch((error) => {
  message.textContent = error.message;
});
