FROM registry.access.redhat.com/ubi8/python-311

# Set working directory
WORKDIR /app

# Copy application files
COPY ai_scaler.py requirements.txt /app/

# Install dependencies and clean up
RUN dnf -y update && \
    dnf -y install gcc libffi-devel openssl-devel curl && \
    pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    dnf -y remove gcc && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Set default command
CMD ["python", "ai_scaler.py"]