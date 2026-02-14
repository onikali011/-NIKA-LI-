"""
ÖNIKA LI Telegram Bot
四层AI融合体 · 统一入口
适配 Vercel Webhook 部署
"""

import os
import logging
import asyncio
import json
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# AI 客户端
try:
    from openai import OpenAI
    ANTHROPIC_AVAILABLE = True
    try:
        import anthropic
    except ImportError:
        ANTHROPIC_AVAILABLE = False
        logging.warning("Anthropic not installed")
except ImportError:
    OpenAI = None
    ANTHROPIC_AVAILABLE = False
    logging.warning("OpenAI not installed")

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class OnikaliBot:
    """ÖNIKA LI Bot 核心"""

    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.moonshot_key = os.getenv('MOONSHOT_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')

        self.moonshot_client = None
        self.anthropic_client = None
        self.current_layer = 1
        self.application = None

        if OpenAI and self.moonshot_key:
            self.moonshot_client = OpenAI(
                api_key=self.moonshot_key,
                base_url="https://api.moonshot.cn/v1"
            )
            logger.info("✅ Layer 1 initialized")

        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            logger.info("✅ Layer 2 initialized")

    async def init_app(self):
        """初始化应用"""
        if not self.application:
            self.application = Application.builder().token(self.token).build()
            self._register_handlers()
            await self.application.initialize()
        return self.application

    def _register_handlers(self):
        """注册处理器"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("hello", self.cmd_hello))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("create", self.cmd_create))
        self.application.add_handler(CommandHandler("radar", self.cmd_radar))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_ai_message)
        )
        self.application.add_error_handler(self.error_handler)

    async def _call_moonshot(self, message: str) -> str:
        """调用 Kimi"""
        if not self.moonshot_client:
            raise Exception("Layer 1 not available")

        response = self.moonshot_client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": "你是 ÖNIKA LI，摇滚风格AI助手，简洁有力，偶尔用emoji。"},
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    async def _call_claude(self, message: str) -> str:
        """调用 Claude"""
        if not self.anthropic_client:
            raise Exception("Layer 2 not available")

        response = self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            system="你是 ÖNIKA LI，摇滚风格AI助手，简洁有力，偶尔用emoji。",
            messages=[{"role": "user", "content": message}]
        )
        return response.content[0].text

    async def _get_ai_response(self, message: str) -> tuple[str, int]:
        """获取AI响应，自动故障转移"""
        if self.moonshot_client:
            try:
                response = await self._call_moonshot(message)
                self.current_layer = 1
                return response, 1
            except Exception as e:
                logger.warning(f"Layer 1 failed: {e}")

        if self.anthropic_client:
            try:
                response = await self._call_claude(message)
                self.current_layer = 2
                return response, 2
            except Exception as e:
                logger.error(f"Layer 2 failed: {e}")

        return "⚠️ 所有AI层都暂时不可用，请稍后再试。", 0

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """启动命令"""
        layer_status = []
        if self.moonshot_client:
            layer_status.append("✅ Layer 1 (Kimi 2.5) - 运行中")
        else:
            layer_status.append("❌ Layer 1 (Kimi 2.5) - 未配置")

        if self.anthropic_client:
            layer_status.append("✅ Layer 2 (Claude 3) - 备用")
        else:
            layer_status.append("⏸️ Layer 2 (Claude 3) - 未配置")

        welcome_text = (
            "🎸 <b>ÖNIKA LI 已激活</b>\n"
            "━━━━━━━━━━━━━━\n"
            "四层AI融合体 · 故障自愈 · 自动切换\n\n"
            "<b>当前状态：</b>\n" +
            "\n".join(layer_status) +
            "\n⏸️ Layer 3 (DeepSeek) - 预留\n"
            "⏸️ Layer 4 (Groq) - 预留\n\n"
            "输入 /help 查看所有指令\n"
            "直接发消息即可对话！"
        )
        await update.message.reply_text(welcome_text, parse_mode='HTML')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看状态"""
        layer1_status = "✅ 运行中" if self.moonshot_client else "❌ 未配置"
        layer2_status = "✅ 备用就绪" if self.anthropic_client else "⏸️ 未配置"

        status_text = (
            "🎸 <b>ÖNIKA LI 系统状态</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            f"<b>🧠 意识层：</b>\n"
            f"{'🟢' if self.current_layer == 1 else '⚪'} Layer 1 (Kimi 2.5) {layer1_status}\n"
            f"   角色：主力创作 · 中文长文本\n\n"
            f"{'🟢' if self.current_layer == 2 else '⚪'} Layer 2 (Claude 3) {layer2_status}\n"
            f"   角色：备用兜底 · 英文质量\n\n"
            f"⏸️ Layer 3 (DeepSeek) - 预留\n"
            f"⏸️ Layer 4 (Groq) - 预留\n\n"
            f"<b>📊 当前使用：</b>Layer {self.current_layer}\n"
            f"<b>系统健康：</b>✅ 正常"
        )
        await update.message.reply_text(status_text, parse_mode='HTML')

    async def cmd_hello(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """测试对话"""
        test_response, layer = await self._get_ai_response("用一句话介绍你自己")

        await update.message.reply_text(
            f"🎸 ÖNIKA LI 回应\n"
            f"━━━━━━━━━━━━━━\n"
            f"{test_response}\n\n"
            f"<i>（由 Layer {layer} 生成）</i>",
            parse_mode='HTML'
        )

    async def cmd_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """创建内容"""
        args = context.args
        topic = ' '.join(args) if args else "今日摇滚热点"

        await update.message.reply_text(
            f"🎸 <b>ÖNIKA LI 生成中...</b>\n"
            f"主题：{topic}\n"
            f"━━━━━━━━━━━━━━",
            parse_mode='HTML'
        )

        prompt = f"生成一段关于'{topic}'的摇滚风格内容，100字左右，带emoji"
        response, layer = await self._get_ai_response(prompt)

        await update.message.reply_text(
            f"{response}\n\n"
            f"<i>— 由 Layer {layer} 生成</i>",
            parse_mode='HTML'
        )

    async def cmd_radar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """信息雷达"""
        await update.message.reply_text(
            "🎸 <b>ÖNIKA LI 信息雷达</b>\n"
            "━━━━━━━━━━━━━━\n"
            "扫描中...\n\n"
            "<i>（功能开发中）</i>",
            parse_mode='HTML'
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助"""
        help_text = (
            "🎸 <b>ÖNIKA LI 指令列表</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "<b>基础指令：</b>\n"
            "/start - 启动系统\n"
            "/status - 查看四层状态\n"
            "/hello - 测试AI对话\n"
            "/help - 显示帮助\n\n"
            "<b>内容创作：</b>\n"
            "/create [主题] - 生成内容\n"
            "/radar - 启动信息雷达\n\n"
            "<b>直接发消息 = AI对话</b>\n\n"
            "<i>故障时会自动切换备用模型</i>"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def handle_ai_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        text = update.message.text
        await update.message.chat.send_action(action="typing")

        response, layer = await self._get_ai_response(text)

        if layer == 2:
            response += "\n\n<i>— Layer 2 (备用)</i>"

        await update.message.reply_text(response, parse_mode='HTML')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """错误处理"""
        logger.error(f"Update {update} caused error {context.error}")


# 全局Bot实例
bot = OnikaliBot()


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Handler"""

    def do_POST(self):
        """处理Webhook POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            update = Update.de_json(data, bot.application.bot if bot.application else None)

            # 异步处理更新
            asyncio.run(self._process_update(update))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    async def _process_update(self, update):
        """处理Telegram更新"""
        app = await bot.init_app()
        await app.process_update(update)

    def do_GET(self):
        """健康检查"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'ÖNIKA LI Bot is running!')


# 本地测试用
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "local":
        # 本地轮询模式
        asyncio.run(bot.init_app())
        bot.application.run_polling()
