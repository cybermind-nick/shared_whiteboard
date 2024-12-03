FROM python:3.10

WORKDIR /server

COPY server.py requirements.txt server/

RUN python -m pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "./server.py"]