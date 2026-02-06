# Use official Python image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Upgrade pip early for security fixes
RUN pip install --upgrade pip

# Copy dependency metadata first for better layer caching
COPY pyproject.toml README.md ./

# Copy the rest of the source
COPY . .

# Install the application and dependencies
RUN pip install --no-cache-dir .

# Create non-root user and drop privileges
RUN addgroup --system app && adduser --system --ingroup app appuser \
	&& chown -R appuser:app /app
USER appuser

# Expose port
EXPOSE 8000

# Command to run
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
