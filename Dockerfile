FROM python:3.8

WORKDIR /demo_app

COPY requirements.txt .

RUN pip install -Iv cmake==3.22.1
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install -r requirements.txt

COPY ./app ./app

CMD cd app && python ./main.py
