FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the default port (Change to 7860 if deploying to Hugging Face)
EXPOSE 8000

# Run the Uvicorn server, binding to the dynamic PORT environment variable if provided by the host
CMD ["sh", "-c", "uvicorn main_app:app --host 0.0.0.0 --port ${PORT:-8000}"]