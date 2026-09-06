FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils postgresql-client \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY engine/ engine/
COPY api/ api/
RUN pip install --no-cache-dir ./engine ./api
WORKDIR /srv/api
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
