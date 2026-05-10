# FROM python:3.12-slim
# ENV PYTHONUNBUFFERED=1
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# COPY ../../shared /app/shared
# CMD ["python", "-m", "app.simulator"]




FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/simulator/app ./app
COPY shared ./shared
CMD ["python", "-m", "app.simulator"]