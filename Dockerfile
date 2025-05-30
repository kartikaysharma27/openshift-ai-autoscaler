FROM registry.access.redhat.com/ubi8/python-311

WORKDIR /app

COPY ai_scaler.py /app/ai_scaler.py
COPY requirements.txt /app/requirements.txt

# Use dnf to install packages, upgrade pip/setuptools, install python deps, then clean up
RUN dnf -y update && \
dnf -y install gcc libffi-devel openssl-devel curl && \
pip install --no-cache-dir --upgrade pip setuptools && \
pip install --no-cache-dir -r /app/requirements.txt && \
dnf -y remove gcc && \
dnf clean all && \
rm -rf /var/cache/dnf

CMD ["python", "/app/ai_scaler.py"]