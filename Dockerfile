FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory if it doesn't exist
RUN mkdir -p uploads

# Command to run the application - use Flask app directly as WSGI entry point
CMD gunicorn api:app --bind 0.0.0.0:$PORT
