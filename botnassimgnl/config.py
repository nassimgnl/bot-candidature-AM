"""Configuration lue depuis le fichier .env."""

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILENAME = "bot.db"
# Nom de la base dans la premiere version du projet : renommee automatiquement au lancement.
LEGACY_DATABASE_FILENAME = "insider.db"
# Valeurs d'exemple de .env.example : tant qu'elles sont la, la boite mail n'est pas consideree comme configuree.
PLACEHOLDER_VALUES = frozenset({"ton.adresse@gmail.com", "xxxx xxxx xxxx xxxx"})

SMTP_PRESETS = {
    "gmail": {"label": "Gmail", "hint": "Recommande", "smtp": "smtp.gmail.com", "port": 587,
              "imap": "imap.gmail.com", "app_password_url": "https://myaccount.google.com/apppasswords"},
    "outlook": {"label": "Outlook", "hint": "Hotmail, Live, Microsoft 365", "smtp": "smtp.office365.com", "port": 587,
                "imap": "outlook.office365.com", "app_password_url": "https://account.microsoft.com/security"},
    "yahoo": {"label": "Yahoo", "hint": "Yahoo Mail, AOL", "smtp": "smtp.mail.yahoo.com", "port": 465,
              "imap": "imap.mail.yahoo.com", "app_password_url": "https://login.yahoo.com/account/security"},
    "other": {"label": "Autre", "hint": "Serveur personnalise", "smtp": "", "port": 587, "imap": "",
              "app_password_url": ""},
}


def detect_provider(smtp_host: str) -> str:
    """Fournisseur correspondant au serveur SMTP configure (sinon "other")."""
    host = (smtp_host or "").lower()
    return next((key for key, preset in SMTP_PRESETS.items() if preset["smtp"] and preset["smtp"] == host), "other")


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} doit etre un nombre entier (valeur actuelle : {raw!r})") from exc


@dataclass(frozen=True)
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    imap_host: str
    sender_name: str
    send_delay_seconds: int
    daily_send_limit: int
    followup_delay_days: int
    followup_max: int
    secret_key: str
    data_dir: Path

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password) and not self.uses_placeholders

    @property
    def uses_placeholders(self) -> bool:
        return self.smtp_user in PLACEHOLDER_VALUES or self.smtp_password in PLACEHOLDER_VALUES

    @property
    def imap_configured(self) -> bool:
        return bool(self.imap_host and self.smtp_user and self.smtp_password) and not self.uses_placeholders

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


def load_settings() -> Settings:
    """Construit la configuration a partir des variables d'environnement."""
    data_dir = Path(os.environ.get("DATA_DIR", BASE_DIR / "data")).resolve()
    return Settings(
        smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com").strip(),
        smtp_port=_int("SMTP_PORT", 587),
        smtp_user=os.environ.get("SMTP_USER", "").strip(),
        smtp_password=os.environ.get("SMTP_PASSWORD", "").strip(),
        imap_host=os.environ.get("IMAP_HOST", "imap.gmail.com").strip(),
        sender_name=os.environ.get("SENDER_NAME", "").strip(),
        send_delay_seconds=max(0, _int("SEND_DELAY_SECONDS", 20)),
        daily_send_limit=max(1, _int("DAILY_SEND_LIMIT", 100)),
        followup_delay_days=max(1, _int("FOLLOWUP_DELAY_DAYS", 5)),
        followup_max=min(3, max(0, _int("FOLLOWUP_MAX", 3))),
        secret_key=os.environ.get("SECRET_KEY", "").strip() or os.urandom(24).hex(),
        data_dir=data_dir,
    )
