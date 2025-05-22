# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only necessary requirement files
COPY requirements*.txt ./
# Use the primary requirements file for wheel building
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim as production

WORKDIR /app

ARG APP_USER_ID=1000
ARG APP_GROUP_ID=1000

# Create group and non-root user with specified IDs
RUN groupadd -g ${APP_GROUP_ID} appgroup && \
    useradd -m -u ${APP_USER_ID} -g appgroup appuser

# Install runtime dependencies (ensure only necessary ones are included)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    # Add other runtime-specific system dependencies if needed
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
# Copy the primary requirements file for verification or other tools if needed
COPY --from=builder /app/requirements.txt .

# Install Python packages from wheels
# Consider adding --prefer-binary for potentially faster installs
RUN pip install --no-cache-dir /wheels/*
# Explicitly install Gunicorn/Uvicorn here if not in requirements.txt
# RUN pip install --no-cache-dir gunicorn uvicorn 

# Copy application code as the appuser
# Ensure .dockerignore is properly configured to exclude unnecessary files
COPY --chown=appuser:appgroup . .

# Set permissions for potentially created directories after code copy
# RUN chown -R appuser:appgroup /app 
# Create necessary directories if not copied, and set ownership
RUN mkdir -p logs media && chown -R appuser:appgroup logs media

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Add other runtime environment variables
    PYTHONPATH=/app

# Run the application using Gunicorn
# Use environment variables for host/port/workers if possible
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "app.main:app"] 