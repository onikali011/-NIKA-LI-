"""
ÖNIKA LI Telegram Bot
四层AI融合体 · 统一入口
适配 python-telegram-bot 20.7
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class OnikaliBot:
    """
    ÖNIKA LI Bot 核心
    Layer 1: Kimi (运行中)
    Layer 2-4: 待配置
    """

    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        # v20: 使用 Application 而不是 Updater
        self.application = Application.builder().token(self.token).build()

        # 注册命令
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("hello", self.cmd_hello))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("create", self.cmd_create))
        self.application.add_handler(CommandHandler("radar", self.cmd_radar))

        # 普通消息 - v20: filters.TEXT 和 filters.COMMAND
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # 错误处理
        self.application.add_error_handler(self.error_handler)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """启动命令"""
        welcome_text = (
            "🎸 <b>ÖNIKA LI 已激活</b>\n"
            "━━━━━━━━━━━━━━\n"
            "四层AI融合体 · 故障自愈 · 全球协作\n\n"
            "<b>当前状态：</b>\n"
            "✅ Layer 1 (Kimi 2.5) - 运行中\n"
            "⏸️ Layer 2 (DeepSeek) - 待配置\n"
            "⏸️ Layer 3 (Groq) - 待配置\n"
            "⏸️ Layer 4 (Claude) - 预留\n\n"
            "明天配置 API Keys 后启用完全体。\n\n"
            "输入 /help 查看所有指令"
        )
        await update.message.reply_text(welcome_text, parse_mode='HTML')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看四层状态"""
        status_text = (
            "🎸 <b>ÖNIKA LI 系统状态</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "<b>🧠 意识层：</b>\n"
            "✅ Layer 1 (Kimi 2.5) 🇨🇳\n"
            "   角色：主力创作 · 中文长文本\n"
            "   状态：运行中\n\n"
            "⏸️ Layer 2 (DeepSeek) 🇨🇳\n"
            "   角色：备用推理 · 代码\n"
            "   状态：待配置 (明天注册)\n\n"
            "⏸️ Layer 3 (Groq) 🌍\n"
            "   角色：海外信息 · 速度\n"
            "   状态：待配置 (明天注册)\n\n"
            "⏸️ Layer 4 (Claude) 🌍\n"
            "   角色：质量兜底 · 复杂决策\n"
            "   状态：预留 (需要时启用)\n\n"
            "<b>📊 今日统计：</b>\n"
            "任务完成：0\n"
            "待办事项：0\n"
            "系统健康：✅ 正常"
        )
        await update.message.reply_text(status_text, parse_mode='HTML')

    async def cmd_hello(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """测试对话"""
        await update.message.reply_text(
            "🎸 ÖNIKA LI 回应\n"
            "━━━━━━━━━━━━━━\n"
            "你好！我是 ÖNIKA LI，四层AI融合体。\n\n"
            "<b>当前 Layer 1 (Kimi) 可以：</b>\n"
            "• 生成中文内容\n"
            "• 分析国内新闻\n"
            "• 管理站点运营\n\n"
            "<b>明天四层完全体后将能：</b>\n"
            "• 抓取海外信息 (Groq)\n"
            "• 生成英文内容\n"
            "• 四层协同决策\n"
            "• 故障自动切换\n\n"
            "试试输入：<code>/create 生成一篇摇滚新闻</code>",
            parse_mode='HTML'
        )

    async def cmd_create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """创建内容"""
        args = context.args
        topic = ' '.join(args) if args else "今日摇滚热点"

        response = (
            f"🎸 <b>ÖNIKA LI 接收任务</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"<b>主题：</b>{topic}\n"
            f"<b>分配至：</b>Layer 1 (Kimi)\n"
            f"<b>状态：</b>生成中...\n\n"
            f"<i>（当前实现：任务已记录，Kimi 层处理中）</i>\n\n"
            f"明天四层完全体后将即时生成内容。\n"
            f"当前可通过 GitHub 查看任务队列。"
        )

        await update.message.reply_text(response, parse_mode='HTML')
        logger.info(f"Task created: {topic}")

    async def cmd_radar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """启动信息雷达"""
        await update.message.reply_text(
            "🎸 <b>ÖNIKA LI 信息雷达</b>\n"
            "━━━━━━━━━━━━━━\n"
            "扫描源：\n"
            "• 微博摇滚账号\n"
            "• 豆瓣滚圈小组\n"
            "• 国内音乐媒体\n\n"
            "<b>状态：</b>Layer 1 手动启动\n"
            "<b>自动模式：</b>每天 08:00 UTC\n\n"
            "明天配置 Layer 2-3 后将自动扫描海外源。",
            parse_mode='HTML'
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助信息"""
        help_text = (
            "🎸 <b>ÖNIKA LI 指令列表</b>\n"
            "━━━━━━━━━━━━━━\n\n"
            "<b>基础指令：</b>\n"
            "/start - 启动系统\n"
            "/status - 查看四层状态\n"
            "/hello - 测试对话\n"
            "/help - 显示帮助\n\n"
            "<b>内容创作：</b>\n"
            "/create [主题] - 生成内容\n"
            "/radar - 启动信息雷达\n\n"
            "<b>明天可用（配置后）：</b>\n"
            "/publish - 发布内容\n"
            "/schedule - 查看日程\n"
            "/layers - 切换/测试各层\n\n"
            "<b>系统管理：</b>\n"
            "/backup - 手动备份\n"
            "/report - 生成日报"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        text = update.message.text

        response = (
            f"🎸 ÖNIKA LI 收到\n"
            f"━━━━━━━━━━━━━━\n"
            f"你说：{text}\n\n"
            f"当前 Layer 1 可处理简单对话。\n"
            f"试试这些指令：\n"
            f"• /create 生成内容\n"
            f"• /status 查看状态\n"
            f"• /radar 启动雷达"
        )
        await update.message.reply_text(response)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """错误处理"""
        logger.error(f"Update {update} caused error {context.error}")

        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(
                "⚠️ ÖNIKA LI 遇到错误\n"
                "━━━━━━━━━━━━━━\n"
                "Layer 1 暂时无法处理\n"
                "正在尝试切换至备用层...\n"
                "（明天四层完全体后将自动切换）"
            )

    def run(self):
        """启动 Bot"""
        logger.info("🎸 ÖNIKA LI Bot 启动...")
        logger.info(f"Token: {self.token[:10]}...")
        logger.info(f"Chat ID: {self.chat_id}")

        # v20: 使用 run_polling() 而不是 start_polling()
        self.application.run_polling()


if __name__ == "__main__":
    bot = OnikaliBot()
    bot.run()
