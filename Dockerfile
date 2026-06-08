FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Secrets (COMPOSIO_API_KEY, IMAP_PASSWORD, WALLET_API_TOKEN, etc.)
# are injected at runtime by Railway — never baked into the image.
# Do NOT use ARG or ENV for sensitive values here.

EXPOSE ${PORT:-8000}

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
