const state = {
  items: [],
  categories: [],
  subcategories: [],
  tiers: [],
  loadouts: [],
  activeLoadoutId: localStorage.getItem("icarus.activeLoadoutId") || localStorage.getItem("icarus.activeBucketId") || "",
  activeCategory: localStorage.getItem("icarus.activeCategory") || "",
  activeSubcategory: localStorage.getItem("icarus.activeSubcategory") || "",
  activeTier: localStorage.getItem("icarus.activeTier") || "",
  hideCompleted: localStorage.getItem("icarus.gather.hideCompleted") === "1",
  resources: null,
};

const els = {
  meta: document.querySelector("#meta"),
  calculatorView: document.querySelector("#calculatorView"),
  gatherView: document.querySelector("#gatherView"),
  calculatorTab: document.querySelector("#calculatorTab"),
  gatherTab: document.querySelector("#gatherTab"),
  gatherLoadoutSelect: document.querySelector("#gatherLoadoutSelect"),
  hideCompletedToggle: document.querySelector("#hideCompletedToggle"),
  gatherClearCollectedBtn: document.querySelector("#gatherClearCollectedBtn"),
  gatherIgnored: document.querySelector("#gatherIgnored"),
  gatherMaterials: document.querySelector("#gatherMaterials"),
  items: document.querySelector("#items"),
  search: document.querySelector("#search"),
  resetFiltersBtn: document.querySelector("#resetFiltersBtn"),
  categoryFilter: document.querySelector("#categoryFilter"),
  subcategoryFilter: document.querySelector("#subcategoryFilter"),
  tierFilter: document.querySelector("#tierFilter"),
  loadoutForm: document.querySelector("#loadoutForm"),
  loadoutName: document.querySelector("#loadoutName"),
  loadoutSelect: document.querySelector("#loadoutSelect"),
  loadoutId: document.querySelector("#loadoutId"),
  accountId: document.querySelector("#accountId"),
  copyAccountBtn: document.querySelector("#copyAccountBtn"),
  switchAccountBtn: document.querySelector("#switchAccountBtn"),
  shareSection: document.querySelector("#shareSection"),
  sharedWithChips: document.querySelector("#sharedWithChips"),
  addShareBtn: document.querySelector("#addShareBtn"),
  sharedBadge: document.querySelector("#sharedBadge"),
  loadoutItems: document.querySelector("#loadoutItems"),
  ignoredMaterials: document.querySelector("#ignoredMaterials"),
  materials: document.querySelector("#materials"),
  steps: document.querySelector("#steps"),
  storageItems: document.querySelector("#storageItems"),
  clearCollectedBtn: document.querySelector("#clearCollectedBtn"),
  clearStorageBtn: document.querySelector("#clearStorageBtn"),
  copyShareBtn: document.querySelector("#copyShareBtn"),
  exportLoadoutBtn: document.querySelector("#exportLoadoutBtn"),
  importLoadoutInput: document.querySelector("#importLoadoutInput"),
  deleteLoadoutBtn: document.querySelector("#deleteLoadoutBtn"),
  gatherLink: document.querySelector("#gatherLink"),
  itemTemplate: document.querySelector("#itemTemplate"),
};

