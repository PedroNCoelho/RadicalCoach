FROM python:3.12
WORKDIR .
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y
COPY . .
EXPOSE 5000
CMD ["python3", "main.py"]
