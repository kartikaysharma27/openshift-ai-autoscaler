FROM python:3.11.8-slim
WORKDIR /app
COPY ai_nodescaler.py /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "ai_nodescaler.py"]