function saveLocalLoadouts() {
  localStorage.setItem("icarus.loadouts.snapshot", JSON.stringify(state.loadouts));
  localStorage.setItem("icarus.activeLoadoutId", state.activeLoadoutId || "");
  localStorage.setItem("icarus.activeCategory", state.activeCategory || "");
  localStorage.setItem("icarus.activeSubcategory", state.activeSubcategory || "");
  localStorage.setItem("icarus.activeTier", state.activeTier || "");
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
  const subcategory = state.activeSubcategory.toLowerCase();
  const tier = state.activeTier.toLowerCase();
  const categoryFiltered = category
    ? state.items.filter((item) => item.primary_category.toLowerCase() === category || item.categories.some((entry) => entry.toLowerCase() === category))
    : state.items;
  const subcategoryFiltered = subcategory
    ? categoryFiltered.filter((item) => item.categories.some((entry) => entry.toLowerCase() === subcategory))
    : categoryFiltered;
  const tierFiltered = tier
    ? subcategoryFiltered.filter((item) => item.tier && item.tier.toLowerCase() === tier)
    : subcategoryFiltered;
  const filtered = tierFiltered.filter((item) => {
    const recipes = item.recipes?.length ? item.recipes : item.recipe ? [item.recipe] : [];
    const recipeInputs = recipes.flatMap((recipe) => recipe.inputs?.map((entry) => entry.name) || []).join(" ");
    const effects = item.effects?.length ? item.effects : item.buffs || [];
    return `${item.name} ${item.tier || ""} ${effects.join(" ")} ${item.benches.join(" ")} ${item.categories.join(" ")} ${recipeInputs}`.toLowerCase().includes(term);
  });
  const sorted = term
    ? [...filtered].sort((a, b) => {
        const aMatches = a.name.toLowerCase().includes(term) ? 0 : 1;
        const bMatches = b.name.toLowerCase().includes(term) ? 0 : 1;
        return aMatches - bMatches;
      })
    : filtered;

  els.items.innerHTML = "";
  if (!sorted.length) {
    els.items.innerHTML = '<p class="muted">No items match this filter.</p>';
    return;
  }
  for (const item of sorted) {
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
    const recipes = item.recipes?.length ? item.recipes : item.recipe ? [item.recipe] : [];
    if (recipes.length) {
      recipes.forEach((option, index) => {
        if (recipes.length > 1) {
          const header = document.createElement("li");
          header.className = "recipe-option-label";
          const strong = document.createElement("strong");
          strong.textContent = `Option ${index + 1}: ${option.label}`;
          header.appendChild(strong);
          recipe.appendChild(header);
        }
        for (const ingredient of option.inputs || []) {
          const li = document.createElement("li");
          li.textContent = `${formatQuantity(ingredient.quantity)} ${ingredient.name}`;
          recipe.appendChild(li);
        }
      });
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

function renderSubcategories() {
  const sourceItems = state.activeCategory
    ? state.items.filter((item) => item.primary_category === state.activeCategory)
    : state.items;
  const counts = new Map();
  for (const item of sourceItems) {
    for (const subcategory of item.categories) {
      counts.set(subcategory, (counts.get(subcategory) || 0) + 1);
    }
  }
  const subcategories = [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name));
  els.subcategoryFilter.innerHTML = '<option value="">All subcategories</option>';
  for (const subcategory of subcategories) {
    const option = document.createElement("option");
    option.value = subcategory.name;
    option.textContent = `${subcategory.name} (${subcategory.count})`;
    els.subcategoryFilter.appendChild(option);
  }
  if (state.activeSubcategory && subcategories.some((subcategory) => subcategory.name === state.activeSubcategory)) {
    els.subcategoryFilter.value = state.activeSubcategory;
  } else {
    state.activeSubcategory = "";
    els.subcategoryFilter.value = "";
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
    els.gatherLink.href = `/gather?loadout=${encodeURIComponent(loadout.id)}`;
  } else {
    els.loadoutId.textContent = "No loadout selected";
    els.gatherLink.href = "/gather";
  }
  saveLocalLoadouts();
  renderLoadoutItems();
  renderShare();
}

function renderShare() {
  const loadout = activeLoadout();
  const isOwner = loadout && loadout.owner_id === getAccountId();
  els.shareSection.hidden = !isOwner;
  els.sharedBadge.hidden = !loadout || isOwner;
  els.deleteLoadoutBtn.hidden = !isOwner;
  if (isOwner) {
    renderShareChips(els.sharedWithChips, loadout.shared_with, (accountId) => setShared(accountId, false));
  }
}

async function setShared(accountId, shared) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/share`, {
    method: "PUT",
    body: JSON.stringify({ account_id: accountId, shared }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
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
  const colors = sourceColorMap(loadout);
  for (const entry of loadout.items) {
    const itemName = entry.item || entry.food;
    const row = document.createElement("div");
    row.className = "loadout-row";
    const nameSpan = document.createElement("span");
    nameSpan.className = "name";
    const dot = document.createElement("span");
    dot.className = "source-dot";
    dot.style.backgroundColor = colors.get(itemName) || "var(--muted)";
    dot.style.marginRight = "6px";
    nameSpan.appendChild(dot);
    nameSpan.appendChild(document.createTextNode(itemName));
    const stepper = createStepper({
      value: entry.quantity,
      min: 1,
      step: 1,
      ariaLabel: `Quantity for ${itemName}`,
      onChange: (value) => setItemQuantity(itemName, Math.round(value)),
    });
    row.appendChild(nameSpan);
    row.appendChild(stepper);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = "X";
    remove.setAttribute("aria-label", `Remove ${itemName}`);
    remove.addEventListener("click", () => removeItem(itemName));
    row.appendChild(remove);
    els.loadoutItems.appendChild(row);
  }
}

function renderResources() {
  els.materials.innerHTML = "";
  els.steps.innerHTML = "";
  els.storageItems.innerHTML = "";
  const data = state.resources;
  if (!data || !activeLoadout()) {
    els.materials.innerHTML = '<p class="muted">Select a Loadout to calculate materials.</p>';
    return;
  }

  if (!data.materials.length) {
    els.materials.innerHTML = '<p class="muted">No materials needed yet.</p>';
  }
  const colors = sourceColorMap(activeLoadout());
  for (const material of data.materials) {
    const row = document.createElement("div");
    row.className = "material-row";
    const main = document.createElement("div");
    main.className = "material-main";
    const name = document.createElement("strong");
    name.textContent = material.name;
    const materialDots = renderSourceDots(material.sources, colors);
    if (materialDots) name.appendChild(materialDots);
    const ignoreToggle = createIgnoreToggle({
      ignored: false,
      ariaLabel: `Ignore ${material.name}`,
      onToggle: () => setIgnoredMaterial(material.name, true),
    });
    name.appendChild(ignoreToggle);
    const summary = document.createElement("span");
    summary.className = "muted";
    summary.textContent = `Need ${formatQuantity(material.quantity)} · Remaining ${formatQuantity(material.remaining ?? material.quantity)}`;
    main.appendChild(name);
    main.appendChild(summary);
    row.appendChild(main);
    const tracker = document.createElement("div");
    tracker.className = "collected-control";
    const stepper = createStepper({
      value: formatQuantity(material.collected ?? material.farmed ?? 0),
      min: 0,
      step: 1,
      ariaLabel: `Collected ${material.name}`,
      onChange: (value) => updateCollected(material.name, value),
    });
    tracker.appendChild(stepper);
    row.appendChild(tracker);
    els.materials.appendChild(row);
  }

  renderIgnoredChips(els.ignoredMaterials, activeLoadout()?.ignored_materials || [], (name) => setIgnoredMaterial(name, false));

  if (!data.steps.length) {
    els.steps.innerHTML = '<p class="muted">No craftable steps in this loadout.</p>';
  }
  const recipeOptionsByItem = new Map((data.recipe_options || []).map((entry) => [entry.item, entry]));
  for (const step of data.steps) {
    const node = document.createElement("div");
    node.className = "step";

    const title = document.createElement("div");
    title.className = "step-title";
    const name = document.createElement("strong");
    name.textContent = step.item;
    const stepDots = renderSourceDots(step.sources, colors);
    if (stepDots) name.appendChild(stepDots);
    const qty = document.createElement("span");
    qty.className = "qty";
    qty.textContent = `x${formatQuantity(step.quantity)}`;
    title.appendChild(name);
    title.appendChild(qty);
    node.appendChild(title);

    const recipeOptions = recipeOptionsByItem.get(step.item);
    if (recipeOptions) {
      const recipeRow = document.createElement("div");
      recipeRow.className = "step-recipe";
      const label = document.createElement("label");
      label.textContent = "Recipe: ";
      const select = document.createElement("select");
      for (const option of recipeOptions.options) {
        const optionEl = document.createElement("option");
        optionEl.value = option.id;
        optionEl.textContent = option.label;
        if (option.id === recipeOptions.selected) {
          optionEl.selected = true;
        }
        select.appendChild(optionEl);
      }
      select.addEventListener("change", () => setRecipeChoice(step.item, select.value));
      label.appendChild(select);
      recipeRow.appendChild(label);
      node.appendChild(recipeRow);
    }

    const summary = document.createElement("p");
    summary.className = "muted";
    summary.textContent = `${step.benches?.length ? `Bench: ${step.benches.join(", ")}` : "Bench not listed"} · batches ${formatQuantity(step.batches)}`;
    node.appendChild(summary);

    const list = document.createElement("ul");
    for (const input of step.inputs) {
      const li = document.createElement("li");
      li.textContent = `${formatQuantity(input.quantity)} ${input.name}`;
      list.appendChild(li);
    }
    node.appendChild(list);

    els.steps.appendChild(node);
  }

  if (!data.storage_items?.length) {
    els.storageItems.innerHTML = '<p class="muted">No craftable items to track in storage.</p>';
  }
  for (const entry of data.storage_items || []) {
    const row = document.createElement("div");
    row.className = "material-row";
    const main = document.createElement("div");
    main.className = "material-main";
    const name = document.createElement("strong");
    name.textContent = entry.name;
    const summary = document.createElement("span");
    summary.className = "muted";
    summary.textContent = `Need ${formatQuantity(entry.quantity)} · Remaining ${formatQuantity(entry.remaining)}`;
    main.appendChild(name);
    main.appendChild(summary);
    row.appendChild(main);
    const tracker = document.createElement("div");
    tracker.className = "collected-control";
    const stepper = createStepper({
      value: formatQuantity(entry.have ?? 0),
      min: 0,
      step: 1,
      ariaLabel: `In storage ${entry.name}`,
      onChange: (value) => setStorageQuantity(entry.name, value),
    });
    tracker.appendChild(stepper);
    row.appendChild(tracker);
    els.storageItems.appendChild(row);
  }
}

function renderGatherView() {
  els.gatherLoadoutSelect.innerHTML = "";
  for (const loadout of state.loadouts) {
    const option = document.createElement("option");
    option.value = loadout.id;
    option.textContent = loadout.name;
    els.gatherLoadoutSelect.appendChild(option);
  }
  const loadout = activeLoadout();
  const data = state.resources;
  if (!loadout || !data) {
    els.gatherMaterials.innerHTML = '<p class="muted">Select a Loadout to calculate materials.</p>';
    els.gatherIgnored.hidden = true;
    return;
  }
  els.gatherLoadoutSelect.value = loadout.id;
  const colors = sourceColorMap(loadout);
  renderMaterialCards(els.gatherMaterials, data.materials, colors, {
    hideCompleted: state.hideCompleted,
    onIgnore: (name) => setIgnoredMaterial(name, true),
    onCollectedChange: updateCollected,
  });
  renderIgnoredChips(els.gatherIgnored, loadout.ignored_materials || [], (name) => setIgnoredMaterial(name, false));
}

function switchView(view) {
  const isGather = view === "gather";
  els.calculatorView.hidden = isGather;
  els.gatherView.hidden = !isGather;
  els.calculatorTab.setAttribute("aria-selected", String(!isGather));
  els.gatherTab.setAttribute("aria-selected", String(isGather));
  location.hash = isGather ? "gather" : "";
}

async function loadResources() {
  const loadout = activeLoadout();
  if (!loadout) {
    state.resources = null;
    renderResources();
    renderGatherView();
    return;
  }
  state.resources = await api(`/api/loadouts/${loadout.id}/resources`);
  renderResources();
  renderGatherView();
}

async function pollUpdates() {
  try {
    const { loadouts } = await api("/api/loadouts");
    state.loadouts = loadouts;
    await loadResources();
  } catch (error) {
    console.error("Poll for updates failed:", error);
  }
}

async function loadAll() {
  els.accountId.textContent = getAccountId();
  els.hideCompletedToggle.checked = state.hideCompleted;
  if (location.hash === "#gather") {
    switchView("gather");
  }
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
      body: JSON.stringify({ name: "Loadout" }),
    });
    state.loadouts = [created];
  }
  renderCategories();
  renderSubcategories();
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

async function setItemQuantity(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/items`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity }),
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

