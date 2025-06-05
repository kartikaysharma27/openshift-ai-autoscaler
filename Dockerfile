FROM registry.access.redhat.com/ubi9/python-311

# Set working directory
WORKDIR /app

# Copy source and requirements
COPY ai_nodescaler.py requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Run the app
CMD ["python", "ai_nodescaler.py"]