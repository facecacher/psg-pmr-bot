FROM python:3.11-slim

WORKDIR /app

# Copier tous les fichiers du site (HTML, CSS, JS, etc.)
# Utiliser COPY . . pour copier tout le contenu du dossier Site
COPY . .

# Exposer le port 8080
EXPOSE 8080

# Lancer un serveur HTTP simple (http.server est inclus dans Python)
CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0"]

