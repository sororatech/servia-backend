FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev libxml2-dev libxslt-dev libzip-dev \
    libmagic1 poppler-utils tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health/ || exit 1

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
