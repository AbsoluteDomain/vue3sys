"""平台-文件视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.openapi import resp
from core.response import error, success

from .selectors import extract_file_path
from .services import MinioFileService


@extend_schema(tags=["10.文件接口"])
class FileViewSet(ViewSet):
    """文件上传视图"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="文件上传",
        request=inline_serializer(
            name="FileUploadRequest",
            fields={"file": serializers.FileField()},
        ),
        responses=resp(
            "FileUploadResult",
            inline_serializer(
                name="FileInfo",
                fields={
                    "name": serializers.CharField(),
                    "url": serializers.CharField(),
                },
            ),
        ),
    )
    def create(self, request):
        """
        上传文件接口
        """
        # 获取上传的文件
        upload_file = request.FILES.get('file')
        if not upload_file:
            return error("请求必填参数为空", code="A0410", status=status.HTTP_400_BAD_REQUEST)

        try:
            # 交给对象存储服务处理
            svc = MinioFileService()
            file_info = svc.upload_file(upload_file)
            return success({"name": file_info.name, "url": file_info.url}, status=status.HTTP_200_OK)
        except Exception as e:
            return error(f"上传文件异常: {str(e)}", code="A0700", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="文件删除",
        parameters=[
            OpenApiParameter(
                name="filePath",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
                description="文件路径或 URL（服务端会解析为对象存储路径）",
            ),
        ],
        responses=resp("FileDeleteResult", serializers.DictField(required=False)),
    )
    def destroy(self, request):
        """
        删除文件接口（逻辑删除）
        """
        # 获取文件路径参数
        file_path_or_url = request.query_params.get('filePath')
        if not file_path_or_url:
            return error("请求必填参数为空", code="A0410", status=status.HTTP_400_BAD_REQUEST)
        
        # 支持 URL/路径两种输入，统一解析成对象存储路径
        file_path = extract_file_path(file_path_or_url)
        if not file_path:
            return error("用户请求参数错误", code="A0400", status=status.HTTP_400_BAD_REQUEST)

        try:
            # 删除对象存储中的文件
            svc = MinioFileService()
            svc.delete_file(file_path)
            return success(None, status=status.HTTP_200_OK)
        except Exception as e:
            return error(f"删除文件异常: {str(e)}", code="A0710", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
