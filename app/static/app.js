const state = {
  items: [],
  categories: [],
  tiers: [],
  loadouts: [],
  activeLoadoutId: localStorage.getItem("icarus.activeLoadoutId") || localStorage.getItem("icarus.activeBucketId") || "",
  activeCategory: localStorage.getItem("icarus.activeCategory") || "",
  activeTier: localStorage.getItem("icarus.activeTier") || "",
  resources: null,
};

const els = {
  meta: document.querySelector("#meta"),
  items: document.querySelector("#items"),
  search: document.querySelector("#search"),
  categoryFilter: document.querySelector("#categoryFilter"),
  tierFilter: document.querySelector("#tierFilter"),
  loadoutForm: document.querySelector("#loadoutForm"),
  loadoutName: document.querySelector("#loadoutName"),
  loadoutSelect: document.querySelector("#loadoutSelect"),
  loadoutId: document.querySelector("#loadoutId"),
  loadoutItems: document.querySelector("#loadoutItems"),
  materials: document.querySelector("#materials"),
  steps: document.querySelector("#steps"),
  clearCollectedBtn: document.querySelector("#clearCollectedBtn"),
  copyShareBtn: document.querySelector("#copyShareBtn"),
  exportLoadoutBtn: document.querySelector("#exportLoadoutBtn"),
  importLoadoutInput: document.querySelector("#importLoadoutInput"),
  refreshBtn: document.querySelector("#refreshBtn"),
  itemTemplate: document.querySelector("#itemTemplate"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function saveLocalLoadouts() {
  localStorage.setItem("icarus.loadouts.snapshot", JSON.stringify(state.loadouts));
  localStorage.setItem("icarus.activeLoadoutId", state.activeLoadoutId || "");
  localStorage.setItem("icarus.activeCategory", state.activeCategory || "");
  localStorage.setItem("icarus.activeTier", state.activeTier || "");
}

function formatQuantity(value) {
  return Number.isInteger(value) ? value.toString() : Number(value).toFixed(2).replace(/\.?0+$/, "");
}

function activeLoadout() {
  return state.loadouts.find((loadout) => loadout.id === state.activeLoadoutId) || state.loadouts[0];
}

function renderMeta(meta) {
  const when = meta.refreshed_at ? new Date(meta.refreshed_at).toLocaleString() : "not refreshed yet";
  els.meta.textContent = `${meta.count || 0} items cached from wiki.gg. Last refresh: ${when}.`;
}

function renderItems() {
  const term = els.search.value.trim().toLowerCase();
  const category = state.activeCategory.toLowerCase();
  const tier = state.activeTier.toLowerCase();
  const categoryFiltered = category
    ? state.items.filter((item) => item.categories.some((entry) => entry.toLowerCase() === category))
    : state.items;
  const tierFiltered = tier
    ? categoryFiltered.filter((item) => item.tier && item.tier.toLowerCase() === tier)
    : categoryFiltered;
  const filtered = tierFiltered.filter((item) => {
    const recipeInputs = item.recipe?.inputs?.map((entry) => entry.name).join(" ") || "";
    const effects = item.effects?.length ? item.effects : item.buffs || [];
    return `${item.name} ${item.tier || ""} ${effects.join(" ")} ${item.benches.join(" ")} ${item.categories.join(" ")} ${recipeInputs}`.toLowerCase().includes(term);
  });

  els.items.innerHTML = "";
  if (!filtered.length) {
    els.items.innerHTML = '<p class="muted">No items match this filter.</p>';
    return;
  }
  for (const item of filtered) {
    const node = els.itemTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = item.name;
    node.querySelector(".bench").textContent = item.benches.length ? `Crafted at: ${item.benches.join(", ")}` : "No crafting bench listed";

    const categories = node.querySelector(".categories");
    if (item.tier) {
      const tier = document.createElement("span");
      tier.className = "tier-pill";
      tier.textContent = item.tier;
      categories.appendChild(tier);
    }
    for (const categoryName of item.categories.slice(0, 5)) {
      const pill = document.createElement("span");
      pill.className = "category-pill";
      pill.textContent = categoryName;
      categories.appendChild(pill);
    }

    const effects = item.effects?.length ? item.effects : item.buffs || [];
    const effectList = node.querySelector(".effects");
    for (const effect of effects.slice(0, 8)) {
      const pill = document.createElement("span");
      pill.className = "effect";
      pill.textContent = effect;
      effectList.appendChild(pill);
    }
    if (!effects.length) {
      const empty = document.createElement("span");
      empty.className = "muted";
      empty.textContent = "No effects or stats listed";
      effectList.appendChild(empty);
    }

    const recipe = node.querySelector(".recipe");
    const inputs = item.recipe?.inputs || [];
    if (inputs.length) {
      for (const ingredient of inputs) {
        const li = document.createElement("li");
        li.textContent = `${formatQuantity(ingredient.quantity)} ${ingredient.name}`;
        recipe.appendChild(li);
      }
    } else {
      const li = document.createElement("li");
      li.textContent = "No recipe listed";
      recipe.appendChild(li);
    }

    const quantity = node.querySelector("input");
    node.querySelector("button").addEventListener("click", () => addItem(item.name, Number(quantity.value || 1)));
    els.items.appendChild(node);
  }
}

function renderCategories() {
  els.categoryFilter.innerHTML = '<option value="">All categories</option>';
  for (const category of state.categories) {
    const option = document.createElement("option");
    option.value = category.name;
    option.textContent = `${category.name} (${category.count})`;
    els.categoryFilter.appendChild(option);
  }
  if (state.activeCategory && state.categories.some((category) => category.name === state.activeCategory)) {
    els.categoryFilter.value = state.activeCategory;
  } else {
    state.activeCategory = "";
    els.categoryFilter.value = "";
  }
  saveLocalLoadouts();
}

function renderTiers() {
  els.tierFilter.innerHTML = '<option value="">All tiers</option>';
  for (const tier of state.tiers) {
    const option = document.createElement("option");
    option.value = tier.name;
    option.textContent = `${tier.name} (${tier.count})`;
    els.tierFilter.appendChild(option);
  }
  if (state.activeTier && state.tiers.some((tier) => tier.name === state.activeTier)) {
    els.tierFilter.value = state.activeTier;
  } else {
    state.activeTier = "";
    els.tierFilter.value = "";
  }
  saveLocalLoadouts();
}

function renderLoadouts() {
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
    els.loadoutId.textContent = loadout.id;
  } else {
    els.loadoutId.textContent = "No loadout selected";
  }
  saveLocalLoadouts();
  renderLoadoutItems();
}

function loadoutShareUrl(loadout) {
  const url = new URL(window.location.href);
  url.searchParams.set("loadout", loadout.id);
  return url.toString();
}

function renderLoadoutItems() {
  const loadout = activeLoadout();
  els.loadoutItems.innerHTML = "";
  if (!loadout || !loadout.items.length) {
    els.loadoutItems.innerHTML = '<p class="muted">No items in this loadout yet.</p>';
    return;
  }
  for (const entry of loadout.items) {
    const itemName = entry.item || entry.food;
    const row = document.createElement("div");
    row.className = "loadout-row";
    row.innerHTML = `<span>${itemName}</span><span class="qty">x${entry.quantity}</span>`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => removeItem(itemName));
    row.appendChild(remove);
    els.loadoutItems.appendChild(row);
  }
}

