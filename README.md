# BOT nassimgnl — bot de candidatures

Site local (mode clair / sombre) pour envoyer des candidatures spontanées en masse aux banques : on importe un fichier CSV de contacts, le site devine l'email pro de chaque personne grâce au **format mail de sa banque**, remplit automatiquement un modèle de mail, l'envoie depuis ta boîte Gmail avec ton CV, puis gère les **relances** et le suivi des réponses.

## Installation (une seule fois)

Il faut **Python 3.10 ou plus récent**.

```bash
git clone https://github.com/nassimgnl/bot-candidature-AM.git
cd bot-candidature-AM
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows : copy .env.example .env
```

Puis ouvre le fichier `.env` et remplis-le (voir ci-dessous).

## Lancement

```bash
source .venv/bin/activate
python app.py
```

Ouvre **http://localhost:5000** dans ton navigateur. Le site n'est accessible que depuis ton ordinateur.

## Lancer depuis GitHub Codespaces (sans rien installer)

1. Sur la page GitHub du projet : bouton vert **Code** → onglet **Codespaces** → **Create codespace on main**.
2. Attends 1 à 2 minutes : les dépendances s'installent et le site se lance tout seul (`python app.py`).
3. Une notification propose **Open in Browser** (sinon : onglet **Ports** → port 5000 → icône 🌐).
4. Pour relancer le site plus tard : dans le terminal, `python app.py`.

**Identifiants mail dans Codespaces** : le plus sûr est d'utiliser les *secrets Codespaces* (github.com → Settings → Codespaces → Secrets) : crée `SMTP_USER`, `SMTP_PASSWORD`, `SENDER_NAME`, `SECRET_KEY` et autorise-les pour ce dépôt, puis redémarre le codespace. (Tu peux aussi créer un fichier `.env` dans le codespace : il n'est jamais envoyé sur GitHub.)

⚠️ Le site n'a pas de connexion : laisse le port 5000 en visibilité **Private** (réglage par défaut). En « Public », n'importe qui ayant le lien pourrait envoyer des mails depuis ta boîte.

À savoir : un codespace s'arrête après 30 min d'inactivité (un envoi groupé en cours s'interrompt) ; tes contacts sont conservés tant que tu ne supprimes pas le codespace.

## Le fichier `.env`

| Variable | À mettre | Exemple |
|---|---|---|
| `SMTP_HOST` | Serveur d'envoi | `smtp.gmail.com` |
| `SMTP_PORT` | Port d'envoi | `587` |
| `SMTP_USER` | Ton adresse mail | `prenom.nom@gmail.com` |
| `SMTP_PASSWORD` | **Mot de passe d'application** Google (16 caractères) | `abcd efgh ijkl mnop` |
| `IMAP_HOST` | Serveur de lecture (pour « Vérifier inbox ») | `imap.gmail.com` |
| `SENDER_NAME` | Nom affiché comme expéditeur | `Nassim Goundoul` |
| `SEND_DELAY_SECONDS` | Pause entre deux mails | `20` |
| `DAILY_SEND_LIMIT` | Maximum de mails par jour | `100` |
| `FOLLOWUP_DELAY_DAYS` | Relancer après X jours sans réponse | `5` |
| `FOLLOWUP_MAX` | Nombre de relances max (0 à 3) | `3` |
| `SECRET_KEY` | Chaîne aléatoire | `python -c "import secrets; print(secrets.token_hex(32))"` |

**Mot de passe d'application Gmail** : myaccount.google.com → Sécurité → active la validation en 2 étapes → *Mots de passe des applications* → crée-en un nommé « BOT nassimgnl » → copie les 16 caractères dans `SMTP_PASSWORD`.

⚠️ Le fichier `.env` contient ton mot de passe : il est exclu de Git (`.gitignore`) et ne doit jamais être publié.

## Comment ça marche

1. **Profil** : prénom, nom, école, poste et CV (utilisés dans les mails).
2. **Contacts** : ajout manuel ou **import CSV / Excel** (`Prenom`, `Nom` obligatoires ; `Institution`, `Poste`, `Civilite`, `Email` facultatifs). L'email est généré automatiquement si la banque est connue.
3. **Formats mail** : ajoute, modifie ou supprime une banque et ses formats (`{prenom}.{nom}@banque.com`, `{prenom[0]}{nom}@banque.com`…).
4. **Compose** : choisis les destinataires et un modèle (FR/EN · Candidature / Coffee Chat / Relance). Les variables `{Civilite} {Prenom} {Nom} {Poste} {Institution} {Mon_Prenom} {Mon_Nom} {Mon_Ecole} {Mon_Poste} {Date}` sont remplacées pour chaque contact. Le bouton **« M'envoyer un mail test »** t'envoie le mail à toi-même.
5. **Relances** : les contacts sans réponse depuis `FOLLOWUP_DELAY_DAYS` jours apparaissent ici. Les relances 1, 2 et 3 partent **dans le même fil** que le premier mail. Après la dernière, le contact passe en « Sans réponse ».
6. **Vérifier inbox** : lit ta boîte et passe automatiquement les contacts en « Répondu » ou « Bounce ».
7. **Suivi / Pipeline / Analytics** : statuts, tableau à glisser-déposer, entonnoir et envois par jour.

Format du CSV : voir `static/template_import_contacts.csv` (téléchargeable depuis la page Contacts).

## Tests

```bash
python -m pytest
```

## Structure

```
app.py                 point d'entrée
botnassimgnl/          code Python (Flask)
  email_format.py      génération des emails à partir des formats
  csv_import.py        lecture CSV / Excel
  templating.py        variables des modèles
  campaigns.py         préparation des envois et des relances
  sender.py            envoi groupé en arrière-plan
  mailer.py / inbox.py SMTP (envoi) et IMAP (réponses, bounces)
  repos/               accès à la base SQLite
  routes/              une page = un fichier
templates/             pages HTML
static/                CSS / JS
data/                  base de données et CV (créé au lancement, jamais publié)
```

## Bientôt

Un script de scan LinkedIn générera automatiquement le fichier CSV de contacts à importer.
