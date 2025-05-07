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
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY не е наличен")
            # Извличаме текущата температура от прогнозните данни
            current_temp = forecast_data.get("current", {}).get("temp_c", "N/A")
            return {
                "анализ": f"[!] AI анализът временно недостъпен (липсва API ключ). Базовите данни показват температура от {current_temp}°C в Обзор.",
                "влияние": "[!] Поради липса на AI анализ, препоръчваме да следите метеорологичните условия от стандартната прогноза.",
                "слънчев_ден": "[!] AI оценката за 'слънчев ден' не е налична поради липсващ API ключ.",
                "статус": "error",
                "error_details": "Липсва ANTHROPIC_API_KEY"
            }

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
        # Гарантираме, че всички параметри са низове
        video_analysis_text_safe = video_analysis_text if video_analysis_text is not None else ""
        historical_text_safe = historical_text if historical_text is not None else ""
        forecast_text_safe = forecast_text if forecast_text is not None else ""

        prompt = f"""
        Задача: Ти си професионален метеоролог, който представя времето за Обзор (древния Хелиополис) с балансирана комбинация от точност и топлота. Говориш уверено и информативно, с елегантни препратки към историята на града.

Текущ кадър от Обзор: {video_analysis_text_safe}

Исторически данни (вчера): {historical_text_safe}

Прогнозни данни (днес и утре): {forecast_text_safe}

Моля, представи кратък и точен анализ в три части (всяка до 2-3 изречения):

1. Текущо време:
- Опиши основните характеристики: температура, облачност, морски условия
- Сравни с вчерашния ден, отбележи значими промени
- Избягвай прекалено поетични описания

2. Влияние върху хората:
- Как времето влияе на ежедневните дейности
- Кратък, практичен съвет за деня
- Фокусирай се върху полезна информация

3. Оценка на "слънчевия ден":
- Кратка оценка дали денят е "слънчев" според дефиницията
- Елегантна препратка към историята на Хелиополис
- Без излишна драматизация

Важни изисквания:
• Поддържай професионален, но достъпен тон
• Избягвай прекалена емоционалност или "сладникави" описания
• Фокусирай се върху точност и полезност
• Включвай само релевантни детайли
• Пази баланс между информативност и достъпност

Отговорът трябва да е на български език, стегнат и професионален, без излишни украшения или преиграване.
        """
        
        # Логваме prompt-а преди изпращане
        logger.info(f"Изпращане на prompt към Anthropic API: {repr(prompt)}")

        payload = {
            "model": ANTHROPIC_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.2
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
                error_msg = f"Технически проблем с AI анализа (код: {response.status_code})"
                return {
                    "анализ": f"[!] {error_msg}. В момента в древния Град на Слънцето времето е приятно за разходки, но нашите системи временно не могат да предоставят детайлен анализ.",
                    "влияние": "[!] Поради техническа поддръжка на AI системите, моля проверете прогнозата от други източници. Междувременно можете да се насладите на морския бриз.",
                    "слънчев_ден": "[!] Временно недостъпна информация поради технически проблем с AI анализа.",
                    "статус": "error",
                    "error_details": error_msg
                }
            
            result = response.json()
            logger.info(f"Пълен отговор от Anthropic API: {result}")
            
            # Извличане на съдържанието от отговора на Anthropic
            content = result.get("content", [])
            if not content:
                logger.error("Няма съдържание в отговора от Anthropic")
                raise Exception("Празен отговор от AI модела")
                
            generated_text = content[0].get("text", "")
            logger.info(f"Извлечен текст от отговора: {generated_text}")
            
            # Разделяне и обработка на отговора
            try:
                # Разделяме текста на параграфи
                paragraphs = [p.strip() for p in generated_text.split('\n\n') if p.strip()]
                logger.info(f"Разделени параграфи: {paragraphs}")
                
                # Търсим съответните секции по ключови думи
                analysis = ""
                influence = ""
                sunny_day = ""
                
                for p in paragraphs:
                    p_lower = p.lower()
                    # Премахваме номерация и маркери
                    p = p.replace("1.", "").replace("2.", "").replace("3.", "").strip()
                    p = p.replace("1)", "").replace("2)", "").replace("3)", "").strip()
                    
                    if not analysis and ("време" in p_lower or "небе" in p_lower or "температура" in p_lower):
                        analysis = p
                    elif not influence and ("влияние" in p_lower or "усещане" in p_lower or "настроение" in p_lower):
                        influence = p
                    elif not sunny_day and ("слънчев" in p_lower or "хелиополис" in p_lower):
                        sunny_day = p
                
                # Ако не сме намерили някоя секция, вземаме параграфите подред
                if not analysis and paragraphs:
                    analysis = paragraphs[0]
                if not influence and len(paragraphs) > 1:
                    influence = paragraphs[1]
                if not sunny_day and len(paragraphs) > 2:
                    sunny_day = paragraphs[2]
                
                # Ако все още нямаме някоя секция, използваме подходящо съобщение
                if not analysis:
                    analysis = "Времето в момента е приятно за разходка из древния Град на Слънцето."
                if not influence:
                    influence = "Условията предразполагат към приятни разходки и активности на открито."
                if not sunny_day:
                    sunny_day = "Денят носи типичното за Хелиополис слънчево настроение."
                
                logger.info(f"Обработен отговор: Анализ: {analysis}, Влияние: {influence}, Слънчев ден: {sunny_day}")
                
            except Exception as e:
                logger.error(f"Грешка при обработка на отговора: {str(e)}")
                analysis = "В момента в древния Град на Слънцето времето е приятно, с лек морски бриз и променлива облачност."
                influence = "Атмосферата предразполага към спокойни разходки покрай морето, където шумът на вълните създава усещане за безметежност."
                sunny_day = "Въпреки променливата облачност, Хелиополис не губи своя слънчев характер, напомняйки ни за древната си история като Град на Слънцето."
            
            return {
                "анализ": analysis,
                "влияние": influence,
                "слънчев_ден": sunny_day
            }
    except Exception as e:
        logger.error(f"Грешка при анализ на тренда: {str(e)}")
        error_msg = f"Системна грешка: {str(e)}"
        return {
            "анализ": f"[!] {error_msg}. Базовите ни системи показват типично крайморско време в Хелиополис.",
            "влияние": "[!] Поради технически проблем не можем да предоставим детайлен анализ. Моля, проверете други източници.",
            "слънчев_ден": "[!] Временно недостъпна информация поради системна грешка.",
            "статус": "error",
            "error_details": error_msg
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
