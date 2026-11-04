FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /usr/sbin/nologin nexawork \
    && chown -R nexawork:nexawork /app

USER nexawork

EXPOSE 8000

ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; host = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')[0].strip(); url = f\"http://127.0.0.1:{os.getenv('PORT', '8000')}/ready\"; urllib.request.urlopen(urllib.request.Request(url, headers={'Host': host}), timeout=4)"]

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
