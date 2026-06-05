from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta,timezone

app = FastAPI()

# 模拟数据库用户
FAKE_USER_DB = {
    "admin": {"password": "123456", "roles": ["admin"], "nickname": "管理员"}
}
SECRET_KEY = "your-secret-key-change-this-in-production" 

# 1. 定义前端期望的请求体 (已移除验证码字段)
class LoginReq(BaseModel):
    username: str
    password: str
    rememberMe: Optional[bool] = False # 加上这个字段以防前端发送

# 2. 定义前端期望的返回体
# 2. 【关键修复】定义返回体
class ApiResponse(BaseModel):
    code: str = "00000"  # 👈 改为 str！这样 "00000" 就不会变成 0 了
    msg: str = "操作成功"
    data: dict            # 👈 建议改为 Any 或 dict，兼容性强

# ✅ 核心修复：路径从 "/auth/login" 改为 "/api/v1/auth/login"
@app.get("/api/v1/users/me", response_model=ApiResponse)
async def get_current_user():
    return ApiResponse(
        code="00000",
        msg="操作成功",
        data={
            "id": 1,
            "username": "admin",
            "nickname": "超级管理员",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin",
            "roles": ["admin"],       # 直接在 data 下
            "permissions": ["*:*:*"]  # 直接在 data 下
        }
    )
    
    
@app.post("/api/v1/auth/login")
async def login(login_req: LoginReq):
    print(f"🚀 收到登录请求: {login_req.username}")
    
    user = FAKE_USER_DB.get(login_req.username)
    
    if not user or user["password"] != login_req.password:
        # 构造错误响应
        error_response = {
            "code": "A0401",
            "msg": "用户名或密码错误",
            "data": {}
        }
        print("❌ 返回错误响应:", error_response) # 👈 新增这行
        return error_response

    # 生成 Token
    expire = datetime.now(timezone.utc) + timedelta(minutes=120)
    token_data = {
        "sub": login_req.username, 
        "roles": user["roles"],
        "exp": expire
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")

    # 构造成功响应
    success_response = {
        "code": "00000",  # ✅ 确保这里是字符串 "00000"
        "msg": "登录成功",
        "data": {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 7200,
            "user": {
                "id": 1,
                "username": login_req.username,
                "nickname": user["nickname"],
                "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
            }
        }
    }
    
    print("✅ 返回成功响应:", success_response) # 👈 新增这行
    return success_response
    
    
    
# 3. 获取用户信息接口
# ✅ 同样建议加上 /api/v1 前缀，保持风格一致，防止后续 404
@app.get("/api/v1/sys/user/profile", response_model=ApiResponse)
async def get_profile():
    # 这里省略了 Token 验证逻辑
    print("📄 获取用户资料请求")
    return ApiResponse(
        code="00000",
        msg="获取成功",
        data={
            "user": {
                "id": 1,
                "username": "admin",
                "nickname": "管理员",
                "roles": ["admin"],
                "permissions": ["*:*:*"],
                "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
            },
            "roles": ["admin"],
            "permissions": ["*:*:*"]
        }
    )

# 启动命令: uvicorn main:app --reload --port 8000