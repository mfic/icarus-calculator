function getAccountId() {
  let id = localStorage.getItem("icarus.accountId");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("icarus.accountId", id);
  }
  return id;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", "X-Account-Id": getAccountId() },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatQuantity(value) {
  return Number.isInteger(value) ? value.toString() : Number(value).toFixed(2).replace(/\.?0+$/, "");
}

const SOURCE_COLORS = [
  "#d2a84a",
  "#72b587",
  "#5f9ee1",
  "#e16f5f",
  "#b58fe1",
  "#e1c95f",
  "#5fe1c9",
  "#e15f9e",
  "#9ee15f",
  "#e1925f",
];

function sourceColorMap(loadout) {
  const map = new Map();
  if (!loadout) return map;
  loadout.items.forEach((entry, index) => {
    const name = entry.item || entry.food;
    map.set(name, SOURCE_COLORS[index % SOURCE_COLORS.length]);
  });
  return map;
}

function renderSourceDots(sources, colors) {
  if (!sources?.length) return null;
  const wrap = document.createElement("span");
  wrap.className = "source-dots";
  for (const source of sources) {
    const dot = document.createElement("span");
    dot.className = "source-dot";
    dot.style.backgroundColor = colors.get(source) || "var(--muted)";
    dot.title = source;
    wrap.appendChild(dot);
  }
  return wrap;
}

function createStepper({ value, min = 0, step = 1, ariaLabel, onChange }) {
  const wrap = document.createElement("div");
  wrap.className = "stepper";

  const decrement = document.createElement("button");
  decrement.type = "button";
  decrement.className = "stepper-btn secondary";
  decrement.textContent = "−";
  decrement.setAttribute("aria-label", `Decrease ${ariaLabel}`);

  const input = document.createElement("input");
  input.type = "number";
  input.className = "stepper-input";
  input.min = String(min);
  input.step = String(step);
  input.value = value;
  input.setAttribute("aria-label", ariaLabel);

  const increment = document.createElement("button");
  increment.type = "button";
  increment.className = "stepper-btn secondary";
  increment.textContent = "+";
  increment.setAttribute("aria-label", `Increase ${ariaLabel}`);

  function commit(nextValue) {
    const clamped = Math.max(min, nextValue);
    input.value = clamped;
    onChange(clamped);
  }

  decrement.addEventListener("click", () => commit((Number(input.value) || 0) - step));
  increment.addEventListener("click", () => commit((Number(input.value) || 0) + step));
  input.addEventListener("change", () => commit(Number(input.value) || 0));

  wrap.appendChild(decrement);
  wrap.appendChild(input);
  wrap.appendChild(increment);
  return wrap;
}

const EYE_ICON =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>' +
  '<circle cx="12" cy="12" r="3"/></svg>';

const EYE_OFF_ICON =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>' +
  '<circle cx="12" cy="12" r="3"/><line x1="2" y1="2" x2="22" y2="22"/></svg>';

function createIgnoreToggle({ ignored, ariaLabel, onToggle }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "icon-btn ignore-toggle";
  button.innerHTML = ignored ? EYE_OFF_ICON : EYE_ICON;
  button.setAttribute("aria-pressed", String(ignored));
  button.title = ariaLabel;
  button.setAttribute("aria-label", ariaLabel);
  button.addEventListener("click", () => onToggle(!ignored));
  return button;
}

function renderIgnoredChips(container, names, onRestore) {
  container.innerHTML = "";
  if (!names?.length) {
    container.hidden = true;
    return;
  }
  container.hidden = false;
  for (const name of names) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "ignored-chip";
    chip.textContent = name;
    chip.title = `Restore ${name}`;
    chip.setAttribute("aria-label", `Restore ${name}`);
    chip.addEventListener("click", () => onRestore(name));
    container.appendChild(chip);
  }
}

function renderMaterialCards(container, materials, colors, { hideCompleted = false, onIgnore, onCollectedChange } = {}) {
  container.innerHTML = "";
  const filtered = hideCompleted
    ? materials.filter((material) => (material.remaining ?? material.quantity) > 0)
    : materials;
  if (!filtered.length) {
    container.innerHTML = '<p class="muted">Nothing to gather. Add items to this loadout from the calculator.</p>';
    return;
  }
  for (const material of filtered) {
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
      onToggle: () => onIgnore(material.name, true),
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
      onChange: (value) => onCollectedChange(material.name, value),
    });
    actions.appendChild(stepper);
    const maxBtn = document.createElement("button");
    maxBtn.type = "button";
    maxBtn.className = "secondary";
    maxBtn.textContent = "Max";
    maxBtn.setAttribute("aria-label", `Set ${material.name} collected to ${formatQuantity(material.quantity)}`);
    maxBtn.addEventListener("click", () => onCollectedChange(material.name, material.quantity));
    actions.appendChild(maxBtn);
    card.appendChild(actions);

    container.appendChild(card);
  }
}

function renderShareChips(container, accountIds, onRemove) {
  container.innerHTML = "";
  for (const accountId of accountIds || []) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "ignored-chip";
    chip.textContent = accountId;
    chip.title = `Remove ${accountId}`;
    chip.setAttribute("aria-label", `Remove ${accountId}`);
    chip.addEventListener("click", () => onRemove(accountId));
    container.appendChild(chip);
  }
}
