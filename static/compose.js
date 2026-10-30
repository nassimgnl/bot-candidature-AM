// Page Compose : templates, apercu, sauvegarde de templates et suivi de l'envoi groupe.
(() => {
  const form = document.getElementById("compose-form");
  const subject = document.getElementById("subject");
  const body = document.getElementById("body");
  const sendBtn = document.getElementById("send-btn");
  const templateButtons = [...document.querySelectorAll("[data-template]")];
  const state = { lang: "fr", cat: "candidature", template: null };

  const selectedIds = () => [...form.querySelectorAll('input[name="ids"]:checked')].map((b) => b.value);

  function setActive(selector, attr, value) {
    document.querySelectorAll(selector).forEach((b) => b.classList.toggle("tab-active", b.dataset[attr] === value));
  }

  function filterTemplates() {
    setActive("[data-lang]", "lang", state.lang);
    setActive("[data-cat]", "cat", state.cat);
    let count = 0;
    templateButtons.forEach((btn) => {
      const t = JSON.parse(btn.dataset.template);
      const visible = t.lang === state.lang && t.category === state.cat;
      btn.classList.toggle("hidden", !visible);
      btn.classList.toggle("tab-active", state.template && state.template.id === t.id);
      if (visible) count += 1;
    });
    document.getElementById("tpl-count").textContent = count;
  }

  function loadTemplate(t) {
    state.template = t;
    subject.value = t.subject;
    body.value = t.body;
    document.getElementById("tpl-update").classList.remove("hidden");
    document.getElementById("tpl-delete").classList.remove("hidden");
    filterTemplates();
    refreshPreview();
  }

  const refreshPreview = debounce(async () => {
    const ids = selectedIds();
    const smtpReady = sendBtn.dataset.smtpReady === "true";
    sendBtn.disabled = !(smtpReady && ids.length && subject.value.trim() && body.value.trim());
    if (!subject.value.trim() && !body.value.trim()) return;
    try {
      const data = await postJSON(form.dataset.previewUrl, { contact_id: ids[0] || "", subject: subject.value, body: body.value });
      document.getElementById("preview-empty").classList.add("hidden");
      document.getElementById("preview").classList.remove("hidden");
      document.getElementById("pv-to").textContent = ids.length > 1 ? `${data.to} (+${ids.length - 1} autres)` : data.to;
      document.getElementById("pv-subject").textContent = data.subject;
      // HTML deja echappe cote serveur (render_html) : seuls les liens des variables sont des balises.
      document.getElementById("pv-body").innerHTML = data.html;
    } catch (err) {
      console.error(err);
    }
  }, 300);

  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => { state.lang = b.dataset.lang; filterTemplates(); }));
  document.querySelectorAll("[data-cat]").forEach((b) => b.addEventListener("click", () => { state.cat = b.dataset.cat; filterTemplates(); }));
  templateButtons.forEach((b) => b.addEventListener("click", () => loadTemplate(JSON.parse(b.dataset.template))));
  [subject, body].forEach((el) => el.addEventListener("input", refreshPreview));
  form.addEventListener("change", (e) => { if (e.target.name === "ids" || e.target.dataset.selectAll) refreshPreview(); });

  // Delegue : les variables perso sont ajoutees dynamiquement par variables.js.
  document.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-var]");
    if (!chip) return;
    const start = body.selectionStart ?? body.value.length;
    body.setRangeText(chip.dataset.var, start, body.selectionEnd ?? start, "end");
    body.focus();
    refreshPreview();
  });
  document.addEventListener("variables:changed", refreshPreview);

  const search = document.getElementById("recipient-search");
  if (search) search.addEventListener("input", () => {
    const q = search.value.toLowerCase();
    document.querySelectorAll("#recipients [data-search]").forEach((row) => row.classList.toggle("hidden", !row.dataset.search.includes(q)));
  });

  // Sauvegarde / suppression de templates via un formulaire cache.
  const tplForm = document.getElementById("tpl-form");
  const urls = document.getElementById("tpl-urls").dataset;
  // namedItem evite les conflits avec les proprietes natives du formulaire (form.name, form.lang).
  const field = (name) => tplForm.elements.namedItem(name);
  function submitTemplate(action, name) {
    tplForm.action = action;
    field("name").value = name;
    field("lang").value = state.lang;
    field("category").value = state.cat;
    field("followup_step").value = state.template && state.template.category === state.cat ? state.template.followup_step ?? "" : "";
    field("subject").value = subject.value;
    field("body").value = body.value;
    tplForm.submit();
  }
  document.getElementById("tpl-save-new").addEventListener("click", () => {
    const name = window.prompt("Nom du nouveau template :");
    if (name) submitTemplate(urls.create, name);
  });
  document.getElementById("tpl-update").addEventListener("click", () => {
    if (state.template) submitTemplate(`${urls.base}${state.template.id}`, state.template.name);
  });
  document.getElementById("tpl-delete").addEventListener("click", () => {
    if (state.template && window.confirm(`Supprimer le template « ${state.template.name} » ?`)) {
      tplForm.action = `${urls.base}${state.template.id}/delete`;
      tplForm.submit();
    }
  });

  // Suivi de l'envoi groupe.
  const job = document.getElementById("job");
  if (job) {
    const STATES = { running: "", done: "— termine ✅", stopped: "— arrete", limit: "— limite journaliere atteinte" };
    const poll = async () => {
      const data = await (await fetch(job.dataset.url)).json();
      job.querySelector("[data-progress]").textContent = `${data.sent + data.failed} / ${data.total}`;
      job.querySelector("[data-state]").textContent = `${STATES[data.status] || ""} (${data.sent} envoye(s), ${data.failed} echec(s))`;
      job.querySelector("[data-bar]").style.width = `${(100 * (data.sent + data.failed)) / Math.max(data.total, 1)}%`;
      job.querySelector("[data-log]").replaceChildren(...data.log.slice().reverse().map((line) => Object.assign(document.createElement("li"), { textContent: line })));
      job.querySelector("[data-stop-btn]").classList.toggle("hidden", data.status !== "running");
      if (data.status === "running") setTimeout(poll, 2000);
    };
    job.querySelector("[data-stop-btn]").addEventListener("click", () => postJSON(job.dataset.stop, {}));
    poll();
  }

  const first = templateButtons.map((b) => JSON.parse(b.dataset.template)).find((t) => t.lang === state.lang && t.category === state.cat);
  if (first) loadTemplate(first); else filterTemplates();
})();
