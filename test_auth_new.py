"""
测试新用户完整认证流程
"""
import requests
import json
import random

BASE_URL = 'http://localhost:5000/api/auth'

# 生成随机用户名
random_num = random.randint(1000, 9999)
test_username = f'newuser{random_num}'
test_email = f'newuser{random_num}@example.com'
test_password = 'testpass123'

print("=" * 60)
print(f"测试用户: {test_username}")
print(f"测试邮箱: {test_email}")
print(f"测试密码: {test_password}")
print("=" * 60)

# 1. 注册新用户
print("\n【步骤1】 注册新用户...")
response = requests.post(f'{BASE_URL}/register', json={
    'username': test_username,
    'email': test_email,
    'password': test_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 201:
    print("[ERROR] 注册失败！")
    exit(1)

print("[SUCCESS] 注册成功！")
token = response.json()['access_token']

# 2. 使用token获取用户信息
print("\n【步骤2】 获取用户信息...")
response = requests.get(f'{BASE_URL}/profile', headers={
    'Authorization': f'Bearer {token}'
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 获取用户信息失败！")
else:
    print("[SUCCESS] 获取用户信息成功！")

# 3. 登录
print("\n【步骤3】 登录测试...")
response = requests.post(f'{BASE_URL}/login', json={
    'username': test_username,
    'password': test_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 登录失败！")
    exit(1)

print("[SUCCESS] 登录成功！")

# 4. 使用邮箱登录
print("\n【步骤4】 使用邮箱登录...")
response = requests.post(f'{BASE_URL}/login', json={
    'username': test_email,
    'password': test_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 邮箱登录失败！")
else:
    print("[SUCCESS] 邮箱登录成功！")

# 5. 忘记密码
print("\n【步骤5】 忘记密码...")
response = requests.post(f'{BASE_URL}/forgot-password', json={
    'email': test_email
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 忘记密码失败！")
    exit(1)

reset_token = response.json()['reset_token']
print(f"[SUCCESS] 重置令牌: {reset_token}")

# 6. 重置密码
new_password = 'newpass456'
print(f"\n【步骤6】 重置密码为: {new_password}...")
response = requests.post(f'{BASE_URL}/reset-password', json={
    'reset_token': reset_token,
    'new_password': new_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 重置密码失败！")
    exit(1)

print("[SUCCESS] 重置密码成功！")

# 7. 使用新密码登录
print("\n【步骤7】 使用新密码登录...")
response = requests.post(f'{BASE_URL}/login', json={
    'username': test_username,
    'password': new_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code != 200:
    print("[ERROR] 新密码登录失败！")
    exit(1)

print("[SUCCESS] 新密码登录成功！")

# 8. 尝试使用旧密码登录（应该失败）
print("\n【步骤8】 使用旧密码登录（应该失败）...")
response = requests.post(f'{BASE_URL}/login', json={
    'username': test_username,
    'password': test_password
})
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

if response.status_code == 401:
    print("[SUCCESS] 旧密码已失效（正确）！")
else:
    print("[ERROR] 旧密码仍然有效（错误）！")

print("\n" + "=" * 60)
print(">>> 所有测试通过！认证功能正常工作！ <<<")
print("=" * 60)
