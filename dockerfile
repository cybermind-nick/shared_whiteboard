FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

COPY server.py .
# COPY try_redis.py . # for testing

RUN apt-get update && apt-get install -y python3-tk && apt-get clean

RUN pip install --no-cache-dir -r requirements.txt

# CMD ["python", "server.py"] # command specified in compose
