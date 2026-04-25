FROM node:20-alpine AS ui
WORKDIR /build
COPY admin-ui ./admin-ui
WORKDIR /build/admin-ui
RUN npm install && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY --from=ui /build/app/static/admin ./app/static/admin
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
