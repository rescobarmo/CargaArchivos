FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p backend/uploads/imagen backend/uploads/texto backend/uploads/xls backend/uploads/thumbnails data

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn run:app --host 0.0.0.0 --port ${PORT}"]
