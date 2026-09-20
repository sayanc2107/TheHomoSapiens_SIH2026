# Use official Python 3.11
FROM python:3.11-slim

# Install all Linux system libraries required by MediaPipe
RUN apt-get update && apt-get install -y \
    libgles2 \
    libgl1 \
    libglib2.0-0 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Run the server using Render's automatic PORT variable
CMD uvicorn main_app:app --host 0.0.0.0 --port $PORT