FROM python:3.9-slim-buster

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
COPY . /app

CMD ["python", "main.py"]
