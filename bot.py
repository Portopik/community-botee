import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
TOKEN = "8533919423:AAEmkagykEzeRorF-MzkQSIrrITwcpQRtP8"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН ОТ @BotFather

# Ссылки
RULES_LINK = "https://t.me/+-yBQzgebofs2MWUy"
CHAT_LINK = "https://t.me/+xvWIFeupCAtkZDgy"

# Ранги (10 ранга нет для обычных пользователей)
RANKS = [
    {"symbol": "?", "name": "Луркер 🕶️", "xp": 0},
    {"symbol": "??", "name": "Ньюфаг 🐣", "xp": 50},
    {"symbol": "???", "name": "Контактёр 📡", "xp": 150},
    {"symbol": "????", "name": "Мемолог 🎭", "xp": 300},
    {"symbol": "?????", "name": "Гуру 🧠", "xp": 500},
    {"symbol": "??????", "name": "Криэйтор ✨", "xp": 800},
    {"symbol": "???????", "name": "Модератор ⚖️", "xp": 1200},
    {"symbol": "????????", "name": "Интегратор 🔗", "xp": 1700},
    {"symbol": "?????????", "name": "Легенда 🏆", "xp": 2300}
    # 10 ранг (?????????? — ОГ (Original G) 👑) только для разработчика
]

# Конфигурация заданий (без заданий для 10 ранга)
QUESTS = {
    # Для рангов 1-3 (0-299 XP)
    "rank_1_3": [
        {
            "id": "chat_top3",
            "name": "Общительный 💬",
            "description": "Занять ТОП-3 по сообщениям за день",
            "type": "chat_top",
            "goal": 3,
            "reward_xp": 30,
            "reward_bonus": 10,
            "icon": "💬"
        },
        {
            "id": "heart_giver",
            "name": "Оценщик ❤️",
            "description": "Отправить 3 реакции ❤️ другим пользователям",
            "type": "hearts_given",
            "goal": 3,
            "reward_xp": 25,
            "reward_bonus": 8,
            "icon": "❤️"
        },
        {
            "id": "good_behavior",
            "name": "Послушатель 😇",
            "description": "Не получать наказаний целый день",
            "type": "no_punishments",
            "goal": 1,
            "reward_xp": 20,
            "reward_bonus": 5,
            "icon": "😇"
        }
    ],
    
    # Для рангов 4-7 (300-1199 XP)
    "rank_4_7": [
        {
            "id": "like_giver",
            "name": "Добряк 👍",
            "description": "Отправить 1 реакцию 👍 пользователю",
            "type": "likes_given",
            "goal": 1,
            "reward_xp": 40,
            "reward_bonus": 15,
            "icon": "👍"
        },
        {
            "id": "warn_giver",
            "name": "Надзиратель ⚠️",
            "description": "Выдать варн за нарушение правил",
            "type": "warns_given",
            "goal": 1,
            "reward_xp": 50,
            "reward_bonus": 20,
            "icon": "⚠️"
        }
    ],
    
    # Для рангов 7-9 (1200-2300 XP)
    "rank_7_9": [
        {
            "id": "nerd_giver",
            "name": "Мудрец 🤓",
            "description": "Отправить реакцию 🤓 пользователю",
            "type": "nerds_given",
            "goal": 1,
            "reward_xp": 60,
            "reward_bonus": 25,
            "icon": "🤓"
        },
        {
            "id": "content_creator",
            "name": "Контент-мейкер 🎨",
            "description": "Создать полезный контент для сообщества",
            "type": "content_created",
            "goal": 1,
            "reward_xp": 70,
            "reward_bonus": 30,
            "icon": "🎨"
        },
        {
            "id": "community_leader",
            "name": "Лидер сообщества 👑",
            "description": "Провести мини-ивент или активность",
            "type": "event_hosted",
            "goal": 1,
            "reward_xp": 80,
            "reward_bonus": 35,
            "icon": "👑"
        }
    ]
}

