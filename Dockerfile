# Multi-stage build to reduce image size
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage - minimal runtime image
FROM python:3.10-slim

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set working directory
WORKDIR /app

# Copy only necessary application files
COPY generate_batch_videos.py .
COPY config.py .
COPY thirukural_git.json .
COPY assets/ ./assets/

# Create necessary directories (will be created at runtime if needed)
RUN mkdir -p dist data/audio_generated temp logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
# Prevent downloading models during build
ENV TRANSFORMERS_OFFLINE=0
# Use CPU for PyTorch (smaller image)
ENV TORCH_CUDA_ARCH_LIST=""

# Run the script
CMD ["python3", "generate_batch_videos.py"]
