FROM registry.access.redhat.com/ubi9/python-311
WORKDIR /app
COPY ai_nodescaler.py /app
COPY requirements.txt /app
RUN microdnf update -y && microdnf clean all && pip install --no-cache-dir -r requirements.txt
CMD ["python", "ai_nodescaler.py"]