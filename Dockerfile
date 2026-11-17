# syntax=docker/dockerfile:1
# Built in the cloud with `az acr build` (see scripts/deploy.ps1); no local Docker needed.

FROM node:22-alpine AS ui
WORKDIR /ui
COPY src/ui/package.json src/ui/package-lock.json ./
RUN npm ci
COPY src/ui/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code, the packaged corpus (read-only install directory) and config.
COPY src/knowledge_enrichment ./src/knowledge_enrichment
COPY data ./data
COPY config ./config
COPY --from=ui /ui/dist ./ui-dist

RUN useradd --create-home --uid 10001 app \
 && mkdir -p /app/runtime && chown app /app/runtime \
 && chmod -R a-w /app/data /app/config
USER app

EXPOSE 8000
CMD ["uvicorn", "knowledge_enrichment.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
