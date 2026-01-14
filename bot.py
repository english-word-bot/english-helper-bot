import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMINS
from database import db
from modules.translators import get_word_translation
from modules.generator import generate_sentences
from modules.achievements import check_achievements
from modules.limits import check_and_update_limit

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния FSM
class DictionaryState(StatesGroup):
    waiting_for_word = State()
    waiting_for_translation = State()
    waiting_for_example = State()
    waiting_for_category = State()
    waiting_for_custom_category = State()

class GeneratorState(StatesGroup):
    waiting_for_words = State()
    waiting_for_theme = State()
    waiting_for_format = State()

# ===== КЛАВИАТУРЫ =====
def main_menu_keyboard():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск слова")],
            [KeyboardButton(text="✍️ Генератор"), KeyboardButton(text="📖 Мой словарь")],
            [KeyboardButton(text="📝 Шпаргалки"), KeyboardButton(text="🔄 Синонимы")],
            [KeyboardButton(text="✨ Помощь"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="💎 Премиум")]
        ],
        resize_keyboard=True
    )
    return keyboard

def back_to_menu_keyboard():
    """Кнопка возврата в меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="↩️ В главное меню")]],
        resize_keyboard=True
    )
    return keyboard

def translation_actions_keyboard(word_data):
    """Действия после перевода"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Сохранить в словарь", callback_data=f"save_{word_data['word']}")],
            [InlineKeyboardButton(text="✨ Примеры от ИИ", callback_data=f"examples_{word_data['word']}")],
            [InlineKeyboardButton(text="📝 Формы слова", callback_data=f"forms_{word_data['word']}")],
            [InlineKeyboardButton(text="🔄 Синонимы", callback_data=f"synonyms_{word_data['word']}")]
        ]
    )
    return keyboard

# ===== КОМАНДЫ =====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Добавляем пользователя в БД
    db.add_user(user_id, username)
    
    # Проверяем достижения
    await check_achievements(user_id, "daily_login")
    
    welcome_text = f"""
👋 Привет, {username}!

📚 Добро пожаловать в <b>English Word Master</b> — твой личный помощник для изучения английского!

🎯 <b>Основные функции:</b>
• 🔍 Перевод слов с 4 источниками
• ✍️ Генератор предложений с ИИ
• 📖 Личный словарь с категориями
• 📝 Шпаргалки с формами слов
• 🎮 Система достижений и уровней

📊 <b>Ваш статус:</b> 🆓 БЕСПЛАТНЫЙ уровень
🔍 Поисков сегодня: {await get_limit_info(user_id, 'search')}
✍️ Генераций сегодня: {await get_limit_info(user_id, 'generate')}
✨ Исправлений сегодня: {await get_limit_info(user_id, 'fix')}

👇 Выберите действие:
    """
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
📚 <b>Справка по командам:</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка
/stats - Ваша статистика
/words - Ваш словарь
/limits - Ваши лимиты

<b>Быстрые действия:</b>
Просто введите английское слово для перевода!
Или используйте кнопки меню.

<b>Лимиты (бесплатный уровень):</b>
🔍 10 поисков слов в день
✍️ 5 генераций предложений
✨ 3 исправления текста
📖 100 слов в словаре

<b>Поддержка:</b>
По вопросам и предложениям: @ваш_ник
    """
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика пользователя"""
    user_id = message.from_user.id
    
    # Получаем данные из БД
    word_count = db.get_word_count(user_id)
    achievements = db.get_achievements(user_id)
    completed = len([a for a in achievements if a['is_completed']])
    
    stats_text = f"""
📊 <b>ВАША СТАТИСТИКА</b>

🎯 <b>Основное:</b>
• Слов в словаре: {word_count}
• Достижений: {completed}/{len(achievements)}
• Уровень: 🆓 Бесплатный

📈 <b>Сегодня:</b>
🔍 Поисков: {await get_limit_info(user_id, 'search', True)}
✍️ Генераций: {await get_limit_info(user_id, 'generate', True)}
✨ Исправлений: {await get_limit_info(user_id, 'fix', True)}

🏆 <b>Ближайшие цели:</b>
• 10 слов в словаре ({word_count}/10)
• 50 поисков (следующее достижение)
• Неделя с ботом
    """
    
    await message.answer(stats_text, parse_mode="HTML")

