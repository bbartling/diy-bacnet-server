# ---- Base image ----
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    net-tools \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install from pyproject.toml (unpinned deps; resolve at image build time).
COPY . /app
RUN pip install --no-cache-dir .
EXPOSE 47808/udp
EXPOSE 5000

CMD ["python3", "-u", "-m", "bacpypes_server.main", "--name", "BensServer", "--instance", "123456", "--public"]