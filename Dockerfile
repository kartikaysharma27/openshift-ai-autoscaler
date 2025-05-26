FROM python:3.11-slim
WORKDIR /app
COPY ai_scaler.py /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "ai_scaler.py"]