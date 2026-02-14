# ÖNIKA LI - Vercel 部署指南

## 部署步骤

### 1. 更新代码
将 `bot/onikali_bot.py` 替换为新的Webhook版本

### 2. 添加配置文件
- `vercel.json` → 根目录
- `requirements.txt` → 根目录（如果已有则覆盖）

### 3. 注册Vercel
- 访问 https://vercel.com
- 用GitHub账号登录
- 导入 `onikali011/OnikaLi` 仓库

### 4. 设置环境变量
在Vercel控制台 → Settings → Environment Variables 添加：
- `TELEGRAM_TOKEN` = 你的Bot Token
- `MOONSHOT_API_KEY` = Kimi API Key
- `ANTHROPIC_API_KEY` = Claude API Key（可选）

### 5. 部署
点击 Deploy，等待完成

### 6. 设置Webhook
部署完成后，运行：
```bash
pip install requests
python setup_webhook.py
```
输入你的Vercel域名（例如：`onikali.vercel.app`）

### 7. 测试
在Telegram发送 `/start`，应该能正常回复

## 本地测试（可选）
```bash
python bot/onikali_bot.py local
```
