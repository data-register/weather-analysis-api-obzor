import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json

# Импортиране на функции от weather_data.py
from weather_data import (
    get_historical_weather,
    get_forecast_weather,
    format_historical_data,
    format_forecast_data
)
from video_analysis import analyze_video_stream

# Настройка на логването
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Weather Trend Analysis")

# Добавяне на CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Изтегляне на ключовете от секретите на Hugging Face Spaces
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Проверка дали API ключовете са налични
if not WEATHER_API_KEY:
    logger.error("WEATHER_API_KEY не е наличен! Моля, добавете го като секрет в Hugging Face Spaces.")
    
if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY не е наличен! Моля, добавете го като секрет в Hugging Face Spaces.")

# Конфигурация на Anthropic модела
ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

async def analyze_weather_trend(historical_data, forecast_data, video_analysis_text):
    """Изпраща данни към Anthropic API за анализ на тренда"""
    try:
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Форматиране на историческите данни
        historical_text = format_historical_data(historical_data)
        
        # Форматиране на прогнозните данни
        forecast_text = format_forecast_data(forecast_data)
        
        # Изграждане на заявката към Claude
        prompt = f"""
        Задача: Ти си метеоролог, който представя кратък и достъпен анализ на времето в стил телевизионна прогноза. Говориш топло и разбираемо за обикновени хора. Анализирай метеорологичните данни за древния Хелиополис (днешен Обзор) — Градът на Слънцето, използвайки комбинация от живо видео, исторически и прогнозни данни.

Текущ кадър от Обзор: {video_analysis_text}

Исторически данни (вчера): {historical_text}

Прогнозни данни (днес и утре): {forecast_text}

Моля, напиши в топъл и достъпен тон:
1. Какво време е в момента — като за новините, описвайки как изглежда градът и морето.
2. Как текущите условия влияят на усещането на хората в града.
3. Дали денят е "слънчев" за древния Хелиополис (слънчев ден е такъв, в който Слънцето е видимо и грее поне частично).

Важни аспекти:
• Избягвай технически термини
• Говори топло и вдъхновяващо
• Обръщай внимание на морските условия
• При вятър от изток/североизток - морето е по-неспокойно
• Северозападният вятър успокоява вълнението

Отговорът трябва да е на български език, достъпен и вдъхновяващ. Не използвай встъпителни фрази.
        """
        
        payload = {
            "model": ANTHROPIC_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ANTHROPIC_API_URL, 
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Грешка от Anthropic API: {response.text}")
                return {
                    "тренд": "Не можахме да определим тренда поради технически проблем.",
                    "съвет": "Проверете актуалната прогноза за времето от друг източник."
                }
            
            result = response.json()
            logger.info(f"Отговор от модела: {result}")
            
            # Извличане на съдържанието от отговора на Anthropic
            generated_text = result.get("content", [{}])[0].get("text", "")
            
            # Разделяне на трите секции от отговора
            try:
                lines = [line.strip() for line in generated_text.strip().split('\n') if line.strip()]
                
                analysis = ""
                influence = ""
                sunny_day = ""
                
                for line in lines:
                    line = line.replace("1.", "").replace("2.", "").replace("3.", "").strip()
                    if not analysis and "време" in line.lower():
                        analysis = line
                    elif not influence and "влия" in line.lower():
                        influence = line
                    elif not sunny_day and "слънчев" in line.lower():
                        sunny_day = line
                
                if not analysis:
                    analysis = lines[0] if lines else "Няма наличен анализ на времето"
                if not influence:
                    influence = lines[1] if len(lines) > 1 else "Няма информация за влиянието върху хората"
                if not sunny_day:
                    sunny_day = lines[2] if len(lines) > 2 else "Няма информация за слънчевия ден"
                
            except Exception as e:
                logger.error(f"Грешка при обработка на отговора: {str(e)}")
                analysis = "Времето в момента е променливо"
                influence = "Препоръчваме да следите прогнозата"
                sunny_day = "Няма информация за слънчевия ден"
            
            return {
                "анализ": analysis,
                "влияние": influence,
                "слънчев_ден": sunny_day
            }
    except Exception as e:
        logger.error(f"Грешка при анализ на тренда: {str(e)}")
        return {
            "анализ": "В момента времето в Обзор е променливо. Моля, проверете актуалната прогноза.",
            "влияние": "Препоръчваме да следите метеорологичните условия за промени.",
            "слънчев_ден": "Информацията за слънчевия ден не е налична в момента."
        }

@app.get("/")
async def root():
    """Начална страница с информация за API"""
    html_content = """
    <html>
        <head>
            <title>Weather Trend API</title>
        </head>
        <body>
            <h1>Weather Trend API</h1>
            <p>API за анализ на тенденциите на времето с помощта на Claude AI</p>
            <p>Използвайте <a href="/weather-trend?location=Obzor,Bulgaria">/weather-trend?location=Obzor,Bulgaria</a> за получаване на анализ</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/weather-trend")
async def weather_trend(location: str = "8250 Obzor, Bulgaria"):
    """Анализира тренда на времето на базата на исторически данни, прогнози и видео поток"""
    try:
        # Извличаме исторически данни за предишния ден
        historical_data = await get_historical_weather(location, WEATHER_API_KEY)
        
        # Извличаме прогнозни данни за следващите 2 дни
        forecast_data = await get_forecast_weather(location, 2, WEATHER_API_KEY)

        # Анализираме видео потока
        video_stream_url = "https://restream.obzorweather.com/ad508abf-ee51-4e32-b223-70c463b05587.html"
        video_analysis_text = await analyze_video_stream(video_stream_url)
        
        # Анализираме тренда с Anthropic Claude
        trend_analysis = await analyze_weather_trend(historical_data, forecast_data, video_analysis_text)
        
        # Извличаме основна информация за отговора
        location_info = forecast_data.get("location", {})
        current_info = forecast_data.get("current", {})
        
        # Връщаме резултата
        return {
            "местоположение": location_info.get("name", "Неизвестно"),
            "държава": location_info.get("country", "Неизвестно"),
            "текуща_температура": current_info.get("temp_c", "N/A"),
            "текущо_състояние": current_info.get("condition", {}).get("text", "Неизвестно"),
            "видео_анализ": video_analysis_text,
            "анализ_на_времето": trend_analysis.get("анализ", "Няма наличен анализ"),
            "влияние_върху_хората": trend_analysis.get("влияние", "Няма информация за влиянието"),
            "слънчев_ден": trend_analysis.get("слънчев_ден", "Няма информация")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неочаквана грешка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Неочаквана грешка: {str(e)}")

@app.get("/health")
async def health():
    """Проверка на състоянието на API"""
    return {"status": "healthy", "version": "1.0.0", "model": ANTHROPIC_MODEL}

# Добавяме конфигурация за стартиране на приложението
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
