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
  const materials = state.hideCompleted
    ? data.materials.filter((material) => (material.remaining ?? material.quantity) > 0)
    : data.materials;
  if (!materials.length) {
    els.materials.innerHTML = '<p class="muted">Nothing to gather. Add items to this loadout from the calculator.</p>';
    return;
  }
  for (const material of materials) {
    const remaining = material.remaining ?? material.quantity;
    const card = document.createElement("article");
    card.className = "gather-card";
    if (remaining <= 0) card.classList.add("done");

    const header = document.createElement("div");
    header.className = "gather-card-header";
    const name = document.createElement("strong");
    name.textContent = material.name;
    const dots = renderSourceDots(material.sources, colors);
    if (dots) name.appendChild(dots);
    const ignoreToggle = createIgnoreToggle({
      ignored: false,
      ariaLabel: `Ignore ${material.name}`,
      onToggle: () => setIgnoredMaterial(material.name, true),
    });
    name.appendChild(ignoreToggle);
    header.appendChild(name);
    card.appendChild(header);

    const summary = document.createElement("p");
    summary.className = "muted";
    summary.textContent = `Need ${formatQuantity(material.quantity)} · Remaining ${formatQuantity(remaining)}`;
    card.appendChild(summary);

    const actions = document.createElement("div");
    actions.className = "gather-card-actions";
    const stepper = createStepper({
      value: formatQuantity(material.collected ?? material.farmed ?? 0),
      min: 0,
      step: 1,
      ariaLabel: `Collected ${material.name}`,
      onChange: (value) => updateCollected(material.name, value),
    });
    actions.appendChild(stepper);
    const maxBtn = document.createElement("button");
    maxBtn.type = "button";
    maxBtn.className = "secondary";
    maxBtn.textContent = "Max";
    maxBtn.setAttribute("aria-label", `Set ${material.name} collected to ${formatQuantity(material.quantity)}`);
    maxBtn.addEventListener("click", () => updateCollected(material.name, material.quantity));
    actions.appendChild(maxBtn);
    card.appendChild(actions);

    els.materials.appendChild(card);
  }

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
