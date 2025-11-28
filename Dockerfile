FROM python:3.10-slim

# Install system dependencies
# - tesseract-ocr: For image text extraction
# - ffmpeg: For audio processing
# - Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates curl unzip \
    tesseract-ocr \
    ffmpeg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
    libgtk-3-0 libgbm1 libasound2 libxcomposite1 libxdamage1 libxrandr2 \
    libxfixes3 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Expose port (Render sets PORT env var, but good to document)
EXPOSE 8000

# Start command
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
