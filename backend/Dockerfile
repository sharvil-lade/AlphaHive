FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --user so the whole dependency tree lands in one directory the runner can copy.
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

# curl is not incidental: the compose healthcheck shells out to it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --system --uid 1001 alphahive

COPY --from=builder /root/.local /usr/local
COPY . /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER alphahive
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
