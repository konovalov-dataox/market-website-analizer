FROM python:3.9

RUN apt-get update

RUN pip install --upgrade pip

RUN mkdir app

WORKDIR /app

COPY . /app

ENV PYTHONPATH /app

RUN pip install -r api/requirements.txt
