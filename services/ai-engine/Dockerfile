# FROM python:3.12-slim
# ENV PYTHONUNBUFFERED=1
# WORKDIR /app
# RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# COPY ../../shared /app/shared
# EXPOSE 8002
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]


FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/ai-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/ai-engine/app ./app
COPY shared ./shared
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]