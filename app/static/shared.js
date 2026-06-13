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
