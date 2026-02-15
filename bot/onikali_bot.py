#!/usr/bin/env python3
"""
🎸 ÖNIKA LI - 四层AI融合体 (全OpenRouter版)
Free-first routing · Fault-tolerant · Cost-aware
"""

import os
import logging
import asyncio
import aiohttp
import ssl
from typing import Optional, Dict, Any
from dataclasses import dataclass
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)

# ============ 配置 ============
TELEGRAM_TOKEN = "8256004848:AAED5v5CxrXIb-s38u6pxJIX-U4FPjh4sWc"
OPENROUTER_API_KEY = "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"

# 四层AI配置 (全部走OpenRouter，免费优先)
LAYERS = {
    1: {
        "name": "Kimi 2.5",
        "model": "moonshot/kimi-k2.5",
        "free": True,
        "timeout": 30
    },
    2: {
        "name": "DeepSeek V3",
        "model": "deepseek/deepseek-chat",
        "free": True,
        "timeout": 25
    },
    3: {
        "name": "Groq Llama 3.1",
        "model": "groq/llama-3.1-70b-versatile",
        "free": True,
        "timeout": 20
    },
    4: {
        "name": "Claude 3.5 Haiku",
        "model": "anthropic/claude-3.5-haiku",
        "free": False,
        "timeout": 20
    }
}

DAILY_BUDGET_LIMIT = 1.0  # USD
MAX_RETRIES = 2

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@dataclass
class LayerResponse:
    layer: int
    model: str
    content: str
    latency: float
    cost: float
    success: bool
    error: Optional[str] = None


class OnikaLiCore:
    """四层AI核心"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.daily_cost = 0.0

    async def init(self):
        """初始化HTTP会话"""
        # 创建SSL上下文（禁用证书验证，解决部分地区SSL问题）
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)

    async def query_layer(self, layer_num: int, message: str) -> LayerResponse:
        """查询指定AI层"""
        layer = LAYERS[layer_num]
        import time
        start = time.time()

        try:
            # 检查预算（付费层）
            if not layer["free"] and self.daily_cost >= DAILY_BUDGET_LIMIT:
                return LayerResponse(
                    layer_num, layer["name"], "", 0, 0, False, "Budget limit"
                )

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://t.me/OnikaLiBot",
                "X-Title": "OnikaLi Bot",
                "Content-Type": "application/json"
            }

            payload = {
                "model": layer["model"],
                "messages": [
                    {"role": "system", "content": "You are OnikaLi, a helpful AI assistant. Be concise and friendly."},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            # 付费层限制token
            if not layer["free"]:
                payload["max_tokens"] = 1000

            async with self.session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=layer["timeout"])
            ) as resp:

                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {error_text[:100]}")

                data = await resp.json()
                content = data["choices"][0]["message"]["content"]

                # 计算成本
                cost = 0.0
                if not layer["free"]:
                    usage = data.get("usage", {})
                    tokens = usage.get("total_tokens", 0)
                    cost = (tokens / 1000000) * 0.5
                    self.daily_cost += cost

                latency = time.time() - start

                return LayerResponse(
                    layer_num, layer["name"], content, latency, cost, True
                )

        except Exception as e:
            latency = time.time() - start
            logger.error(f"Layer {layer_num} error: {e}")
            return LayerResponse(
                layer_num, layer["name"], "", latency, 0, False, str(e)
            )

    async def chat(self, message: str) -> Dict[str, Any]:
        """智能路由 - 免费优先，故障自愈"""

        errors = []

        for layer_num in [1, 2, 3, 4]:
            layer = LAYERS[layer_num]

            if not layer["free"] and self.daily_cost >= DAILY_BUDGET_LIMIT:
                errors.append(f"Layer {layer_num}: Budget limit")
                continue

            for retry in range(MAX_RETRIES):
                response = await self.query_layer(layer_num, message)

                if response.success:
                    icon = "✅" if layer["free"] else "💰"
                    return {
                        "success": True,
                        "layer": layer_num,
                        "model": response.model,
                        "content": response.content,
                        "latency": round(response.latency, 2),
                        "cost": round(response.cost, 4),
                        "free": layer["free"],
                        "icon": icon
                    }

                errors.append(f"Layer {layer_num} retry {retry + 1}: {response.error}")

                if retry < MAX_RETRIES - 1:
                    await asyncio.sleep(1)

        # 全部失败
        error_msg = "\n".join(errors[-4:])
        logger.error(f"All layers failed: {error_msg}")

        return {
            "success": False,
            "error": error_msg,
            "content": "⚠️ 所有AI层暂时不可用，请稍后再试。"
        }

    async def get_status(self) -> str:
        """获取系统状态"""
        lines = [
            "🎸 ÖNIKA LI 日报",
            "━" * 20,
            "四层AI融合体 · 故障自愈",
            ""
        ]

        for num, layer in LAYERS.items():
            icon = "✅" if layer["free"] else "💰"
            lines.append(f"{icon} Layer {num}: {layer['name']}")

        lines.extend([
            "",
            f"💳 今日花费: ${self.daily_cost:.4f}",
            f"📊 预算剩余: ${DAILY_BUDGET_LIMIT - self.daily_cost:.2f}"
        ])

        return "\n".join(lines)


class OnikaLiBot:
    """Telegram Bot 包装"""

    def __init__(self):
        self.core = OnikaLiCore()
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎸 ÖNIKA LI 已激活\n"
            "━━━━━━━━━━━━━━\n"
            "四层AI融合体 · 故障自愈 · 自动切换\n\n"
            "输入 /status 查看状态\n"
            "直接发消息即可对话！"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """🎸 ÖNIKA LI 指令

/status - 查看AI层状态
/help - 显示此帮助

直接发送消息自动路由最优AI
策略：免费优先，故障自动切换"""
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = await self.core.get_status()
        await update.message.reply_text(status)

    async def chat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        message = update.message.text
        thinking_msg = await update.message.reply_text("🎸 思考中...")

        try:
            result = await self.core.chat(message)
            await thinking_msg.delete()

            if result["success"]:
                header = f"{result['icon']} *{result['model']}* ({result['latency']}s)\n\n"
                await update.message.reply_text(
                    header + result["content"],
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ 所有AI层失败\n\n{result['content']}"
                )
        except Exception as e:
            await thinking_msg.delete()
            logger.error(f"Chat error: {e}")
            await update.message.reply_text("❌ 处理消息时出错")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")

    async def post_init(self, application: Application):
        await self.core.init()
        logger.info("🎸 ÖNIKA LI 初始化完成")

    def run(self):
        self.application = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .post_init(self.post_init)
            .build()
        )

        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.chat_handler)
        )
        self.application.add_error_handler(self.error_handler)

        logger.info("🎸 ÖNIKA LI 启动中...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = OnikaLiBot()
    bot.run()
