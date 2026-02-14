"""
ÖNIKA LI Webhook 设置脚本
部署到Vercel后运行此脚本设置Webhook
"""

import os
import requests

# 从环境变量读取
TOKEN = os.getenv('TELEGRAM_TOKEN')
VERCEL_URL = os.getenv('VERCEL_URL')  # 部署后Vercel会自动提供

if not TOKEN:
    print("❌ 错误: 请设置 TELEGRAM_TOKEN 环境变量")
    exit(1)

# 如果VERCEL_URL没设置，手动输入
if not VERCEL_URL:
    VERCEL_URL = input("请输入你的Vercel域名 (例如: onikali.vercel.app): ")
    if not VERCEL_URL.startswith('https://'):
        VERCEL_URL = f"https://{VERCEL_URL}"

WEBHOOK_URL = f"{VERCEL_URL}/"

# 设置Webhook
api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
payload = {
    "url": WEBHOOK_URL,
    "allowed_updates": ["message", "callback_query"]
}

response = requests.post(api_url, json=payload)
data = response.json()

if data.get('ok'):
    print(f"✅ Webhook 设置成功!")
    print(f"🌐 URL: {WEBHOOK_URL}")

    # 获取webhook信息
    info_response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
    info = info_response.json()
    if info.get('ok'):
        print(f"📊 挂起更新数: {info['result'].get('pending_update_count', 0)}")
else:
    print(f"❌ 设置失败: {data.get('description', '未知错误')}")
