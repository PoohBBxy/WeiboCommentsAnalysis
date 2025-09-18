from utils.query import query
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def get_serializer():
    """Create a URLSafeTimedSerializer using current app's secret key."""
    secret = current_app.config.get('SECRET_KEY') or current_app.secret_key
    return URLSafeTimedSerializer(secret)

def get_current_user_info(username):
    """
    一个独立的用户信息获取函数，不依赖于任何蓝图或app实例。
    """
    if not username:
        return None
    # 在查询中增加 status 字段
    user_data = query(
        "SELECT role, avatar, createTime, nickname, email, status FROM user WHERE username = %s LIMIT 1",
        [username], 'select'
    )
    if user_data:
        role, avatar_path, create_time, nickname, email, status = user_data[0]
        return {
            'username': username,
            'nickname': nickname,
            'email': email,
            'role': role,
            'avatar_url': avatar_path,
            'createTime': create_time,
            'status': status
        }
    return None
