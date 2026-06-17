# vue3sys Windows 部署说明

将本项目压缩复制到目标 Windows 电脑后，使用 `deploy` 目录下的脚本完成配置、安装与检查。

## 一、压缩包应包含的内容

```
vue3sys/
├── deploy/                    ← 部署脚本（本目录）
├── youlai-django/             ← Django 后端
├── vue3-element-admin/        ← Vue3 前端
├── Redis/                     ← Windows 版 Redis（可选，建议带上）
├── youlai_admin_django.sql    ← 数据库全量备份（强烈建议带上）
└── （可选）youlai-django/sql/mysql/  增量补丁 SQL
```

### 建议不要打进压缩包（体积大、可重建）

- `youlai-django/venv/`
- `vue3-element-admin/node_modules/`
- `.git/`（若不需要版本历史）
- 各目录下的 `__pycache__/`

### 打包前注意

1. **复制 `youlai-django/.env`** 到压缩包，或在目标机用 `configure.ps1` 重新生成（推荐重新生成并改密码）。
2. **删除敏感信息**：`运行步骤.txt` 等文件若含 API Key，不要随包外传。
3. 确认压缩包内含 **`youlai_admin_django.sql`**（纯净系统必需）。

---

## 二、纯净 Windows 系统（无 Python/MySQL 等）

脚本会通过 **winget** 自动安装（需 Windows 10/11 且联网）：

| 组件 | 安装方式 |
|------|----------|
| Python 3.12 | winget `Python.Python.3.12` |
| Node.js LTS | winget `OpenJS.NodeJS.LTS` |
| MySQL 8 | winget `Oracle.MySQL`（可能有安装向导） |
| pnpm | Node 安装后 `npm install -g pnpm` |
| VC++ 运行库 | winget（可选，减少 pip 报错） |
| Redis | **项目自带** `Redis/` 目录，无需单独安装 |

### 推荐流程（目标电脑）

1. 解压到 `D:\vue3sys`
2. **右键以管理员运行** `deploy\安装前置环境-管理员.bat`  
   （自动安装 Python / Node / MySQL / pnpm）
3. 双击 `deploy\一键部署.bat`，选 **「9. 纯净系统全流程」**  
   或手动：3 → 4 → 5 → 2 → 7
4. 浏览器访问 **http://localhost:3000**

若 winget 不可用，脚本会输出 **手动下载链接**，按指引安装后重新运行检查。

---

## 三、已有开发环境的机器

| 软件 | 版本建议 |
|------|----------|
| Python | 3.10 ~ 3.14 |
| Node.js | 18+ LTS |
| pnpm | 最新 |
| MySQL | 8.x |
| MinIO | 可选（文件上传） |

---

## 四、快速开始（目标电脑）

1. 解压到例如 `D:\vue3sys`
2. 纯净系统：先执行第二节的管理员脚本
3. 双击 **`deploy\一键部署.bat`**
4. 选 **「9. 纯净系统全流程」** 或 **「8. 一键部署 3-5」**
5. 选 **「7. 启动所有服务」**
6. 浏览器访问：**http://localhost:3000**

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
| `install-deps.ps1` | venv、pip、pnpm、migrate |
| `import-database.ps1` | 导入 SQL（`-CreateDatabase` 建库） |
| `verify-services.ps1` | 验证 MySQL/Redis/Django |
| `start-all.ps1` | 启动 Redis + Django + 前端 |
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

# 分步部署
powershell -ExecutionPolicy Bypass -File .\configure.ps1
powershell -ExecutionPolicy Bypass -File .\install-deps.ps1
powershell -ExecutionPolicy Bypass -File .\import-database.ps1 -CreateDatabase
powershell -ExecutionPolicy Bypass -File .\check-env.ps1
powershell -ExecutionPolicy Bypass -File .\start-all.ps1
powershell -ExecutionPolicy Bypass -File .\verify-services.ps1
```

---

## 六、常见问题

### 1. winget 不可用

- Windows 10/11 打开 Microsoft Store，更新 **「应用安装程序 / App Installer」**
- 或按 `install-prerequisites.ps1` 输出的链接 **手动下载** Python / Node / MySQL
- 手动安装 Python 时务必勾选 **Add python.exe to PATH**

### 2. MySQL 安装后仍连不上

- 打开 `services.msc`，启动 **MySQL80** 服务
- 安装向导里设置的 **root 密码** 需与 `configure.ps1` 中填写一致
- 安装后 **重新打开** 部署脚本窗口（刷新 PATH）

### 3. 脚本无法运行

以管理员打开 PowerShell 执行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

或直接双击 `一键部署.bat`（已带 `-ExecutionPolicy Bypass`）。

### 4. django check 报数据库连接失败

- 确认 MySQL 服务已启动（服务管理器 → MySQL80）
- 检查 `youlai-django\.env` 中 DB_HOST / DB_USER / DB_PASSWORD
- 用 `import-database.ps1 -CreateDatabase` 创建并导入库

### 5. Redis 连接失败

- 确认 `Redis\redis-server.exe` 已启动
- `configure.ps1` 会把 `.env` 中 `REDIS_PASSWORD` 写入 `redis.windows.conf`
- 开发环境 `config/settings/dev.py` 中 Redis 地址固定为 `localhost:6379`

### 6. 前端能开但接口 404

- 确认 Django 在 8000 端口运行
- 前端 `.env.development` 中 `VITE_APP_BASE_API=/api`，Vite 会代理到 8000

### 7. 文件上传失败

需单独安装并启动 MinIO（或使用 `OSS_TYPE=local` 改本地存储，需自行改 `.env`）。

---

## 七、生产环境说明

当前脚本面向 **Windows 开发/内网部署**。若需正式生产：

- 后端改用 `config.settings.prod`，使用 Gunicorn + NSSM 注册 Windows 服务
- 前端 `pnpm build` 后由 IIS/Nginx 托管 `dist/`
- 修改 `DJANGO_ALLOWED_HOSTS`、HTTPS、强密码

---

## 八、迁移检查清单

- [ ] 解压到 `D:\vue3sys` 等简单路径
- [ ] **纯净系统**：已管理员运行 `安装前置环境-管理员.bat`
- [ ] `check-prerequisites.ps1` 通过
- [ ] 运行 configure.ps1 生成新 `.env`
- [ ] 运行 install-deps.ps1 无报错
- [ ] 导入 SQL 成功
- [ ] check-env.ps1 无红色错误
- [ ] start-all.ps1 后 verify-services.ps1 通过
- [ ] 浏览器可登录系统
