const SETTINGS_LABELS = {
  env_buffer_radius_m: "רדיוס באפר סביבתי (מ')",
  intersection_density_threshold_per_km2: "סף צפיפות צמתים (לקמ\"ר)",
  population_density_threshold_per_km2: "סף צפיפות אוכלוסין (לקמ\"ר)",
  employment_density_threshold_per_km2: "סף צפיפות מועסקים (לקמ\"ר)",
  active_edge_buffer_m: "רוחב רצועת דפנות, לכל צד (מ')",
  active_edge_builtup_pct_threshold: "סף אחוז שטח בנוי לדפנות פעילות",
  crossing_spacing_threshold_m: "סף מרווח בין מעברי חצייה (מ')",
  walking_path_length_gap_pct_threshold: "סף אחוז פער באורך מסלול ההליכה",
};

// Modes that accumulate multiple shapes instead of replacing the previous one.
const MULTI_SHAPE_MODES = new Set(["crossings"]);

const map = L.map("map").setView([31.78, 35.2137], 15);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 19,
}).addTo(map);

const referenceLayerGroup = L.layerGroup().addTo(map);
const groups = {
  project: L.featureGroup().addTo(map),
  crossings: L.featureGroup().addTo(map),
  road: L.featureGroup().addTo(map),
  walkingWith: L.featureGroup().addTo(map),
  walkingWithout: L.featureGroup().addTo(map),
};
const colors = {
  project: "#1B3CC0",
  crossings: "#d69e2e",
  road: "#ef4444",
  walkingWith: "#16a34a",
  walkingWithout: "#7c3aed",
};

let activeDrawer = null;

function stopDrawing() {
  if (activeDrawer) {
    activeDrawer.disable();
    activeDrawer = null;
  }
  document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
}

function startDraw(mode) {
  stopDrawing();
  document.querySelector(`.mode-btn[data-mode="${mode}"]`).classList.add("active");

  const shapeOptions = { color: colors[mode] };
  const drawer = mode === "project"
    ? new L.Draw.Polygon(map, { shapeOptions })
    : new L.Draw.Polyline(map, { shapeOptions });

  activeDrawer = drawer;
  drawer.enable();
}

map.on(L.Draw.Event.CREATED, (e) => {
  const activeBtn = document.querySelector(".mode-btn.active");
  const mode = activeBtn ? activeBtn.dataset.mode : null;
  if (!mode) return;

  if (!MULTI_SHAPE_MODES.has(mode)) groups[mode].clearLayers();
  if (e.layer.setStyle) e.layer.setStyle({ color: colors[mode] });
  groups[mode].addLayer(e.layer);
  stopDrawing();
});

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => startDraw(btn.dataset.mode));
});

document.getElementById("clear-btn").addEventListener("click", () => {
  Object.values(groups).forEach((g) => g.clearLayers());
  stopDrawing();
});

document.querySelectorAll(".file-input").forEach((input) => {
  input.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    const data = JSON.parse(text);
    const target = input.dataset.target;
    groups[target].clearLayers();
    L.geoJSON(data, { pointToLayer: (f, latlng) => L.marker(latlng) }).eachLayer((layer) => {
      if (layer.setStyle) layer.setStyle({ color: colors[target] });
      groups[target].addLayer(layer);
    });
  });
});

function groupToGeoJSON(group) {
  return group.toGeoJSON();
}

// --- Settings form ---
async function loadSettingsForm() {
  const defaults = await fetch("/api/settings/defaults").then((r) => r.json());
  const container = document.getElementById("settings-form");
  container.innerHTML = "";
  Object.entries(defaults).forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "field-row";
    row.innerHTML = `<label>${SETTINGS_LABELS[key] || key}</label><input type="number" data-key="${key}" value="${value}" />`;
    container.appendChild(row);
  });
}

function readSettingsForm() {
  const settings = {};
  document.querySelectorAll("#settings-form input").forEach((input) => {
    settings[input.dataset.key] = parseFloat(input.value);
  });
  return settings;
}

// --- Manual indicator forms ---
function buildManualForm(containerId, labels) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  Object.entries(labels).forEach(([key, label]) => {
    const row = document.createElement("div");
    row.className = "field-row";
    row.innerHTML = `<label>${label}</label>
      <select data-key="${key}">
        <option value="-1">-1</option>
        <option value="0" selected>0</option>
        <option value="1">1</option>
      </select>`;
    container.appendChild(row);
  });
}

