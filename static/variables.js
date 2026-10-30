// Variables perso (bouton + de Compose) : creer, modifier, supprimer sans recharger la page.
(() => {
  const dialog = document.getElementById("var-dialog");
  if (!dialog) return;
  const chips = document.getElementById("custom-vars");
  const list = document.getElementById("var-list");
  const rowTemplate = document.getElementById("var-row-tpl");
  const newForm = document.getElementById("var-new");
  const errorBox = document.getElementById("var-error");
  const urls = dialog.dataset;

  function showError(message) {
    errorBox.textContent = message || "";
    errorBox.classList.toggle("hidden", !message);
  }

  function renderChips(variables) {
    chips.replaceChildren(...variables.map((v) => {
      const chip = Object.assign(document.createElement("button"), { type: "button", className: "var-chip var-chip-custom", textContent: `{${v.name}}` });
      chip.dataset.var = `{${v.name}}`;
      chip.title = v.value || "(vide)";
      return chip;
    }));
  }

  function renderRows(variables) {
    if (!variables.length) {
      list.replaceChildren(Object.assign(document.createElement("li"), { className: "text-sm text-subtle", textContent: "Aucune variable perso pour l'instant." }));
      return;
    }
    list.replaceChildren(...variables.map((v) => {
      const row = rowTemplate.content.firstElementChild.cloneNode(true);
      row.querySelector("[data-name]").textContent = `{${v.name}}`;
      row.querySelector("[data-value]").value = v.value;
      row.querySelector("[data-save]").addEventListener("click", () => save(`${urls.base}${v.id}`, { value: row.querySelector("[data-value]").value }));
      row.querySelector("[data-delete]").addEventListener("click", () => {
        if (window.confirm(`Supprimer {${v.name}} ?`)) save(`${urls.base}${v.id}/delete`, {});
      });
      return row;
    }));
  }

  function render(variables) {
    renderChips(variables);
    renderRows(variables);
  }

  async function save(url, payload) {
    try {
      const data = await postJSON(url, payload);
      render(data.variables);
      showError("");
      document.dispatchEvent(new CustomEvent("variables:changed"));
      return true;
    } catch (err) {
      showError(err.message);
      return false;
    }
  }

  newForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ok = await save(urls.create, { name: newForm.elements.namedItem("name").value, value: newForm.elements.namedItem("value").value });
    if (ok) newForm.reset();
  });
  document.getElementById("var-add").addEventListener("click", () => {
    showError("");
    dialog.showModal();
    newForm.elements.namedItem("name").focus();
  });
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });

  render(JSON.parse(urls.items));
})();
