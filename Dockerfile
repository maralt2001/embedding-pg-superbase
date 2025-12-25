# Stage 1: Builder - Install dependencies and create virtual environment
FROM python:3.11.14-slim-bookworm AS builder

# Install build dependencies for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PATH="/opt/venv/bin:$PATH" \
    WEB_PORT=8000

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application code (owned by root for security)
COPY --chown=root:root backend/ ./backend/
COPY --chown=root:root frontend/ ./frontend/
COPY --chown=root:root scripts/ ./scripts/
COPY --chown=root:root run.py requirements.txt ./

# Fix file permissions to ensure appuser can read all files
# Create uploads directory with write permissions for appuser
RUN chmod -R a+rX /app && \
    mkdir -p /app/uploads && \
    chown appuser:appuser /app/uploads

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check - verify the application is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/config', timeout=5)" || exit 1

# Run the application
CMD ["python", "run.py"]
