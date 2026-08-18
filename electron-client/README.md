# 协作事业部生产管理系统 - 桌面客户端

## 简介

本项目是「协作事业部生产管理系统」的 Electron 桌面客户端壳子，将现有的 Vue3 前端打包后嵌入 Electron 中运行。

**特点：**
- ✅ 服务端完全不变，继续使用现有的 HTTP 接口
- ✅ 前端套壳，双击即可使用
- ✅ 绿色免安装版（portable exe）
- ✅ 配置文件可编辑，灵活切换服务器
- ✅ 独立文件夹，不影响现有项目

## 目录结构

```
electron-client/
├── package.json              # 项目配置和打包脚本
├── config.json               # 服务器配置文件（用户可编辑）
├── README.md                 # 本说明文件
├── src/
│   ├── main.js               # Electron 主进程（窗口、代理、配置）
│   └── preload.js            # 预加载脚本（注入配置到前端）
├── scripts/
│   └── build-frontend.js     # 前端打包脚本
├── resources/
│   └── icon.ico              # 应用图标
├── frontend/                 # 前端打包产物（构建时自动生成）
│   └── dist/
└── release/                  # 打包输出目录（构建时自动生成）
```

## 快速开始

### 1. 环境要求

- Node.js >= 18
- npm 或 pnpm

### 2. 安装依赖

```bash
cd electron-client
npm install
```

### 3. 开发模式运行

开发模式下，客户端会加载本地前端（需要先打包）或远程前端。

```bash
# 方式一：直接运行（加载远程前端）
npm start

# 方式二：开发模式（打开 DevTools）
npm run dev
```

### 4. 完整打包流程

#### 步骤一：打包前端并构建客户端

```bash
# 一键打包（前端 + Electron）
npm run build
```

这条命令会：
1. 在 `vue3-element-admin/` 目录执行 `npm run build` 打包前端
2. 将 `dist/` 复制到 `electron-client/frontend/dist/`
3. 用 electron-builder 打包成 portable exe

#### 步骤二：获取产物

打包完成后，在 `release/` 目录下会生成：

```
release/
└── 协作事业部生产管理系统-1.0.0-portable.exe
```

### 5. 单独打包前端（不重新打包 Electron）

如果只修改了前端代码，可以单独打包前端：

```bash
npm run build:frontend
```

然后用 `npm start` 测试。

## 配置说明

### config.json 配置文件

客户端首次运行时，会在 exe 同级目录自动创建 `config.json`。用户可以手动编辑此文件来修改服务器配置。

```json
{
  "backendUrl": "http://192.168.100.29:8000",
  "externalApiUrl": "http://172.20.45.143:35203",
  "frontendUrl": "http://192.168.100.29:3000",
  "wsEndpoint": "",
  "preferLocalFrontend": true,
  "window": {
    "width": 1400,
    "height": 900,
    "minWidth": 1024,
    "minHeight": 700
  }
}
```

| 字段 | 说明 | 示例 |
|------|------|------|
| `backendUrl` | 后端 API 地址（Django 服务） | `http://192.168.100.29:8000` |
| `externalApiUrl` | 外部订单接口地址 | `http://172.20.45.143:35203` |
| `frontendUrl` | 远程前端地址（本地前端加载失败时备用） | `http://192.168.100.29:3000` |
| `wsEndpoint` | WebSocket 端点（留空则自动推导为 `ws://<backendUrl>/ws`） | `ws://192.168.100.29:8000/ws` |
| `preferLocalFrontend` | 是否优先加载本地打包的前端 | `true` |
| `window` | 窗口大小配置 | - |

### 修改配置

1. 找到 exe 同级目录下的 `config.json`
2. 用文本编辑器打开
3. 修改对应字段
4. 保存后重启客户端

也可以通过菜单栏 **帮助 → 打开配置文件位置** 快速定位。

## 工作原理

### 请求代理

前端在 `file://` 协议下运行时，所有 API 请求（`/api/...`、`/ext-order/...`）会被 Electron 主进程拦截，重定向到配置的后端服务器：

```
前端请求: file:///api/v1/users/  （file:// 协议下的相对路径）
    ↓ Electron 拦截
重定向到: http://192.168.100.29:8000/api/v1/users/
```

### WebSocket 注入

前端打包后，`VITE_APP_WS_ENDPOINT` 环境变量是固定的。Electron 通过 `preload.js` 在运行时注入 WebSocket 端点：

```
config.json 中的 wsEndpoint（或自动推导）
    ↓ main.js 读取
    ↓ 通过环境变量传给 preload.js
    ↓ preload.js 暴露为 window.electronAPI.wsEndpoint
    ↓ 前端 useStomp.ts 优先读取 window.electronAPI.wsEndpoint
```

### 本地前端 + 远程前端备用

1. 优先加载本地打包的前端（`frontend/dist/index.html`）
2. 如果本地前端不存在，加载 `config.json` 中的 `frontendUrl`
3. 如果两者都不可用，显示错误提示

## 分发使用

### 给用户分发

将 `release/协作事业部生产管理系统-1.0.0-portable.exe` 复制给用户即可。

用户使用方式：
1. 双击 exe 运行
2. 首次运行会在 exe 同级目录生成 `config.json`
3. 如需修改服务器地址，编辑 `config.json` 后重启

### 注意事项

- exe 需要放在用户有写权限的目录（因为要生成 config.json）
- 不要放在 `C:\Program Files` 等需要管理员权限的目录
- 建议放在桌面或 `D:\` 等用户目录

## 常见问题

### Q: 启动后白屏？

**A:** 可能是前端未打包。运行 `npm run build:frontend` 打包前端，或修改 `config.json` 中 `preferLocalFrontend` 为 `false` 使用远程前端。

### Q: API 请求失败？

**A:** 检查 `config.json` 中的 `backendUrl` 是否正确，确保后端服务正在运行。

### Q: WebSocket 不连接？

**A:** 检查 `config.json` 中的 `wsEndpoint`，留空会自动推导为 `ws://<backendUrl>/ws`。确保后端 WebSocket 服务正常。

### Q: 如何切换服务器？

**A:** 编辑 exe 同级目录的 `config.json`，修改 `backendUrl` 和 `frontendUrl`，重启客户端。

### Q: 如何清除登录状态？

**A:** 菜单栏 → 视图 → 开发者工具 → Application → Local Storage → 清除。或按 `Ctrl+Shift+R` 强制刷新。

## 删除客户端

如果不再需要桌面客户端，直接删除整个 `electron-client/` 文件夹即可，**不会影响** `vue3-element-admin/` 和 `youlai-django/` 项目。

唯一对现有项目的改动是 `vue3-element-admin/src/composables/websocket/useStomp.ts` 中添加了一行 Electron 兼容代码（不影响 Web 环境运行），可选择性保留或删除。