function readManualForm(containerId) {
  const values = {};
  document.querySelectorAll(`#${containerId} select`).forEach((sel) => {
    values[sel.dataset.key] = parseInt(sel.value, 10);
  });
  return values;
}

async function loadManualForms() {
  const labels = await fetch("/api/manual-indicator-labels").then((r) => r.json());
  buildManualForm("env-manual-form", labels.environment);
  buildManualForm("design-manual-form", labels.design);
}

// --- Reference layers (background context) ---
// built_up_area and intersections are filtered/simplified display copies of
// much larger real layers (~90k footprints / ~140k points - the full layers
// are only used server-side for scoring) - still enough shapes that the
// default SVG renderer would lag, so they get a shared canvas renderer.
const heavyLayerRenderer = L.canvas({ padding: 0.2 });

async function loadReferenceLayers() {
  const layers = await fetch("/api/reference-layers").then((r) => r.json());
  referenceLayerGroup.clearLayers();
  L.geoJSON(layers.built_up_area, {
    renderer: heavyLayerRenderer,
    style: { color: "#888", weight: 1, fillOpacity: 0.15 },
  }).addTo(referenceLayerGroup);
  L.geoJSON(layers.traffic_zones, { style: { color: "#999", weight: 1, dashArray: "4", fillOpacity: 0 } }).addTo(referenceLayerGroup);
  L.geoJSON(layers.intersections, {
    renderer: heavyLayerRenderer,
    pointToLayer: (f, latlng) => L.circleMarker(latlng, { radius: 3, color: "#444", fillOpacity: 0.8 }),
  }).addTo(referenceLayerGroup);
}

// --- Build request payload ---
function singleFeatureOrNull(group) {
  const fc = groupToGeoJSON(group);
  return fc.features.length ? fc.features[0] : null;
}

function buildRequestPayload() {
  const projectFeature = singleFeatureOrNull(groups.project);
  const roadFeature = singleFeatureOrNull(groups.road);
  if (!projectFeature) throw new Error("צייר או העלה את פוליגון הפרויקט תחילה.");
  if (!roadFeature) throw new Error("צייר או העלה את קו הדרך המרכזית תחילה.");

  return {
    project_polygon: projectFeature,
    crossings: groupToGeoJSON(groups.crossings),
    central_road: roadFeature,
    walking_path_with_project: singleFeatureOrNull(groups.walkingWith),
    walking_path_without_project: singleFeatureOrNull(groups.walkingWithout),
    settings: readSettingsForm(),
    manual_environment: readManualForm("env-manual-form"),
    manual_design: readManualForm("design-manual-form"),
  };
}

function renderCategory(title, category) {
  const rows = category.indicators
    .map(
      (ind) => `<tr>
        <td>${ind.label}</td>
        <td>${ind.raw_value ?? "-"}</td>
        <td>${ind.threshold ?? "-"}</td>
        <td>${ind.result}</td>
      </tr>`
    )
    .join("");
  return `<h3>${title} (סה"כ: ${category.total})</h3>
    <table>
      <thead><tr><th>מדד</th><th>ערך נמדד</th><th>סף</th><th>תוצאה</th></tr></thead>
      <tbody>${rows}<tr class="total-row"><td colspan="3">סה"כ</td><td>${category.total}</td></tr></tbody>
    </table>`;
}

document.getElementById("calc-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("status-msg");
  statusEl.textContent = "";
  try {
    const payload = buildRequestPayload();
    statusEl.textContent = "מחשב...";
    const res = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    document.getElementById("results").hidden = false;
    document.getElementById("results-content").innerHTML =
      renderCategory("ציון סביבה", data.environment) + renderCategory("ציון תכנון", data.design);
    statusEl.textContent = "הושלם.";
  } catch (err) {
    statusEl.textContent = "שגיאה: " + err.message;
  }
});

document.getElementById("export-btn").addEventListener("click", async () => {
  const statusEl = document.getElementById("status-msg");
  try {
    const payload = buildRequestPayload();
    statusEl.textContent = "מייצא...";
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ציון_הפרדה_מפלסית.xlsx";
    a.click();
    URL.revokeObjectURL(url);
    statusEl.textContent = "יוצא בהצלחה.";
  } catch (err) {
    statusEl.textContent = "שגיאה: " + err.message;
  }
});

loadSettingsForm();
loadManualForms();
loadReferenceLayers();
