# Orbit Platform

**Unified Communications Management Platform**

Orbit is a modular platform for managing enterprise communication systems. It provides a single, unified interface for administering multiple communication platforms through independent, installable modules.

## Modules

| Module | Description | APIs Used |
|--------|-------------|-----------|
| **Webex Calling** | Cisco Webex Calling provisioning & DID management | Webex REST API |
| **Microsoft Teams** | Teams administration, meetings, call queues | Microsoft Graph API |
| **Cisco UC** | CUCM, Unity Connection, IM&P, Expressway | AXL SOAP, CUPI REST, IM&P REST, Expressway REST |

## Features

- **GUI-based installer** — Interactive terminal UI (whiptail) guides you through module selection, credential entry, and setup
- **Modular architecture** — Install one, two, or all three modules; each runs independently
- **Day/Light mode** — Full dark and light theme support with localStorage persistence
- **Role-based access control** — Platform Admin, GUI Admin, End User roles
- **Audit logging** — SHA-256 chained integrity hashing for tamper detection
- **Background tasks** — Celery workers with scheduled sync jobs per module
- **Landing page** — Central portal linking to all installed modules
- **TLS by default** — Self-signed certificate generated during install (replace with Let's Encrypt for production)
- **Nginx reverse proxy** — Each module proxied under its own URL path
- **Systemd services** — Gunicorn, Celery worker, and Celery beat per module

## Requirements

- **OS**: Ubuntu 20.04/22.04/24.04, Debian 11/12, RHEL/CentOS/Rocky/AlmaLinux 8/9
- **Python**: 3.10+ (installed automatically)
- **PostgreSQL**: 14+ (installed automatically)
- **Redis**: 6+ (installed automatically)
- **Root access**: Required for system package installation and service creation

## Quick Start

```bash
# 1. Extract the archive
unzip orbit-platform.zip
cd orbit-platform

# 2. Run the installer as root
sudo bash install.sh
```

The installer will guide you through:

1. **Module selection** — Choose which modules to install (checkboxes)
2. **Installation directory** — Where to install (default: `/opt/orbit`)
3. **Server configuration** — FQDN or IP for TLS and Nginx
4. **Web admin account** — Username, email, and password for the web interface
5. **CLI admin account** — SSH access credentials (root login is disabled)
6. **Platform credentials** — Per-module API credentials:
   - Webex: Client ID, Client Secret, Org ID
   - Teams: Azure AD Tenant ID, Client ID, Client Secret
   - Cisco UC: CUCM, Unity, IM&P, Expressway host/user/password
7. **Port configuration** — Internal ports for each module
8. **Worker configuration** — Gunicorn and Celery concurrency

## Architecture

```
/opt/orbit/
├── certs/                    # TLS certificates
├── landing/                  # Landing page (module portal)
├── webex-calling/            # Webex Calling module
│   ├── app/                  #   Flask application
│   ├── migrations/           #   Alembic migrations
│   ├── venv/                 #   Python virtual environment
│   ├── .env                  #   Configuration
│   ├── wsgi.py               #   WSGI entry point
│   └── celery_worker.py      #   Celery entry point
├── teams-hub/                # Microsoft Teams module
│   └── (same structure)
└── cisco-uc/                 # Cisco UC module
    └── (same structure)
```

## Service Management

Each module creates three systemd services:

```bash
# Webex Calling
sudo systemctl {start|stop|restart|status} orbit-webex-calling
sudo systemctl {start|stop|restart|status} orbit-webex-calling-celery
sudo systemctl {start|stop|restart|status} orbit-webex-calling-beat

# Microsoft Teams
sudo systemctl {start|stop|restart|status} orbit-teams-hub
sudo systemctl {start|stop|restart|status} orbit-teams-hub-celery
sudo systemctl {start|stop|restart|status} orbit-teams-hub-beat

# Cisco UC
sudo systemctl {start|stop|restart|status} orbit-cisco-uc
sudo systemctl {start|stop|restart|status} orbit-cisco-uc-celery
sudo systemctl {start|stop|restart|status} orbit-cisco-uc-beat
```

## URLs

After installation, access the platform at:

| Resource | URL |
|----------|-----|
| Landing Page | `https://<server>/` |
| Webex Calling | `https://<server>/webex/` |
| Microsoft Teams | `https://<server>/teams/` |
| Cisco UC | `https://<server>/cisco-uc/` |

## Logs

All logs are stored in `/var/log/orbit/`:

```bash
# View module logs
tail -f /var/log/orbit/webex-calling-error.log
tail -f /var/log/orbit/teams-hub-error.log
tail -f /var/log/orbit/cisco-uc-error.log

# View install log
cat /tmp/orbit-install.log
```

## Development Mode

To run a module locally without the full installer:

```bash
cd modules/cisco-uc    # or webex-calling, teams-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FLASK_ENV=development
export FLASK_APP="app:create_app()"

flask db migrate -m "initial"
flask db upgrade
flask admin create-admin --username admin --email admin@example.com --password Admin123!
flask run --port 8000
```

In development mode, each module uses SQLite (no PostgreSQL) and SimpleCache (no Redis).

## CLI Commands

Each module provides these Flask CLI commands:

```bash
# Create a platform admin user
flask admin create-admin --username <user> --email <email> --password <pass>

# List all users
flask admin list-users

# Reset a user's password
flask admin reset-password --username <user> --password <newpass>

# Seed demo data
flask admin seed-demo
```

## TLS Certificate

The installer generates a self-signed certificate. For production, replace with Let's Encrypt:

```bash
sudo certbot --nginx -d your-domain.com
```

## License

Proprietary. All rights reserved.
