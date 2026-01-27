# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for building some python packages if needed)
# libpq-dev is needed for logging postgres driver sometimes, though we use binary check pyproject
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
# If you have requirements.txt, checking... Pyproject used.
# We need to install dependencies from pyproject.toml
# Installing uv or poetry or build tools might be needed. 
# Simplest is just pip install .
# But let's check if there is a requirements.txt or we should generte one.

# Let's generate requirements.txt first for stability in docker build if not using poetry/uv
RUN pip install --upgrade pip

COPY . .

# Install the application and dependencies
# Assuming pyproject.toml is valid compliant
RUN pip install .

# Install uvicorn explicitly if not picked up (it is in dependencies)
# RUN pip install uvicorn

# Expose port
EXPOSE 8000

# Command to run
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