# Данные
users = {}
sticker_tracker = {}

# ========== ФУНКЦИИ СОХРАНЕНИЯ ==========
def save_data():
    """Сохранить данные в файл"""
    data = {"users": users}
    with open("bot_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    """Загрузить данные из файла"""
    global users
    if os.path.exists("bot_data.json"):
        try:
            with open("bot_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                users = data.get("users", {})
        except:
            users = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_rank_info(xp):
    """Получить информацию о ранге по XP"""
    for rank in reversed(RANKS):
        if xp >= rank["xp"]:
            return rank["symbol"], rank["name"]
    return RANKS[0]["symbol"], RANKS[0]["name"]

def init_user_quests():
    """Инициализировать квесты для нового пользователя"""
    return {
        "daily_progress": {
            "hearts_given": 0,
            "likes_given": 0,
            "nerds_given": 0,
            "warns_given": 0,
            "punishments_received": 0,
            "content_created": 0,
            "event_hosted": 0,
            "messages_today": 0
        },
        "completed_today": [],
        "completed_total": [],
        "last_reset": datetime.now().isoformat(),
        "bonus_points": 0,
        "total_xp_from_quests": 0
    }

def get_available_quests(xp):
    """Получить доступные квесты для ранга"""
    if xp < 300:  # Ранги 1-3
        return QUESTS["rank_1_3"]
    elif xp < 1200:  # Ранги 4-7
        return QUESTS["rank_4_7"]
    else:  # Ранги 7-9 (максимум для обычных пользователей)
        return QUESTS["rank_7_9"]

def check_daily_reset(user_quests):
    """Проверить и сбросить ежедневные задания"""
    if "last_reset" not in user_quests:
        return user_quests
    
    last_reset = datetime.fromisoformat(user_quests["last_reset"])
    now = datetime.now()
    
    # Если прошло больше дня
    if (now - last_reset).days >= 1:
        user_quests["daily_progress"] = {
            "hearts_given": 0,
            "likes_given": 0,
            "nerds_given": 0,
            "warns_given": 0,
            "punishments_received": 0,
            "content_created": 0,
            "event_hosted": 0,
            "messages_today": 0
        }
        user_quests["completed_today"] = []
        user_quests["last_reset"] = now.isoformat()
    
    return user_quests

def update_quest_progress(user_quests, quest_type, amount=1):
    """Обновить прогресс задания"""
    if quest_type in user_quests["daily_progress"]:
        user_quests["daily_progress"][quest_type] += amount
    return user_quests

def check_quest_completion(user_quests, xp):
    """Проверить выполнение заданий"""
    available_quests = get_available_quests(xp)
    rewards = {"xp": 0, "bonus": 0, "completed": []}
    
    for quest in available_quests:
        # Пропускаем уже выполненные сегодня
        if quest["id"] in user_quests.get("completed_today", []):
            continue
        
        progress = user_quests["daily_progress"].get(quest["type"], 0)
        
        # Проверяем выполнение
        if quest["type"] == "no_punishments":
            if user_quests["daily_progress"].get("punishments_received", 0) == 0:
                completed = True
            else:
                completed = False
        else:
            completed = progress >= quest["goal"]
        
        if completed:
            rewards["xp"] += quest["reward_xp"]
            rewards["bonus"] += quest["reward_bonus"]
            rewards["completed"].append(quest["name"])
            
            # Добавляем в выполненные
            if "completed_today" not in user_quests:
                user_quests["completed_today"] = []
            user_quests["completed_today"].append(quest["id"])
            
            # В общий список
            if quest["id"] not in user_quests.get("completed_total", []):
                if "completed_total" not in user_quests:
                    user_quests["completed_total"] = []
                user_quests["completed_total"].append(quest["id"])
    
    # Обновляем бонусные очки
    user_quests["bonus_points"] = user_quests.get("bonus_points", 0) + rewards["bonus"]
    user_quests["total_xp_from_quests"] = user_quests.get("total_xp_from_quests", 0) + rewards["xp"]
    
    return user_quests, rewards

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом"""
    keyboard = [[InlineKeyboardButton("🎯 ПРИСОЕДИНИТЬСЯ", callback_data="join")]]
    
    await update.message.reply_text(
        "Приветствуем вас в боте комьюнити «?»!\n"
        "Нажмите кнопку ниже чтобы официально присоединиться",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка присоединения"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = str(user.id)
    
    if user_id in users:
        await query.edit_message_text("Вы уже в комьюнити! Используйте /profile")
        return
    
    # Создаем нового пользователя
    users[user_id] = {
        "id": user.id,
        "username": user.username or "",
        "first_name": user.first_name,
        "xp": 0,
        "rank_symbol": "?",
        "rank_name": "Луркер 🕶️",
        "joined": datetime.now().isoformat(),
        "last_heart": None,
        "hearts_today": 0,
        "last_like": None,
        "likes_today": 0,
        "last_nerd": None,
        "warns": [],
        "quests": init_user_quests()
    }
    
    save_data()
    
    message = f"""🎉🎉 ПОЗДРАВЛЯЕМ, ВЫ ОФИЦИАЛЬНО ПРИСОЕДИНИЛИСЬ 🎉🎉

🎴 Ваша карточка:
👤 Имя: {user.first_name}
🏷️ Ранг: ? — Луркер 🕶️
⭐ Опыт: 0 XP

Чтобы повысить ранг, присоединяйтесь в чат и изучите правила:
{RULES_LINK}"""
    
    keyboard = [[InlineKeyboardButton("📜 Правила", url=RULES_LINK)]]
    
    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала присоединитесь через /start")
        return
    
    user = users[user_id]
    
    next_rank = None
    for rank in RANKS:
        if rank["xp"] > user["xp"]:
            next_rank = rank
            break
    
    needed_xp = next_rank["xp"] - user["xp"] if next_rank else "МАКСИМУМ ДОСТИГНУТ!"
    
    message = f"""🎴 ВАША КАРТОЧКА:

👤 Имя: {user['first_name']}
🏷️ Ранг: {user['rank_symbol']} — {user['rank_name']}
⭐ Опыт: {user['xp']} XP
📈 До след. ранга: {needed_xp} XP
📅 В комьюнити с: {datetime.fromisoformat(user['joined']).strftime('%d.%m.%Y')}
⚠️ Варнов: {len(user['warns'])}"""
    
    await update.message.reply_text(message)

async def heart_xp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ❤️"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    now = datetime.now()
    
    # Проверка таймера (1 раз в минуту)
    if user["last_heart"]:
        last = datetime.fromisoformat(user["last_heart"])
        if (now - last).seconds < 60:
            time_left = 60 - (now - last).seconds
            await update.message.reply_text(f"⏳ Подождите {time_left} секунд")
            return
    
    # Проверка дневного лимита
    if user["last_heart"] and datetime.fromisoformat(user["last_heart"]).date() == now.date():
        if user.get("hearts_today", 0) >= 10:
            await update.message.reply_text("⚠️ Лимит: 10 ❤️ в день")
            return
    
    # Начисление XP
    user["xp"] += 1
    user["last_heart"] = now.isoformat()
    user["hearts_today"] = user.get("hearts_today", 0) + 1
    
    # Обновляем прогресс задания
    if "quests" in user:
        user["quests"] = update_quest_progress(user["quests"], "hearts_given")
    
    # Проверка повышения ранга
    old_rank = user["rank_name"]
    new_symbol, new_name = get_rank_info(user["xp"])
    
    if old_rank != new_name:
        user["rank_symbol"] = new_symbol
        user["rank_name"] = new_name
        rank_up = True
    else:
        rank_up = False
    
    # Проверяем выполнение заданий
    if "quests" in user:
        user["quests"], rewards = check_quest_completion(user["quests"], user["xp"])
        if rewards["xp"] > 0:
            user["xp"] += rewards["xp"]
    
    save_data()
    
    response = f"❤️ +1 XP!\nВсего XP: {user['xp']}"
    
    if rank_up:
        response = f"🎉 ПОЗДРАВЛЯЕМ! Новый ранг: {new_name}\n" + response
    
    await update.message.reply_text(response)

async def like_xp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка 👍"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    now = datetime.now()
    
    # Проверка ранга (с 3 ранга = 150 XP)
    if user["xp"] < 150:
        await update.message.reply_text("👍 доступно с 3 ранга (150 XP)")
        return
    
    # Проверка таймера (1 раз в 5 минут)
    if user["last_like"]:
        last = datetime.fromisoformat(user["last_like"])
        if (now - last).seconds < 300:
            time_left = 300 - (now - last).seconds
            await update.message.reply_text(f"⏳ Подождите {time_left//60} минут")
            return
    
    # Проверка дневного лимита
    if user["last_like"] and datetime.fromisoformat(user["last_like"]).date() == now.date():
        if user.get("likes_today", 0) >= 2:
            await update.message.reply_text("⚠️ Лимит: 2 👍 в день")
            return
    
    # Начисление XP
    user["xp"] += 5
    user["last_like"] = now.isoformat()
    user["likes_today"] = user.get("likes_today", 0) + 1
    
    # Обновляем прогресс задания
    if "quests" in user:
        user["quests"] = update_quest_progress(user["quests"], "likes_given")
    
    # Проверка повышения ранга
    old_rank = user["rank_name"]
    new_symbol, new_name = get_rank_info(user["xp"])
    
    if old_rank != new_name:
        user["rank_symbol"] = new_symbol
        user["rank_name"] = new_name
        rank_up = True
    else:
        rank_up = False
    
    # Проверяем выполнение заданий
    if "quests" in user:
        user["quests"], rewards = check_quest_completion(user["quests"], user["xp"])
        if rewards["xp"] > 0:
            user["xp"] += rewards["xp"]
    
    save_data()
    
    response = f"👍 +5 XP!\nВсего XP: {user['xp']}"
    
    if rank_up:
        response = f"🎉 ПОЗДРАВЛЯЕМ! Новый ранг: {new_name}\n" + response
    
    await update.message.reply_text(response)

async def nerd_xp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка 🤓"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    now = datetime.now()
    
    # Проверка ранга (с 7 ранга = 1200 XP)
    if user["xp"] < 1200:
        await update.message.reply_text("🤓 доступно с 7 ранга (1200 XP)")
        return
    
    # Проверка дневного лимита
    if user["last_nerd"] and datetime.fromisoformat(user["last_nerd"]).date() == now.date():
        await update.message.reply_text("⚠️ Лимит: 1 🤓 в день")
        return
    
    # Начисление XP
    user["xp"] += 10
    user["last_nerd"] = now.isoformat()
    
    # Обновляем прогресс задания
    if "quests" in user:
        user["quests"] = update_quest_progress(user["quests"], "nerds_given")
    
    # Проверка повышения ранга
    old_rank = user["rank_name"]
    new_symbol, new_name = get_rank_info(user["xp"])
    
    if old_rank != new_name:
        user["rank_symbol"] = new_symbol
        user["rank_name"] = new_name
        rank_up = True
    else:
        rank_up = False
    
    # Проверяем выполнение заданий
    if "quests" in user:
        user["quests"], rewards = check_quest_completion(user["quests"], user["xp"])
        if rewards["xp"] > 0:
            user["xp"] += rewards["xp"]
    
    save_data()
    
    response = f"🤓 +10 XP!\nВсего XP: {user['xp']}"
    
    if rank_up:
        response = f"🎉 ПОЗДРАВЛЯЕМ! Новый ранг: {new_name}\n" + response
    
    await update.message.reply_text(response)

async def quests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать задания"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала присоединитесь через /start")
        return
    
    user = users[user_id]
    user_quests = user.get("quests", {})
    
    # Инициализируем если нет
    if not user_quests:
        user_quests = init_user_quests()
        users[user_id]["quests"] = user_quests
        save_data()
    
    # Проверяем сброс
    user_quests = check_daily_reset(user_quests)
    
    # Получаем доступные задания
    available_quests = get_available_quests(user["xp"])
    
    # Формируем сообщение
    message = "🎯 **ЕЖЕДНЕВНЫЕ ЗАДАНИЯ**\n\n"
    
    # Определяем группу рангов
    if user["xp"] < 300:
        rank_group = "Ранги 1-3"
    elif user["xp"] < 1200:
        rank_group = "Ранги 4-7"
    else:
        rank_group = "Ранги 7-9"
    
    message += f"📊 **Ваша группа:** {rank_group}\n\n"
    
    for quest in available_quests:
        completed = quest["id"] in user_quests.get("completed_today", [])
        progress = user_quests["daily_progress"].get(quest["type"], 0)
        
        if completed:
            message += f"✅ **{quest['icon']} {quest['name']}**\n"
        else:
            if quest["type"] == "no_punishments":
                if user_quests["daily_progress"].get("punishments_received", 0) == 0:
                    status = "✅ Нет наказаний"
                else:
                    status = "❌ Были наказания"
                message += f"⏳ **{quest['icon']} {quest['name']}** - {status}\n"
            else:
                message += f"⏳ **{quest['icon']} {quest['name']}** - {progress}/{quest['goal']}\n"
            
            message += f"   _{quest['description']}_\n"
            message += f"   🎁 **{quest['reward_xp']} XP** + **{quest['reward_bonus']} BP**\n"
    
    # Статистика
    completed_today = len(user_quests.get("completed_today", []))
    bonus_points = user_quests.get("bonus_points", 0)
    
    message += f"\n📊 **Статистика:**\n"
    message += f"✅ Выполнено сегодня: **{completed_today}**\n"
    message += f"💎 Бонусных очков: **{bonus_points}**\n"
    message += f"⭐ Всего XP с заданий: **{user_quests.get('total_xp_from_quests', 0)}**"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def claim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить награды за задания"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала присоединитесь через /start")
        return
    
    user = users[user_id]
    user_quests = user.get("quests", {})
    
    if not user_quests:
        await update.message.reply_text("У вас нет заданий")
        return
    
    # Проверяем выполнение заданий
    user_quests, rewards = check_quest_completion(user_quests, user["xp"])
    
    if rewards["completed"]:
        # Выдаем награды
        user["xp"] += rewards["xp"]
        user["quests"] = user_quests
        
        save_data()
        
        message = "🎉 **НАГРАДЫ ПОЛУЧЕНЫ!**\n\n"
        for quest_name in rewards["completed"]:
            message += f"✅ {quest_name}\n"
        
        message += f"\n📊 **Итого:**\n"
        message += f"⭐ +{rewards['xp']} XP\n"
        message += f"💎 +{rewards['bonus']} BP\n"
        message += f"🏆 Всего XP: {user['xp']}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "📭 Нет выполненных заданий для получения наград\n"
            "Продолжайте выполнять задания из /quests"
        )

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать правила"""
    await update.message.reply_text(
        f"📜 Правила нашего комьюнити:\n\n"
        f"1. Уважайте друг друга\n"
        f"2. Не спамьте\n"
        f"3. Соблюдайте тематику\n"
        f"4. Администрация имеет последнее слово\n\n"
        f"Полные правила: {RULES_LINK}"
    )

async def helpadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Позвать администратора"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    
    # Только для рангов 1-7
    if user["xp"] >= 1200:
        await update.message.reply_text("Вы администратор! Можете помогать другим.")
        return
    
    await update.message.reply_text(
        f"🆘 Ваш запрос отправлен администраторам!\n"
        f"Ожидайте ответа в чате: {CHAT_LINK}"
    )

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мут пользователя"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    
    # Определяем время мута в зависимости от ранга
    if user["xp"] < 300:  # Ранги 1-3
        time_str = "5 минут"
    elif user["xp"] < 1700:  # Ранги 4-7
        time_str = "30 минут"
    else:  # Ранги 8-9
        time_str = "7 дней"
    
    if not context.args:
        await update.message.reply_text(f"Использование: /mute @username причина\nВы можете мутить на: {time_str}")
        return
    
    await update.message.reply_text(f"🔇 Мут выдан на {time_str}")

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдать предупреждение"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    
    # Только с 4 ранга
    if user["xp"] < 300:
        await update.message.reply_text("⚠️ Доступно с 4 ранга (Мемолог)")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /warn @username причина")
        return
    
    await update.message.reply_text("⚠️ Предупреждение выдано")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Бан пользователя"""
    user_id = str(update.effective_user.id)
    
    if user_id not in users:
        await update.message.reply_text("Сначала /start")
        return
    
    user = users[user_id]
    
    # Только с 8 ранга
    if user["xp"] < 1700:
        await update.message.reply_text("🔨 Доступно с 8 ранга (Интегратор)")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /ban @username причина")
        return
    
    await update.message.reply_text("🔨 Бан на 30 дней")

