# vue3sys Windows 部署说明

将本项目压缩复制到目标 Windows 电脑后，使用 `deploy` 目录下的脚本完成配置、安装与检查。

> 本文档面向两个场景：**有外网**（脚本自动 winget 安装）与 **无外网**（离线打包部署）。

---

## 一、系统要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10 ~ 3.14（开发机使用 3.13） | |
| Node.js | 20.19+ 或 22.12+（开发机使用 24.x） | 低于 20.19 构建会失败 |
| pnpm | 10.x | `npm install -g pnpm` |
| uv | 最新版（可选，推荐） | Python 依赖安装速度提升 5-10 倍，`pip install uv` |
| MySQL | 8.0+ | 字符集 utf8mb4 |
| Redis | 5.0+ | Windows 版需项目自带 |
| Nginx | 1.24+（可选，生产部署） | 前端静态托管 + 反向代理 |

---

## 二、压缩包应包含的内容

```
vue3sys/
├── deploy/                    ← 部署脚本（本目录）
│   ├── templates/             ← .env 模板
│   ├── _common.ps1            ← 公共函数
│   ├── pack-offline-deps.ps1  ← 离线打包 Python 依赖（联网机器上执行）
│   ├── switch-remote.ps1       ← GitHub <-> Gitea 远程切换
│   └── ...
├── youlai-django/             ← Django 后端
│   ├── requirements.txt
│   └── offline_packages/      ← 离线 wheel 包（离线部署时需准备）
├── vue3-element-admin/        ← Vue3 前端
├── Redis/                     ← Windows 版 Redis（可选，建议带上）
└── youlai_admin_django.sql    ← 数据库全量备份（强烈建议带上）
```

### 建议不要打进压缩包（体积大、可重建）

- `youlai-django/venv/`
- `vue3-element-admin/node_modules/`
- `.git/`（若不需要版本历史）
- 各目录下的 `__pycache__/`

### 打包前注意

1. **复制 `youlai-django/.env`** 到压缩包，或在目标机用 `configure.ps1` 重新生成（推荐重新生成并改密码）。
2. **离线部署**：在联网机器上先运行 `deploy\pack-offline-deps.ps1` 生成 `offline_packages/` 目录。
3. 确认压缩包内含 **`youlai_admin_django.sql`**（纯净系统必需）。

---

## 三、有外网部署（标准流程）

适用于能访问互联网的 Windows 10/11/Server 机器，脚本通过 **winget** 自动安装：

| 组件 | 安装方式 |
|------|----------|
| Python 3.13 | winget `Python.Python.3.13` |
| Node.js LTS | winget `OpenJS.NodeJS.LTS` |
| MySQL 8 | winget `Oracle.MySQL`（可能有安装向导） |
| pnpm | Node 安装后 `npm install -g pnpm` |
| VC++ 运行库 | winget（可选，减少 pip 报错） |
| Redis | **项目自带** `Redis/` 目录，无需单独安装 |

### 推荐流程（目标电脑）

1. 解压到 `D:\vue3sys`
2. **右键以管理员运行** `deploy\安装前置环境-管理员.bat`
3. 双击 `deploy\一键部署.bat`，选 **「9. 纯净系统全流程」**
   或手动：3 → 4 → 5 → 2 → 7
4. 浏览器访问 **http://localhost:3000**

若 winget 不可用，脚本会输出 **手动下载链接**，按指引安装后重新运行检查。

---

## 四、无外网离线部署（新服务器场景）

> 目标服务器无外网，所有依赖必须提前在联网机器上打包。

### 4.1 在联网机器上准备（开发机即可）

#### 4.1.1 打包 Python 离线依赖

```powershell
cd c:\work\vue3sys\deploy
powershell -ExecutionPolicy Bypass -File .\pack-offline-deps.ps1
```

执行后会在 `youlai-django\offline_packages\` 目录生成所有 `.whl` 文件。

#### 4.1.2 打包前端依赖

最简方案：直接将整个 `vue3-element-admin` 目录（含 `node_modules`）拷贝到目标服务器。

或在联网机器上构建好 `dist/` 目录，目标服务器用 Nginx 托管静态文件（见第六节）。

#### 4.1.3 准备软件安装包

下载以下安装包拷贝到目标服务器：

| 软件 | 下载地址 | 说明 |
|------|---------|------|
| Python 3.13 | https://www.python.org/downloads/windows/ | `python-3.13.x-amd64.exe` |
| Node.js 22.x | https://nodejs.org/en/download/ | `node-v22.x.x-x64.msi` |
| MySQL 8.0 | https://dev.mysql.com/downloads/installer/ | `mysql-installer-community.msi` |
| Redis | https://github.com/tporadowski/redis/releases | Windows 版 |
| Nginx | http://nginx.org/en/download.html | 可选，生产用 |

### 4.2 在目标服务器上安装

#### 4.2.1 安装基础软件

按顺序双击安装包，安装 Python、Node.js、MySQL、Redis、Nginx。

- **Python**：安装时勾选 "Add Python to PATH"
- **MySQL**：设置 root 密码，字符集选 utf8mb4
- **Redis**：解压到 `C:\redis`，修改 `redis.windows.conf` 中 `requirepass 123456`
- **pnpm**：`npm install -g pnpm`

#### 4.2.2 解压项目并部署

将项目压缩包解压到 `D:\vue3sys`，确保包含 `offline_packages/` 目录。

```powershell
cd D:\vue3sys\deploy

