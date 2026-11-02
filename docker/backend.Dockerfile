FROM python:3.12-slim
WORKDIR /app
COPY requirements/backend.txt requirements/backend.txt
RUN pip install --no-cache-dir -r requirements/backend.txt
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini .
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]