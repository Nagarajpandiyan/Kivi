FROM python:3.12-slim

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY database ../database
COPY frontend ../frontend
COPY evaluation ../evaluation
COPY data ../data

ENV PYTHONPATH=/app/backend
ENV KIVI_DB_PATH=/app/data/kivi.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
