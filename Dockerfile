# ══════════════════════════════════════════════
# Audiobook Maker — Docker Image
# Silero TTS v5 + Gradio + ffmpeg (MP3)
# ══════════════════════════════════════════════

FROM python:3.11-slim AS base

# Метаданные
LABEL maintainer="audiobook-maker"
LABEL description="Russian TTS audiobook generator with Silero v5"

# Системные зависимости: ffmpeg для MP3/OGG экспорта
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Устанавливаем CPU-only PyTorch (экономим ~1.5 GB vs полный torch)
RUN pip install --no-cache-dir \
    "torch>=2.0,<3.0" --index-url https://download.pytorch.org/whl/cpu

# Устанавливаем остальные зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY config.py .
COPY tts_model.py .
COPY text_processing.py .
COPY converters.py .
COPY synthesizer.py .
COPY ui.py .
COPY app.py .

# Создаём директории
RUN mkdir -p /app/output /app/model

# Переменные окружения
ENV MODEL_DIR=/app/model
ENV TTS_THREADS=4
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Скачиваем модель при сборке (кешируется в слое)
RUN python -c "\
import torch; \
torch.hub.download_url_to_file( \
    'https://models.silero.ai/models/tts/ru/v5_ru.pt', \
    '/app/model/v5_ru.pt' \
); \
print('✅ Модель скачана')"

# Том для выходных файлов
VOLUME ["/app/output"]

# Порт Gradio
EXPOSE 7860

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

# Запуск
CMD ["python", "app.py"]
