FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y python3-tk && apt-get clean

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
