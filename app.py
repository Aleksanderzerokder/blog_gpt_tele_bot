import os
import requests
import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Инициализация FastAPI-приложения
app = FastAPI(title="Blog Post Generator", description="Генерация статей на основе свежих новостей", version="1.0")

# Установка API ключей из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
currentsapi_key = os.getenv("CURRENTS_API_KEY")

# Проверка наличия ключей при старте приложения
if not openai.api_key or not currentsapi_key:
    raise ValueError("Оба API ключа (OPENAI_API_KEY и CURRENTS_API_KEY) должны быть заданы в переменных окружения.")

# Модель входных данных — тема статьи
class Topic(BaseModel):
    topic: str

# Функция получения новостей с Currents API
def get_recent_news(topic: str) -> str:
    url = "https://api.currentsapi.services/v1/latest-news"
    params = {
        "language": "en",
        "keywords": topic,
        "apiKey": currentsapi_key
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ошибка Currents API: {response.text}")

    news_data = response.json().get("news", [])
    if not news_data:
        return "No recent news found."

    # Возвращаем первые 5 заголовков новостей
    return "\n".join([f"- {article['title']}" for article in news_data[:5]])

# Основная функция генерации статьи
def generate_content(topic: str) -> dict:
    recent_news = get_recent_news(topic)

    try:
        # Генерация заголовка
        title_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Сформулируй привлекательный заголовок статьи по теме '{topic}', с учётом новостей:\n{recent_news}"
            }],
            max_tokens=60,
            temperature=0.5
        )
        title = title_response.choices[0].message.content.strip()

        # Генерация мета-описания
        meta_description_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Напиши мета-описание статьи с заголовком: '{title}'. Описание должно быть кратким, информативным и включать ключевые слова."
            }],
            max_tokens=120,
            temperature=0.5
        )
        meta_description = meta_description_response.choices[0].message.content.strip()

        # Генерация основного текста статьи
        post_content_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Напиши статью по теме '{topic}', опираясь на последние новости:\n{recent_news}.
                Требования:
                1. Не менее 1500 символов
                2. Вступление, основная часть, заключение
                3. Структура с подзаголовками
                4. Анализ текущих трендов
                5. Примеры из новостей
                6. Ясный и доступный стиль
                """
            }],
            max_tokens=1500,
            temperature=0.5,
            presence_penalty=0.6,
            frequency_penalty=0.6
        )
        post_content = post_content_response.choices[0].message.content.strip()

        # Возвращаем итог
        return {
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации контента: {str(e)}")

# Эндпоинт генерации статьи
@app.post("/generate-post", summary="Генерация статьи по теме")
async def generate_post(topic: Topic):
    return generate_content(topic.topic)

# Эндпоинт проверки работоспособности
@app.get("/", summary="Корневой эндпоинт")
async def root():
    return {"message": "Сервис генерации работает."}

# Эндпоинт heartbeat для мониторинга
@app.get("/heartbeat", summary="Проверка состояния сервиса")
async def heartbeat():
    return {"status": "OK"}

# Точка входа при запуске через `python app.py`
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
