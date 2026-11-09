"""平台-文件管理模型。

"""
from django.db import models


class FileItem(models.Model):
    """
    表名：file_manager_item
    表说明：文件管理条目表，记录共享文件空间中的文件与文件夹元数据。
    """

    parent_id = models.BigIntegerField(default=0, verbose_name="父目录ID", help_text="父目录ID（0 表示根目录）")
    name = models.CharField(max_length=255, verbose_name="名称", help_text="文件或文件夹名称")
    is_dir = models.SmallIntegerField(default=0, verbose_name="是否文件夹", help_text="是否文件夹（1-是, 0-否）")
    storage_path = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="存储路径", help_text="文件在存储服务中的相对路径"
    )
    file_url = models.CharField(
        max_length=500, blank=True, null=True, verbose_name="访问地址", help_text="文件访问地址"
    )
    file_size = models.BigIntegerField(default=0, verbose_name="文件大小", help_text="文件大小（字节）")
    mime_type = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="MIME类型", help_text="文件 MIME 类型"
    )
    file_type = models.CharField(
        max_length=32, blank=True, null=True, verbose_name="文件类型",
        help_text="文件类型（小写扩展名，文件夹为 folder）",
    )
    uploader_id = models.BigIntegerField(null=True, blank=True, verbose_name="上传人ID", help_text="上传人ID")
    uploader_name = models.CharField(
        max_length=64, blank=True, null=True, verbose_name="上传人", help_text="上传人名称"
    )
    download_count = models.IntegerField(default=0, verbose_name="下载次数", help_text="下载次数")
    is_del = models.SmallIntegerField(default=0, verbose_name="删除标记", help_text="删除标记（0-正常, 1-回收站）")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="删除时间", help_text="删除时间")
    created_at = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")

    class Meta:
        db_table = "file_manager_item"
        verbose_name = "文件管理条目"
        verbose_name_plural = "文件管理条目"
