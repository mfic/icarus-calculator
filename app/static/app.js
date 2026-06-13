const state = {
  items: [],
  categories: [],
  loadouts: [],
  activeLoadoutId: localStorage.getItem("icarus.activeLoadoutId") || localStorage.getItem("icarus.activeBucketId") || "",
  activeCategory: localStorage.getItem("icarus.activeCategory") || "",
  resources: null,
};

const els = {
  meta: document.querySelector("#meta"),
  items: document.querySelector("#items"),
  search: document.querySelector("#search"),
  categoryFilter: document.querySelector("#categoryFilter"),
  loadoutForm: document.querySelector("#loadoutForm"),
  loadoutName: document.querySelector("#loadoutName"),
  loadoutSelect: document.querySelector("#loadoutSelect"),
  loadoutItems: document.querySelector("#loadoutItems"),
  materials: document.querySelector("#materials"),
  steps: document.querySelector("#steps"),
  clearFarmedBtn: document.querySelector("#clearFarmedBtn"),
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
  const categoryFiltered = category
    ? state.items.filter((item) => item.categories.some((entry) => entry.toLowerCase() === category))
    : state.items;
  const filtered = categoryFiltered.filter((item) => {
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
  }
  saveLocalLoadouts();
  renderLoadoutItems();
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
    tracker.className = "farmed-control";
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.value = formatQuantity(material.farmed || 0);
    input.setAttribute("aria-label", `Farmed ${material.name}`);
    const save = document.createElement("button");
    save.type = "button";
    save.textContent = "Save";
    save.addEventListener("click", () => updateFarmed(material.name, Number(input.value || 0)));
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
  const [meta, items, categories, loadouts] = await Promise.all([
    api("/api/meta"),
    api("/api/items"),
    api("/api/categories"),
    api("/api/loadouts"),
  ]);
  renderMeta(meta);
  state.items = items.items;
  state.categories = categories.categories;
  state.loadouts = loadouts.loadouts;
  if (!state.loadouts.length) {
    const created = await api("/api/loadouts", {
      method: "POST",
      body: JSON.stringify({ name: "Team Loadout" }),
    });
    state.loadouts = [created];
  }
  renderCategories();
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

async function updateFarmed(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/farmed`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity: Math.max(0, quantity) }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function clearFarmed() {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/farmed`, { method: "DELETE" });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

els.search.addEventListener("input", renderItems);
els.categoryFilter.addEventListener("change", () => {
  state.activeCategory = els.categoryFilter.value;
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
els.clearFarmedBtn.addEventListener("click", clearFarmed);
els.refreshBtn.addEventListener("click", async () => {
  els.refreshBtn.disabled = true;
  els.refreshBtn.textContent = "Refreshing...";
  const meta = await api("/api/refresh", { method: "POST" });
  renderMeta(meta);
  const [items, categories] = await Promise.all([api("/api/items"), api("/api/categories")]);
  state.items = items.items;
  state.categories = categories.categories;
  renderCategories();
  renderItems();
  await loadResources();
  els.refreshBtn.disabled = false;
  els.refreshBtn.textContent = "Refresh Wiki Data";
});

loadAll().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin:16px"><h1>Startup failed</h1><p>${error.message}</p></main>`;
});