async function setRecipeChoice(itemName, recipeId) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/recipe-choice`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, recipe_id: recipeId }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
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

async function setStorageQuantity(itemName, quantity) {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/storage`, {
    method: "PUT",
    body: JSON.stringify({ item: itemName, quantity: Math.max(0, quantity) }),
  });
  state.loadouts = state.loadouts.map((entry) => (entry.id === updated.id ? updated : entry));
  renderLoadouts();
  await loadResources();
}

async function clearStorage() {
  const loadout = activeLoadout();
  if (!loadout) return;
  const updated = await api(`/api/loadouts/${loadout.id}/storage`, { method: "DELETE" });
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
    els.copyShareBtn.textContent = "Link";
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
      in_storage: loadout.in_storage || {},
      recipe_choices: loadout.recipe_choices || {},
      ignored_materials: loadout.ignored_materials || [],
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

async function deleteLoadout() {
  const loadout = activeLoadout();
  if (!loadout) return;
  if (!confirm(`Delete loadout "${loadout.name}"? This cannot be undone.`)) return;
  await api(`/api/loadouts/${loadout.id}`, { method: "DELETE" });
  state.loadouts = state.loadouts.filter((entry) => entry.id !== loadout.id);
  if (!state.loadouts.length) {
    const created = await api("/api/loadouts", {
      method: "POST",
      body: JSON.stringify({ name: "Loadout" }),
    });
    state.loadouts = [created];
  }
  state.activeLoadoutId = state.loadouts[0].id;
  renderLoadouts();
  await loadResources();
}

async function importLoadout(file) {
  if (!file) return;
  let payload;
  try {
    payload = JSON.parse(await file.text());
  } catch (error) {
    alert("Could not import loadout: the selected file is not valid JSON.");
    return;
  }
  const loadout = payload.loadout || payload;
  const created = await api("/api/loadouts/import", {
    method: "POST",
    body: JSON.stringify({
      name: loadout.name || "Imported Loadout",
      items: loadout.items || [],
      collected: loadout.collected || loadout.farmed || {},
      in_storage: loadout.in_storage || {},
      recipe_choices: loadout.recipe_choices || {},
      ignored_materials: loadout.ignored_materials || [],
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
  state.activeSubcategory = "";
  saveLocalLoadouts();
  renderSubcategories();
  renderItems();
});
els.subcategoryFilter.addEventListener("change", () => {
  state.activeSubcategory = els.subcategoryFilter.value;
  saveLocalLoadouts();
  renderItems();
});
els.tierFilter.addEventListener("change", () => {
  state.activeTier = els.tierFilter.value;
  saveLocalLoadouts();
  renderItems();
});
els.resetFiltersBtn.addEventListener("click", () => {
  els.search.value = "";
  state.activeCategory = "";
  state.activeSubcategory = "";
  state.activeTier = "";
  renderCategories();
  renderSubcategories();
  renderTiers();
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
els.clearStorageBtn.addEventListener("click", async () => {
  try {
    await clearStorage();
  } catch (error) {
    alert(`Could not clear storage: ${error.message}`);
  }
});
els.calculatorTab.addEventListener("click", () => switchView("calculator"));
els.gatherTab.addEventListener("click", () => switchView("gather"));
els.gatherLoadoutSelect.addEventListener("change", async () => {
  state.activeLoadoutId = els.gatherLoadoutSelect.value;
  saveLocalLoadouts();
  renderLoadouts();
  await loadResources();
});
els.hideCompletedToggle.addEventListener("change", () => {
  state.hideCompleted = els.hideCompletedToggle.checked;
  localStorage.setItem("icarus.gather.hideCompleted", state.hideCompleted ? "1" : "0");
  renderGatherView();
});
els.gatherClearCollectedBtn.addEventListener("click", clearCollected);
els.copyShareBtn.addEventListener("click", copyShareLink);
els.copyAccountBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(getAccountId());
  els.copyAccountBtn.textContent = "Copied";
  setTimeout(() => {
    els.copyAccountBtn.textContent = "Copy";
  }, 1200);
});
els.switchAccountBtn.addEventListener("click", () => {
  const code = window.prompt("Enter account code:", getAccountId());
  const trimmed = code?.trim();
  if (!trimmed || trimmed === getAccountId()) return;
  localStorage.setItem("icarus.accountId", trimmed);
  location.reload();
});
els.addShareBtn.addEventListener("click", async () => {
  const code = window.prompt("Enter the account code to share this loadout with:");
  const trimmed = code?.trim();
  if (!trimmed) return;
  await setShared(trimmed, true);
});
els.exportLoadoutBtn.addEventListener("click", exportLoadout);
els.deleteLoadoutBtn.addEventListener("click", async () => {
  try {
    await deleteLoadout();
  } catch (error) {
    alert(`Could not delete loadout: ${error.message}`);
  }
});
els.importLoadoutInput.addEventListener("change", async () => {
  try {
    await importLoadout(els.importLoadoutInput.files[0]);
  } catch (error) {
    alert(`Could not import loadout: ${error.message}`);
  } finally {
    els.importLoadoutInput.value = "";
  }
});
setInterval(pollUpdates, 5000);
window.addEventListener("focus", pollUpdates);

loadAll().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin:16px"><h1>Startup failed</h1><p>${error.message}</p></main>`;
});