function renderResources() {
  els.materials.innerHTML = "";
  els.steps.innerHTML = "";
  const data = state.resources;
  if (!data || !activeLoadout()) {
    els.materials.innerHTML = '<p class="muted">Select a Loadout to calculate materials.</p>';
    return;
  }

  if (!data.materials.length) {
    els.materials.innerHTML = '<p class="muted">No materials needed yet.</p>';
  }
  for (const material of data.materials) {
    const row = document.createElement("div");
    row.className = "material-row";
    row.innerHTML = `
      <div class="material-main">
        <strong>${material.name}</strong>
        <span class="muted">Need ${formatQuantity(material.quantity)} · Remaining ${formatQuantity(material.remaining ?? material.quantity)}</span>
      </div>
    `;
    const tracker = document.createElement("div");
    tracker.className = "collected-control";
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.value = formatQuantity(material.collected ?? material.farmed ?? 0);
    input.setAttribute("aria-label", `Collected ${material.name}`);
    const save = document.createElement("button");
    save.type = "button";
    save.textContent = "Save";
    save.addEventListener("click", () => updateCollected(material.name, Number(input.value || 0)));
    tracker.appendChild(input);
    tracker.appendChild(save);
    row.appendChild(tracker);
    els.materials.appendChild(row);
  }

  if (!data.steps.length) {
    els.steps.innerHTML = '<p class="muted">No craftable steps in this loadout.</p>';
  }
  for (const step of data.steps) {
    const node = document.createElement("div");
    node.className = "step";
    node.innerHTML = `
      <div class="step-title">
        <strong>${step.item}</strong>
        <span class="qty">x${formatQuantity(step.quantity)}</span>
      </div>
      <p class="muted">${step.benches?.length ? `Bench: ${step.benches.join(", ")}` : "Bench not listed"} · batches ${formatQuantity(step.batches)}</p>
      <ul>${step.inputs.map((input) => `<li>${formatQuantity(input.quantity)} ${input.name}</li>`).join("")}</ul>
    `;
    els.steps.appendChild(node);
  }
}

async function loadResources() {
  const loadout = activeLoadout();
  if (!loadout) {
    state.resources = null;
    renderResources();
    return;
  }
  state.resources = await api(`/api/loadouts/${loadout.id}/resources`);
  renderResources();
}

