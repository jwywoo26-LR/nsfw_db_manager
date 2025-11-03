# Backend Dockerfile for NSFW Image Asset Manager
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_server.py .

# Create uploads directory
RUN mkdir -p uploads/images

# Expose port
EXPOSE 8001

# Run the application
CMD ["python", "run_server.py"]
