# vue3sys - Start guide (after MySQL + DB import)

## Important: do NOT copy venv or node_modules

| Folder | Portable? | Action on new PC |
|--------|-----------|------------------|
| youlai-django/venv | NO | Delete and recreate |
| vue3-element-admin/node_modules | NO | Run pnpm install |
| Source code + SQL | YES | Copy with project |

---

## One-time setup on target PC (you may have done part of this)

1. Python 3.10-3.14 installed
2. Node.js + `npm install -g pnpm`
3. MySQL running (MySQL84 service started)
4. Database imported
5. **Run recreate venv** (required if you copied project from another PC):

```
D:\vue3sys\deploy\recreate-venv.bat
```

Or deploy menu option **4** (install-deps) after **deleting** folder:
`D:\vue3sys\youlai-django\venv`

6. If frontend deps missing:

```
cd D:\vue3sys\vue3-element-admin
pnpm install
```

7. Config file (if not done):

```
deploy.bat -> option 3
```

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

**Terminal 2 - Django (uses venv, no need to activate if using full path):**
```
cd D:\vue3sys\youlai-django
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

**Terminal 3 - Frontend (NO venv, uses Node):**
```
cd D:\vue3sys\vue3-element-admin
pnpm run dev
```

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
- Start MySQL84: `net start MySQL84`
- Check D:\vue3sys\youlai-django\.env password

**pnpm not found:**
```
npm install -g pnpm
```
Close and reopen CMD.

**Frontend 404 API:**
- Ensure Django window is running on 8000
- Check vue3-element-admin\.env.development has VITE_APP_BASE_API=/api
