import aiohttp
import json
from config import OPENROUTER_API_KEY

async def generate_sentences(words, theme=None, style="natural"):
    """Генерация предложений через OpenRouter API"""
    
    # Подготовка промпта
    words_text = ", ".join(words) if isinstance(words, list) else words
    
    prompt = f"""Generate 3-4 natural English sentences using these words: {words_text}"""
    
    if theme:
        prompt += f"\nTheme: {theme}"
    
    if style == "business":
        prompt += "\nMake the sentences professional and business-appropriate."
    elif style == "casual":
        prompt += "\nMake the sentences casual and conversational."
    elif style == "academic":
        prompt += "\nMake the sentences formal and academic."
    
    prompt += "\n\nProvide ONLY the sentences in English, each on a new line, without numbers or explanations."
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://english-bot.com",  # Замените на ваш домен
                "X-Title": "English Word Bot"
            }
            
            payload = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an English language expert. Generate natural, grammatically correct English sentences."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        
                        # Парсим предложения
                        sentences = parse_sentences(content)
                        
                        return {
                            "success": True,
                            "sentences": sentences[:4],  # Ограничиваем 4 предложениями
                            "words_used": words if isinstance(words, list) else [words],
                            "theme": theme,
                            "style": style
                        }
                    else:
                        return {
                            "success": False,
                            "error": "No response from AI",
                            "fallback": generate_fallback_sentences(words, theme)
                        }
                else:
                    error_text = await response.text()
                    print(f"OpenRouter error: {response.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status}",
                        "fallback": generate_fallback_sentences(words, theme)
                    }
                    
    except Exception as e:
        print(f"Error in generator: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback": generate_fallback_sentences(words, theme)
        }

def parse_sentences(text):
    """Парсинг предложений из текста"""
    sentences = []
    
    # Разделяем по переводам строк и точкам
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Удаляем номера (1., 2., etc)
        if line and line[0].isdigit() and (line[1] == '.' or line[1] == ')' or line[2] == '.'):
            line = line[line.find('.')+1:].strip() if '.' in line else line[2:].strip()
        
        # Проверяем, что это предложение (начинается с заглавной, заканчивается точкой)
        if line and len(line) > 10 and line[0].isupper() and (line.endswith('.') or line.endswith('!') or line.endswith('?')):
            sentences.append(line)
    
    # Если не нашли нормальные предложения, возвращаем строки как есть
    if not sentences:
        sentences = [line for line in lines if line and len(line) > 5]
    
    return sentences[:4]  # Ограничиваем 4 предложениями

def generate_fallback_sentences(words, theme=None):
    """Резервные шаблонные предложения"""
    
    if isinstance(words, str):
        word_list = [words]
    else:
        word_list = words
    
    sentences = []
    
    # Простые шаблоны
    templates = [
        f"I often use the word '{word_list[0]}' in my daily conversations.",
        f"The word '{word_list[0]}' has an interesting meaning in English.",
        f"You can find '{word_list[0]}' in many English books and articles.",
        f"Learning the word '{word_list[0]}' will help you improve your vocabulary."
    ]
    
    if len(word_list) > 1:
        templates.extend([
            f"I like to use both '{word_list[0]}' and '{word_list[1]}' in my writing.",
            f"The words '{word_list[0]}' and '{word_list[1]}' often appear together.",
            f"You can create interesting sentences with '{word_list[0]}' and '{word_list[1]}'."
        ])
    
    if theme:
        if "business" in theme.lower():
            sentences = [
                f"In business communications, the word '{word_list[0]}' is frequently used.",
                f"Professional emails often include the term '{word_list[0]}'.",
                f"The vocabulary word '{word_list[0]}' is essential for corporate environments."
            ]
        elif "travel" in theme.lower():
            sentences = [
                f"When traveling, you might need the word '{word_list[0]}' at the airport.",
                f"'{word_list[0]}' is a useful word for tourists and travelers.",
                f"Guidebooks often mention the word '{word_list[0]}' for travelers."
            ]
        elif "academic" in theme.lower():
            sentences = [
                f"Academic papers frequently use the term '{word_list[0]}'.",
                f"Students should learn the word '{word_list[0]}' for their studies.",
                f"The vocabulary word '{word_list[0]}' appears in many textbooks."
            ]
        else:
            sentences = templates[:3]
    else:
        sentences = templates[:3]
    
    return sentences

async def test_generator():
    """Тестирование генератора"""
    print("🧪 Тестируем генератор предложений...")
    
    # Тест 1: Одно слово
    result = await generate_sentences("beautiful")
    if result["success"]:
        print(f"✅ Тест 1 (одно слово): Успешно")
        for i, sentence in enumerate(result["sentences"], 1):
            print(f"  {i}. {sentence}")
    else:
        print(f"❌ Тест 1: Ошибка - {result.get('error')}")
        print("  Резервные предложения:")
        for sentence in result.get("fallback", []):
            print(f"  - {sentence}")
    
    # Тест 2: Несколько слов с темой
    result = await generate_sentences(["cat", "sunny", "window"], "home and nature")
    if result["success"]:
        print(f"\n✅ Тест 2 (несколько слов с темой): Успешно")
        for i, sentence in enumerate(result["sentences"], 1):
            print(f"  {i}. {sentence}")
    
    print("\n🎯 Генератор готов к работе!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_generator())
