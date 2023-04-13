FROM python:3.9

RUN apt-get update

RUN pip install --upgrade pip

RUN apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir app

WORKDIR /app

COPY . /app

ENV PYTHONPATH /app

RUN pip install -r image_analyzer/requirements.txt
