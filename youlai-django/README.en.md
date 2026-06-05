# YouLai Django Admin System

## Project Introduction

YouLai Django is a permission management system built with Python, Django,
Django REST framework, JWT, and Redis. It is the Python+Django backend version
of vue3-element-admin. This project integrates rich functional modules and best
practices to help developers quickly build professional management systems.

## Key Features

- **Modular Design**: Adopts a modular architecture with decoupled functional
  modules for easy extension and maintenance
- **Permission Management**: Comprehensive RBAC permission control system
  supporting flexible role permission assignment
- **REST API**: Standard RESTful API interfaces built on Django REST framework
- **JWT Authentication**: Secure user authentication implemented using JWT (JSON
  Web Token)
- **Multiple Login Methods**: Support for account password, verification code,
  email verification code, and other login methods
- **File Storage**: Integration with MinIO distributed object storage for
  efficient file resource management
- **Demo Mode**: Built-in demo mode to protect core data security
- **Notifications**: Support for multiple notification methods including email
  and SMS

## Technology Stack

- **Backend Framework**: Django 5.1.x
- **API Framework**: Django REST Framework
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Database**: MySQL (project default), expandable to support other databases
- **Cache System**: Redis
- **Object Storage**: MinIO
- **Notification Services**: Support for Aliyun SMS, SMTP email services

## Quick Start

### Requirements

- Python 3.10+
- MySQL 5.7+ (8.x recommended)
- Redis (required)
- MinIO (optional, required only if you use file upload/delete APIs)

### Installation Steps

1. **Clone the project**

```bash
git clone https://github.com/youlaitech/youlai-django.git
cd youlai-django
```

> If you are in a mono-repo (e.g. `youlai-admin`), enter
> `youlai-admin/youlai-django` before running commands.

2. **Create and activate virtual environment**

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate
```

> On Windows PowerShell, if script execution is disabled:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configuration**

This project does **NOT** use `conf/env.py`. Update settings in:

- `config/settings/dev.py` (Development)
- `config/settings/prod.py` (Production)

Before local startup, at least update:

- Database: `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`
- Redis: `REDIS_HOST/REDIS_PORT/REDIS_DB/REDIS_PASSWORD`

Optional (required for file APIs):

- MinIO: `MINIO_HOST_PORT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY/MINIO_BUCKET_NAME`

5. **Database initialization**

Option A (fastest): import SQL script

```bash
mysql -u root -p < sql/mysql/youlai_admin_django.sql
python manage.py migrate --fake-initial
```

Option B (recommended for long-term maintenance): migrate from scratch

```bash
python manage.py migrate
```

6. **Start the service**

```bash
python manage.py runserver
```

Access the admin interface via browser at http://127.0.0.1:8000/admin/

### API Documentation

After starting the service, API documentation can be accessed at:

- Swagger UI: http://127.0.0.1:8000/api/docs/swagger/
- Redoc: http://127.0.0.1:8000/api/docs/redoc/
- OpenAPI Schema (JSON): http://127.0.0.1:8000/api/schema/

## Deployment Guide

### Deploy with Gunicorn and Nginx

1. **Install Gunicorn**

```bash
pip install gunicorn
```

2. **Start Gunicorn**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

3. **Nginx configuration example**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Docker Deployment

This repository includes:

- `Dockerfile`
- `docker-compose.yml`

The container startup explicitly uses `--settings=config.settings.dev` so the
app does **NOT** rely on environment variables for configuration.

1. **Start (first time with build)**

```bash
docker compose up -d --build
```

2. **Check status / logs**

```bash
docker compose ps
docker compose logs -f web
```

3. **API docs**

- Swagger UI: http://127.0.0.1:8000/api/docs/swagger/
- Redoc: http://127.0.0.1:8000/api/docs/redoc/
- OpenAPI Schema (JSON): http://127.0.0.1:8000/api/schema/

4. **Stop**

```bash
docker compose down
```

## Contribution Guidelines

1. Fork this repository
2. Create a new feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the
[LICENSE](LICENSE) file for details

#### Gitee Feature

1.  You can use Readme_XXX.md to support different languages, such as
    Readme_en.md, Readme_zh.md
2.  Gitee blog [blog.gitee.com](https://blog.gitee.com)
3.  Explore open source project
    [https://gitee.com/explore](https://gitee.com/explore)
4.  The most valuable open source project [GVP](https://gitee.com/gvp)
5.  The manual of Gitee [https://gitee.com/help](https://gitee.com/help)
6.  The most popular members
    [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
