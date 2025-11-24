# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y --no-install-recommends \
#  && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# Consider a .dockerignore file to exclude unnecessary files
COPY ./src ./src
COPY ./main.py ./

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for the port
ENV PORT 8080
ENV FLASK_APP main.py
# Optional: Set FLASK_ENV to production in real deployments
# ENV FLASK_ENV production

# Run main.py when the container launches
# Using Gunicorn is recommended for production
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2"]
# For development:
# CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
