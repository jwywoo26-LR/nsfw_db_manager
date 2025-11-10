# Frontend Dockerfile for NSFW Image Asset Manager (Gradio)
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gradio_app.py .
COPY src/ ./src/

# Expose port
EXPOSE 7860

# Run the application
CMD ["python", "gradio_app.py"]