async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ссылка на чат"""
    await update.message.reply_text(
        f"💬 Основной чат комьюнити:\n{CHAT_LINK}\n\n"
        f"📜 Правила:\n{RULES_LINK}"
    )

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка стикеров - антиспам"""
    user_id = str(update.effective_user.id)
    now = datetime.now()
    
    if user_id not in sticker_tracker:
        sticker_tracker[user_id] = {"count": 0, "time": now}
    
    data = sticker_tracker[user_id]
    
    # Если прошла минута, сбрасываем счетчик
    if (now - data["time"]).seconds > 60:
        data["count"] = 1
        data["time"] = now
    else:
        data["count"] += 1
    
    # Если 5 стикеров в минуту - выдать варн
    if data["count"] >= 5 and user_id in users:
        warn_data = {
            "reason": "Спам стикерами (5+ в минуту)",
            "time": now.isoformat(),
            "admin": "SYSTEM"
        }
        
        users[user_id]["warns"].append(warn_data)
        
        # Отмечаем наказание для заданий
        if "quests" in users[user_id]:
            users[user_id]["quests"] = update_quest_progress(users[user_id]["quests"], "punishments_received")
        
        save_data()
        
        await update.message.reply_text(
            f"⚠️ @{update.effective_user.username or 'Пользователь'} "
            f"получил предупреждение за спам стикерами!"
        )
        
        # Сбрасываем счетчик
        data["count"] = 0

# ========== ЗАПУСК БОТА ==========
def main():
    """Основная функция запуска бота"""
    # Загружаем данные
    load_data()
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("quests", quests_cmd))
    app.add_handler(CommandHandler("claim", claim_cmd))
    app.add_handler(CommandHandler("rules", rules_cmd))
    app.add_handler(CommandHandler("chat", chat_cmd))
    app.add_handler(CommandHandler("helpadmin", helpadmin_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    
    # Обработчики реакций (эмодзи)
    app.add_handler(MessageHandler(filters.Regex("❤️"), heart_xp))
    app.add_handler(MessageHandler(filters.Regex("👍"), like_xp))
    app.add_handler(MessageHandler(filters.Regex("🤓"), nerd_xp))
    
    # Обработчик стикеров
    app.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))
    
    # Callback запросы
    app.add_handler(CallbackQueryHandler(join_callback, pattern="^join$"))
    
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()
