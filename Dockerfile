# Multi-stage / optimized slim build for Render, Railway, or any Cloud container service
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and configure numerical thread limits
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PORT=8000

WORKDIR /app

# Install system build dependencies and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only wheel first (lightweight, under 180MB instead of 2GB CUDA bundle)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code, models, database, and frontends
COPY . .

# Expose container port
EXPOSE 8000

# Start server respecting dynamic PORT assigned by cloud provider
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
