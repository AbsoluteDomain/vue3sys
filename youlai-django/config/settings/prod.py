"""
生产环境配置

此文件仅包含生产环境的覆盖配置。
"""

from .base import *

from config.env import env_bool, env_int, env_str, require_env


DEBUG = False
if DEBUG:
    raise RuntimeError("DEBUG must be False in production")

ALLOWED_HOSTS = require_env('DJANGO_ALLOWED_HOSTS').split(',')

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': require_env('DB_NAME'),
        'USER': require_env('DB_USER'),
        'PASSWORD': require_env('DB_PASSWORD'),
        'HOST': require_env('DB_HOST'),
        'PORT': env_int('DB_PORT', 3306),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': (
            f"redis://:{env_str('REDIS_PASSWORD', '')}@"
            f"{require_env('REDIS_HOST')}:{env_int('REDIS_PORT', 6379)}/"
            f"{env_int('REDIS_DB', 0)}"
        ),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

EMAIL_BACKEND = env_str('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = require_env('EMAIL_HOST')
EMAIL_PORT = env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = require_env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = require_env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env_str('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

CAPTCHA_ENABLED = True

# 会话类型覆盖（生产环境）
SESSION_TYPE = env_str('SESSION_TYPE', 'jwt')
if SESSION_TYPE == "redis-token":
    DEFAULT_AUTH_CLASSES = (
        "apps.auth.utils.redis_token_authentication.RedisTokenAuthentication",
    )
else:
    DEFAULT_AUTH_CLASSES = (
        "apps.auth.utils.jwt_authentication.VersionedJWTAuthentication",
    )
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = DEFAULT_AUTH_CLASSES

# 关键依赖校验（启动即失败）
require_env('JWT_SECRET_KEY')
if OSS_TYPE == 'minio':
    require_env('MINIO_ACCESS_KEY')
    require_env('MINIO_SECRET_KEY')

LOGGING['handlers']['file'] = {
    'class': 'logging.FileHandler',
    'filename': BASE_DIR / 'logs' / 'django.log',
    'filters': ['request_context'],
    'formatter': 'request',
}
LOGGING['root']['handlers'].append('file')
