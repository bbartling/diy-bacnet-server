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
# Production default is runtime-only (`.`). Test deps are opt-in via BUILD_TESTS=true (`.[test]`).
# Note: `.[test]` is intentionally the minimal container test set used by stack-maintenance flows
# (for example Open-FDD AFDD `bootstrap.sh --diy-bacnet-tests`); it is not required for normal runtime use.
ARG BUILD_TESTS=false
COPY . /app
RUN if [ "$BUILD_TESTS" = "true" ]; then \
      pip install --no-cache-dir ".[test]"; \
    else \
      pip install --no-cache-dir "."; \
    fi
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 47808/udp
EXPOSE 8080/tcp

ENTRYPOINT ["/docker-entrypoint.sh"]