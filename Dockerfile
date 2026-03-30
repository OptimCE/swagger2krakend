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

# ---- Test Generation Stage ----
FROM base AS test-generator
RUN mkdir -p test/output
# Generate the output config from the samples
RUN python3 app.py "test/samples/orders.yaml,test/samples/root.yaml,test/samples/users.yaml" -o test/output/krakend-output.json
# Generate the output config from the single sample
RUN python3 app.py "test/samples/orders.yaml" -o test/output/krakend-output-single.json
#Generate the output config from the single sample with root service name
RUN python3 app.py "test/samples/root.yaml" -o test/output/krakend-output-root.json

# ---- Test Execution Stage ----
FROM devopsfaith/krakend:latest AS test
# Copy the generated configuration from the generator stage
COPY --from=test-generator /app/test/output/krakend-output.json krakend-output.json
COPY --from=test-generator /app/test/output/krakend-output-single.json krakend-output-single.json
COPY --from=test-generator /app/test/output/krakend-output-root.json krakend-output-root.json

# Run the KrakenD check commands on all generated configurations
CMD ["/bin/sh", "-c", "krakend check -tnc krakend-output.json && krakend check -tnc krakend-output-single.json && krakend check -tnc krakend-output-root.json"]
