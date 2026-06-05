<div align="center">
   <img alt="logo" width="100" height="100" src="https://foruda.gitee.com/images/1733417239320800627/3c5290fe_716974.png">
   <h2>youlai-django</h2>
   <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-blue.svg"/>
  <img alt="Django" src="https://img.shields.io/badge/Django-6.0-green.svg"/>
   <a href="https://gitee.com/youlaiorg/youlai-django" target="_blank">
     <img alt="Gitee star" src="https://gitee.com/youlaiorg/youlai-django/badge/star.svg"/>
   </a>     
   <a href="https://github.com/youlaitech/youlai-django" target="_blank">
     <img alt="Github star" src="https://img.shields.io/github/stars/youlaitech/youlai-django.svg?style=social&label=Stars"/>
   </a>
</div>

<p align="center">
  <a target="_blank" href="https://vue.youlai.tech/">🖥️ 在线预览</a>
  <span>&nbsp;|&nbsp;</span>
  <a target="_blank" href="https://www.youlai.tech/youlai-django">📑 阅读文档</a>
  <span>&nbsp;|&nbsp;</span>
  <a target="_blank" href="https://www.youlai.tech">🌐 官网</a>
</p>

## 📢 项目简介

**[youlai-django](https://gitee.com/youlaiorg/youlai-django)** 是 `vue3-element-admin` 配套的 Python 后端实现，基于 Django 6, DRF, SimpleJWT, Redis, MySQL 构建，是 **youlai 全家桶** 的重要组成部分。

- **🚀 现代技术栈**: 基于 Python 3.12+ 和 Django 6，提供稳定高效的后端服务。
- **🔐 安全认证**: 使用 djangorestframework-simplejwt 进行 JWT 认证，保障接口安全。
- **🔑 权限管理**: 内置基于 RBAC 的权限模型，精确控制接口和按钮权限。
- **🛠️ 功能模块**: 包含用户、角色、菜单、部门、字典等后台管理系统的核心功能。

## 🌈 项目源码

| 项目类型 | Gitee | Github | GitCode |
| --- | --- | --- | --- |
| ✅ Python 后端 | [youlai-django](https://gitee.com/youlaiorg/youlai-django) | [youlai-django](https://github.com/youlaitech/youlai-django) | [youlai-django](https://gitcode.com/youlai/youlai-django) |
| vue3 前端 | [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) | [vue3-element-admin](https://github.com/youlaitech/vue3-element-admin) | [vue3-element-admin](https://gitcode.com/youlai/vue3-element-admin) |
| uni-app 移动端 | [vue-uniapp-template](https://gitee.com/youlaiorg/vue-uniapp-template) | [vue-uniapp-template](https://github.com/youlaitech/vue-uniapp-template) | [vue-uniapp-template](https://gitcode.com/youlai/vue-uniapp-template) |

## 项目目录

<details>
<summary> 目录结构 </summary>

```text
youlai-django/
├─ config/                    # 项目配置
│  ├─ settings/               # 环境配置(base/dev/prod)
│  │  ├─ base.py              # 通用配置(不含环境差异)
│  │  ├─ dev.py               # 开发配置
│  │  └─ prod.py              # 生产配置
│  └─ urls.py                 # 全局路由
├─ core/                      # 公共基础能力
│  ├─ viewsets/               # 基础视图集
│  ├─ serializers/            # 基础序列化器
│  ├─ permissions/            # 权限控制
│  └─ ...                     # 其他(分页/过滤器/异常等)
├─ system/                    # 系统核心模块
│  ├─ users/                  # 用户管理
│  ├─ roles/                  # 角色管理
│  ├─ menus/                  # 菜单管理
│  └─ ...                     # 其他(部门/字典/日志等)
├─ auth/                     # 认证模块(登录/Token)
├─ infra/                    # 基础设施
│  ├─ codegen/               # 代码生成
│  └─ file/                  # 文件上传
├─ sql/                      # 数据库脚本
│  └─ mysql/
│     └─ youlai_admin_django.sql
├─ manage.py                  # Django 管理入口
└─ .env                       # 环境变量
```

</details>

## 🚀 快速启动

### 1. 环境准备

| 技术 | 版本/说明 | 安装文档 |
| --- | --- | --- |
| **Python** | `3.12` 或更高版本（推荐 `3.14.2`） | [官方下载](https://www.python.org/downloads/) |
| **MySQL** | `5.7` 或 `8.x` | [Windows](https://youlai.blog.csdn.net/article/details/133272887) / [Linux](https://youlai.blog.csdn.net/article/details/130398179) |
| **Redis** | `7.x` | [Windows](https://youlai.blog.csdn.net/article/details/133410293) / [Linux](https://youlai.blog.csdn.net/article/details/130439335) |

> 💡 **提示**：项目启动依赖 MySQL 和 Redis。为方便快速体验，若本地未配置，项目会默认连接 [youlai](https://www.youlai.tech) 的线上公共环境。

### 2. 开发工具

**PyCharm** (推荐)：

- JetBrains 官方出品的专业 Python IDE，能自动管理虚拟环境，开箱即用。

**VS Code**：

- **Python**: 官方 Python 扩展，提供语法高亮、调试、Linting 等核心功能。
- **Pylance**: 微软官方出品的语言服务器，提供强大的智能提示和代码分析。

### 3. 启动项目

```bash
# 1. 克隆项目
git clone https://gitee.com/youlaiorg/youlai-django.git
cd youlai-django

# 2. 创建并激活虚拟环境 (推荐)
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
#    请使用数据库客户端执行 sql/mysql/youlai_admin_django.sql

# 5. 修改配置
#    修改 .env 并填写 MySQL/Redis 等配置项，默认使用 youlai 的公共环境

# 6. 启动服务
python manage.py runserver [::]:8000
```

### 4. 后续迭代（频繁修改 models.py 必看）

当你修改了 `models.py`（新增/删除字段、修改字段类型或约束、索引、外键关系等）后：

```bash
# 1) 生成迁移文件（迁移文件需要提交到 Git）
python manage.py makemigrations

# 2) 应用迁移到数据库
python manage.py migrate
```

启动成功后，访问 [http://localhost:8000/api/docs/swagger/](http://localhost:8000/api/docs/swagger/) 验证项目是否成功。

## 🤝 前端整合

`youlai-django` 是 [vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin) 配套的 Python 后端实现。

- 前端源码：[vue3-element-admin](https://gitee.com/youlaiorg/vue3-element-admin)
- 在线预览：https://vue.youlai.tech/

```bash
# 1. 获取前端项目
git clone https://gitee.com/youlaiorg/vue3-element-admin.git
cd vue3-element-admin

# 2. 安装依赖
pnpm install

# 3. 配置后端地址 (编辑 .env.development)
VITE_APP_API_URL=http://localhost:8000

# 4. 启动前端
pnpm run dev
```

- **访问地址**: [http://localhost:3000](http://localhost:3000)
- **登录账号**: `admin` / `123456`

## 🐳 项目部署

### 1. Gunicorn + Nginx

```bash
# 安装 gunicorn
pip install gunicorn

# 启动应用
export DJANGO_SETTINGS_MODULE=config.settings.prod
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 2. Docker 部署

```bash
# 构建并启动容器
docker compose up -d --build
```

## 💖 技术交流

① 关注「有来技术」公众号，点击菜单 **交流群** 获取加群二维码（此举防止广告进群，感谢理解和支持）。

② 直接添加微信 **`haoxianrui`** 备注「前端/后端/全栈」。

![有来技术公众号](https://foruda.gitee.com/images/1737108820762592766/3390ed0d_716974.png)

**博客**：[CSDN](https://youlai.blog.csdn.net/) | [稀土掘金](https://juejin.cn/user/4187394044331261) | [博客园](https://www.cnblogs.com/haoxianrui) | [51CTO](https://blog.51cto.com/youlai) | [阿里云](https://developer.aliyun.com/profile/r6wxjk6qzasuy) | [腾讯云社区](https://cloud.tencent.com/developer/user/10500752) | [知乎](https://www.zhihu.com/people/haoxr)

**官网**：https://www.youlai.tech/

**代码仓库**：[Gitee](https://gitee.com/youlaiorg) | [AtomGit](https://atomgit.com/youlai) | [GitHub](https://github.com/youlaitech)
