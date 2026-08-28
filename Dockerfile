FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment configuration
ENV PORT=5000
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Run database setup & start gunicorn
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 run:app"]
