# BASE
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip install uv
WORKDIR /app
COPY pyproject.toml README.md ./

# DEVELOPMENT
FROM base AS development
RUN uv pip install --system -e .[dev,plugins-all]
COPY . .
CMD ["python", "-O", "-m", "bot", "--dev"]

# PRODUCTION
FROM base AS production
RUN uv pip install --system .[plugins-all]
COPY . .
RUN useradd --create-home --shell /bin/bash bot
USER bot
CMD ["python", "-O", "-m", "bot"]