# ===== ОБРАБОТКА ТЕКСТА (поиск слова) =====
@dp.message(F.text == "🔍 Поиск слова")
async def search_word_handler(message: Message):
    """Обработчик поиска слова"""
    await message.answer(
        "🔍 <b>Введите английское слово для перевода:</b>\n\n"
        "Пример: <code>run</code> или <code>beautiful</code>",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard()
    )

@dp.message(F.text == "✍️ Генератор")
async def generator_handler(message: Message):
    """Обработчик генератора"""
    await message.answer(
        "✍️ <b>Генератор предложений</b>\n\n"
        "Введите слова через запятую (английские):\n"
        "Пример: <code>cat, sunny, window</code>",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard()
    )

@dp.message(F.text == "↩️ В главное меню")
async def back_to_menu_handler(message: Message):
    """Возврат в главное меню"""
    await cmd_start(message)

# ===== ОСНОВНАЯ ОБРАБОТКА СЛОВ =====
@dp.message(lambda message: message.text and not message.text.startswith('/') and not message.text in ["🔍 Поиск слова", "✍️ Генератор", "📖 Мой словарь", "📝 Шпаргалки", "🔄 Синонимы", "✨ Помощь", "📊 Статистика", "⚙️ Настройки", "💎 Премиум", "↩️ В главное меню"])
async def handle_word_input(message: Message):
    """Обработка ввода слова для перевода"""
    user_id = message.from_user.id
    word = message.text.strip().lower()
    
    # Проверяем лимит
    can_search, used = await check_and_update_limit(user_id, "search")
    if not can_search:
        await message.answer(
            f"🚫 <b>Лимит исчерпан!</b>\n\n"
            f"Вы использовали {used}/10 поисков сегодня.\n"
            f"Лимит обновится через: <b>{(24 - (used // 10))} часов</b>\n\n"
            f"💎 <b>Премиум</b> даёт безлимитный доступ!",
            parse_mode="HTML"
        )
        return
    
    # Показываем, что идёт поиск
    wait_msg = await message.answer(f"🔍 Ищу перевод слова <b>{word}</b>...", parse_mode="HTML")
    
    try:
        # Получаем перевод
        translation_data = await get_word_translation(word)
        
        if not translation_data or 'error' in translation_data:
            await message.answer(f"⚠️ Не удалось найти перевод для <b>{word}</b>", parse_mode="HTML")
            return
        
        # Форматируем ответ
        response = format_translation_response(translation_data)
        
        # Отправляем результат
        await message.answer(response, parse_mode="HTML", reply_markup=translation_actions_keyboard(translation_data))
        
        # Удаляем сообщение "ищу"
        await wait_msg.delete()
        
        # Проверяем достижения
        await check_achievements(user_id, "search")
        
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        await message.answer("⚠️ Произошла ошибка при поиске перевода. Попробуйте позже.")

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
async def get_limit_info(user_id, limit_type, get_used=False):
    """Получение информации о лимитах"""
    can_search, used = db.check_limit(user_id, limit_type)
    from config import FREE_LIMITS
    
    limit = FREE_LIMITS.get(f"daily_{limit_type}s", 10)
    
    if get_used:
        return f"{used}/{limit}"
    else:
        return f"{limit - used}/{limit}"

def format_translation_response(data):
    """Форматирование ответа с переводом"""
    word = data.get('word', '')
    transcription = data.get('transcription', '')
    translations = data.get('translations', [])
    examples = data.get('examples', [])
    source = data.get('source', 'Неизвестно')
    
    response = f"""
🔍 <b>{word.upper()}</b> {f'[{transcription}]' if transcription else ''}

🎯 <b>ЗНАЧЕНИЯ:</b>
"""
    
    for i, trans in enumerate(translations[:10], 1):  # Ограничиваем 10 значениями
        part_of_speech = trans.get('part_of_speech', '')
        meanings = trans.get('meanings', [])
        if meanings:
            response += f"{i}. <i>{part_of_speech}</i>: {', '.join(meanings[:3])}\n"
    
    if examples:
        response += f"\n💡 <b>ПРИМЕРЫ:</b>\n"
        for i, ex in enumerate(examples[:3], 1):  # Первые 3 примера
            response += f"{i}. {ex.get('en', '')}\n   <i>{ex.get('ru', '')}</i>\n"
    
    response += f"\n🔧 <b>Источник:</b> {source}"
    
    return response

# ===== ЗАПУСК БОТА =====
async def main():
    """Основная функция запуска бота"""
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    from database import init_database
    init_database()
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
