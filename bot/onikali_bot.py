import os
import logging
import asyncio
import aiohttp
import time
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Keys
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
GROQ_KEY = os.getenv('GROQ_API_KEY')
BRAVE_KEY = os.getenv("BRAVE_API_KEY")
PROXY_URL = "http://127.0.0.1:9674"

# 工作目录
WORK_DIR = os.path.expanduser("~/ÖNIKA_Workspace")
os.makedirs(WORK_DIR, exist_ok=True)

# 用户数据存储
user_data = {}
last_request_time = 0
MIN_REQUEST_INTERVAL = 3  # 增加间隔到3秒

def save_to_file(filename, content, folder="文案"):
    folder_path = os.path.join(WORK_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()[:30]
    filepath = os.path.join(folder_path, f"{safe_filename}_{datetime.now().strftime('%m%d_%H%M')}.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {filename}\n# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}")
    return filepath

async def brave_search(query, count=5):
    """Brave Search API"""
    if not BRAVE_KEY:
        return None, "Brave API Key 未配置"
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_KEY
    }
    params = {
        "q": query,
        "count": count,
        "search_lang": "zh"
    }
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, params=params, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for item in data.get('web', {}).get('results', []):
                        results.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'description': item.get('description', '')[:300]
                        })
                    return results, None
                else:
                    text = await resp.text()
                    return None, f"搜索失败: {resp.status}"
    except Exception as e:
        return None, f"搜索错误: {str(e)[:100]}"

async def call_openrouter(messages, model="anthropic/claude-3.5-sonnet", retry=2):
    """调用OpenRouter，带重试"""
    global last_request_time
    
    if not OPENROUTER_KEY:
        return None, "OpenRouter API Key 未配置"
    
    # 速率限制
    current_time = time.time()
    time_since_last = current_time - last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        await asyncio.sleep(MIN_REQUEST_INTERVAL - time_since_last)
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/onikali_bot",
        "X-Title": "ÖNIKA LI"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    for attempt in range(retry):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, headers=headers, json=data, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    last_request_time = time.time()
                    
                    if resp.status == 200:
                        result = await resp.json()
                        return result['choices'][0]['message']['content'], None
                    elif resp.status == 401:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter 401错误: {error_text}")
                        if attempt < retry - 1:
                            await asyncio.sleep(2)
                            continue
                        return None, f"API认证失败(401)，请检查OpenRouter Key是否有效"
                    elif resp.status == 429:
                        return None, "rate_limit"
                    elif resp.status == 402:
                        return None, "no_credits"
                    else:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter错误 {resp.status}: {error_text[:200]}")
                        return None, f"API错误: {resp.status}"
        except Exception as e:
            logger.error(f"OpenRouter请求异常: {str(e)}")
            if attempt < retry - 1:
                await asyncio.sleep(2)
                continue
            return None, f"请求失败: {str(e)[:100]}"
    
    return None, "所有重试失败"

async def call_groq(messages, model="llama-3.3-70b-versatile"):
    """调用Groq"""
    if not GROQ_KEY:
        return None, "Groq未配置"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=data, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['choices'][0]['message']['content'], None
                else:
                    return None, f"Groq错误: {resp.status}"
    except Exception as e:
        return None, f"Groq请求失败: {str(e)[:50]}"

