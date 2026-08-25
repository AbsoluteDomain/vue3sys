# vue3sys - Start Guide (after MySQL + DB import)

## Important: do NOT copy venv or node_modules

| Folder | Portable? | Action on new PC |
|--------|-----------|------------------|
| youlai-django/venv | NO | Delete and recreate |
| vue3-element-admin/node_modules | NO | Run pnpm install (or copy whole folder for offline) |
| youlai-django/offline_packages | YES | Copy for offline pip install |
| Source code + SQL | YES | Copy with project |

---

## One-time setup on target PC

### Online environment

1. Python 3.10-3.14 installed (3.13 recommended)
2. Node.js 20.19+ or 22.12+ and `npm install -g pnpm`
3. MySQL running (MySQL80 service started)
4. Database imported
5. Run deploy menu: **option 4** (install-deps) or **option 8** (steps 3-5)

### Offline environment (no internet)

1. Install Python / Node / MySQL / Redis from local installers
2. Copy project zip (include `offline_packages/` folder)
3. Run configure.ps1 to generate .env
4. Run install-deps.ps1 (auto-detects offline_packages, installs without internet)
5. Run import-database.ps1 -CreateDatabase

```
D:\vue3sys\deploy\configure.ps1
D:\vue3sys\deploy\install-deps.ps1
D:\vue3sys\deploy\import-database.ps1 -CreateDatabase
```

Or deploy menu option **8** (config + deps + import).

---

## Daily start (3 windows)

Double-click in order, or use **start-all.bat**:

| Order | Script | URL |
|-------|--------|-----|
| 1 | start-redis.bat | port 6379 |
| 2 | start-backend.bat | http://localhost:8000 |
| 3 | start-frontend.bat | http://localhost:3000 |

Or: `D:\vue3sys\deploy\start-all.bat`

---

## Manual commands (same as above)

**Terminal 1 - Redis:**
```
cd D:\vue3sys\Redis
redis-server.exe redis.windows.conf
```

**Terminal 2 - Django (uses venv):**
```
cd D:\vue3sys\youlai-django
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

**Terminal 3 - Frontend (uses Node, not venv):**
```
cd D:\vue3sys\vue3-element-admin
pnpm run dev
```

---

## Update from Git (GitHub or Gitea)

After switching remote to Gitea (see switch-remote.ps1), update with:

```
D:\vue3sys\deploy\update.ps1
```

Or deploy menu option **u**. The script:
- Auto-detects remote (GitHub or Gitea)
- Pulls latest code
- Syncs Python deps (offline if offline_packages exists)
- Runs database migrate
- Restarts services

---

## Frontend vs Backend

- **Backend** = Python + venv + Django
- **Frontend** = Node.js + pnpm (separate from venv)

Activating venv only affects Python. Frontend always uses `pnpm` from system PATH.

---

## Troubleshooting

**venv python fails / wrong path:**
```
rd /s /q D:\vue3sys\youlai-django\venv
D:\vue3sys\deploy\recreate-venv.bat
```

**django check fails:**
- Start MySQL80: `net start MySQL80`
- Check D:\vue3sys\youlai-django\.env password

**pnpm not found:**
```
npm install -g pnpm
```
Close and reopen CMD.

**Frontend 404 API:**
- Ensure Django window is running on 8000
- Check vue3-element-admin\.env.development has VITE_APP_BASE_API=/api

**Offline pip install fails:**
- Ensure offline_packages folder exists in youlai-django/
- Check Python version matches the machine that packed wheels
- `pip install --no-index --find-links=offline_packages -r requirements.txt`
