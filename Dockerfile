FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create directory for database (will be mounted as volume in production)
RUN mkdir -p /app/data

# Set environment variable for database path
ENV DATABASE_PATH=/app/data/follower_data.db

# Run the bot
CMD ["python", "bot.py"]
