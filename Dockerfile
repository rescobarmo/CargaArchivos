FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias primero (mejor cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Crear directorios necesarios
RUN mkdir -p backend/uploads/imagen backend/uploads/texto backend/uploads/xls backend/uploads/thumbnails data

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "cd /app/backend && uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
