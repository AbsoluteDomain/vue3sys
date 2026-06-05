"""
开发环境配置

此文件仅包含开发环境的覆盖配置。
"""

from .base import *

from config.env import env_bool, env_int, env_str

# 开发环境调试开关
DEBUG = True
ALLOWED_HOSTS = ['*']

# 开发环境数据库设置（使用环境变量）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env_str('DB_NAME', 'youlai_admin_django'), # ✅ 读取环境变量 DB_NAME，如果没有则默认 'youlai_admin'
        'USER': env_str('DB_USER', 'root'),
        'PASSWORD': env_str('DB_PASSWORD', 'root'),
        'HOST': env_str('DB_HOST', '127.0.0.1'),
        'PORT': env_int('DB_PORT', 3306),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

# 开发环境 Redis 设置
#REDIS_PASSWORD = env_str('REDIS_PASSWORD', '')
#_redis_auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
#CACHES = {
#    'default': {
#        'BACKEND': 'django_redis.cache.RedisCache',
#        'LOCATION': (
#            'redis://localhost:6379/0',
#        ),
#        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
#    }
#}


# 开发环境 Redis 设置
# 1. 直接设置密码为 123456 (或者保留环境变量读取，但默认值改为 123456)
REDIS_PASSWORD = env_str('REDIS_PASSWORD', '123456') 

# 2. 构建认证字符串 (如果有密码则是 :123456@, 否则是空字符串)
_redis_auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # 3. 【关键修改】动态构建 LOCATION，将密码嵌入 URL
        # 结果将是: redis://:123456@localhost:6379/0
        'LOCATION': f'redis://{_redis_auth}localhost:6379/0',
        
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # 4. 【关键修改】显式传递密码给 OPTIONS，确保兼容性
            'PASSWORD': REDIS_PASSWORD,
        },
    }
}

# 邮件配置
EMAIL_BACKEND = env_str('EMAIL_BACKEND', "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env_str('EMAIL_HOST')
EMAIL_PORT = env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = env_str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env_str('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env_str('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or '')

# 会话类型覆盖（开发环境）
SESSION_TYPE = env_str('SESSION_TYPE', 'jwt')
default_auth_classes: tuple[str, ...]
if SESSION_TYPE == "redis-token":
    default_auth_classes = (
        "apps.auth.utils.redis_token_authentication.RedisTokenAuthentication",
    )
else:
    default_auth_classes = (
        "apps.auth.utils.jwt_authentication.VersionedJWTAuthentication",
    )
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = default_auth_classes  # pyright: ignore[reportArgumentType]

# ================================
# 开发环境特定配置
# ================================

# 禁用验证码（开发环境）
CAPTCHA_ENABLED = False

# ================================
# XXL-Job 定时任务配置 (开发环境)
# ================================

# 定时任务开关
XXL_JOB_ENABLED = env_bool('XXL_JOB_ENABLED', False)
# XXL-Job 管理后台地址
XXL_JOB_ADMIN_ADDRESSES = env_str('XXL_JOB_ADMIN_ADDRESSES', 'http://127.0.0.1:8686/xxl-job-admin')
# XXL-Job 访问令牌
XXL_JOB_ACCESS_TOKEN = env_str('XXL_JOB_ACCESS_TOKEN', 'default_token')
# 执行器应用名称
XXL_JOB_EXECUTOR_APP_NAME = env_str('XXL_JOB_EXECUTOR_APP_NAME', 'xxl-job-executor-youlai-django')
# 执行器端口
XXL_JOB_EXECUTOR_PORT = env_int('XXL_JOB_EXECUTOR_PORT', 9999)
# 日志路径
XXL_JOB_LOG_PATH = env_str('XXL_JOB_LOG_PATH', '/data/applogs/xxl-job/jobhandler')
# 日志保留天数
XXL_JOB_LOG_RETENTION_DAYS = env_int('XXL_JOB_LOG_RETENTION_DAYS', 30)
