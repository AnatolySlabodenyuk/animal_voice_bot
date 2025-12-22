FROM python:3.12-slim-bullseye

WORKDIR /app

COPY src /app
COPY requirements.txt /

RUN pip install -r /requirements.txt



RUN sed -i 's/\r$//' /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]