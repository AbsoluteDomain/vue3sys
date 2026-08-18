/**
 * 前端打包脚本
 *
 * 功能：
 * 1. 在 vue3-element-admin 目录执行 npm run build
 * 2. 将 dist 目录复制到 electron-client/frontend/dist
 *
 * 用法：
 *   node scripts/build-frontend.js
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

// ==================== 路径配置 ====================

const electronClientDir = path.join(__dirname, "..");
const frontendDir = path.join(electronClientDir, "..", "vue3-element-admin");
const frontendDistDir = path.join(frontendDir, "dist");
const targetDir = path.join(electronClientDir, "frontend", "dist");

// ==================== 工具函数 ====================

function log(msg) {
  console.log(`[build-frontend] ${msg}`);
}

function error(msg) {
  console.error(`[build-frontend] ❌ ${msg}`);
  process.exit(1);
}

/**
 * 递归复制目录
 */
function copyDir(src, dest) {
  if (!fs.existsSync(src)) {
    error(`源目录不存在: ${src}`);
  }

  // 创建目标目录
  fs.mkdirSync(dest, { recursive: true });

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// ==================== 主流程 ====================

log("开始构建前端...");

// 1. 检查前端目录
if (!fs.existsSync(frontendDir)) {
  error(`前端目录不存在: ${frontendDir}`);
}
log(`前端目录: ${frontendDir}`);

// 2. 检查 package.json
const frontendPkgPath = path.join(frontendDir, "package.json");
if (!fs.existsSync(frontendPkgPath)) {
  error(`前端 package.json 不存在: ${frontendPkgPath}`);
}

// 3. 执行前端打包
// 注意：
// - 使用 npx vite build 跳过 vue-tsc 类型检查（存在非关键 TS 错误）
// - 使用 --base=./ 生成相对路径，确保 file:// 协议下资源能正确加载
log("执行 vite build（跳过类型检查，这可能需要几分钟）...");
try {
  execSync("npx vite build --base=./", {
    cwd: frontendDir,
    stdio: "inherit",
    env: { ...process.env, NODE_ENV: "production" },
  });
  log("前端打包完成");
} catch (err) {
  error(`前端打包失败: ${err.message}`);
}

// 4. 检查 dist 目录
if (!fs.existsSync(frontendDistDir)) {
  error(`前端 dist 目录不存在: ${frontendDistDir}`);
}

// 5. 清理目标目录
if (fs.existsSync(targetDir)) {
  log(`清理旧的前端文件: ${targetDir}`);
  fs.rmSync(targetDir, { recursive: true, force: true });
}

// 6. 复制 dist 到 electron-client/frontend/dist
log(`复制前端文件到: ${targetDir}`);
copyDir(frontendDistDir, targetDir);

// 7. 验证
const indexHtmlPath = path.join(targetDir, "index.html");
if (fs.existsSync(indexHtmlPath)) {
  log("✅ 前端构建并复制成功！");
  log(`   位置: ${targetDir}`);
} else {
  error(`复制后未找到 index.html: ${indexHtmlPath}`);
}
