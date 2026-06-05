"""系统管理-日志模型。

"""

from django.db import models


class Log(models.Model):
    """
    表名：sys_log
    表说明：操作日志表，用于记录系统中各类操作的详细日志信息。
    """

    module = models.CharField(max_length=50, verbose_name="日志模块", help_text="日志模块")
    request_method = models.CharField(max_length=64, verbose_name="请求方式", help_text="请求方式")
    request_params = models.TextField(blank=True, null=True, verbose_name="请求参数", help_text="请求参数（批量请求可能超过 text）")
    response_content = models.TextField(blank=True, null=True, verbose_name="返回参数", help_text="返回参数")
    content = models.CharField(max_length=255, verbose_name="日志内容", help_text="日志内容")
    request_uri = models.CharField(max_length=255, blank=True, null=True, verbose_name="请求路径", help_text="请求路径")
    method = models.CharField(max_length=255, blank=True, null=True, verbose_name="方法名", help_text="方法名")
    ip = models.CharField(max_length=45, blank=True, null=True, verbose_name="IP地址", help_text="IP地址")
    province = models.CharField(max_length=100, blank=True, null=True, verbose_name="省份", help_text="省份")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="城市", help_text="城市")
    execution_time = models.BigIntegerField(blank=True, null=True, verbose_name="执行时间", help_text="执行时间（毫秒）")
    browser = models.CharField(max_length=100, blank=True, null=True, verbose_name="浏览器", help_text="浏览器")
    browser_version = models.CharField(max_length=100, blank=True, null=True, verbose_name="浏览器版本", help_text="浏览器版本")
    os = models.CharField(max_length=100, blank=True, null=True, verbose_name="终端系统", help_text="终端系统")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")

    class Meta:
        db_table = "sys_log"
        verbose_name = "日志表"
        verbose_name_plural = "日志表"

    def __str__(self):
        return f"{self.module} - {self.request_method}"