async def transcribe_voice(voice_file_url):
    """语音识别"""
    if not GROQ_KEY:
        return None, "Groq未配置"
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(voice_file_url, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return None, "下载失败"
                voice_data = await resp.read()
            
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {GROQ_KEY}"}
            data = aiohttp.FormData()
            data.add_field('file', voice_data, filename='voice.ogg', content_type='audio/ogg')
            data.add_field('model', 'whisper-large-v3')
            data.add_field('language', 'zh')
            
            async with session.post(url, headers=headers, data=data, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['text'], None
                else:
                    return None, f"识别失败"
    except Exception as e:
        return None, f"语音错误"

async def generate_content(topic, search_results=None):
    """生成文案"""
    search_info = ""
    if search_results:
        search_info = "基于以下网络信息创作：\n"
        for i, r in enumerate(search_results[:3], 1):
            search_info += f"{i}. {r['title']}: {r['description'][:200]}\n"
    
    prompt = f"""你是LiveGigs Asia的专业文案写手。

主题：{topic}

{search_info}

请创作包含以下内容的文案：
1. 吸引人的标题
2. 正文（300-500字，包含具体数据、时间、亮点）
3. 社交媒体标签（#话题）
4. 适合发布的平台建议

风格：专业、有激情、适合音乐演出行业。如果提供了搜索信息，必须融入真实数据。"""
    
    messages = [{"role": "user", "content": prompt}]
    
    # 先尝试Claude
    content, error = await call_openrouter(messages, "anthropic/claude-3.5-sonnet")
    if content:
        return content, "Claude 3.5"
    
    # 如果失败，尝试DeepSeek免费版
    if error in ["rate_limit", "no_credits"]:
        content, error = await call_openrouter(messages, "deepseek/deepseek-r1-0528:free")
        if content:
            return content, "DeepSeek R1"
    
    # 最后尝试Groq
    if GROQ_KEY:
        content, error = await call_groq(messages)
        if content:
            return content, "Groq Llama"
    
    return None, error

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """🎸 ÖNIKA LI 运营助理

✅ 自动上网搜索: Brave Search
✅ AI文案生成: Claude 3.5 / DeepSeek / Groq
✅ 语音识别: Whisper

📋 指令：
/write [主题] - 自动搜索+写文案
/search [关键词] - 搜索信息
/modify [要求] - 修改文案

💡 直接发送主题，如"noname乐队2026巡演"，自动写文案"""
    await update.message.reply_text(welcome)

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """搜索命令"""
    if not context.args:
        await update.message.reply_text("🔍 用法：/search [关键词]")
        return
    
    query = " ".join(context.args)
    await update.message.chat.send_action(action="typing")
    
    results, error = await brave_search(query)
    if error:
        await update.message.reply_text(f"⚠️ {error}")
        return
    
    text = f"🔍 {query} 的搜索结果：\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(results[:3], 1):
        text += f"{i}. {r['title']}\n{r['description'][:150]}...\n{r['url']}\n\n"
    
    await update.message.reply_text(text[:1500])

async def write_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """写文案"""
    if not context.args:
        await update.message.reply_text("📝 用法：/write [主题]")
        return
    
    topic = " ".join(context.args)
    await do_write(update, topic)

async def do_write(update: Update, topic: str):
    """执行写作流程"""
    user_id = update.effective_user.id
    
    await update.message.chat.send_action(action="typing")
    msg = await update.message.reply_text(f"🔍 正在搜索【{topic}】...")
    
    # 强制搜索
    search_results, search_error = await brave_search(topic, count=5)
    
    # 生成
    await update.message.chat.send_action(action="typing")
    content, layer = await generate_content(topic, search_results)
    
    if content:
        # 保存
        filename = topic[:25]
        filepath = save_to_file(filename, content, "文案")
        
        # 记录
        user_data[user_id] = {
            "last_content": content,
            "last_topic": topic,
            "last_filepath": filepath,
            "search_results": search_results
        }
        
        preview = content[:700] + "..." if len(content) > 700 else content
        
        text = f"""✅ 文案已生成（使用 {layer}）！

📁 保存：{filepath}

{preview}

💡 提修改意见（太长/加数据/改风格），我自动修改"""
        await msg.edit_text(text)
    else:
        await msg.edit_text(f"⚠️ 生成失败：{layer}\n\n建议：\n1. 检查OpenRouter Key是否有效\n2. 等待1分钟再试\n3. 或联系管理员检查配置")

async def modify_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """修改文案"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("⚠️ 没有可修改的文案，先发送主题生成")
        return
    
    if not context.args:
        await update.message.reply_text("""✏️ 用法：/modify [修改要求]

例如：
/modify 缩短到200字
/modify 加更多演出时间
/modify 改得更口语化""")
        return
    
    modification = " ".join(context.args)
    last_content = user_data[user_id]["last_content"]
    topic = user_data[user_id]["last_topic"]
    
    await update.message.chat.send_action(action="typing")
    
    prompt = f"""修改以下文案。

原文主题：{topic}

原文案：
{last_content}

修改要求：{modification}

请输出修改后的完整文案。"""
    
    messages = [{"role": "user", "content": prompt}]
    new_content, error = await call_openrouter(messages)
    
    if new_content:
        filename = f"{topic}_修改版"
        filepath = save_to_file(filename, new_content, "文案")
        
        user_data[user_id]["last_content"] = new_content
        user_data[user_id]["last_filepath"] = filepath
        
        preview = new_content[:700] + "..." if len(new_content) > 700 else new_content
        
        text = f"""✅ 已修改！

📁 新版本：{filepath}

{preview}

💡 继续修改或说定稿"""
        await update.message.reply_text(text)
    else:
        await update.message.reply_text(f"⚠️ 修改失败：{error}")

async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动保存"""
    if len(context.args) < 2:
        await update.message.reply_text("💾 用法：/save [文件名] [内容]")
        return
    
    filename = context.args[0]
    content = " ".join(context.args[1:])
    filepath = save_to_file(filename, content, "手动保存")
    
    await update.message.reply_text(f"✅ 已保存：{filepath}")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """状态"""
    text = f"""🎸 ÖNIKA LI 运营助理状态
━━━━━━━━━━━━━━
✅ Brave Search - 自动上网
✅ Claude 3.5 - 主要AI
✅ DeepSeek R1 - 免费备用
✅ Groq Llama - 极速备用
✅ Whisper - 语音识别

🔑 OpenRouter Key: {'✅' if OPENROUTER_KEY else '❌'}
🔑 Groq Key: {'✅' if GROQ_KEY else '❌'}

💾 工作目录：{WORK_DIR}"""
    await update.message.reply_text(text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文字消息"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # 忽略命令
    if text.startswith('/'):
        return
    
    # 修改意图检测
    modify_keywords = ['太长', '太短', '加', '改', '换', '优化', '调整', '不够', '要', '不要', '删除', '增加', '减少']
    if user_id in user_data and any(kw in text for kw in modify_keywords):
        context.args = text.split()
        await modify_cmd(update, context)
        return
    
    # 定稿/发布
    if '定稿' in text or '发布' in text:
        await update.message.reply_text("""📋 定稿功能开发中...

当前：
✅ 文案生成
✅ 自动修改
✅ 本地保存

待开发：
🔄 自动推送到网站
🔄 发布到社交媒体""")
        return
    
    # 默认：当作主题直接写文案
    if len(text) > 3 and not text.startswith(('你好', '在吗', '帮助', 'help', 'hi', 'hello')):
        await do_write(update, text)
        return
    
    # 其他情况：帮助提示
    await update.message.reply_text("""💡 发送主题直接写文案，例如：
- "noname乐队2026巡演"
- "AI音乐演出趋势"
- "LiveGigs Asia宣传"

或发送修改意见自动修改""")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语音"""
    if not GROQ_KEY:
        await update.message.reply_text("🎤 语音识别未配置")
        return
    
    await update.message.chat.send_action(action="typing")
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    
    text, error = await transcribe_voice(file.file_path)
    if error:
        await update.message.reply_text(f"⚠️ {error}")
        return
    
    await update.message.reply_text(f"🎤 识别：{text}")
    
    # 作为文字处理
    update.message.text = text
    await handle_text(update, context)

def main():
    if not TOKEN:
        logger.error("TOKEN未设置")
        return
    
    logger.info("🎸 ÖNIKA LI 运营助理启动...")
    logger.info(f"🔑 OpenRouter: {'已配置' if OPENROUTER_KEY else '未配置'}")
    logger.info(f"🔑 Groq: {'已配置' if GROQ_KEY else '未配置'}")
    logger.info(f"💾 工作目录: {WORK_DIR}")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("write", write_cmd))
    app.add_handler(CommandHandler("modify", modify_cmd))
    app.add_handler(CommandHandler("save", save_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ 就绪！直接发送主题即可写文案")
    app.run_polling()

if __name__ == '__main__':
    main()
