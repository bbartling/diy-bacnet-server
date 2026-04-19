# ---- Base image ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    net-tools \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install from pyproject.toml (unpinned deps; resolve at image build time).
# Include [test] extra so `python3 -m pytest tests/` works in-container.
COPY . /app
RUN pip install --no-cache-dir ".[test]"
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 47808/udp
EXPOSE 8080/tcp

ENTRYPOINT ["/docker-entrypoint.sh"]