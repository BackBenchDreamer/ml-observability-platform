# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY generator.py .

# Set environment variables with defaults
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    ENABLE_DRIFT=false \
    EVENT_INTERVAL=1.0 \
    STREAM_NAME=ml-events

# Make script executable
RUN chmod +x generator.py

# Run the generator
CMD ["python3", "-u", "generator.py"]