FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Hugging Face Spaces default port
EXPOSE 7860

# Start FastAPI - PORT env var is set by Spaces to 7860
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
