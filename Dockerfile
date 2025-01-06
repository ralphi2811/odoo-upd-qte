FROM python:3.9-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY api.py .
COPY .env.example .

# Exposition du port
EXPOSE 9999

# Commande de démarrage
CMD ["python", "api.py"]
