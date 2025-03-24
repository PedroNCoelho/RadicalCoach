FROM python:3.12
RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 net-tools iputils-ping vim -y
COPY . /app
EXPOSE 2564
CMD ["python3", "/app/main.py"]
