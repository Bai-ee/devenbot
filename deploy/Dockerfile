FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Make the main script executable
RUN chmod +x grok_bot.py

# Create non-root user for security
RUN groupadd -r grokbot && useradd -r -g grokbot grokbot
RUN chown -R grokbot:grokbot /app
USER grokbot

# Health check endpoint (simple)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "grok_bot.py", "--daemon"]

# Expose port for webhook if needed
EXPOSE 8080 