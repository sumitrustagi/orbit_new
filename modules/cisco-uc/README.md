# Cisco UC Hub

A comprehensive management platform for Cisco Unified Communications infrastructure. Monitor and manage **CUCM**, **Unity Connection**, **IM&P**, and **Expressway** from a single web interface.

## Features

### CUCM (Cisco Unified Communications Manager)
- **Phones** — View, search, and manage IP phones with registration status
- **Device Pools** — Monitor device pool configurations
- **Partitions & CSS** — View dial plan partitions and calling search spaces
- **Route Patterns** — Manage route and translation patterns
- **Gateways & Trunks** — Monitor voice gateways and SIP trunks

### Unity Connection
- **Mailboxes** — View and manage voicemail mailboxes
- **Users** — Monitor Unity Connection user accounts

### IM&P (Instant Messaging & Presence)
- **Presence Users** — View Jabber/IM&P users with real-time presence status
- **IM Status** — Monitor IM enablement and federation

### Expressway / VCS
- **Nodes** — Monitor Expressway-C and Expressway-E nodes
- **Zones** — View traversal zones, CUCM zones, and search rules
- **MRA Status** — Mobile and Remote Access monitoring

### Platform
- **Day/Light Mode** — Toggle between dark and light themes
- **Role-Based Access** — Platform Admin, GUI Admin, End User roles
- **Audit Logging** — SHA-256 chained integrity with full audit trail
- **Background Sync** — Celery-powered scheduled synchronization
- **Setup Wizard** — First-run configuration wizard
- **Multi-Auth** — Local, LDAP, SAML, OIDC authentication support

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 16 (production) or SQLite (development)
- Redis 7 (production, for Celery)

### Installation

```bash
# Clone or extract the project
cd cisco-uc-hub

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Set Flask environment
export FLASK_ENV=development
export FLASK_APP=wsgi:app

# Initialize database
flask db upgrade

# Create admin user
flask admin create-admin --username admin --email admin@example.com --password YourPassword123!

# (Optional) Seed demo data
flask admin seed-demo

# Run the application
flask run --port 8000
```

### Access
Open http://localhost:8000 in your browser.

## CLI Commands

```bash
# Create a platform admin
flask admin create-admin --username admin --email admin@example.com --password Pass123!

# List all users
flask admin list-users

# Reset a user's password
flask admin reset-password --username admin --password NewPass123!

# Seed demo data (phones, device pools, mailboxes, etc.)
flask admin seed-demo
```

## Background Tasks (Celery)

For production, start a Celery worker and beat scheduler:

```bash
# Worker
celery -A celery_worker.celery worker --loglevel=info

# Beat (scheduled tasks)
celery -A celery_worker.celery beat --loglevel=info
```

### Scheduled Tasks
| Task | Schedule | Description |
|------|----------|-------------|
| Sync CUCM | Hourly | Sync phones, device pools, partitions, CSS, routes, gateways, trunks |
| Sync Unity Users | Every 4 hours | Sync Unity Connection users |
| Sync Unity Mailboxes | Every 4 hours | Sync Unity Connection mailboxes |
| Sync IM&P Users | Every 4 hours | Sync IM&P presence users |
| Sync Expressway | Every 4 hours | Sync Expressway nodes and zones |
| Health Ping | Every 5 minutes | Celery health check |
| Audit Purge | Daily | Purge audit logs older than 90 days |

## Production Deployment

For production, use Gunicorn with PostgreSQL and Redis:

```bash
# Install production dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost:5432/cisco_uc_hub
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Run with Gunicorn
gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 4 --timeout 120
```

## Architecture

```
cisco-uc-hub/
├── app/
│   ├── __init__.py          # App factory (10-step init)
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   │   ├── user.py          # User with RBAC
│   │   ├── audit.py         # Audit log with SHA-256 chaining
│   │   ├── app_config.py    # Dynamic runtime config
│   │   ├── cucm.py          # Phone, DevicePool, Partition, CSS, RoutePattern, Gateway, Trunk
│   │   ├── unity.py         # UnityMailbox, UnityUser
│   │   ├── imp.py           # IMPUser
│   │   └── expressway.py    # Expressway, Zone
│   ├── services/            # API clients
│   │   ├── axl_client.py    # CUCM AXL/RIS SOAP + REST
│   │   ├── unity_client.py  # Unity Connection REST (CUPI)
│   │   ├── imp_client.py    # IM&P REST
│   │   └── expressway_client.py  # Expressway REST
│   ├── routes/              # Flask blueprints
│   ├── forms/               # WTForms
│   ├── tasks/               # Celery background tasks
│   ├── cli/                 # Flask CLI commands
│   ├── utils/               # Decorators, crypto, filters
│   └── templates/           # Jinja2 templates
├── migrations/              # Alembic migrations
├── config.py                # Configuration classes
├── wsgi.py                  # WSGI entry point
├── celery_worker.py         # Celery entry point
└── requirements.txt         # Python dependencies
```

## API Integrations

| Platform | API | Protocol |
|----------|-----|----------|
| CUCM | AXL (Administrative XML) | SOAP via Zeep |
| CUCM | RIS (Real-time Info) | SOAP/REST |
| Unity Connection | CUPI | REST (JSON) |
| IM&P | Presence API | REST (JSON) |
| Expressway | Provisioning API | REST (JSON) |

## License

Internal use only. Not for redistribution.
