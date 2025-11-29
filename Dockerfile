# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first for better Docker layer caching
# This way, dependencies only reinstall if requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY main_optimized.py .

# Expose port 8000 (standard for FastAPI/uvicorn)
EXPOSE 8000

# Health check - verifies container is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/', timeout=5)"

# Run the application
# Using --host 0.0.0.0 makes it accessible outside the container
# --port 8000 is standard, but cloud platforms often override with $PORT
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]