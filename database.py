import sqlite3
import json
import os
from datetime import datetime, date
from config import DB_PATH, WORD_FORMS_PATH, SYNONYMS_PATH

def init_database():
    """Инициализация базы данных"""
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        level TEXT DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active DATE DEFAULT CURRENT_DATE
    )
    ''')
    
    # Лимиты пользователя
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_limits (
        user_id INTEGER,
        date DATE DEFAULT CURRENT_DATE,
        searches_used INTEGER DEFAULT 0,
        generations_used INTEGER DEFAULT 0,
        fixes_used INTEGER DEFAULT 0,
        words_added INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    ''')
    
    # Личный словарь
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_dictionary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        word TEXT NOT NULL,
        translation TEXT,
        example TEXT,
        category TEXT DEFAULT 'Без категории',
        added_date DATE DEFAULT CURRENT_DATE,
        review_count INTEGER DEFAULT 0,
        last_reviewed DATE,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Категории пользователя
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_categories (
        user_id INTEGER,
        category_name TEXT NOT NULL,
        color TEXT DEFAULT '#3498db',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, category_name),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Достижения
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id TEXT NOT NULL,
        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        progress_current INTEGER DEFAULT 0,
        progress_total INTEGER DEFAULT 1,
        is_completed BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (user_id, achievement_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # История действий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action_type TEXT,
        data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    def add_user(self, user_id, username):
        """Добавление нового пользователя"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username) 
                VALUES (?, ?)
            ''', (user_id, username))
            self.conn.commit()
            
            # Создаём запись в лимитах
            self.cursor.execute('''
                INSERT OR IGNORE INTO user_limits (user_id, date) 
                VALUES (?, DATE('now'))
            ''', (user_id,))
            self.conn.commit()
            
            # Создаём категорию "Без категории"
            self.cursor.execute('''
                INSERT OR IGNORE INTO user_categories (user_id, category_name) 
                VALUES (?, ?)
            ''', (user_id, "Без категории"))
            self.conn.commit()
            
            return True
        except Exception as e:
            print(f"Ошибка добавления пользователя: {e}")
            return False
    
    def update_user_activity(self, user_id):
        """Обновление активности пользователя"""
        self.cursor.execute('''
            UPDATE users SET last_active = DATE('now') 
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()
    
    # ===== ЛИМИТЫ =====
    def check_limit(self, user_id, limit_type):
        """Проверка лимита"""
        from config import FREE_LIMITS
        
        self.cursor.execute('''
            SELECT searches_used, generations_used, fixes_used 
            FROM user_limits 
            WHERE user_id = ? AND date = DATE('now')
        ''', (user_id,))
        
        result = self.cursor.fetchone()
        if not result:
            return True, 0
        
        limits = {
            'search': result['searches_used'],
            'generate': result['generations_used'],
            'fix': result['fixes_used']
        }
        
        used = limits.get(limit_type, 0)
        allowed = FREE_LIMITS.get(f"daily_{limit_type}s", 10)
        
        return used < allowed, used
    
    def increment_limit(self, user_id, limit_type):
        """Увеличение счётчика лимита"""
        column = f"{limit_type}s_used"
        
        self.cursor.execute(f'''
            INSERT INTO user_limits (user_id, date, {column})
            VALUES (?, DATE('now'), 1)
            ON CONFLICT(user_id, date) DO UPDATE SET
            {column} = {column} + 1
        ''', (user_id,))
        self.conn.commit()
    
    # ===== СЛОВАРЬ =====
    def add_word(self, user_id, word, translation, example=None, category="Без категории"):
        """Добавление слова в словарь"""
        try:
            self.cursor.execute('''
                INSERT INTO user_dictionary 
                (user_id, word, translation, example, category)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, word, translation, example, category))
            self.conn.commit()
            
            # Обновляем счётчик добавленных слов за день
            self.cursor.execute('''
                UPDATE user_limits 
                SET words_added = words_added + 1 
                WHERE user_id = ? AND date = DATE('now')
            ''', (user_id,))
            self.conn.commit()
            
            return True
        except Exception as e:
            print(f"Ошибка добавления слова: {e}")
            return False
    
    def get_user_words(self, user_id, category=None):
        """Получение слов пользователя"""
        if category:
            self.cursor.execute('''
                SELECT * FROM user_dictionary 
                WHERE user_id = ? AND category = ?
                ORDER BY added_date DESC
            ''', (user_id, category))
        else:
            self.cursor.execute('''
                SELECT * FROM user_dictionary 
                WHERE user_id = ? 
                ORDER BY added_date DESC
            ''', (user_id,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_word_count(self, user_id):
        """Количество слов в словаре"""
        self.cursor.execute('''
            SELECT COUNT(*) as count FROM user_dictionary 
            WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()['count']
    
    # ===== КАТЕГОРИИ =====
    def add_category(self, user_id, category_name, color="#3498db"):
        """Добавление категории"""
        try:
            self.cursor.execute('''
                INSERT INTO user_categories (user_id, category_name, color)
                VALUES (?, ?, ?)
            ''', (user_id, category_name, color))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Категория уже существует
    
    def get_categories(self, user_id):
        """Получение категорий пользователя"""
        self.cursor.execute('''
            SELECT category_name, color FROM user_categories 
            WHERE user_id = ?
        ''', (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def update_word_category(self, word_id, new_category):
        """Изменение категории слова"""
        self.cursor.execute('''
            UPDATE user_dictionary 
            SET category = ? 
            WHERE id = ?
        ''', (new_category, word_id))
        self.conn.commit()
    
    # ===== ДОСТИЖЕНИЯ =====
    def update_achievement_progress(self, user_id, achievement_id, progress=1):
        """Обновление прогресса достижения"""
        self.cursor.execute('''
            INSERT INTO achievements (user_id, achievement_id, progress_current)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, achievement_id) DO UPDATE SET
            progress_current = progress_current + ?,
            unlocked_at = CASE 
                WHEN progress_current + ? >= (SELECT progress_total FROM achievements WHERE user_id = ? AND achievement_id = ?)
                THEN CURRENT_TIMESTAMP
                ELSE unlocked_at
            END,
            is_completed = CASE 
                WHEN progress_current + ? >= (SELECT progress_total FROM achievements WHERE user_id = ? AND achievement_id = ?)
                THEN TRUE
                ELSE FALSE
            END
        ''', (user_id, achievement_id, progress, progress, progress, user_id, achievement_id, progress, user_id, achievement_id))
        self.conn.commit()
    
    def get_achievements(self, user_id):
        """Получение достижений пользователя"""
        self.cursor.execute('''
            SELECT * FROM achievements 
            WHERE user_id = ?
        ''', (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    # ===== ЛОКАЛЬНЫЕ БАЗЫ (формы слов, синонимы) =====
    def load_word_forms(self):
        """Загрузка форм слов из JSON"""
        if os.path.exists(WORD_FORMS_PATH):
            with open(WORD_FORMS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def load_synonyms(self):
        """Загрузка синонимов из JSON"""
        if os.path.exists(SYNONYMS_PATH):
            with open(SYNONYMS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def close(self):
        """Закрытие соединения"""
        self.conn.close()

# Инициализация при импорте
init_database()

# Глобальный экземпляр для использования
db = Database()
