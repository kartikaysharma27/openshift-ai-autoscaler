FROM registry.access.redhat.com/ubi9/python-311

# Set working directory
WORKDIR /app

# Copy source code and requirements
COPY ai_nodescaler.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Add readiness/liveness probe file
RUN echo "healthy" > /tmp/healthy

# Expose metrics port (optional: recommended for Prometheus)
EXPOSE 8000

# Run the autoscaler
CMD ["python", "ai_nodescaler.py"]