FROM python:3.12-slim

# libspatialindex for rtree (osmnx spatial queries) is wheel-bundled; gdal
# not needed since pyogrio ships wheels. Keep the image lean.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static

# Public/demo mode by default in the container: one preloaded, frozen
# city graph (cached under /app/cache -- mount a volume to persist it).
ENV PRELOAD_GRAPH=true
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
