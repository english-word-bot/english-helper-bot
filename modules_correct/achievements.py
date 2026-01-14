import asyncio
from datetime import datetime, timedelta
from database import db
from config import ACHIEVEMENTS_CONFIG

async def check_achievements(user_id, action_type, count=1):
    """Проверка и обновление достижений"""
    updated_achievements = []
    
    for achievement_id, config in ACHIEVEMENTS_CONFIG.items():
        condition = config.get('condition', {})
        
        if condition.get('action') == action_type:
            # Обновляем прогресс
            db.update_achievement_progress(user_id, achievement_id, count)
            
            # Проверяем, выполнено ли достижение
            achievements = db.get_achievements(user_id)
            for ach in achievements:
                if ach['achievement_id'] == achievement_id and ach['is_completed']:
                    # Проверяем, только что выполнено
                    if is_newly_completed(ach):
                        updated_achievements.append({
                            'id': achievement_id,
                            'name': config['name'],
                            'description': config['description'],
                            'reward': config.get('reward', {})
                        })
    
    return updated_achievements

def is_newly_completed(achievement):
    """Проверяем, выполнено ли достижение в последние 5 минут"""
    if not achievement['is_completed']:
        return False
    
    unlocked_at = datetime.fromisoformat(achievement['unlocked_at'].replace('Z', '+00:00'))
    time_diff = datetime.now() - unlocked_at
    
    return time_diff < timedelta(minutes=5)

async def format_achievement_message(achievement):
    """Форматирование сообщения о достижении"""
    name = achievement['name']
    description = achievement['description']
    reward = achievement['reward']
    
    message = f"""
🏆 <b>НОВОЕ ДОСТИЖЕНИЕ!</b>

🎯 <b>{name}</b>
📝 {description}

🎁 <b>Награда:</b>
"""
    
    if 'extra_searches' in reward:
        message += f"🔍 +{reward['extra_searches']} дополнительных поисков\n"
    
    if 'extra_generations' in reward:
        message += f"✍️ +{reward['extra_generations']} дополнительных генераций\n"
    
    message += "\n🎮 Продолжайте в том же духе!"
    
    return message

async def get_user_achievements(user_id):
    """Получение всех достижений пользователя с прогрессом"""
    achievements = db.get_achievements(user_id)
    result = {
        'completed': [],
        'in_progress': [],
        'locked': []
    }
    
    for achievement_id, config in ACHIEVEMENTS_CONFIG.items():
        user_ach = next((a for a in achievements if a['achievement_id'] == achievement_id), None)
        
        achievement_info = {
            'id': achievement_id,
            'name': config['name'],
            'description': config['description'],
            'total': config['condition']['count'],
            'reward': config.get('reward', {})
        }
        
        if user_ach:
            if user_ach['is_completed']:
                achievement_info['current'] = user_ach['progress_total']
                achievement_info['completed_at'] = user_ach['unlocked_at']
                result['completed'].append(achievement_info)
            else:
                achievement_info['current'] = user_ach['progress_current']
                result['in_progress'].append(achievement_info)
        else:
            achievement_info['current'] = 0
            result['locked'].append(achievement_info)
    
    return result

async def calculate_level(user_id):
    """Расчёт уровня пользователя на основе опыта"""
    achievements = db.get_achievements(user_id)
    completed = len([a for a in achievements if a['is_completed']])
    
    # Простая система уровней
    levels = [
        (0, "Новичок", "🎯"),
        (3, "Ученик", "📚"),
        (7, "Специалист", "🎓"),
        (12, "Эксперт", "🏆"),
        (20, "Мастер", "👑"),
        (30, "Гуру", "🌟")
    ]
    
    current_level = "Новичок"
    current_emoji = "🎯"
    next_level_at = 3
    
    for threshold, level_name, emoji in levels:
        if completed >= threshold:
            current_level = level_name
            current_emoji = emoji
        else:
            next_level_at = threshold
            break
    
    progress = completed
    progress_max = next_level_at
    
    return {
        'name': current_level,
        'emoji': current_emoji,
        'progress': progress,
        'progress_max': progress_max,
        'completed_achievements': completed
    }

# Тестирование
async def test_achievements():
    """Тестирование системы достижений"""
    print("🧪 Тестируем систему достижений...")
    
    # Тестовый пользователь
    test_user_id = 123456
    
    # Симулируем действия
    print("1. Первый поиск...")
    new_ach = await check_achievements(test_user_id, "search")
    if new_ach:
        print(f"✅ Разблокировано достижение: {new_ach[0]['name']}")
    
    print("2. Сохранение 10 слов...")
    for i in range(10):
        await check_achievements(test_user_id, "save_word")
    
    new_ach = await check_achievements(test_user_id, "save_word")
    if new_ach:
        print(f"✅ Разблокировано достижение: {new_ach[0]['name']}")
    
    print("\n🎮 Система достижений готова!")

if __name__ == "__main__":
    asyncio.run(test_achievements())
