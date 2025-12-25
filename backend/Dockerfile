# IDO Backend - Hugging Face Spaces Deployment
# FastAPI + ML Models (spaCy, etc.)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Create storage directory for temp files
RUN mkdir -p /app/storage

# Expose port (HF Spaces expects 7860)
EXPOSE 7860

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
# HF Spaces requires port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
