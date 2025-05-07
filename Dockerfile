# Използваме официалния образ на Python
FROM python:3.9-slim

# Работна директория в контейнера
WORKDIR /app

# Копираме само файла с изискванията първо, за да използваме кеширането на слоевете
COPY requirements.txt .

# Инсталираме зависимостите
RUN pip install --no-cache-dir -r requirements.txt

# Копираме останалите файлове на приложението
COPY . .

# Излагаме порта, който ще използваме - Hugging Face Spaces използва порт 7860
EXPOSE 7860

# Стартираме FastAPI приложението
# Hugging Face Spaces ще автоматично предаде променливите на средата от секретите
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]