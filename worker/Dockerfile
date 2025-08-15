FROM python:3.11-slim
WORKDIR /worker
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Use unbuffered Python output so logs appear immediately
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "worker.py"]