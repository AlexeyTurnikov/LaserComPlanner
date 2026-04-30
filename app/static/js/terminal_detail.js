const token = localStorage.getItem("access_token");

if (!token) {
  window.location.href = "/login";
}

const authHeaders = {
  Authorization: `Bearer ${token}`,
};

const terminalId = Number(document.body.dataset.terminalId);

function logout() {
  localStorage.removeItem("access_token");
}

document.querySelector("#logout-link")?.addEventListener("click", logout);

async function apiGet(url, allowMissing = false) {
  const response = await fetch(url, {headers: authHeaders});
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  }
  if (allowMissing && response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function setDetails(elementId, items) {
  const element = document.querySelector(elementId);
  element.innerHTML = "";
  for (const [label, value] of items) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value === null || value === undefined ? "No data" : value;
    element.append(dt, dd);
  }
}

function renderLinks(links) {
  const list = document.querySelector("#link-list");
  list.innerHTML = "";
  for (const link of links) {
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <strong>${link.source_terminal_id} -> ${link.target_terminal_id}</strong>
      <span class="meta">${link.distance_km} km · ${link.quality} · ${link.is_active ? "active" : "inactive"}</span>
    `;
    list.appendChild(item);
  }
  if (links.length === 0) {
    list.innerHTML = "<div class=\"list-item\">No linked fiber lines</div>";
  }
}

function renderWeatherHistory(items) {
  const list = document.querySelector("#check-history");
  list.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `
      <strong>${new Date(item.timestamp).toLocaleString()}</strong>
      <span class="meta">Cloud ${item.cloud_cover_percent}% · visibility ${item.visibility_m ?? "No data"} m</span>
    `;
    list.appendChild(row);
  }
  if (items.length === 0) {
    list.innerHTML = "<div class=\"list-item\">No weather history</div>";
  }
}

async function loadTerminalDetail() {
  const [terminal, weather, availability, links, history] = await Promise.all([
    apiGet(`/api/v1/terminals/${terminalId}`),
    apiGet(`/api/v1/weather/${terminalId}/latest`, true),
    apiGet(`/api/v1/availability/${terminalId}/latest`, true),
    apiGet(`/api/v1/fiber-links?terminal_id=${terminalId}`),
    apiGet(`/api/v1/weather/${terminalId}/history`, true),
  ]);

  document.querySelector("#terminal-title").textContent = terminal.name;
  setDetails("#terminal-summary", [
    ["ID", terminal.id],
    ["Status", terminal.status],
    ["Latitude", terminal.latitude],
    ["Longitude", terminal.longitude],
    ["Altitude", `${terminal.altitude_m} m`],
    ["Max data rate", `${terminal.max_data_rate_gbps} Gbps`],
    ["Min elevation", `${terminal.min_elevation_deg} deg`],
  ]);

  setDetails("#weather-summary", [
    ["Cloud cover", weather ? `${weather.cloud_cover_percent}%` : null],
    ["Visibility", weather?.visibility_m ? `${weather.visibility_m} m` : null],
    ["Precipitation", weather ? `${weather.precipitation_mm} mm` : null],
    ["Wind speed", weather ? `${weather.wind_speed_kmh} km/h` : null],
    ["Wind gusts", weather ? `${weather.wind_gusts_kmh} km/h` : null],
    ["Temperature", weather ? `${weather.temperature_c} C` : null],
  ]);

  setDetails("#availability-summary", [
    ["Status", availability?.status],
    ["Score", availability?.availability_score],
    ["Reason", availability?.reason?.join("; ")],
    ["Checked at", availability ? new Date(availability.checked_at).toLocaleString() : null],
  ]);

  renderLinks(links);
  renderWeatherHistory(history || []);
}

loadTerminalDetail().catch((error) => {
  document.querySelector("#terminal-title").textContent = error.message;
});
