# Production Dockerfile for swagger2krakend
# Builds a minimal production image for generating KrakenD configurations

# ---- Base Stage ----
FROM python:3-alpine AS base
COPY requirements.txt .
RUN pip3 install -r requirements.txt
WORKDIR /app
COPY . .
RUN chmod +x app.py

# ---- Release Stage (Default) ----
FROM base AS release
CMD ["python3", "-u", "app.py"]
