FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour playwright, psycopg2, pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Playwright browsers (pour le scraping)
RUN playwright install chromium --with-deps

# Copie du code source
COPY src/ ./src/

# L'utilisateur non-root pour la prod
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000 8501
