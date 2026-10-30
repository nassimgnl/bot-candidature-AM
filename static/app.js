// Outils partages par toutes les pages.
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Erreur ${response.status}`);
  return data;
}

function debounce(fn, delay = 250) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

// Case "tout selectionner" : data-select-all="nom-des-cases".
document.querySelectorAll("[data-select-all]").forEach((master) => {
  const boxes = () => document.querySelectorAll(`input[name="${master.dataset.selectAll}"]`);
  const counter = document.querySelector(`[data-select-count="${master.dataset.selectAll}"]`);
  const refresh = () => {
    if (counter) counter.textContent = [...boxes()].filter((b) => b.checked).length;
  };
  master.addEventListener("change", () => { boxes().forEach((b) => { b.checked = master.checked; }); refresh(); });
  document.addEventListener("change", (e) => { if (e.target.name === master.dataset.selectAll) refresh(); });
  refresh();
});

// Bascule mode clair / mode sombre (memorise dans le navigateur).
function syncThemeLabels() {
  const dark = document.documentElement.dataset.theme === "dark";
  document.querySelectorAll("[data-theme-label]").forEach((el) => { el.textContent = dark ? "Mode clair" : "Mode sombre"; });
}
document.querySelectorAll("[data-theme-toggle]").forEach((btn) => btn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) { /* navigation privee : theme non memorise */ }
  syncThemeLabels();
}));
syncThemeLabels();

// Fermeture des messages.
document.querySelectorAll("[data-dismiss]").forEach((btn) => btn.addEventListener("click", () => btn.closest(".flash").remove()));

// Copier dans le presse-papiers : data-copy="#id-de-l-element".
document.querySelectorAll("[data-copy]").forEach((btn) => btn.addEventListener("click", async () => {
  const source = document.querySelector(btn.dataset.copy);
  const label = btn.querySelector("[data-copy-label]");
  try {
    await navigator.clipboard.writeText(source.innerText.trim());
    if (label) { label.textContent = "Copie !"; setTimeout(() => { label.textContent = "Copier"; }, 1600); }
  } catch (e) {
    window.alert("Copie impossible : selectionne le texte et fais Cmd+C.");
  }
}));

// Confirmation avant une action destructive : data-confirm="message".
document.addEventListener("submit", (event) => {
  const submitter = event.submitter;
  const message = (submitter && submitter.dataset.confirm) || event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});
