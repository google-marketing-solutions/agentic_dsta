# Use a slim base image to reduce the attack surface
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt /app/
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos "" myuser

COPY . /app/
# Set ownership of the application files to the non-root user
RUN chown -R myuser:myuser /app && chmod +x main.py

# Switch to the non-root user
USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"
ENV GOOGLE_CLOUD_LOCATION="us-central1"
ENV GOOGLE_GENAI_USE_VERTEXAI="True"


CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]