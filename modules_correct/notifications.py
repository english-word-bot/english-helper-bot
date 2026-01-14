import asyncio
from datetime import datetime, time
from database import db
from modules_correct.achievements import check_achievements, format_achievement_message

class NotificationManager:
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_tasks = []
    
    async def send_achievement_notification(self, user_id, achievement):
        """Отправка уведомления о достижении"""
        try:
            message = await format_achievement_message(achievement)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            
            print(f"✅ Отправлено уведомление о достижении пользователю {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления: {e}")
            return False
    
    async def send_daily_reminder(self, user_id):
        """Ежедневное напоминание"""
        try:
            # Получаем статистику пользователя
            word_count = db.get_word_count(user_id)
            achievements = db.get_achievements(user_id)
            completed = len([a for a in achievements if a['is_completed']])
            
            # Получаем лимиты
            from modules_correct.limits import get_todays_limits
            limits = get_todays_limits(user_id)
            
            message = f"""
🌅 <b>ДОБРОЕ УТРО!</b>

📊 <b>Ваша статистика:</b>
• Слов в словаре: {word_count}
• Достижений: {completed}
• Уровень: 🆓 Бесплатный

🎯 <b>Цели на сегодня:</b>
• Добавить 3 новых слова (0/3)
• Сделать 5 поисков (0/5)
• Повторить 5 старых слов (0/5)

📈 <b>Лимиты сегодня:</b>
🔍 Поисков: {limits['search']['remaining']}/{limits['search']['max']}
✍️ Генераций: {limits['generate']['remaining']}/{limits['generate']['max']}
✨ Исправлений: {limits['fix']['remaining']}/{limits['fix']['max']}

💡 <b>Совет дня:</b>
Сохраняйте слова с примерами — так они лучше запоминаются!

📖 <b>Продолжайте учиться!</b>
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            
            print(f"✅ Отправлено ежедневное напоминание пользователю {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания: {e}")
            return False
    
    async def send_evening_summary(self, user_id):
        """Вечерняя сводка"""
        try:
            # Получаем активность за день
            # (можно добавить отслеживание в будущем)
            
            message = f"""
🌙 <b>ВЕЧЕРНЯЯ СВОДКА</b>

📅 <b>Сегодня вы:</b>
• Добавили 0 новых слов
• Сделали 0 поисков
• Повторили 0 слов

🏆 <b>Прогресс:</b>
До следующего уровня: 3 достижения

🎯 <b>Цели на завтра:</b>
1. Добавить хотя бы 2 новых слова
2. Повторить 3 старых слова
3. Использовать генератор предложений

💤 <b>Спокойной ночи и хорошего отдыха!</b>
Завтра новые слова ждут вас!
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            
            print(f"✅ Отправлена вечерняя сводка пользователю {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки сводки: {e}")
            return False
    
    async def check_and_notify_achievements(self, user_id, action_type, count=1):
        """Проверка и отправка уведомлений о достижениях"""
        new_achievements = await check_achievements(user_id, action_type, count)
        
        for achievement in new_achievements:
            await self.send_achievement_notification(user_id, achievement)
        
        return len(new_achievements)
    
    async def schedule_daily_notifications(self):
        """Планирование ежедневных уведомлений"""
        # Пока просто заглушка
        # В будущем можно добавить реальное планирование через asyncio.sleep
        print("⏰ Менеджер уведомлений инициализирован")
    
    async def send_word_reminder(self, user_id, words):
        """Напоминание о повторении слов"""
        if not words:
            return
        
        message = f"""
🔄 <b>ПОВТОРЕНИЕ СЛОВ</b>

💡 <b>Слова для повторения сегодня:</b>
"""
        
        for i, word in enumerate(words[:5], 1):
            message += f"{i}. <b>{word['word']}</b> - {word['translation'][:30]}...\n"
        
        message += "\n📚 Повторяйте слова регулярно для лучшего запоминания!"
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML"
            )
            print(f"✅ Отправлено напоминание о словах пользователю {user_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания о словах: {e}")

# Тестирование
async def test_notifications():
    """Тестирование системы уведомлений"""
    print("🧪 Тестируем систему уведомлений...")
    
    # Тестовый бот (заглушка)
    class TestBot:
        async def send_message(self, **kwargs):
            print(f"📨 Отправлено сообщение: {kwargs.get('text', '')[:50]}...")
            return True
    
    bot = TestBot()
    manager = NotificationManager(bot)
    
    # Тест уведомлений
    print("\n1. Тестируем уведомление о достижении...")
    test_achievement = {
        'id': 'novice',
        'name': 'Новичок',
        'description': 'Первый поиск слова',
        'reward': {'extra_searches': 5}
    }
    await manager.send_achievement_notification(123456, test_achievement)
    
    print("\n2. Тестируем ежедневное напоминание...")
    await manager.send_daily_reminder(123456)
    
    print("\n3. Тестируем вечернюю сводку...")
    await manager.send_evening_summary(123456)
    
    print("\n✅ Система уведомлений готова!")

if __name__ == "__main__":
    asyncio.run(test_notifications())