async function loadAll() {
  const [meta, items, categories, tiers, loadouts] = await Promise.all([
    api("/api/meta"),
    api("/api/items"),
    api("/api/categories"),
    api("/api/tiers"),
    api("/api/loadouts"),
  ]);
  renderMeta(meta);
  state.items = items.items;
  state.categories = categories.categories;
  state.tiers = tiers.tiers;
  state.loadouts = loadouts.loadouts;
  const requestedLoadoutId = new URLSearchParams(window.location.search).get("loadout");
  if (requestedLoadoutId && state.loadouts.some((loadout) => loadout.id === requestedLoadoutId)) {
    state.activeLoadoutId = requestedLoadoutId;
  }
  if (!state.loadouts.length) {
    const created = await api("/api/loadouts", {
      method: "POST",
      body: JSON.stringify({ name: "Team Loadout" }),
    });
    state.loadouts = [created];
  }
  renderCategories();
  renderTiers();
  renderItems();
  renderLoadouts();
  await loadResources();
}

async function addItem(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const existing = loadout.items.find((entry) => (entry.item || entry.food) === itemName);
  const nextQuantity = (existing?.quantity || 0) + Math.max(1, quantity);
  const updated = await api(`/api/loadouts/${loadout.id}/items`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity: nextQuantity }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function removeItem(itemName) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/items/${encodeURIComponent(itemName)}`, { method: "DELETE" });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function updateCollected(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/collected`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity: Math.max(0, quantity) }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function clearCollected() {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/collected`, { method: "DELETE" });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function copyShareLink() {
  const loadout = activeLoadout();
  if (!loadout) return;
  await navigator.clipboard.writeText(loadoutShareUrl(loadout));
  els.copyShareBtn.textContent = "Copied";
  setTimeout(() => {
    els.copyShareBtn.textContent = "Copy Link";
  }, 1200);
}

function exportLoadout() {
  const loadout = activeLoadout();
  if (!loadout) return;
  const payload = {
    version: 1,
    exported_at: new Date().toISOString(),
    loadout: {
      name: loadout.name,
      items: loadout.items.map((entry) => ({ item: entry.item || entry.food, quantity: entry.quantity })),
      collected: loadout.collected || {},
    },
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${loadout.name.replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "") || "icarus-loadout"}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function importLoadout(file) {
  if (!file) return;
  const payload = JSON.parse(await file.text());
  const loadout = payload.loadout || payload;
  const created = await api("/api/loadouts/import", {
    method: "POST",
    body: JSON.stringify({
      name: loadout.name || "Imported Loadout",
      items: loadout.items || [],
      collected: loadout.collected || loadout.farmed || {},
    }),
  });
  state.loadouts.push(created);
  state.activeLoadoutId = created.id;
  renderLoadouts();
  await loadResources();
}

els.search.addEventListener("input", renderItems);
els.categoryFilter.addEventListener("change", () => {
  state.activeCategory = els.categoryFilter.value;
  saveLocalLoadouts();
  renderItems();
});
els.tierFilter.addEventListener("change", () => {
  state.activeTier = els.tierFilter.value;
  saveLocalLoadouts();
  renderItems();
});
els.loadoutSelect.addEventListener("change", async () => {
  state.activeLoadoutId = els.loadoutSelect.value;
  saveLocalLoadouts();
  renderLoadoutItems();
  await loadResources();
});
els.loadoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = els.loadoutName.value.trim();
  if (!name) return;
  const loadout = await api("/api/loadouts", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  state.loadouts.push(loadout);
  state.activeLoadoutId = loadout.id;
  els.loadoutName.value = "";
  renderLoadouts();
  await loadResources();
});
els.clearCollectedBtn.addEventListener("click", clearCollected);
els.copyShareBtn.addEventListener("click", copyShareLink);
els.exportLoadoutBtn.addEventListener("click", exportLoadout);
els.importLoadoutInput.addEventListener("change", async () => {
  await importLoadout(els.importLoadoutInput.files[0]);
  els.importLoadoutInput.value = "";
});
els.refreshBtn.addEventListener("click", async () => {
  els.refreshBtn.disabled = true;
  els.refreshBtn.textContent = "Refreshing...";
  const meta = await api("/api/refresh", { method: "POST" });
  renderMeta(meta);
  const [items, categories, tiers] = await Promise.all([api("/api/items"), api("/api/categories"), api("/api/tiers")]);
  state.items = items.items;
  state.categories = categories.categories;
  state.tiers = tiers.tiers;
  renderCategories();
  renderTiers();
  renderItems();
  await loadResources();
  els.refreshBtn.disabled = false;
  els.refreshBtn.textContent = "Refresh Wiki Data";
});

loadAll().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin:16px"><h1>Startup failed</h1><p>${error.message}</p></main>`;
});
