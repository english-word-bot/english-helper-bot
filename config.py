import os
from dotenv import load_dotenv

load_dotenv()

# ===== ТЕЛЕГРАМ =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMINS = [5762295959]  # Только ваш ID

# ===== API КЛЮЧИ =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# ===== ЛИМИТЫ =====
FREE_LIMITS = {
    "daily_searches": 10,
    "daily_generations": 5,
    "daily_fixes": 3,
    "max_words": 100,
    "max_categories": 3
}

PREMIUM_LIMITS = {
    "daily_searches": 9999,
    "daily_generations": 9999,
    "daily_fixes": 9999,
    "max_words": 5000,
    "max_categories": 999
}

# ===== ДОСТИЖЕНИЯ =====
ACHIEVEMENTS_CONFIG = {
    "novice": {
        "name": "Новичок",
        "description": "Первый поиск слова",
        "reward": {"extra_searches": 5},
        "condition": {"action": "search", "count": 1}
    },
    "collector_10": {
        "name": "Коллекционер",
        "description": "10 слов в словаре",
        "reward": {"extra_searches": 10},
        "condition": {"action": "save_word", "count": 10}
    }
}

# ===== ПЕРЕВОДЧИКИ =====
TRANSLATOR_PRIORITY = ["yandex", "oxford", "google", "mymemory"]
CACHE_DURATION = 3600

# ===== БАЗЫ ДАННЫХ =====
DB_PATH = "data/database.db"
WORD_FORMS_PATH = "data/word_forms.json"
SYNONYMS_PATH = "data/synonyms.json"

print("✅ Конфиг загружен (без ключей в коде)")

# ===== ПУТИ К МОДУЛЯМ =====
# Используем modules_correct вместо modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules_correct'))
