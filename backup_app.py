import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import json

# Настройка на логването
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Weather Trend Analysis")

# Добавяне на CORS middleware - Hugging Face Spaces изисква това за правилна работа
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # За Hugging Face Spaces е препоръчително да е "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Изтегляне на ключовете от секретите на Hugging Face Spaces
# Hugging Face Spaces автоматично инжектира секретите като променливи на средата
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY")

# Проверка дали API ключовете са налични
if not WEATHER_API_KEY:
    logger.error("WEATHER_API_KEY не е наличен! Моля, добавете го като секрет в Hugging Face Spaces.")
    
if not HUGGING_FACE_API_KEY:
    logger.error("HUGGING_FACE_API_KEY не е наличен! Моля, добавете го като секрет в Hugging Face Spaces.")

# Модел на Hugging Face за обобщение
HF_MODEL = "facebook/bart-large-cnn"  # Добър модел за обобщения

async def get_weather_data(location="8250 Obzor, Bulgaria", days=1):
    """Извлича данни за времето от WeatherAPI"""
    try:
        weather_url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&days={days}&aqi=no"
        async with httpx.AsyncClient() as client:
            response = await client.get(weather_url)
            
            if response.status_code != 200:
                logger.error(f"Грешка при извличане на данни за времето: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Неуспешно извличане на данни за времето")
            
            return response.json()
    except Exception as e:
        logger.error(f"Грешка при заявка към WeatherAPI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Грешка при заявка към WeatherAPI: {str(e)}")

async def get_trend_from_hugging_face(weather_text):
    """Изпраща данни към Hugging Face и получава обобщение"""
    try:
        headers = {"Authorization": f"Bearer {HUGGING_FACE_API_KEY}"}
        url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        
        # Заявка към Hugging Face API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"inputs": weather_text, "parameters": {"max_length": 100, "min_length": 30}},
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Грешка от Hugging Face API: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Грешка от Hugging Face модела")
            
            result = response.json()
            
            # Ако резултатът е списък (типичен формат на отговор за обобщение)
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("summary_text", "Не можахме да генерираме обобщение.")
            
            return "Не можахме да разпознаем формата на отговора от модела."
    except Exception as e:
        logger.error(f"Грешка при комуникация с Hugging Face: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Грешка при комуникация с Hugging Face: {str(e)}")

def format_weather_data(weather_data):
    """Форматира данните за времето в текст за обработка от езиковия модел"""
    try:
        location = weather_data.get("location", {})
        current = weather_data.get("current", {})
        forecast = weather_data.get("forecast", {}).get("forecastday", [])
        
        location_text = f"Местоположение: {location.get('name', 'Неизвестно')}, {location.get('country', 'Неизвестно')}"
        current_text = f"Текущо време: Температура {current.get('temp_c', 'N/A')}°C, {current.get('condition', {}).get('text', 'Неизвестно')}"
        
        forecast_text = "Прогноза: "
        for day in forecast:
            date = day.get("date", "Неизвестна дата")
            day_data = day.get("day", {})
            forecast_text += f"Дата {date}: Минимална температура {day_data.get('mintemp_c', 'N/A')}°C, "
            forecast_text += f"Максимална температура {day_data.get('maxtemp_c', 'N/A')}°C, "
            forecast_text += f"Условия: {day_data.get('condition', {}).get('text', 'Неизвестно')}. "
        
        return f"{location_text}. {current_text}. {forecast_text} Моля, направи обобщение на тенденцията на времето."
    except Exception as e:
        logger.error(f"Грешка при форматиране на данните за времето: {str(e)}")
        return "Не можахме да форматираме данните за времето."

@app.get("/")
async def root():
    """Начална страница с информация за API"""
    html_content = """
    <html>
        <head>
            <title>Weather Trend Analysis API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .endpoint { background: #f4f4f4; padding: 15px; border-radius: 5px; margin: 15px 0; }
                code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>Weather Trend Analysis API</h1>
            <p>Това API предоставя анализ на тенденциите в метеорологичните данни с помощта на Hugging Face модели.</p>
            
            <div class="endpoint">
                <h2>Крайна точка: /weather-trend</h2>
                <p>Получава прогноза и анализ на тенденциите на времето.</p>
                <p>Параметри на заявката:</p>
                <ul>
                    <li><code>location</code> (опционално): Локация за прогнозата. По подразбиране: 8250 Obzor, Bulgaria</li>
                    <li><code>days</code> (опционално): Брой дни за прогнозата. По подразбиране: 1</li>
                </ul>
                <p>Пример: <a href="/weather-trend?location=Sofia,Bulgaria&days=3">/weather-trend?location=Sofia,Bulgaria&days=3</a></p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/weather-trend")
async def weather_trend(location: str = "8250 Obzor, Bulgaria", days: int = 1):
    """Извлича данни за времето и генерира анализ на тенденциите"""
    try:
        # Проверка на параметрите
        if days < 1 or days > 10:
            raise HTTPException(status_code=400, detail="Броят дни трябва да бъде между 1 и 10")
        
        # Извличаме данните от WeatherAPI
        weather_data = await get_weather_data(location, days)
        
        # Форматираме данните за обработка от езиковия модел
        weather_text = format_weather_data(weather_data)
        
        # Получаваме обобщен тренд от Hugging Face
        trend = await get_trend_from_hugging_face(weather_text)
        
        # Връщаме резултата
        return {
            "location": weather_data.get("location", {}).get("name", "Неизвестно"),
            "current_temp": weather_data.get("current", {}).get("temp_c", "N/A"),
            "current_condition": weather_data.get("current", {}).get("condition", {}).get("text", "Неизвестно"),
            "trend_analysis": trend,
            "days_forecasted": days
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неочаквана грешка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Неочаквана грешка: {str(e)}")

# Проверки на състоянието на приложението
@app.get("/health")
async def health():
    """Проверка на състоянието на API"""
    return {"status": "healthy", "version": "1.0.0"}