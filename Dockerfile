# Multi-stage production-ready Dockerfile
FROM python:3.12-slim AS builder

# Set work directory
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies (ffmpeg is CRITICAL for yt-dlp operations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and source code
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Set environment paths and variables
ENV PATH="/opt/venv/bin:$PATH"
ENV FLASK_APP=app.py
ENV PORT=5000

# Create download folder on disk
RUN mkdir -p /app/downloads && chmod 777 /app/downloads

# Expose container port
EXPOSE 5000

# Start server using gunicorn if installed, fallback to flask run
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
