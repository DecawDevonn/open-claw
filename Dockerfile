# Use the official Python image from the Docker Hub
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app.py .

# Expose the port
EXPOSE 8080

# Run the application with health checks
CMD ["python", "app.py"]