# FROM python:3.12-slim
# ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# WORKDIR /app
# RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
# COPY requirements.txt requirements-dev.txt ./
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# COPY ../../shared /app/shared
# EXPOSE 8000
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]



FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/api-gateway/requirements.txt services/api-gateway/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY services/api-gateway/app ./app
COPY shared ./shared
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]