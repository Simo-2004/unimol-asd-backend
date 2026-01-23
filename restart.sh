#!/bin/bash
# Script per riavviare il progetto con migrazioni

echo "🔄 Fermando container..."
docker compose down

echo "🏗️  Ricostruendo immagini..."
docker compose build

echo "🚀 Avviando container..."
docker compose up -d

echo "⏳ Attendendo che il database sia pronto..."
sleep 5

echo "📊 Applicando migrazioni..."
docker compose exec backend python manage.py migrate

echo "✅ Progetto avviato!"
echo "🌐 Backend: http://localhost:8000/api/"
echo "🌐 Frontend: http://localhost:3000"
echo "🛠️  Admin: http://localhost:8000/admin/"
