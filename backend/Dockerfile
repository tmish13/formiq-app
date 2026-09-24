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
    libmagic1 \
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

# --- Bake the MediaPipe complexity-2 ("heavy") pose model into the image ---
# MediaPipe ships the complexity 0/1 models but DOWNLOADS pose_landmark_heavy.tflite
# on first use, into its own (root-owned) site-packages directory. Because the
# runtime user below is non-root appuser, that download failed at runtime with
# "[Errno 13] Permission denied" and AIService silently fell back to
# model_complexity=1 (app/services/ai_service.py:100-104) — despite
# AI_MODEL_COMPLEXITY defaulting to 2 (app/core/config.py:768-770).
#
# That is a train/serve skew: PostureV1 was evaluated on complexity-2 keypoints
# (scripts/output/posture_v1_labels_and_results.csv records complexity=2, and
# scripts/e2e_posture_v1_smoke.py:372 asserts model_complexity == 2) but was
# being served complexity-1 keypoints. Measured on one fixture video, that moved
# prob_fault from 0.0001 to 0.4739 against a 0.525 threshold.
#
# Constructing Pose(model_complexity=2) here, as root and with build-time network,
# triggers the download once and bakes it in world-readable. The `test -f` makes
# the build FAIL LOUDLY rather than silently shipping an image that will fall back.
RUN python -c "import mediapipe as mp; p = mp.solutions.pose.Pose(model_complexity=2); p.close()" \
    && test -f /usr/local/lib/python3.11/site-packages/mediapipe/modules/pose_landmark/pose_landmark_heavy.tflite \
    && chmod -R a+rX /usr/local/lib/python3.11/site-packages/mediapipe/modules

# Copy application code as the appuser
# Ensure .dockerignore is properly configured to exclude unnecessary files
COPY --chown=appuser:appgroup . .
RUN chmod +x /app/deployment/entrypoint.sh

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
# The API starts through deployment/entrypoint.sh: alembic upgrade head, then gunicorn (G-23).
# The gunicorn flags live in that script; worker and beat override the command in compose.
CMD ["/app/deployment/entrypoint.sh"]
