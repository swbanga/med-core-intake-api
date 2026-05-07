# -----------------------------------------
# STAGE 1: The Builder
# -----------------------------------------
FROM python:3.12.3-slim as builder

# Stop Python from generating .pyc files and force stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install system dependencies required for cryptography and asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy strictly the requirements to leverage Docker layer caching
COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------
# STAGE 2: The Production Matrix
# -----------------------------------------
FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY the runtime libraries required by asyncpg (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# SECURITY PROTOCOL: Create a non-root user
RUN addgroup --system medcoregroup && adduser --system --group medcoreuser

# Copy the application code
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY alembic.ini /app/

# Transfer ownership to the non-root user
RUN chown -R medcoreuser:medcoregroup /app

# Switch to the non-root user
USER medcoreuser

# Expose the standard cloud port
EXPOSE 8080

# The Ignition Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]