# 1. 配置 .env 文件
powershell -ExecutionPolicy Bypass -File .\configure.ps1

# 2. 安装依赖（自动检测 offline_packages 离线安装）
powershell -ExecutionPolicy Bypass -File .\install-deps.ps1

# 3. 导入数据库
powershell -ExecutionPolicy Bypass -File .\import-database.ps1 -CreateDatabase

# 4. 验证
powershell -ExecutionPolicy Bypass -File .\check-env.ps1

# 5. 启动服务
powershell -ExecutionPolicy Bypass -File .\start-all.ps1
```

验证：浏览器访问 `http://localhost:3000`

---

## 五、脚本说明

| 脚本 | 作用 |
|------|------|
| `安装前置环境-管理员.bat` | **纯净系统首选**，自动 winget 安装 Python/Node/MySQL/pnpm |
| `install-prerequisites.ps1` | 检查/安装系统前置（交互或 `-InstallAll`） |
| `check-prerequisites.ps1` | 仅检查前置，不安装 |
| `prerequisites-config.json` | winget 包 ID 与 MySQL 路径配置 |
| `一键部署.bat` | 双击入口，调用 setup.ps1 |
| `setup.ps1` | 交互式主菜单（含选项 9 纯净全流程） |
| `check-env.ps1` | 检查前置 + 项目配置 + 端口 + Django |
| `configure.ps1` | 生成 `.env`、同步 Redis 密码 |
| `install-deps.ps1` | venv、pip、pnpm、migrate（**支持离线安装 + uv 加速**） |
| `pack-offline-deps.ps1` | **联网机器上执行**，打包 Python wheel 包 |
| `import-database.ps1` | 导入 SQL（`-CreateDatabase` 建库） |
| `verify-services.ps1` | 验证 MySQL/Redis/Django |
| `start-all.ps1` | 启动 Redis + Django + 前端 |
| `update.ps1` | **从 Git 远程拉取更新**（支持 GitHub/Gitea） |
| `switch-remote.ps1` | **切换 Git 远程**（GitHub <-> Gitea） |
| `打包项目.bat` | 源电脑打 zip（排除 node_modules/venv） |

### 命令行直接调用（PowerShell）

```powershell
cd D:\vue3sys\deploy

# 纯净系统：管理员 PowerShell
powershell -ExecutionPolicy Bypass -File .\install-prerequisites.ps1 -InstallAll

# 纯净系统全流程
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Action fresh

# 仅检查前置
powershell -ExecutionPolicy Bypass -File .\check-prerequisites.ps1

# 离线安装依赖（自动检测 offline_packages 目录，uv 在 PATH 中会自动启用 uv 模式）
powershell -ExecutionPolicy Bypass -File .\install-deps.ps1

# 显式使用 uv（更快，安装依赖 5-10x 速度）
powershell -ExecutionPolicy Bypass -File .\install-deps.ps1 -UseUv

# 分步部署
powershell -ExecutionPolicy Bypass -File .\configure.ps1
powershell -ExecutionPolicy Bypass -File .\install-deps.ps1
powershell -ExecutionPolicy Bypass -File .\import-database.ps1 -CreateDatabase
powershell -ExecutionPolicy Bypass -File .\check-env.ps1
powershell -ExecutionPolicy Bypass -File .\start-all.ps1
powershell -ExecutionPolicy Bypass -File .\verify-services.ps1
```

---

## 六、生产环境部署（Nginx + 静态前端）

面向正式生产环境，前端构建为静态文件由 Nginx 托管，后端用 Daphne 运行。

### 6.1 构建前端

在联网或开发机上执行：

```powershell
cd c:\work\vue3sys\vue3-element-admin
pnpm build
# 产物在 dist/ 目录
```

### 6.2 拷贝到服务器

```
D:\vue3sys\
├── youlai-django\          # 后端（含 venv、offline_packages）
├── vue3-element-admin\dist\  # 前端构建产物
└── youlai_admin_django.sql
```

