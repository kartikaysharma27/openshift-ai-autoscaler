FROM registry.access.redhat.com/ubi8/python-311

# Set working directory
WORKDIR /app

# Copy application files
COPY ai_nodescaler.py requirements.txt /app/

# Install dependencies and clean up
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt 
     
# Set default command
CMD ["python", "ai_nodescaler.py"]