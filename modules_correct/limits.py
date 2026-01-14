from datetime import datetime, date
from database import db
from config import FREE_LIMITS, PREMIUM_LIMITS

async def check_and_update_limit(user_id, action_type):
    """
    Проверяет лимит и обновляет счётчик если можно
    
    Возвращает: (can_proceed, used_count)
    """
    # Получаем уровень пользователя
    user_level = get_user_level(user_id)  # 'free' или 'premium'
    
    # Получаем лимиты для уровня
    if user_level == 'premium':
        limits = PREMIUM_LIMITS
    else:
        limits = FREE_LIMITS
    
    # Проверяем лимит
    can_proceed, used = db.check_limit(user_id, action_type)
    
    # Получаем максимальный лимит
    max_limit_key = f"daily_{action_type}s"
    max_limit = limits.get(max_limit_key, 10)
    
    if can_proceed:
        # Увеличиваем счётчик
        db.increment_limit(user_id, action_type)
        used += 1  # Обновляем used после увеличения
    
    return can_proceed, used

def get_user_level(user_id):
    """Определяем уровень пользователя"""
    # Пока все бесплатные, потом добавим проверку премиума
    return 'free'

def get_todays_limits(user_id):
    """Получение всех лимитов на сегодня"""
    user_level = get_user_level(user_id)
    limits = PREMIUM_LIMITS if user_level == 'premium' else FREE_LIMITS
    
    # Получаем использованные лимиты
    used_limits = {
        'search': 0,
        'generate': 0,
        'fix': 0
    }
    
    for action in used_limits.keys():
        can_proceed, used = db.check_limit(user_id, action)
        used_limits[action] = used
    
    # Формируем результат
    result = {}
    for action in ['search', 'generate', 'fix']:
        max_key = f"daily_{action}s"
        max_limit = limits.get(max_key, 10)
        used = used_limits[action]
        
        result[action] = {
            'used': used,
            'max': max_limit,
            'remaining': max(max_limit - used, 0),
            'percentage': (used / max_limit * 100) if max_limit > 0 else 0
        }
    
    return result

def format_limits_message(limits_data):
    """Форматирование сообщения о лимитах"""
    search = limits_data['search']
    generate = limits_data['generate']
    fix = limits_data['fix']
    
    # Прогресс-бары
    def progress_bar(used, total, width=10):
        filled = int((used / total) * width) if total > 0 else 0
        return '▰' * filled + '▱' * (width - filled)
    
    message = f"""
📊 <b>ВАШИ ЛИМИТЫ НА СЕГОДНЯ</b>

🔍 <b>Поиск слов:</b>
{progress_bar(search['used'], search['max'])} {search['used']}/{search['max']}
{get_time_until_reset()} до обновления

✍️ <b>Генерация предложений:</b>
{progress_bar(generate['used'], generate['max'])} {generate['used']}/{generate['max']}

✨ <b>Исправление текстов:</b>
{progress_bar(fix['used'], fix['max'])} {fix['used']}/{fix['max']}

🎯 <b>Советы:</b>
• Используйте лимиты равномерно
• Сохраняйте важные слова в словарь
• Достижения дают бонусные лимиты!

💎 <b>Премиум:</b> Безлимитный доступ ко всему
"""
    
    return message

def get_time_until_reset():
    """Время до обновления лимитов (до 00:00)"""
    now = datetime.now()
    tomorrow = date.today()  # Уже сегодня
    reset_time = datetime.combine(tomorrow, datetime.min.time())
    
    # Если уже после полуночи, считаем до следующей полуночи
    if now.hour >= 0:
        reset_time = datetime.combine(tomorrow.replace(day=tomorrow.day + 1), datetime.min.time())
    
    time_diff = reset_time - now
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds % 3600) // 60
    
    return f"{hours}ч {minutes}м"

async def add_bonus_limits(user_id, bonus_type, amount):
    """Добавление бонусных лимитов за достижения"""
    # Пока просто пропускаем, потом реализуем
    pass

# Тестирование
def test_limits():
    """Тестирование системы лимитов"""
    print("🧪 Тестируем систему лимитов...")
    
    # Тестовый пользователь
    test_user_id = 123456
    
    # Проверяем начальные лимиты
    limits = get_todays_limits(test_user_id)
    print(f"1. Начальные лимиты:")
    print(f"   Поисков: {limits['search']['used']}/{limits['search']['max']}")
    print(f"   Генераций: {limits['generate']['used']}/{limits['generate']['max']}")
    
    # Пробуем использовать лимит
    print("\n2. Используем 3 поиска:")
    for i in range(3):
        can_proceed, used = check_and_update_limit(test_user_id, "search")
        print(f"   Попытка {i+1}: Можно? {can_proceed}, Использовано: {used}")
    
    # Проверяем после использования
    limits = get_todays_limits(test_user_id)
    print(f"\n3. После использования:")
    print(f"   Поисков: {limits['search']['used']}/{limits['search']['max']}")
    
    # Форматированное сообщение
    print(f"\n4. Форматированное сообщение:")
    print(format_limits_message(limits))
    
    print("\n✅ Система лимитов готова!")

if __name__ == "__main__":
    test_limits()