### 6.3 启动后端（Daphne）

```powershell
cd D:\vue3sys\youlai-django
.\venv\Scripts\daphne.exe -b 0.0.0.0 -p 8000 config.asgi:application
```

### 6.4 配置 Nginx

编辑 `C:\nginx\conf\nginx.conf`：

```nginx
worker_processes  1;

events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    client_max_body_size 100m;

    server {
        listen       80;
        server_name  localhost;

        # 前端静态页面
        location / {
            root   D:/vue3sys/vue3-element-admin/dist;
            index  index.html;
            try_files $uri $uri/ /index.html;
        }

        # API 代理到后端
        location /prod-api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

```powershell
cd C:\nginx
start nginx.exe
```

验证：浏览器访问 `http://服务器IP/` 应显示登录页面。

### 6.5 注册 Windows 服务（自启动，推荐）

下载 [NSSM](https://nssm.cc/download)（在联网机器下载后拷贝）：

```powershell
# 后端服务
nssm install YoulaiBackend "D:\vue3sys\youlai-django\venv\Scripts\daphne.exe"
nssm set YoulaiBackend AppParameters "-b 0.0.0.0 -p 8000 config.asgi:application"
nssm set YoulaiBackend AppDirectory "D:\vue3sys\youlai-django"
nssm start YoulaiBackend

# Nginx 服务
nssm install YoulaiNginx "C:\nginx\nginx.exe"
nssm set YoulaiNginx AppDirectory "C:\nginx"
nssm start YoulaiNginx

# Redis 服务
C:\redis\redis-server.exe --service-install C:\redis\redis.windows.conf --service-name RedisService
net start RedisService
```

---

## 七、从 GitHub 迁移到 Gitea

适用于：目标服务器上已有 Gitea，希望将 GitHub 上的仓库迁移到内网 Gitea。

### 7.1 在 Gitea 上创建空仓库

1. 登录 Gitea Web 界面（如 `http://192.168.1.100:3000`）
2. 点击 **"+" → "新建仓库"**
3. 填写仓库名称（如 `vue3sys`）
4. **不要**勾选"初始化仓库"（不要添加 README/.gitignore）
5. 点击 **创建仓库**

### 7.2 方法一：Gitea 自带迁移功能（推荐）

Gitea 支持直接从 GitHub 导入：

1. 在 Gitea 新建仓库页面，点击 **"迁移"** 选项卡
2. 选择 **GitHub**
3. 填写：
   - GitHub 仓库地址：`https://github.com/AbsoluteDomain/vue3sys`
   - GitHub 用户名和 Token（需在 GitHub 生成 Personal Access Token）
4. 选择要迁移的内容（issues、labels、releases 等）
5. 点击 **迁移仓库**

> 此方法需要 Gitea 服务器能访问 GitHub。如果 Gitea 也在内网无法访问外网，用方法二。

### 7.3 方法二：本地推送（Gitea 无法访问 GitHub 时）

在开发机（能同时访问 GitHub 和 Gitea）上操作：

```powershell
cd c:\work\vue3sys

# 1. 确保已从 GitHub 拉取最新代码
git fetch --all
git checkout master
git pull origin master

# 2. 添加 Gitea 为新远程
git remote add gitea http://192.168.1.100:3000/your-user/vue3sys.git

# 3. 推送所有分支和标签到 Gitea
git push gitea --all
git push gitea --tags

# 4. 验证
git remote -v
# 应显示:
#   origin  https://github.com/AbsoluteDomain/vue3sys.git (fetch)
#   origin  https://github.com/AbsoluteDomain/vue3sys.git (push)
#   gitea   http://192.168.1.100:3000/your-user/vue3sys.git (fetch)
#   gitea   http://192.168.1.100:3000/your-user/vue3sys.git (push)
```

### 7.4 切换默认远程为 Gitea

在目标服务器上（或开发机上）使用部署脚本切换：

```powershell
cd D:\vue3sys\deploy

# 查看当前远程
powershell -ExecutionPolicy Bypass -File .\switch-remote.ps1 -Action list

# 切换到 Gitea
powershell -ExecutionPolicy Bypass -File .\switch-remote.ps1 -Action gitea -GiteaUrl "http://192.168.1.100:3000/your-user/vue3sys.git"

# 切回 GitHub
powershell -ExecutionPolicy Bypass -File .\switch-remote.ps1 -Action github
```

### 7.5 从 Gitea 更新代码

切换到 Gitea 后，正常使用 update.ps1 即可：

```powershell
cd D:\vue3sys\deploy
powershell -ExecutionPolicy Bypass -File .\update.ps1
```

脚本会自动检测远程是 Gitea 还是 GitHub，执行 `git pull` + 同步依赖 + 数据库迁移 + 重启服务。

### 7.6 Gitea 凭据缓存

为避免每次 push/pull 输入密码，配置凭据存储：

```powershell
# 存储凭据（明文，仅内网建议）
git config --global credential.helper store

# 或使用 Gitea 的 Personal Access Token 作为密码：
# 在 Gitea -> 头像 -> 设置 -> 应用 -> 生成 Token
# push 时用户名填 Gitea 用户名，密码填 Token
```

---

## 八、常见问题

### 1. winget 不可用

- Windows 10/11 打开 Microsoft Store，更新 **「应用安装程序 / App Installer」**
- 或按 `install-prerequisites.ps1` 输出的链接 **手动下载** Python / Node / MySQL
- 手动安装 Python 时务必勾选 **Add python.exe to PATH**

### 2. 离线安装 pip 报错

- 确认 `offline_packages/` 目录与 `requirements.txt` 在同一层级
- 确认下载 wheel 包的 Python 版本/系统架构与目标服务器一致
- 手动安装：`pip install --no-index --find-links=offline_packages -r requirements.txt`

### 3. MySQL 安装后仍连不上

- 打开 `services.msc`，启动 **MySQL80** 服务
- 安装向导里设置的 **root 密码** 需与 `configure.ps1` 中填写一致
- 安装后 **重新打开** 部署脚本窗口（刷新 PATH）

### 4. 脚本无法运行

以管理员打开 PowerShell 执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

或直接双击 `一键部署.bat`（已带 `-ExecutionPolicy Bypass`）。

### 5. django check 报数据库连接失败

- 确认 MySQL 服务已启动（服务管理器 → MySQL80）
- 检查 `youlai-django\.env` 中 DB_HOST / DB_USER / DB_PASSWORD
- 用 `import-database.ps1 -CreateDatabase` 创建并导入库

### 6. Redis 连接失败

- 确认 `Redis\redis-server.exe` 已启动
- `configure.ps1` 会把 `.env` 中 `REDIS_PASSWORD` 写入 `redis.windows.conf`
- 开发环境 `config/settings/dev.py` 中 Redis 地址固定为 `localhost:6379`

### 7. 前端能开但接口 404

- 确认 Django 在 8000 端口运行
- 前端 `.env.development` 中 `VITE_APP_BASE_API=/api`，Vite 会代理到 8000
- 生产环境 `.env.production` 中 `VITE_APP_BASE_API=/prod-api`，Nginx 代理 `/prod-api/` 到 8000

### 8. 文件上传失败

需单独安装并启动 MinIO（或使用 `OSS_TYPE=local` 改本地存储，需自行改 `.env`）。

### 9. 迁移报 "Table already exists"

```powershell
cd D:\vue3sys\youlai-django
.\venv\Scripts\python.exe manage.py migrate --fake
```

### 10. git pull 提示凭据错误

- GitHub：使用 Personal Access Token 代替密码
- Gitea：在 Gitea 设置中生成 Token，作为密码使用
- 配置凭据存储：`git config --global credential.helper store`

### 11. 日志中记录的 IP 全是 127.0.0.1

经过 Vite 开发服务器或 Nginx 反向代理后，Django 直连看到的是代理本机地址，需由代理透传真实 IP：

- **Vite（3000 端口 dev 模式）**：`vite.config.ts` 的 `/api` 代理必须配置 `xfwd: true`，修改后**必须重启 Vite 服务**才会生效。
- **Nginx**：`location /api/` 与 `/prod-api/` 均需包含 `proxy_set_header X-Real-IP $remote_addr;` 和 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`，改完执行 `nginx -s reload`。
- 后端通过 `get_client_ip()` 统一按 `X-Real-IP → X-Forwarded-For → Forwarded → REMOTE_ADDR` 顺序解析，无需各业务日志自行处理。
- 正式环境建议使用 Nginx 托管 `dist/` 静态文件，不要长期运行 Vite dev server。

---

## 九、迁移检查清单

- [ ] 解压到 `D:\vue3sys` 等简单路径
- [ ] **纯净系统**：已管理员运行 `安装前置环境-管理员.bat`
- [ ] **离线部署**：`offline_packages/` 目录已准备
- [ ] `check-prerequisites.ps1` 通过
- [ ] 运行 configure.ps1 生成新 `.env`
- [ ] 运行 install-deps.ps1 无报错
- [ ] 导入 SQL 成功
- [ ] check-env.ps1 无红色错误
- [ ] start-all.ps1 后 verify-services.ps1 通过
- [ ] 浏览器可登录系统
- [ ] **Gitea 迁移**：仓库已创建、代码已推送、远程已切换
