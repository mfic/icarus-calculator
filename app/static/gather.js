const state = {
  loadouts: [],
  activeLoadoutId: "",
  resources: null,
  hideCompleted: localStorage.getItem("icarus.gather.hideCompleted") === "1",
};

const els = {
  subtitle: document.querySelector("#gatherSubtitle"),
  loadoutSelect: document.querySelector("#gatherLoadoutSelect"),
  hideCompletedToggle: document.querySelector("#hideCompletedToggle"),
  clearCollectedBtn: document.querySelector("#clearCollectedBtn"),
  ignoredMaterials: document.querySelector("#gatherIgnored"),
  materials: document.querySelector("#gatherMaterials"),
};

function activeLoadout() {
  return state.loadouts.find((loadout) => loadout.id === state.activeLoadoutId) || state.loadouts[0];
}

function renderLoadoutSelect() {
  els.loadoutSelect.innerHTML = "";
  for (const loadout of state.loadouts) {
    const option = document.createElement("option");
    option.value = loadout.id;
    option.textContent = loadout.name;
    els.loadoutSelect.appendChild(option);
  }
  const loadout = activeLoadout();
  if (loadout) {
    state.activeLoadoutId = loadout.id;
    els.loadoutSelect.value = loadout.id;
  }
}

function renderMaterials() {
  const loadout = activeLoadout();
  els.materials.innerHTML = "";
  if (!loadout) {
    els.subtitle.textContent = "No loadouts found. Open the calculator first.";
    return;
  }
  els.subtitle.textContent = loadout.name;
  const data = state.resources;
  if (!data) return;
  const colors = sourceColorMap(loadout);
  renderMaterialCards(els.materials, data.materials, colors, {
    hideCompleted: state.hideCompleted,
    onIgnore: (name) => setIgnoredMaterial(name, true),
    onCollectedChange: updateCollected,
  });

  renderIgnoredChips(els.ignoredMaterials, activeLoadout()?.ignored_materials || [], (name) => setIgnoredMaterial(name, false));
}

async function loadResources() {
  const loadout = activeLoadout();
  if (!loadout) {
    state.resources = null;
    renderMaterials();
    return;
  }
  state.resources = await api(`/api/loadouts/${loadout.id}/resources`);
  renderMaterials();
}

async function updateCollected(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  await api(`/api/loadouts/${loadout.id}/collected`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity: Math.max(0, quantity) }),
  });
  await loadResources();
}

async function clearCollected() {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/collected`, { method: "DELETE" });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  await loadResources();
}

async function setIgnoredMaterial(itemName, ignored) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/ignored-materials`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, ignored }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  await loadResources();
}

function resolveActiveLoadoutId() {
  const requested = new URLSearchParams(window.location.search).get("loadout");
  if (requested && state.loadouts.some((loadout) => loadout.id === requested)) {
    return requested;
  }
  const stored = localStorage.getItem("icarus.gather.loadoutId");
  if (stored && state.loadouts.some((loadout) => loadout.id === stored)) {
    return stored;
  }
  const shared = localStorage.getItem("icarus.activeLoadoutId");
  if (shared && state.loadouts.some((loadout) => loadout.id === shared)) {
    return shared;
  }
  return state.loadouts[0]?.id || "";
}

async function init() {
  const { loadouts } = await api("/api/loadouts");
  state.loadouts = loadouts;
  state.activeLoadoutId = resolveActiveLoadoutId();
  els.hideCompletedToggle.checked = state.hideCompleted;
  renderLoadoutSelect();
  await loadResources();
}

els.loadoutSelect.addEventListener("change", async () => {
  state.activeLoadoutId = els.loadoutSelect.value;
  localStorage.setItem("icarus.gather.loadoutId", state.activeLoadoutId);
  await loadResources();
});

els.hideCompletedToggle.addEventListener("change", () => {
  state.hideCompleted = els.hideCompletedToggle.checked;
  localStorage.setItem("icarus.gather.hideCompleted", state.hideCompleted ? "1" : "0");
  renderMaterials();
});

els.clearCollectedBtn.addEventListener("click", clearCollected);

setInterval(loadResources, 15000);
window.addEventListener("focus", loadResources);

init().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin:16px"><h1>Startup failed</h1><p>${error.message}</p></main>`;
});
