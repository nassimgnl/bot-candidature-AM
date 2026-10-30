// Onglet Contacts > Ajouter : email genere en direct, choix d'institution, glisser-deposer.
(() => {
  const instInput = document.getElementById("institution-input");
  const form = document.getElementById("add-form");
  const emailInput = document.getElementById("email-input");
  const formatRow = document.getElementById("format-row");
  const formatSelect = document.getElementById("format-select");
  const unknownHint = document.getElementById("unknown-hint");
  let emailTouched = false;
  emailInput.addEventListener("input", () => { emailTouched = emailInput.value !== ""; });

  const refresh = debounce(async () => {
    const params = new URLSearchParams({
      prenom: form.prenom.value, nom: form.nom.value,
      institution: instInput.value, format_index: formatSelect.value || 0,
    });
    const data = await (await fetch(`${document.getElementById("add-form").dataset.previewUrl}?${params}`)).json();
    const previous = formatSelect.value;
    formatSelect.replaceChildren(...data.formats.map((f, i) => new Option(f, i)));
    formatSelect.value = previous && previous < data.formats.length ? previous : 0;
    formatRow.classList.toggle("hidden", data.formats.length < 2);
    unknownHint.classList.toggle("hidden", !instInput.value || data.formats.length > 0);
    if (!emailTouched) emailInput.value = data.email;
  });
  [form.prenom, form.nom, instInput, formatSelect].forEach((el) => el.addEventListener("input", refresh));

  document.querySelectorAll("[data-inst]").forEach((btn) => btn.addEventListener("click", () => {
    instInput.value = btn.dataset.inst; refresh(); form.prenom.focus();
  }));
  document.getElementById("inst-search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll("[data-inst]").forEach((btn) => {
      btn.classList.toggle("hidden", !btn.dataset.inst.toLowerCase().includes(q));
    });
  });

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const showName = () => { if (fileInput.files[0]) document.getElementById("drop-label").textContent = fileInput.files[0].name; };
  fileInput.addEventListener("change", showName);
  ["dragenter", "dragover"].forEach((t) => dropzone.addEventListener(t, (e) => { e.preventDefault(); dropzone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((t) => dropzone.addEventListener(t, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); }));
  dropzone.addEventListener("drop", (e) => { fileInput.files = e.dataTransfer.files; showName(); });
})();
