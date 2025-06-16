# syntax=docker/dockerfile:1
FROM python:3.13.5-alpine3.22

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY PygBrother ./PygBrother
COPY README.md .

# Entrypoint
# Use docker-compose or docker run --env-file to provide environment variables
CMD ["python", "-m", "PygBrother.main"]
