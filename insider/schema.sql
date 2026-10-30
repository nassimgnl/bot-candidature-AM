PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS institutions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_formats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    institution_id  INTEGER NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    pattern         TEXT NOT NULL,
    position        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (institution_id, pattern)
);

CREATE TABLE IF NOT EXISTS contacts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    civilite         TEXT NOT NULL DEFAULT 'Monsieur',
    prenom           TEXT NOT NULL,
    nom              TEXT NOT NULL,
    poste            TEXT NOT NULL DEFAULT '',
    institution      TEXT NOT NULL DEFAULT '',
    email            TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT 'non_contacte',
    followups_sent   INTEGER NOT NULL DEFAULT 0,
    lang             TEXT NOT NULL DEFAULT 'fr',
    notes            TEXT NOT NULL DEFAULT '',
    last_sent_at     TEXT,
    replied_at       TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email COLLATE NOCASE) WHERE email <> '';
CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);

CREATE TABLE IF NOT EXISTS templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    lang            TEXT NOT NULL CHECK (lang IN ('fr', 'en')),
    category        TEXT NOT NULL CHECK (category IN ('candidature', 'coffee_chat', 'relance')),
    followup_step   INTEGER,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emails (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN ('initial', 'relance', 'test')),
    subject      TEXT NOT NULL,
    body         TEXT NOT NULL,
    message_id   TEXT,
    ok           INTEGER NOT NULL DEFAULT 1,
    error        TEXT,
    sent_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_emails_contact ON emails(contact_id);
CREATE INDEX IF NOT EXISTS idx_emails_sent_at ON emails(sent_at);

CREATE TABLE IF NOT EXISTS profile (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    prenom        TEXT NOT NULL DEFAULT '',
    nom           TEXT NOT NULL DEFAULT '',
    ecole         TEXT NOT NULL DEFAULT '',
    poste_actuel  TEXT NOT NULL DEFAULT '',
    cv_filename   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
