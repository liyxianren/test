"""
测试认证功能脚本
"""
import requests
import json

BASE_URL = 'http://localhost:5000/api/auth'

def test_register():
    """测试注册功能"""
    print("\n=== 测试用户注册 ===")
    data = {
        'username': 'testuser123',
        'email': 'test@example.com',
        'password': 'password123'
    }

    try:
        response = requests.post(f'{BASE_URL}/register', json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

        if response.status_code == 201:
            return response.json().get('access_token')
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_login():
    """测试登录功能"""
    print("\n=== 测试用户登录 ===")
    data = {
        'username': 'testuser123',
        'password': 'password123'
    }

    try:
        response = requests.post(f'{BASE_URL}/login', json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

        if response.status_code == 200:
            return response.json().get('access_token')
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_forgot_password():
    """测试忘记密码功能"""
    print("\n=== 测试忘记密码 ===")
    data = {
        'email': 'test@example.com'
    }

    try:
        response = requests.post(f'{BASE_URL}/forgot-password', json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

        if response.status_code == 200:
            return response.json().get('reset_token')
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_reset_password(reset_token):
    """测试重置密码功能"""
    print("\n=== 测试重置密码 ===")
    data = {
        'reset_token': reset_token,
        'new_password': 'newpassword123'
    }

    try:
        response = requests.post(f'{BASE_URL}/reset-password', json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_login_with_new_password():
    """使用新密码测试登录"""
    print("\n=== 使用新密码测试登录 ===")
    data = {
        'username': 'testuser123',
        'password': 'newpassword123'
    }

    try:
        response = requests.post(f'{BASE_URL}/login', json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_get_profile(token):
    """测试获取用户信息"""
    print("\n=== 测试获取用户信息 ===")
    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.get(f'{BASE_URL}/profile', headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("开始测试认证功能")
    print("=" * 60)

    # 测试注册
    token = test_register()

    # 如果注册失败（可能用户已存在），尝试登录
    if not token:
        print("\n注册失败，尝试登录...")
        token = test_login()

    # 测试获取用户信息
    if token:
        test_get_profile(token)

    # 测试忘记密码流程
    reset_token = test_forgot_password()

    # 测试重置密码
    if reset_token:
        success = test_reset_password(reset_token)

        # 测试新密码登录
        if success:
            test_login_with_new_password()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
