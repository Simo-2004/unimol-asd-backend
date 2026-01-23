FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Installa dipendenze di sistema (gcc e libpq-dev servono per il driver postgres)
RUN apt-get update && apt-get install -y gcc python3-dev libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice (assicurati di avere un .dockerignore per escludere venv e __pycache__)
COPY . /app/

# Aspettiamo che il DB sia pronto ed eseguiamo le migrazioni all'avvio
# Nota: "sh -c" è corretto per eseguire comandi multipli
CMD sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"