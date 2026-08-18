/**
 * Electron 预加载脚本
 *
 * 通过 contextBridge 向前端注入安全的全局变量
 * 前端可通过 window.electronAPI 访问这些配置
 *
 * 关键作用：
 * 1. 标识当前运行在 Electron 中（前端可据此判断环境）
 * 2. 注入 WebSocket 端点（前端优先使用此值，而非打包时写死的值）
 * 3. 注入后端 API 地址
 */

const { contextBridge } = require("electron");

// 从环境变量读取主进程注入的配置
const wsEndpoint = process.env.ELECTRON_WS_ENDPOINT || "";
const backendUrl = process.env.ELECTRON_BACKEND_URL || "";

contextBridge.exposeInMainWorld("electronAPI", {
  // 标识当前运行在 Electron 中
  isElectron: true,

  // 服务器配置（前端可用于动态设置 WebSocket 等）
  wsEndpoint: wsEndpoint,
  backendUrl: backendUrl,

  // 获取应用版本
  getVersion: () => process.env.npm_package_version || "1.0.0",

  // 平台信息
  platform: process.platform,
});

// 注入 WebSocket 配置到 localStorage，供前端读取
// 前端 useStomp.ts 优先读取 window.electronAPI.wsEndpoint，其次读 VITE_APP_WS_ENDPOINT
if (wsEndpoint) {
  try {
    localStorage.setItem("ELECTRON_WS_ENDPOINT", wsEndpoint);
  } catch (e) {
    // localStorage 可能不可用，忽略
  }
}
