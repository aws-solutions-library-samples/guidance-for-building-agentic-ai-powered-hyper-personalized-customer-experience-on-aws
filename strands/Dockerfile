FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY cli.py .
COPY run_catalog_load.py .
COPY agents/ ./agents/
COPY config/ ./config/
COPY models/ ./models/
COPY services/ ./services/
COPY utils/ ./utils/
COPY data/product_catalog.json ./data/
COPY data/customer_profiles.json ./data/
COPY .env .

# Create a non-root user to run the application
RUN useradd -m appuser
USER appuser

# Expose the port the app runs on
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/ || exit 1

# Command to run the application with Uvicorn
# - port: 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
