FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# App deps (shared with the FastAPI service) + Temporal SDK.
COPY requirements.txt ./requirements.txt
COPY subs_temporal/requirements.txt ./subs_temporal-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r subs_temporal-requirements.txt

COPY . .

CMD ["python", "-m", "subs_temporal.worker"]