FROM python:3.11-slim

# Installer Chrome et dépendances
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium pour Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copier le script
COPY psm.py .

# Lancer le script
CMD ["python", "-u", "psm.py"]
