from database import db
from datetime import datetime, timedelta

class DictionaryManager:
    def __init__(self):
        self.db = db
    
    def add_word_to_dictionary(self, user_id, word_data, example=None, category=None):
        """Добавление слова в словарь пользователя"""
        
        # Формируем перевод
        translations = []
        for trans in word_data.get('translations', []):
            pos = trans.get('part_of_speech', '')
            meanings = trans.get('meanings', [])
            if meanings:
                translations.append(f"{pos}: {', '.join(meanings[:2])}")
        
        translation_text = '; '.join(translations) if translations else word_data.get('word', '')
        
        # Если категория не указана, используем "Без категории"
        if not category:
            category = "Без категории"
        
        # Проверяем, существует ли категория
        categories = self.db.get_categories(user_id)
        category_exists = any(cat['category_name'] == category for cat in categories)
        
        if not category_exists and category != "Без категории":
            # Создаём новую категорию
            self.db.add_category(user_id, category)
        
        # Добавляем слово
        success = self.db.add_word(
            user_id=user_id,
            word=word_data.get('word', ''),
            translation=translation_text[:500],  # Ограничиваем длину
            example=example[:300] if example else None,  # Ограничиваем пример
            category=category
        )
        
        return success
    
    def get_user_dictionary_stats(self, user_id):
        """Получение статистики словаря"""
        words = self.db.get_user_words(user_id)
        categories = self.db.get_categories(user_id)
        
        # Статистика по категориям
        category_stats = {}
        for category in categories:
            cat_name = category['category_name']
            cat_words = [w for w in words if w['category'] == cat_name]
            category_stats[cat_name] = {
                'count': len(cat_words),
                'color': category.get('color', '#3498db')
            }
        
        # Общая статистика
        total_words = len(words)
        words_with_examples = len([w for w in words if w.get('example')])
        
        # Слова для повторения (добавлены больше 3 дней назад)
        review_words = []
        for word in words:
            added_date = datetime.strptime(word['added_date'], '%Y-%m-%d') if isinstance(word['added_date'], str) else word['added_date']
            days_since_added = (datetime.now().date() - added_date.date()).days
            
            if days_since_added >= 3 and word['review_count'] < 3:
                review_words.append(word)
        
        return {
            'total_words': total_words,
            'words_with_examples': words_with_examples,
            'categories': category_stats,
            'review_needed': len(review_words),
            'recent_words': words[:5]  # Последние 5 слов
        }
    
    def format_dictionary_for_display(self, user_id, category=None):
        """Форматирование словаря для отображения"""
        words = self.db.get_user_words(user_id, category)
        
        if not words:
            return "📭 Ваш словарь пуст!\n\nДобавьте первое слово через поиск 🔍"
        
        # Группируем по категориям
        if not category:
            categories = {}
            for word in words:
                cat = word['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(word)
            
            # Формируем сообщение
            message = f"📚 <b>ВАШ СЛОВАРЬ</b> ({len(words)} слов)\n\n"
            
            for cat_name, cat_words in categories.items():
                message += f"🏷️ <b>{cat_name}</b> ({len(cat_words)} слов):\n"
                for word in cat_words[:5]:  # Показываем по 5 слов на категорию
                    message += format_word_entry(word)
                if len(cat_words) > 5:
                    message += f"   ... и ещё {len(cat_words) - 5} слов\n"
                message += "\n"
            
            return message
        else:
            # Только одна категория
            message = f"🏷️ <b>КАТЕГОРИЯ: {category}</b> ({len(words)} слов)\n\n"
            for word in words:
                message += format_word_entry(word)
            return message
    
    def get_words_for_review(self, user_id, count=5):
        """Получение слов для повторения"""
        all_words = self.db.get_user_words(user_id)
        
        # Сортируем по приоритету повторения
        review_words = []
        for word in all_words:
            # Рассчитываем "срочность" повторения
            added_date = datetime.strptime(word['added_date'], '%Y-%m-%d') if isinstance(word['added_date'], str) else word['added_date']
            days_since_added = (datetime.now().date() - added_date.date()).days
            review_count = word.get('review_count', 0)
            
            # Алгоритм интервальных повторений (упрощённый)
            if days_since_added >= 3 and review_count < 3:
                priority = days_since_added * (3 - review_count)
                review_words.append((priority, word))
        
        # Сортируем по приоритету
        review_words.sort(key=lambda x: x[0], reverse=True)
        
        return [word for _, word in review_words[:count]]
    
    def mark_word_as_reviewed(self, user_id, word_id):
        """Отметка слова как повторённого"""
        # Обновляем в базе данных
        self.db.cursor.execute('''
            UPDATE user_dictionary 
            SET review_count = review_count + 1, 
                last_reviewed = DATE('now') 
            WHERE id = ? AND user_id = ?
        ''', (word_id, user_id))
        self.db.conn.commit()

def format_word_entry(word):
    """Форматирование записи слова"""
    entry = f"• <b>{word['word']}</b> - {word['translation'][:50]}"
    
    if word.get('example'):
        entry += f"\n   💬 {word['example'][:60]}..."
    
    entry += f"\n   📅 {word['added_date']}\n"
    
    return entry

# Тестирование
def test_dictionary():
    print("🧪 Тестируем менеджер словаря...")
    
    manager = DictionaryManager()
    
    # Тестовые данные
    test_user_id = 123456
    test_word = {
        'word': 'test',
        'translations': [{'part_of_speech': 'сущ.', 'meanings': ['тест', 'проверка']}]
    }
    
    # Добавление слова
    print("1. Добавляем слово...")
    success = manager.add_word_to_dictionary(test_user_id, test_word, "This is a test example.", "Тестовая")
    print(f"   Результат: {'✅ Успешно' if success else '❌ Ошибка'}")
    
    # Статистика
    print("\n2. Получаем статистику...")
    stats = manager.get_user_dictionary_stats(test_user_id)
    print(f"   Всего слов: {stats['total_words']}")
    print(f"   Категорий: {len(stats['categories'])}")
    
    # Форматирование
    print("\n3. Форматируем словарь...")
    formatted = manager.format_dictionary_for_display(test_user_id)
    print(f"   Длина сообщения: {len(formatted)} символов")
    
    print("\n✅ Менеджер словаря готов!")

if __name__ == "__main__":
    test_dictionary()
