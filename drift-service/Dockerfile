FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY consumer.py .
COPY drift.py .
COPY metrics.py .
COPY db.py .
COPY main.py .

# Expose metrics port
EXPOSE 8000

# Run the service
CMD ["python3", "main.py"]