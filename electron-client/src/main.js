/**
 * Electron 主进程
 *
 * 架构：
 * 1. 启动本地 HTTP 服务器（端口 18888）
 * 2. 本地服务器提供前端静态文件 + 代理 API 请求到远程后端
 * 3. Electron 加载 http://localhost:18888
 *
 * 这样避免了 file:// 协议的跨域和资源路径问题
 */

const { app, BrowserWindow, Menu, shell, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const http = require("http");
const https = require("https");

// ==================== 配置管理 ====================

const DEFAULT_CONFIG = {
  backendUrl: "http://192.168.100.29:8000",
  externalApiUrl: "http://172.20.45.143:35203",
  frontendUrl: "http://192.168.100.29:3000",
  wsEndpoint: "",
  window: {
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
  },
  preferLocalFrontend: true,
};

/**
 * 获取配置文件路径
 */
function getConfigPath() {
  const possiblePaths = [
    path.join(process.cwd(), "config.json"),
    path.join(app.getAppPath(), "config.json"),
    path.join(__dirname, "..", "config.json"),
  ];

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }
  return path.join(process.cwd(), "config.json");
}

/**
 * 读取配置文件，首次运行自动创建
 */
function loadConfig() {
  const configPath = getConfigPath();

  try {
    if (fs.existsSync(configPath)) {
      const fileContent = fs.readFileSync(configPath, "utf-8");
      const userConfig = JSON.parse(fileContent);
      console.log(`[配置] 已加载: ${configPath}`);
      return { ...DEFAULT_CONFIG, ...userConfig };
    }
  } catch (err) {
    console.warn(`[配置] 读取失败: ${err.message}`);
  }

  console.log("[配置] 自动创建默认配置");
  try {
    fs.writeFileSync(configPath, JSON.stringify(DEFAULT_CONFIG, null, 2), "utf-8");
  } catch (err) {
    console.warn(`[配置] 创建失败: ${err.message}`);
  }
  return DEFAULT_CONFIG;
}

/**
 * 根据 backendUrl 推导 WebSocket 端点
 */
function deriveWsEndpoint(config) {
  if (config.wsEndpoint) return config.wsEndpoint;
  return config.backendUrl.replace(/\/$/, "").replace(/^http/, "ws") + "/ws";
}

// ==================== 本地 HTTP 服务器 ====================

const LOCAL_PORT = 18888;
let localServer = null;

/**
 * MIME 类型映射
 */
const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".map": "application/json",
  ".txt": "text/plain; charset=utf-8",
};

/**
 * 获取本地前端目录
 */
function getFrontendDir() {
  const possiblePaths = [
    path.join(__dirname, "..", "frontend", "dist"),
    path.join(process.resourcesPath || "", "frontend", "dist"),
    path.join(app.getAppPath(), "frontend", "dist"),
  ];

  for (const p of possiblePaths) {
    if (fs.existsSync(path.join(p, "index.html"))) {
      console.log(`[前端] 找到本地前端: ${p}`);
      return p;
    }
  }
  return null;
}

/**
 * 代理请求到远程服务器
 */
function proxyRequest(req, res, targetUrl) {
  const parsedTarget = new URL(targetUrl);
  const isHttps = parsedTarget.protocol === "https:";
  const httpModule = isHttps ? https : http;

  const options = {
    hostname: parsedTarget.hostname,
    port: parsedTarget.port || (isHttps ? 443 : 80),
    path: parsedTarget.pathname + parsedTarget.search,
    method: req.method,
    headers: {
      ...req.headers,
      host: parsedTarget.host, // 设置正确的 host
    },
  };

  // 删除可能导致问题的头
  delete options.headers["origin"];
  delete options.headers["referer"];

  const proxyReq = httpModule.request(options, (proxyRes) => {
    // 复制响应头，添加 CORS
    const headers = { ...proxyRes.headers };
    headers["access-control-allow-origin"] = "*";
    headers["access-control-allow-headers"] = "*";
    headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS";

    res.writeHead(proxyRes.statusCode || 200, headers);
    proxyRes.pipe(res);
  });

  proxyReq.on("error", (err) => {
    console.error(`[代理] 请求失败: ${targetUrl}`, err.message);
    res.writeHead(502, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ code: 500, msg: "无法连接到服务器: " + err.message }));
  });

  // 发送请求体
  req.pipe(proxyReq);
}

