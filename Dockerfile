FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application files
COPY . .

# Create knowledge directory if it doesn't exist
RUN mkdir -p knowledge

# Build embeddings if knowledge files exist
RUN if [ -n "$(find knowledge -name '*.md' 2>/dev/null)" ]; then \
        echo "Building embeddings..."; \
        python build.py; \
    else \
        echo "No knowledge files, creating empty embeddings"; \
        echo "[]" > embeddings.json; \
    fi

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start application
CMD ["python", "app.py"]
