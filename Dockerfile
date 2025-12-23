FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
# Les dépendances système sont déjà installées manuellement ci-dessus
# Ignorer les erreurs de playwright install-deps (certains packages peuvent être obsolètes)
RUN playwright install-deps chromium || true

COPY psm.py .
COPY Site/ ./Site/

# Optionnel : Copier firebase-credentials.json si présent (pour méthode fichier)
# ⚠️ NE PAS commiter ce fichier sur GitHub !
# COPY firebase-credentials.json /app/firebase-credentials.json || true

ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

EXPOSE 8081 5000

CMD ["python", "-u", "psm.py"]
