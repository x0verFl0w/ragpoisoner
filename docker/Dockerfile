FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/data/chroma_db", "/app/results"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
