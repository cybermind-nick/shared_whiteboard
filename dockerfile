FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

COPY server.py .

# for testing
# COPY try_redis.py .

# RUN apt-get update && apt-get install -y python3-tk && apt-get clean

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

# command specified in compose
# CMD ["python", "server.py"]
