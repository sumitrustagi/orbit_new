# Teams Hub

**Microsoft Teams Management Platform** — built with Flask, Microsoft Graph API, SQLAlchemy, Celery & Redis.

Teams Hub is a self-hosted admin dashboard for managing Microsoft Teams, Channels, Users, Meetings, Call Queues, and Auto Attendants through the Microsoft Graph API. It follows the same architecture and patterns as [Orbit](https://github.com/sumitrustagi/orbit) (Webex Calling management platform).

---

## Features

| Area | Capabilities |
|------|-------------|
| **Teams & Channels** | Create, list, archive/unarchive teams; create channels; sync from Microsoft 365 |
| **User Management** | Local user accounts with roles (Platform Admin, GUI Admin, End User); Microsoft 365 user sync |
| **Meetings** | Schedule and list online meetings via Graph API |
| **Call Management** | View/sync Call Queues and Auto Attendants from Teams Phone System |
| **Settings** | Configure Graph API credentials, SMTP, security policies, and app appearance at runtime |
| **Audit Logging** | SHA-256 chained audit logs with full HTTP context; filterable log viewer |
| **Task Monitor** | Live Celery worker status, manual task triggers, execution history |
| **Authentication** | Local auth with bcrypt; extensible for LDAP, SAML, OIDC SSO |
| **Day / Light Mode** | Toggle between dark and light themes; preference saved in `localStorage` |
| **Background Sync** | Celery beat schedules for hourly team sync, 4-hourly user sync, daily audit purge |
| **Setup Wizard** | First-run wizard to create admin account and configure Graph API |
| **CLI Tools** | `flask admin create-admin`, `list-users`, `reset-password`, `seed-demo` |

---

## Architecture

```
teams-hub/
├── app/
│   ├── __init__.py          # Application factory (10-step init)
│   ├── extensions.py        # Flask extension instances
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Blueprint route handlers
│   ├── forms/               # WTForms
│   ├── services/            # Microsoft Graph API client
│   ├── tasks/               # Celery async tasks
│   ├── cli/                 # Flask CLI commands
│   ├── utils/               # Decorators, crypto, template filters
│   └── templates/           # Jinja2 templates with day/light mode
├── migrations/              # Alembic database migrations
├── config.py                # Config hierarchy (Dev/Test/Prod)
├── wsgi.py                  # Gunicorn entry point
├── celery_worker.py         # Celery worker entry point
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variable template
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- A Microsoft Azure AD App Registration with Graph API permissions

### Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**, name it "Teams Hub"
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Go to **Certificates & secrets** → **New client secret** → copy the value
5. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**:
   - `Team.ReadBasic.All`, `Team.Create`, `TeamMember.Read.All`
   - `Channel.ReadBasic.All`, `Channel.Create`
   - `User.Read.All`, `User.ReadWrite.All`
   - `OnlineMeetings.ReadWrite.All`
   - `Organization.Read.All`
6. Click **Grant admin consent**

### Setup

```bash
# 1. Create a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment
export FLASK_ENV=development
export FLASK_APP=wsgi:app
export SECRET_KEY=dev-secret-key

# 4. Initialize the database
flask db upgrade

# 5. (Optional) Create an admin user via CLI
flask admin create-admin --username admin --email admin@example.com --password Admin123!

# 6. Run the development server
flask run --port 8000

# 7. (Optional) Run Celery worker in another terminal
celery -A celery_worker.celery worker --loglevel=info

# 8. (Optional) Run Celery beat in another terminal
celery -A celery_worker.celery beat --loglevel=info
```

The first time you visit, you'll be redirected to the **Setup Wizard** to create an admin account.

---

## Production Deployment

For production use, set:

```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@host:5432/teamshub
export REDIS_URL=redis://host:6379/0
export SECRET_KEY=<long-random-string>
export MS_TENANT_ID=<your-tenant-id>
export MS_CLIENT_ID=<your-client-id>
export MS_CLIENT_SECRET=<your-client-secret>
```

Run with Gunicorn:

```bash
gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 4
```

---

## CLI Commands

```bash
# Create a platform admin
flask admin create-admin --username admin --email admin@example.com --password SecretPass1!

# List all users
flask admin list-users

# Reset a user's password
flask admin reset-password --username admin --password NewPass123!

# Seed demo data (5 teams, 5 channels, 3 call queues, 2 auto attendants)
flask admin seed-demo
```

---

## Configuration

Teams Hub uses a config hierarchy:

| Config Class | Use Case | Database | Cache |
|-------------|----------|----------|-------|
| `DevelopmentConfig` | Local dev | SQLite | SimpleCache |
| `TestingConfig` | pytest | In-memory SQLite | SimpleCache |
| `ProductionConfig` | Deployment | PostgreSQL | Redis |

Set `FLASK_ENV=development|testing|production` to select the active config.

All sensitive settings (Graph API credentials, SMTP passwords) can also be configured at runtime through the **Settings** UI, stored encrypted in the database via the `AppConfig` model.

---

## Day / Light Mode

Teams Hub includes a dark (default) and light theme. Toggle via the sun/moon button in the top bar. The preference is stored in `localStorage` and restored on every page load. All colors use CSS custom properties for seamless switching.

---

## Background Tasks (Celery)

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_all_teams` | Every hour | Syncs teams and channels from Microsoft 365 |
| `sync_graph_users` | Every 4 hours | Syncs users from Azure AD |
| `sync_call_resources` | Every 4 hours | Syncs call queues and auto attendants |
| `health_ping` | Every 5 minutes | Health check recorded in audit log |
| `purge_old_audit_logs` | Daily at midnight | Removes audit entries older than 90 days |

---

## Stack

- **Backend**: Flask 3.1, SQLAlchemy 2.0, Alembic, Flask-Login, Flask-WTF
- **API**: Microsoft Graph API via MSAL (client credentials flow)
- **Database**: PostgreSQL (prod) / SQLite (dev)
- **Queue**: Celery 5.4 + Redis
- **Web Server**: Gunicorn
- **Auth**: bcrypt, extensible for LDAP/SAML/OIDC

---

## License

This project is provided as-is for internal use. Modify and deploy as needed.