/**
 * 处理 OPTIONS 预检请求
 */
function handleOptions(res) {
  res.writeHead(204, {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
    "access-control-max-age": "86400",
  });
  res.end();
}

/**
 * 启动本地 HTTP 服务器
 */
function startLocalServer(config) {
  const backendUrl = config.backendUrl.replace(/\/$/, "");
  const externalApiUrl = config.externalApiUrl.replace(/\/$/, "");
  const frontendDir = getFrontendDir();

  if (!frontendDir) {
    console.log("[服务器] 本地前端不存在，跳过启动");
    return false;
  }

  localServer = http.createServer((req, res) => {
    // 处理 CORS 预检
    if (req.method === "OPTIONS") {
      handleOptions(res);
      return;
    }

    const parsedUrl = new URL(req.url, `http://localhost:${LOCAL_PORT}`);
    const pathname = parsedUrl.pathname;

    // 1. 代理 /api 请求到后端
    if (pathname.startsWith("/api")) {
      const targetUrl = backendUrl + pathname + (parsedUrl.search || "");
      console.log(`[代理] ${pathname} → ${targetUrl}`);
      proxyRequest(req, res, targetUrl);
      return;
    }

    // 2. 代理 /ext-order 请求到外部接口（去掉前缀）
    if (pathname.startsWith("/ext-order")) {
      const newPath = pathname.replace(/^\/ext-order/, "") || "/";
      const targetUrl = externalApiUrl + newPath + (parsedUrl.search || "");
      console.log(`[代理] ${pathname} → ${targetUrl}`);
      proxyRequest(req, res, targetUrl);
      return;
    }

    // 3. 提供静态文件
    let filePath = path.join(frontendDir, decodeURIComponent(pathname));
    if (pathname === "/" || pathname === "") {
      filePath = path.join(frontendDir, "index.html");
    }

    // 安全检查：防止路径遍历
    if (!filePath.startsWith(frontendDir)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        // 文件不存在，返回 index.html（支持前端路由）
        const indexPath = path.join(frontendDir, "index.html");
        fs.readFile(indexPath, (err2, indexData) => {
          if (err2) {
            res.writeHead(404);
            res.end("Not Found");
            return;
          }
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(indexData);
        });
        return;
      }

      const ext = path.extname(filePath).toLowerCase();
      const contentType = MIME_TYPES[ext] || "application/octet-stream";
      res.writeHead(200, { "Content-Type": contentType });
      res.end(data);
    });
  });

  localServer.listen(LOCAL_PORT, "127.0.0.1", () => {
    console.log(`[服务器] 本地服务器已启动: http://127.0.0.1:${LOCAL_PORT}`);
  });

  localServer.on("error", (err) => {
    console.error(`[服务器] 启动失败: ${err.message}`);
  });

  return true;
}

// ==================== 窗口管理 ====================

let mainWindow = null;

