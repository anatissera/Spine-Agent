FROM python:3.11-slim

WORKDIR /app

# System dependencies for psycopg (binary wheels) and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package in editable mode so module imports work
RUN pip install --no-cache-dir -e .

# Streamlit config
EXPOSE 8501

# Railway sets PORT env var — Streamlit needs explicit --server.port
CMD streamlit run interfaces/dashboard/app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true
