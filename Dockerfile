FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для PDF и графиков
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
