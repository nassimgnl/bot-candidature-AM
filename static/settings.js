// Page Parametres : choix du fournisseur -> tutoriel et bloc .env correspondants.
(() => {
  const snippet = document.getElementById("env-snippet");
  const presets = JSON.parse(snippet.dataset.presets);
  const buttons = [...document.querySelectorAll("[data-provider]")];

  function envFor(key) {
    const p = presets[key];
    return [
      `SMTP_HOST=${p.smtp || "smtp.ton-fournisseur.com"}`,
      `SMTP_PORT=${p.port}`,
      `SMTP_USER=${snippet.dataset.user}`,
      "SMTP_PASSWORD=xxxx xxxx xxxx xxxx",
      `IMAP_HOST=${p.imap || "imap.ton-fournisseur.com"}`,
      "SENDER_NAME=Prenom Nom",
    ].join("\n");
  }

  function select(key) {
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.provider === key)));
    document.querySelectorAll("[data-provider-panel]").forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.providerPanel !== key);
    });
    snippet.textContent = envFor(key);
  }

  buttons.forEach((b) => b.addEventListener("click", () => select(b.dataset.provider)));
  const initial = buttons.find((b) => b.getAttribute("aria-pressed") === "true");
  select(initial ? initial.dataset.provider : "gmail");
})();
