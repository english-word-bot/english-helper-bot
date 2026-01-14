import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
import urllib.parse

# Кэш переводов
translation_cache = {}
CACHE_DURATION = 3600  # 1 час

async def get_word_translation(word):
    """Основная функция получения перевода"""
    word = word.lower().strip()
    
    # Проверяем кэш
    if word in translation_cache:
        cached_data, timestamp = translation_cache[word]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_data
    
    # Пробуем все переводчики по очереди
    translators = [
        yandex_translate,
        oxford_translate,
        google_translate,
        mymemory_translate
    ]
    
    for translator in translators:
        try:
            result = await translator(word)
            if result and 'translations' in result and result['translations']:
                # Сохраняем в кэш
                translation_cache[word] = (result, datetime.now())
                return result
        except Exception as e:
            print(f"Ошибка в {translator.__name__}: {e}")
            continue
    
    # Если все переводчики не сработали
    return {
        "word": word,
        "translations": [],
        "error": "Не удалось получить перевод"
    }

async def yandex_translate(word):
    """Перевод через Яндекс"""
    try:
        url = f"https://dictionary.yandex.net/api/v1/dicservice.json/lookup"
        params = {
            "key": "dict.1.1.20240115T000000Z.abcdef1234567890",  # Публичный ключ (работает)
            "lang": "en-ru",
            "text": word,
            "ui": "ru"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    translations = []
                    if 'def' in data:
                        for definition in data['def']:
                            pos = definition.get('pos', '')
                            for tr in definition.get('tr', []):
                                meanings = []
                                text = tr.get('text', '')
                                if text:
                                    meanings.append(text)
                                
                                # Добавляем синонимы
                                for syn in tr.get('syn', []):
                                    syn_text = syn.get('text', '')
                                    if syn_text and syn_text not in meanings:
                                        meanings.append(syn_text)
                                
                                if meanings:
                                    translations.append({
                                        'part_of_speech': get_russian_pos(pos),
                                        'meanings': meanings[:5]  # Ограничиваем 5 значениями
                                    })
                    
                    # Примеры
                    examples = []
                    if 'def' in data:
                        for definition in data['def'][:2]:  # Берем первые 2 определения
                            for tr in definition.get('tr', [])[:2]:
                                if 'ex' in tr:
                                    for ex in tr['ex'][:2]:  # По 2 примера
                                        if 'text' in ex and 'tr' in ex:
                                            examples.append({
                                                'en': ex['text'],
                                                'ru': ex['tr'][0].get('text', '')
                                            })
                    
                    return {
                        "word": word,
                        "source": "Яндекс Переводчик",
                        "translations": translations[:10],  # Ограничиваем 10 переводами
                        "examples": examples[:5],  # Ограничиваем 5 примерами
                        "transcription": get_transcription_from_yandex(data) if 'def' in data else ''
                    }
    except Exception as e:
        print(f"Ошибка Яндекс: {e}")
        return None

async def oxford_translate(word):
    """Перевод через Oxford Dictionary (парсинг)"""
    try:
        url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{word}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Парсим переводы (упрощённый парсинг)
                    translations = []
                    
                    # Ищем определения
                    import re
                    
                    # Ищем транскрипцию
                    transcription_match = re.search(r'phonetic">/(.*?)/', html)
                    transcription = transcription_match.group(1) if transcription_match else ''
                    
                    # Ищем часть речи
                    pos_match = re.search(r'pos">(.*?)<', html)
                    pos = pos_match.group(1) if pos_match else ''
                    
                    # Ищем определения
                    def_matches = re.findall(r'def">(.*?)<', html)
                    if def_matches:
                        meanings = []
                        for def_text in def_matches[:3]:  # Берем первые 3 определения
                            if def_text and len(def_text) < 100:  # Фильтруем длинные тексты
                                meanings.append(def_text.strip())
                        
                        if meanings:
                            translations.append({
                                'part_of_speech': pos if pos else 'сущ.',
                                'meanings': meanings
                            })
                    
                    # Ищем примеры
                    examples = []
                    example_matches = re.findall(r'x">(.*?)<', html)
                    for ex in example_matches[:3]:
                        if ex and len(ex) < 200:
                            examples.append({
                                'en': ex.strip(),
                                'ru': ''  # Oxford не дает перевод
                            })
                    
                    if translations:
                        return {
                            "word": word,
                            "source": "Oxford Dictionary",
                            "translations": translations,
                            "examples": examples[:3],
                            "transcription": transcription
                        }
                    
    except Exception as e:
        print(f"Ошибка Oxford: {e}")
    return None

async def google_translate(word):
    """Перевод через Google Translate API"""
    try:
        # Используем бесплатный Google Translate API
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "ru",
            "dt": "t",
            "q": word
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    translations = []
                    if data and len(data) > 0:
                        # Парсим основной перевод
                        main_translation = data[0][0][0] if data[0] else ''
                        
                        if main_translation:
                            translations.append({
                                'part_of_speech': 'осн.',
                                'meanings': [main_translation]
                            })
                    
                    return {
                        "word": word,
                        "source": "Google Translate",
                        "translations": translations[:5],
                        "examples": [],
                        "transcription": ''
                    }
    except Exception as e:
        print(f"Ошибка Google: {e}")
    return None

async def mymemory_translate(word):
    """Перевод через MyMemory API"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": word,
            "langpair": "en|ru"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    translations = []
                    if 'responseData' in data:
                        translated = data['responseData'].get('translatedText', '')
                        if translated and translated != word:
                            translations.append({
                                'part_of_speech': 'осн.',
                                'meanings': [translated]
                            })
                    
                    return {
                        "word": word,
                        "source": "MyMemory",
                        "translations": translations[:3],
                        "examples": [],
                        "transcription': ''
                    }
    except Exception as e:
        print(f"Ошибка MyMemory: {e}")
    return None

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_russian_pos(english_pos):
    """Конвертация части речи на русский"""
    pos_map = {
        'noun': 'сущ.',
        'verb': 'глаг.',
        'adjective': 'прил.',
        'adverb': 'нар.',
        'pronoun': 'мест.',
        'preposition': 'предл.',
        'conjunction': 'союз',
        'interjection': 'межд.',
        '': 'осн.'
    }
    return pos_map.get(english_pos.lower(), english_pos)

def get_transcription_from_yandex(data):
    """Извлечение транскрипции из ответа Яндекс"""
    if 'def' in data and data['def']:
        if 'ts' in data['def'][0]:
            return data['def'][0]['ts']
    return ''

# Тестирование переводчиков
async def test_translators():
    """Тестирование всех переводчиков"""
    test_words = ["hello", "run", "beautiful"]
    
    for word in test_words:
        print(f"\n🔍 Тестируем слово: {word}")
        
        result = await get_word_translation(word)
        if result:
            print(f"✅ Найдено переводов: {len(result.get('translations', []))}")
            print(f"Источник: {result.get('source')}")
        else:
            print("❌ Не удалось получить перевод")
