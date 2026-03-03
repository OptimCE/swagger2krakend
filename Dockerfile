FROM python:3-alpine
# Install envsubst for environment variable substitution in configuration files
RUN apk --no-cache add gettext
# Install any additional Python dependencies if needed (e.g., for configuration generation)
# Based on the requirements.txt file of the application.
COPY requirements.txt .
RUN pip3 install -r requirements.txt
# Set working directory
WORKDIR /app
# Copy the application code
COPY . .
# Make the configuration generator script executable
RUN chmod +x app.py
# Generate the configuration file using environment variables
CMD python3 -u app.py