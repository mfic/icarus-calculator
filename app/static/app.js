const state = {
  foods: [],
  categories: [],
  buckets: [],
  activeBucketId: localStorage.getItem("icarus.activeBucketId") || "",
  activeCategory: localStorage.getItem("icarus.activeCategory") || "",
  resources: null,
};

const els = {
  meta: document.querySelector("#meta"),
  foods: document.querySelector("#foods"),
  search: document.querySelector("#search"),
  categoryFilter: document.querySelector("#categoryFilter"),
  bucketForm: document.querySelector("#bucketForm"),
  bucketName: document.querySelector("#bucketName"),
  bucketSelect: document.querySelector("#bucketSelect"),
  bucketItems: document.querySelector("#bucketItems"),
  materials: document.querySelector("#materials"),
  steps: document.querySelector("#steps"),
  refreshBtn: document.querySelector("#refreshBtn"),
  foodTemplate: document.querySelector("#foodTemplate"),
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

function saveLocalBuckets() {
  localStorage.setItem("icarus.buckets.snapshot", JSON.stringify(state.buckets));
  localStorage.setItem("icarus.activeBucketId", state.activeBucketId || "");
  localStorage.setItem("icarus.activeCategory", state.activeCategory || "");
}

function formatQuantity(value) {
  return Number.isInteger(value) ? value.toString() : Number(value).toFixed(2).replace(/\.?0+$/, "");
}

function activeBucket() {
  return state.buckets.find((bucket) => bucket.id === state.activeBucketId) || state.buckets[0];
}

function renderMeta(meta) {
  const when = meta.refreshed_at ? new Date(meta.refreshed_at).toLocaleString() : "not refreshed yet";
  els.meta.textContent = `${meta.count || 0} items cached from wiki.gg. Last refresh: ${when}.`;
}

function renderFoods() {
  const term = els.search.value.trim().toLowerCase();
  const category = state.activeCategory.toLowerCase();
  const categoryFiltered = category
    ? state.foods.filter((food) => food.categories.some((entry) => entry.toLowerCase() === category))
    : state.foods;
  const filtered = categoryFiltered.filter((food) => {
    const recipeInputs = food.recipe?.inputs?.map((entry) => entry.name).join(" ") || "";
    return `${food.name} ${food.buffs.join(" ")} ${food.benches.join(" ")} ${food.categories.join(" ")} ${recipeInputs}`.toLowerCase().includes(term);
  });

  els.foods.innerHTML = "";
  if (!filtered.length) {
    els.foods.innerHTML = '<p class="muted">No items match this filter.</p>';
    return;
  }
  for (const food of filtered) {
    const node = els.foodTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = food.name;
    node.querySelector(".bench").textContent = food.benches.length ? `Crafted at: ${food.benches.join(", ")}` : "No crafting bench listed";

    const categories = node.querySelector(".categories");
    for (const categoryName of food.categories.slice(0, 5)) {
      const pill = document.createElement("span");
      pill.className = "category-pill";
      pill.textContent = categoryName;
      categories.appendChild(pill);
    }

    const buffs = node.querySelector(".buffs");
    for (const buff of food.buffs.slice(0, 8)) {
      const pill = document.createElement("span");
      pill.className = "buff";
      pill.textContent = buff;
      buffs.appendChild(pill);
    }
    if (!food.buffs.length) {
      const empty = document.createElement("span");
      empty.className = "muted";
      empty.textContent = "No buff data listed";
      buffs.appendChild(empty);
    }

    const recipe = node.querySelector(".recipe");
    const inputs = food.recipe?.inputs || [];
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
    node.querySelector("button").addEventListener("click", () => addFood(food.name, Number(quantity.value || 1)));
    els.foods.appendChild(node);
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
  saveLocalBuckets();
}

function renderBuckets() {
  els.bucketSelect.innerHTML = "";
  for (const bucket of state.buckets) {
    const option = document.createElement("option");
    option.value = bucket.id;
    option.textContent = bucket.name;
    els.bucketSelect.appendChild(option);
  }
  const bucket = activeBucket();
  if (bucket) {
    state.activeBucketId = bucket.id;
    els.bucketSelect.value = bucket.id;
  }
  saveLocalBuckets();
  renderBucketItems();
}

function renderBucketItems() {
  const bucket = activeBucket();
  els.bucketItems.innerHTML = "";
  if (!bucket || !bucket.items.length) {
    els.bucketItems.innerHTML = '<p class="muted">No foods in this loadout yet.</p>';
    return;
  }
  for (const item of bucket.items) {
    const row = document.createElement("div");
    row.className = "bucket-row";
    row.innerHTML = `<span>${item.food}</span><span class="qty">x${item.quantity}</span>`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => removeFood(item.food));
    row.appendChild(remove);
    els.bucketItems.appendChild(row);
  }
}

function renderResources() {
  els.materials.innerHTML = "";
  els.steps.innerHTML = "";
  const data = state.resources;
  if (!data || !activeBucket()) {
    els.materials.innerHTML = '<p class="muted">Select a bucket to calculate materials.</p>';
    return;
  }

  if (!data.materials.length) {
    els.materials.innerHTML = '<p class="muted">No materials needed yet.</p>';
  }
  for (const material of data.materials) {
    const row = document.createElement("div");
    row.className = "material-row";
    row.innerHTML = `<span>${material.name}</span><span class="qty">${formatQuantity(material.quantity)}</span>`;
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
  const bucket = activeBucket();
  if (!bucket) {
    state.resources = null;
    renderResources();
    return;
  }
  state.resources = await api(`/api/buckets/${bucket.id}/resources`);
  renderResources();
}

async function loadAll() {
  const [meta, foods, categories, buckets] = await Promise.all([
    api("/api/meta"),
    api("/api/items"),
    api("/api/categories"),
    api("/api/buckets"),
  ]);
  renderMeta(meta);
  state.foods = foods.items;
  state.categories = categories.categories;
  state.buckets = buckets.buckets;
  if (!state.buckets.length) {
    const created = await api("/api/buckets", {
      method: "POST",
      body: JSON.stringify({ name: "Team Loadout" }),
    });
    state.buckets = [created];
  }
  renderCategories();
  renderFoods();
  renderBuckets();
  await loadResources();
}

async function addFood(food, quantity) {
  const bucket = activeBucket();
  if (!bucket) return;
  const existing = bucket.items.find((item) => item.food === food);
  const nextQuantity = (existing?.quantity || 0) + Math.max(1, quantity);
  const updated = await api(`/api/buckets/${bucket.id}/items`, {
    method: "PUT",
    body: JSON.stringify({ food, quantity: nextQuantity }),
  });
  state.buckets = state.buckets.map((entry) => (entry.id === updated.id ? updated : entry));
  renderBuckets();
  await loadResources();
}

async function removeFood(food) {
  const bucket = activeBucket();
  if (!bucket) return;
  const updated = await api(`/api/buckets/${bucket.id}/items/${encodeURIComponent(food)}`, { method: "DELETE" });
  state.buckets = state.buckets.map((entry) => (entry.id === updated.id ? updated : entry));
  renderBuckets();
  await loadResources();
}

els.search.addEventListener("input", renderFoods);
els.categoryFilter.addEventListener("change", () => {
  state.activeCategory = els.categoryFilter.value;
  saveLocalBuckets();
  renderFoods();
});
els.bucketSelect.addEventListener("change", async () => {
  state.activeBucketId = els.bucketSelect.value;
  saveLocalBuckets();
  renderBucketItems();
  await loadResources();
});
els.bucketForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = els.bucketName.value.trim();
  if (!name) return;
  const bucket = await api("/api/buckets", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  state.buckets.push(bucket);
  state.activeBucketId = bucket.id;
  els.bucketName.value = "";
  renderBuckets();
  await loadResources();
});
els.refreshBtn.addEventListener("click", async () => {
  els.refreshBtn.disabled = true;
  els.refreshBtn.textContent = "Refreshing...";
  const meta = await api("/api/refresh", { method: "POST" });
  renderMeta(meta);
  const [foods, categories] = await Promise.all([api("/api/items"), api("/api/categories")]);
  state.foods = foods.items;
  state.categories = categories.categories;
  renderCategories();
  renderFoods();
  await loadResources();
  els.refreshBtn.disabled = false;
  els.refreshBtn.textContent = "Refresh Wiki Data";
});

loadAll().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin:16px"><h1>Startup failed</h1><p>${error.message}</p></main>`;
});