function createWindow(config) {
  const windowConfig = { ...DEFAULT_CONFIG.window, ...config.window };

  mainWindow = new BrowserWindow({
    width: windowConfig.width,
    height: windowConfig.height,
    minWidth: windowConfig.minWidth,
    minHeight: windowConfig.minHeight,
    title: "协作事业部生产管理系统",
    icon: path.join(__dirname, "..", "resources", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
    show: false,
  });

  // 注入 WebSocket 配置
  const wsEndpoint = deriveWsEndpoint(config);
  process.env.ELECTRON_WS_ENDPOINT = wsEndpoint;
  process.env.ELECTRON_BACKEND_URL = config.backendUrl;
  console.log(`[WebSocket] 端点: ${wsEndpoint}`);

  // 加载前端
  loadFrontend(config);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.maximize();
  });

  // 外部链接在浏览器中打开
  mainWindow.webContents.setWindowOpenHandler(({ url: targetUrl }) => {
    if (targetUrl.startsWith("http://") || targetUrl.startsWith("https://")) {
      // 允许本地服务器地址
      if (targetUrl.includes("127.0.0.1") || targetUrl.includes("localhost")) {
        return { action: "allow" };
      }
      shell.openExternal(targetUrl);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  if (process.argv.includes("--dev")) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

/**
 * 加载前端：优先本地服务器，备用远程 URL
 */
function loadFrontend(config) {
  // 如果本地服务器已启动，加载本地
  if (localServer && config.preferLocalFrontend) {
    console.log("[前端] 加载本地前端（通过本地服务器）");
    mainWindow.loadURL(`http://127.0.0.1:${LOCAL_PORT}`);
    return;
  }

  // 备用：加载远程前端
  if (config.frontendUrl) {
    console.log(`[前端] 加载远程前端: ${config.frontendUrl}`);
    mainWindow.loadURL(config.frontendUrl);
  } else {
    dialog.showErrorBox(
      "配置错误",
      "未找到本地前端文件，且未配置远程前端地址。\n请检查 config.json 中的 frontendUrl 配置。"
    );
  }
}

// ==================== 菜单 ====================

function createMenu() {
  const template = [
    {
      label: "文件",
      submenu: [
        {
          label: "重新加载",
          accelerator: "CmdOrCtrl+R",
          click: () => { if (mainWindow) mainWindow.reload(); },
        },
        {
          label: "强制刷新",
          accelerator: "CmdOrCtrl+Shift+R",
          click: () => { if (mainWindow) mainWindow.webContents.reloadIgnoringCache(); },
        },
        { type: "separator" },
        {
          label: "退出",
          accelerator: "CmdOrCtrl+Q",
          click: () => app.quit(),
        },
      ],
    },
    {
      label: "编辑",
      submenu: [
        { label: "撤销", accelerator: "CmdOrCtrl+Z", role: "undo" },
        { label: "重做", accelerator: "CmdOrCtrl+Shift+Z", role: "redo" },
        { type: "separator" },
        { label: "剪切", accelerator: "CmdOrCtrl+X", role: "cut" },
        { label: "复制", accelerator: "CmdOrCtrl+C", role: "copy" },
        { label: "粘贴", accelerator: "CmdOrCtrl+V", role: "paste" },
        { label: "全选", accelerator: "CmdOrCtrl+A", role: "selectAll" },
      ],
    },
    {
      label: "视图",
      submenu: [
        { label: "放大", accelerator: "CmdOrCtrl+=", role: "zoomIn" },
        { label: "缩小", accelerator: "CmdOrCtrl+-", role: "zoomOut" },
        { label: "重置缩放", accelerator: "CmdOrCtrl+0", role: "resetZoom" },
        { type: "separator" },
        { label: "全屏", accelerator: "F11", role: "togglefullscreen" },
        { type: "separator" },
        {
          label: "开发者工具",
          accelerator: "F12",
          click: () => { if (mainWindow) mainWindow.webContents.toggleDevTools(); },
        },
      ],
    },
    {
      label: "帮助",
      submenu: [
        {
          label: "关于",
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: "info",
              title: "关于",
              message: "协作事业部生产管理系统",
              detail: `版本: ${app.getVersion()}\nElectron: ${process.versions.electron}\n描述: 桌面客户端（前端套壳）`,
              buttons: ["确定"],
            });
          },
        },
        {
          label: "打开配置文件位置",
          click: () => {
            const configPath = getConfigPath();
            shell.showItemInFolder(configPath);
          },
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ==================== 应用生命周期 ====================

app.whenReady().then(() => {
  const config = loadConfig();

  // 启动本地服务器（提供前端文件 + 代理 API）
  startLocalServer(config);

  // 创建窗口
  createWindow(config);
  createMenu();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(config);
    }
  });
});

app.on("window-all-closed", () => {
  // 关闭本地服务器
  if (localServer) {
    localServer.close();
    localServer = null;
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (localServer) {
    localServer.close();
    localServer = null;
  }
});
