# Use Python 3.10.12 as the base image
FROM python:3.10.12-slim

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your Flask app runs on (default is 5000)
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
